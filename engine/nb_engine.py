# -*- coding: utf-8 -*-
"""NeoBestiary Studio - moteur d'image moderne (FLUX.2 klein 4B / Z-Image Turbo, nœuds natifs de ComfyUI).

Le texte de l'utilisateur part tel quel (l'encodeur Qwen3 comprend le français) : pas de lexique, pas de
pondérations, pas de négatifs imposés. FLUX.2 klein sait aussi éditer à partir d'images de référence
(ReferenceLatent) : c'est ce qui fait tourner la créature et l'anime en gardant son design.
"""
import math
import uuid

from PIL import Image, ImageChops, ImageOps

import nb_archetypes
import nb_auto
import nb_comfy as nbc
import nb_core
import nb_guides

ENCODER = "qwen_3_4b.safetensors"
MODELS = {
    "klein": dict(unet="flux-2-klein-4b.safetensors", vae="flux2-vae.safetensors", clip_type="flux2", steps=4),
    "zimage": dict(unet="z_image_turbo_int8_convrot.safetensors", vae="ae.safetensors", clip_type="lumina2", steps=8),
}
SIZE = 1024
CUT_MODEL = "birefnet.safetensors"  # détourage (models/background_removal) : fond et ombre portée retirés

STYLE = ("Pixel art sprite of a single creature for a top-down RPG, seen from above at a three-quarter angle "
         "(camera tilted about 30 degrees down). Entire creature visible, centered, crisp pixels, clean dark outline, "
         "flat plain light gray background, no text, no scenery, no cast shadow on the ground.")

# Orientation stricte : les jeux à 4 directions veulent face / dos / profil francs, pas un corps tourné de biais.
FACING = {
    "bas": ("It faces straight toward the bottom of the screen, perfectly frontal and symmetrical: its body is aligned "
            "on the vertical axis of the image, not turned to the left or to the right at all."),
    "haut": ("Show this exact same creature seen exactly from behind: it walks straight up toward the top of the screen, "
             "perfectly symmetrical, its body aligned on the vertical axis, not turned to either side. We see its back "
             "and the back of its head; no face and no eyes are visible. The reference image is already flipped "
             "left-right as seen from behind: keep every limb, wing, weapon and held object on the same side of the "
             "image as in the reference."),
    "gauche": ("Turn this exact same creature a full 90 degrees so it faces exactly toward the left edge of the screen: "
               "a pure side profile, in exactly the same posture as in the reference image{posture}, its face pointing left, "
               "nothing of it turned toward the viewer."),
}
KEEP = (" Keep the identical design, colors, proportions and pixel art style, and the same top-down camera. "
        "Keep exactly the same body parts and the same number of {parts}: add nothing, remove nothing. "
        "Plain flat light gray background, no cast shadow.")
GUESSED_POSTURE = " (a four-legged creature stays on all fours, an upright one stays upright)"


# parties qu'on compte : le modèle retombe sur l'anatomie habituelle (une vache a 2 cornes) si on n'insiste pas
COUNTABLE = {"head": ("head", "heads"), "tail": ("tail", "tails"), "legs": ("leg", "legs"), "arms": ("arm", "arms"),
             "wings": ("wing", "wings"), "horns": ("horn", "horns"), "eyes": ("eye", "eyes"),
             "tentacles": ("tentacle", "tentacles"), "pincers": ("pincer", "pincers"), "ears": ("ear", "ears"),
             "fins": ("fin", "fins"), "fangs": ("fang", "fangs"), "hands": ("hand", "hands")}
SINGLE = {"horns": "a single horn growing from the middle of the forehead, like a unicorn's horn, not a pair of horns",
          "eyes": "a single eye in the middle of the face, like a cyclops, not a pair of eyes"}  # où va « la seule »
PAIRED = {"horns", "eyes", "wings", "ears", "arms", "legs", "pincers", "fangs", "hands", "fins"}  # « une corne » compte
ONE_RE = nb_core.re.compile(r"\b(?:un|une)\s+(?:seule?\s+)?(?:[a-z]+\s+)?(" + nb_core._PART_ALT + r")\b")


def counts(description):
    """{partie: nombre} demandés explicitement (« six tentacules », « une corne », « un seul œil »)."""
    spec = nb_core.analyze("", description)
    out = {k: n for k, n in spec.counts.items() if k in COUNTABLE}
    ones = {}
    for m in ONE_RE.finditer(nb_core.fold(description)):
        word = m.group(1)
        slot = nb_core.PARTS[word][0]
        if slot in PAIRED and not word.endswith(("s", "x")) and slot not in out:  # singulier seulement
            ones[slot] = ones.get(slot, 0) + 1  # « un œil rouge et un œil bleu » = 2
    return {**ones, **out}


def count_line(description):
    """Phrase affirmative (jamais « pas de corne sur les côtés » : nommer ce qu'on ne veut pas le fait dessiner)."""
    parts = []
    for slot, n in counts(description).items():
        one, many = COUNTABLE[slot]
        parts.append(f"exactly ONE {one} (1), " + SINGLE.get(slot, f"a single {one}") if n == 1
                     else f"exactly {nb_core.num_en(n)} {many} ({n})")
    if not parts:
        return ""
    return (" Count carefully: " + "; ".join(parts) + ". Draw exactly this number, "
            "as described, not the usual anatomy.")


# posture comprise (nb_writer.brief, ou devinée) : dite en clair, surtout au profil, où le modèle ne voit que la face
POSE = {
    "quatre_pattes": "It stands on all four legs.",
    "deux_jambes": "It stands upright on its two legs.",
    "plusieurs_pattes": "It stands on its {n} legs.",
    "flotte": ("It floats in mid-air, well above the ground, with empty space beneath its smooth rounded underside; "
               "it hovers, it does not stand."),
    "vole": "It hovers in mid-air on its wings, above the ground.",
    "rampe": "Its long body lies flat on the ground and slithers along it, belly on the ground.",
    "nage": "It swims, floating in the water with its fins, its body ending in a tail.",
    "sautille": "It crouches on its strong hind legs, ready to leap, like a frog or a hare.",
    "roule": "Its body is a compact ball, curled up round, ready to roll along the ground.",
    "glisse": "It is a soft, gooey mass resting on the ground, a low dome with no legs, that slides along.",
    "enracine": "It is rooted in the ground: its base spreads into roots or a stump planted in the soil, it does not walk.",
}
# au profil, le modèle ne voit que la face : on lui dit à quoi ressemble la silhouette de côté, posture par posture
PROFILE = {
    "quatre_pattes": (" Its body is horizontal: head at the left, rump and tail at the right, the four legs under the body "
                      "(the two near legs in front of the two far ones). The side view is wider than tall."),
    "deux_jambes": " It stands upright, seen from its side, one leg slightly ahead of the other, arms along its body.",
    "plusieurs_pattes": " Its body is horizontal, head at the left, and its legs are spread in a row along its side, all under the body.",
    "flotte": " It hovers well above the ground, with empty space under it, seen from the side.",
    "vole": " Its wings are spread and raised above its back, seen from the side, and it hovers above the ground.",
    "rampe": (" Its long body is stretched out flat along the ground, from its head at the left to the tip of its tail at the "
              "right, low and horizontal, slightly wavy: it does not stand up, rear up or coil upward. The side view is much "
              "wider than tall."),
    "nage": (" Its body is horizontal like a fish seen from the side: head at the left, tail fin at the right, fins along "
             "its belly and back. The side view is wider than tall."),
    "sautille": " It crouches, seen from the side, its big folded hind legs under its body, ready to leap toward the left.",
    "roule": " Seen from the side it is the same compact ball, round, sitting on the ground.",
    "glisse": " Seen from the side it is a low soft dome lying on the ground, wider than tall, sliding toward the left.",
    "enracine": " Seen from the side it is still rooted in the ground, its top leaning slightly toward the left.",
}
WIDE = {"quatre_pattes", "plusieurs_pattes", "rampe", "nage", "glisse"}  # profil plus large que haut, sinon mauvais profil
FLOATING = {"flotte", "vole", "nage"}
_GUESS = (("flotte", r"flott|levit|dans les airs|en l.air|plane\b|suspendu"), ("vole", r"\bvol(e|ant)\b"),
          ("rampe", r"\bramp(e|ant)|serpent|\bver\b|limace|anguille|mille.pattes"), ("nage", r"\bnage|poisson"),
          ("glisse", r"gelee|slime|\bblob|visqueu|glisse"), ("sautille", r"saute|sautill|bondi|grenouille|lievre|lapin|kangourou"),
          ("roule", r"\broule|en boule|boule roulante"), ("enracine", r"enracin|racines|souche|arbre vivant"))


LEGLESS = {"flotte", "rampe", "nage", "glisse", "roule"}


def said_posture(description):
    """La posture écrite en toutes lettres dans la description (« rampante », « qui flotte »), ou ""."""
    folded = nb_core.fold(description)
    return next((p for p, rx in _GUESS if nb_core.re.search(rx, folded)), "")


def guess_brief(description):
    """Sans plume (pas d'Ollama) : la posture devinée par mots-clés, la description reste en français."""
    folded = nb_core.fold(description)
    posture = next((p for p, rx in _GUESS if nb_core.re.search(rx, folded)), "")
    if not posture and not nb_archetypes.says_posture(description):
        posture = next((p for p, _ in nb_archetypes.match(description) if p), "")
    legs = 0 if posture or not has_legs(description) else counts(description).get("legs", 0)  # 0 : on ne sait pas
    if legs and not posture:
        posture = {2: "deux_jambes", 4: "quatre_pattes"}.get(legs, "plusieurs_pattes")
    return dict(posture=posture, pattes=legs, en="", profil="")


def pose_line(brief):
    p = (brief or {}).get("posture")
    return " " + POSE[p].format(n=brief.get("pattes") or "many") if p in POSE else ""


def anatomy_line(description, brief=None):
    """Les nombres, placés : « 3 heads: each on its own neck… » (la plume) ou la phrase de comptage (mots-clés)."""
    parts = (brief or {}).get("anatomie")
    if parts:
        return " Exact anatomy, count carefully and draw every part: " + "; ".join(parts) + "."
    return count_line(description)


def reference_line(description):
    refs = nb_archetypes.match(description)
    return (" Reference: " + "; ".join(t for _, t in refs) + ".") if refs else ""


def describe(description, brief=None):
    """Ce qu'on dit du sujet au modèle d'image : l'anglais précis d'abord, le français d'origine ensuite."""
    b = brief or {}
    if b.get("en"):
        head = (b["silhouette"] + ". " if b.get("silhouette") else "") + b["en"]
        return (f"{head}{anatomy_line(description, b)}{reference_line(description)}{pose_line(b)}"
                f"\n(Original description, in French: {description.strip()})")
    return f"{description.strip()}{count_line(description)}{reference_line(description)}{pose_line(b)}"


def design_prompt(description, brief=None):
    return f"{describe(description, brief)}\n\n{STYLE} {FACING['bas']}"


# profil d'une créature à pattes : sans ça le corps se tasse (vache trapue, pattes cachées)
PROPORTIONS = (" Same proportions as the front view: same head size, same leg length and body size, drawn true to scale "
               "(the side view is as tall as the front view); all legs fully visible and straight under the body, "
               "feet on the ground.")


def view_prompt(direction, legs=False, brief=None, description=""):
    b = brief or {}
    head = f"The creature: {describe(description, b)}\n" if (b.get("en") or description.strip()) else ""
    side = f" Seen from the side: {b['profil']}" if direction == "gauche" and b.get("profil") else ""
    side += PROFILE.get(b.get("posture"), "") if direction == "gauche" else ""
    known = b.get("posture") in POSE
    facing = FACING[direction].replace("{posture}", "" if known else GUESSED_POSTURE)
    walks = legs or not known  # posture inconnue : on garde les pattes dans la liste, comme avant
    keep = KEEP.format(parts="heads, " + ("legs, " if walks else "") + "eyes, horns, tentacles and wings")
    return head + facing + side + (PROPORTIONS if legs and direction == "gauche" else "") + keep


def _loaders(g, model):
    cfg = MODELS[model]
    g["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": cfg["unet"], "weight_dtype": "default"}}
    g["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": ENCODER, "type": cfg["clip_type"], "device": "default"}}
    g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": cfg["vae"]}}
    return ["1", 0], ["2", 0], ["3", 0]


def build_graph(model, prompt, seed, *, refs=(), size=SIZE, steps=None, cut=False, prefix="neobestiary/engine",
                init=None, mask=None):
    """Graphe texte -> image. refs : noms d'images déjà envoyées à ComfyUI (édition par référence, klein seulement).
    cut : détoure la créature avec BiRefNet et sauve un PNG transparent.
    init + mask (klein) : retouche ciblée, seule la zone du masque est redessinée (le masque est l'alpha inversé
    de l'image envoyée : transparent = à redessiner), puis l'original est recollé autour au pixel près."""
    cfg = MODELS[model]
    steps = steps or cfg["steps"]
    g = {}
    unet, clip, vae = _loaders(g, model)
    g["4"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": prompt}}
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": ""}}
    pos, neg = ["4", 0], ["5", 0]
    if model == "klein":
        for i, name in enumerate(refs):
            li, ls, le, lr = (str(20 + i * 4 + k) for k in range(4))
            g[li] = {"class_type": "LoadImage", "inputs": {"image": name}}
            g[ls] = {"class_type": "ImageScaleToTotalPixels",
                     "inputs": {"image": [li, 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}}
            g[le] = {"class_type": "VAEEncode", "inputs": {"pixels": [ls, 0], "vae": vae}}
            g[lr] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": pos, "latent": [le, 0]}}
            pos = [lr, 0]
        g["6"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": size, "height": size, "batch_size": 1}}
        g["7"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": size, "height": size}}
        g["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
        g["9"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}}
        g["10"] = {"class_type": "CFGGuider", "inputs": {"model": unet, "positive": pos, "negative": neg, "cfg": 1.0}}
        latent = ["6", 0]
        if init and mask:
            g["30"] = {"class_type": "LoadImage", "inputs": {"image": init}}
            g["31"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["30", 0], "vae": vae}}
            g["32"] = {"class_type": "LoadImage", "inputs": {"image": mask}}
            g["33"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["31", 0], "mask": ["32", 1]}}
            latent = ["33", 0]
        g["11"] = {"class_type": "SamplerCustomAdvanced",
                   "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["7", 0],
                              "latent_image": latent}}
        samples = ["11", 0]
    else:
        if refs:
            raise ValueError("Z-Image Turbo ne fait pas d'édition par référence")
        g["6"] = {"class_type": "EmptySD3LatentImage", "inputs": {"width": size, "height": size, "batch_size": 1}}
        g["7"] = {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": unet, "shift": 3.0}}
        g["11"] = {"class_type": "KSampler",
                   "inputs": {"model": ["7", 0], "positive": pos, "negative": neg, "latent_image": ["6", 0],
                              "seed": int(seed), "steps": steps, "cfg": 1.0, "sampler_name": "euler",
                              "scheduler": "simple", "denoise": 1.0}}
        samples = ["11", 0]
    g["12"] = {"class_type": "VAEDecode", "inputs": {"samples": samples, "vae": vae}}
    image = ["12", 0]
    if init and mask and model == "klein":  # hors de la zone : les pixels d'origine, exactement
        g["34"] = {"class_type": "ImageCompositeMasked",
                   "inputs": {"destination": ["30", 0], "source": image, "x": 0, "y": 0, "resize_source": False,
                              "mask": ["32", 1]}}
        image = ["34", 0]
    if cut:
        g["14"] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": CUT_MODEL}}
        g["15"] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["14", 0], "image": image}}
        g["16"] = {"class_type": "InvertMask", "inputs": {"mask": ["15", 0]}}  # JoinImageWithAlpha ré-inverse
        g["17"] = {"class_type": "JoinImageWithAlpha", "inputs": {"image": image, "alpha": ["16", 0]}}
        image = ["17", 0]
    g["13"] = {"class_type": "SaveImage", "inputs": {"images": image, "filename_prefix": prefix}}
    return g


def ready(client, model):
    """Liste des fichiers manquants pour ce modèle (vide = prêt)."""
    cfg = MODELS[model]
    have_unet = client.choices("UNETLoader", "unet_name")
    have_clip = client.choices("CLIPLoader", "clip_name")
    have_vae = client.choices("VAELoader", "vae_name")
    have_cut = client.choices("LoadBackgroundRemovalModel", "bg_removal_name")
    return [f for f, ok in ((cfg["unet"], cfg["unet"] in have_unet), (ENCODER, ENCODER in have_clip),
                            (cfg["vae"], cfg["vae"] in have_vae), (CUT_MODEL, CUT_MODEL in have_cut)) if not ok]


def _flat(im):
    """Référence envoyée au modèle : créature détourée posée sur un gris uni (sans l'ombre d'origine)."""
    if im.mode != "RGBA":
        return im.convert("RGB")
    bg = Image.new("RGB", im.size, (200, 200, 200))
    bg.paste(im, mask=im.getchannel("A"))
    return bg


def clean_cut(im):
    """Finit le détourage de BiRefNet : bord net, plus de liseré du fond gris, plus de miettes détachées (restes du
    fond, étincelles). Les trous ne sont pas bouchés : un vide entre l'aile et la queue est souvent un vrai vide."""
    import numpy as np
    from scipy import ndimage
    im = im.convert("RGBA")
    arr = np.asarray(im).astype(np.float32)
    rgb, a = arr[..., :3].copy(), arr[..., 3].copy()
    if (a >= 200).sum() < 50:
        return im
    clear = a < 16
    bg = np.median(rgb[clear], axis=0) if clear.sum() > 100 else np.array([200., 200., 200.])
    a[a < 48] = 0
    body = a > 0
    # liseré : pixels du bord (2 px) de la couleur du fond
    rim = body & ~ndimage.binary_erosion(body, iterations=2)
    a[rim & (np.abs(rgb - bg).max(axis=2) < 14)] = 0
    body = a > 0
    # miettes : tout morceau détaché minuscule, ou un petit morceau gris clair comme le fond
    lab, n = ndimage.label(body)
    if n > 1:
        sizes = ndimage.sum(body, lab, range(1, n + 1))
        big = sizes.max()
        for i, size in enumerate(sizes, 1):
            if size >= big:
                continue
            part = lab == i
            col = rgb[part].mean(axis=0)
            if size < big * .004 or (size < big * .05 and np.abs(col - bg).max() < 30):
                a[part] = 0
        body = a > 0
    a[a >= 230] = 255
    # bord : les pixels semi-transparents prennent la couleur de l'intérieur voisin, pas celle du fond
    solid = (a == 255).astype(np.float32)
    edge = (a > 0) & (a < 255) & ~ndimage.binary_erosion(a > 0, iterations=3)  # le bord seulement : ailes translucides gardées
    w = ndimage.gaussian_filter(solid, 2)
    c = np.stack([ndimage.gaussian_filter(rgb[..., k] * solid, 2) for k in range(3)], axis=2)
    fix = edge & (w > .05)
    rgb[fix] = c[fix] / w[fix][:, None]
    out = np.dstack([rgb, a]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def render(client, model, prompt, seed, refs_img=(), cancel=lambda: False, **kw):
    refs = [client.upload_png(_flat(im), f"eref_{uuid.uuid4().hex[:8]}.png") for im in refs_img]
    g = build_graph(model, prompt, seed, refs=refs, **kw)
    im = nbc.run_workflow(client, g, cancel, mode="RGBA" if kw.get("cut") else "RGB")
    return clean_cut(im) if kw.get("cut") else im


def edit_prompt(instruction, zone):
    where = "Edit only the marked area of this creature" if zone else "Edit this creature"
    return (f"{where}: {instruction.strip()}. Keep everything else exactly identical: same design, colors, "
            "proportions, pose, camera and pixel art style. Plain flat light gray background, no cast shadow.")


def zone_mask(size, x, y, radius):
    """Masque de retouche : un disque adouci autour du point cliqué (x, y, radius en fraction de l'image).
    Envoyé comme alpha inversé : LoadImage de ComfyUI donne masque = 1 - alpha."""
    from PIL import ImageDraw, ImageFilter
    w, h = size
    m = Image.new("L", size, 0)
    r = max(4, radius * w)
    ImageDraw.Draw(m).ellipse((x * w - r, y * h - r, x * w + r, y * h + r), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(r * .15))
    out = Image.new("RGBA", size, (0, 0, 0, 255))
    out.putalpha(m.point(lambda v: 255 - v))
    return out


# --- corrections d'orientation : le modèle d'édition ne sait pas faire tourner une créature (« il est de dos, il doit
# être de face » ne fait que repeindre). On reconnaît ces phrases et on agit nous-mêmes : miroir, retournement, ou la vue
# refaite dans la bonne orientation, avec une consigne renforcée.
_O = r"(?:vue? |vu |tourne(?:e)? )?de (face|dos|profil)"
_FLIP = (r"\b(?:la )?tete en bas\b|\bsens dessus dessous\b|\b(?:les )?pattes en l'air\b|\bsur le dos\b"
         r"|\ba l'envers (?:de haut en bas|verticalement)\b|\bretourne(?:e)? (?:de haut en bas|verticalement)\b")
_MIRROR = (r"\bregarde (?:vers |a )?(?:la )?droite\b|\btourne(?:e)? vers la droite\b|\bla tete (?:a|vers la) droite\b"
           r"|\ben miroir\b|\bde l'autre cote\b|\bmauvais cote\b")
_ENVERS = r"\ba l'envers\b|\bretourne(?:e|-le|-la)?\b|\bdans le mauvais sens\b|\bdans l'autre sens\b|\binverse(?:e)?\b|\bmal oriente(?:e)?\b"
_WANT = (r"(?:^|\bmais|\bdoit etre|\bdevrait etre|\bil faut (?:qu'(?:il|elle) soit|le mettre|la mettre)?|\bje (?:le |la )?veux"
         r"|\bremets?(?:-le|-la| le| la)?|\bmets?(?:-le|-la| le| la)?|\bplutot|\bpas de \w+ mais)\s*" + _O)
_NOT = r"(?:\bn'est pas|\best pas|\bpas|\bne doit pas etre|\bplus)\s+" + _O
_SEEN = r"\bon (?:voit|apercoit|distingue) (?:bien |encore )?(?:son|le|ses|sa|les) (dos|visage|yeux|figure|face|museau|bouche)\b"
_IS = r"\b(?:il|elle) est " + _O
EXPECTED = {"bas": "face", "haut": "dos", "gauche": "profil"}
FIX_NOTE = {"mirror": "retournée en miroir", "flip": "remise à l'endroit", "bas": "remise de face", "haut": "remise de dos",
            "gauche": "remise de profil"}


def orientation_fix(instruction, key):
    """Ce qu'une retouche demande pour l'orientation de la vue key (bas = face, haut = dos, gauche = profil tête à gauche).
    Rend (action, reste) : action = "mirror" | "flip" | "regen" | None ; reste = la retouche ordinaire qui reste à faire."""
    re = nb_core.re
    t = nb_core.fold(instruction)
    spans, wrong, want = [], set(), None

    def grab(pat):
        found = list(re.finditer(pat, t))
        spans.extend(m.span() for m in found)
        return found
    flip = bool(grab(_FLIP))
    mirror = bool(grab(_MIRROR))
    for m in grab(_WANT):
        want = m.group(1)
    for m in grab(_NOT):
        wrong.add(m.group(1))
    for m in grab(_SEEN):
        wrong.add("dos" if m.group(1) == "dos" else "face")
    for m in grab(_IS):
        if m.group(1) != EXPECTED.get(key):
            wrong.add(m.group(1))
    envers = bool(grab(_ENVERS))
    wrong.discard(want)
    exp = EXPECTED.get(key)
    if flip:
        action = "flip"
    elif key == "gauche":
        if wrong & {"face", "dos"} or (want == "profil" and not mirror):
            action = "regen"
        elif mirror or envers:
            action = "mirror"
        else:
            action = None
    elif key in ("bas", "haut"):
        action = "regen" if (envers or wrong or want == exp or (want and want != exp)) else None
    else:
        action = None
    if action is None:
        return None, instruction.strip()
    keep = [c for i, c in enumerate(t) if not any(a <= i < b for a, b in spans)]
    rest = re.sub(r"\s+", " ", "".join(keep))
    rest = re.sub(r"^(?:[\s,.;:!-]|\b(?:il|elle|est|mais|et|c'est|non|pas|alors|donc|stp|svp)\b)+", "", rest)
    rest = re.sub(r"(?:[\s,.;:!-]|\b(?:il|elle|est|mais|et|pas)\b)+$", "", rest)
    return action, (rest if len(re.findall(r"[a-z]{3,}", rest)) >= 2 else "")


def generate_facing(client, direction, refs, seed, progress=lambda m: None, cancel=lambda: False, legs=False, brief=None,
                    description=""):
    """La vue refaite dans la bonne orientation : consigne d'orientation renforcée, 2 essais, le mieux noté gardé."""
    insist = {"bas": " The previous picture wrongly showed it from behind or from the side: this time it must face the "
                     "viewer, its face and eyes clearly visible, toward the bottom of the screen.",
              "haut": " The previous picture wrongly showed its face: this time we must see only its back and the back of "
                      "its head, with no eyes and no face visible.",
              "gauche": " The previous picture was not a clean side view: this time show a pure side profile, its head "
                        "pointing to the left edge of the screen."}[direction]
    prompt = (STYLE + " " if direction == "bas" else "") + view_prompt(direction, legs, brief, description) + insist
    return _best(client, prompt, refs, direction, seed, 2, cancel, progress, "Orientation",
                 (brief or {}).get("posture", ""))[0]


def generate_edit(client, image, instruction, seed, zone=None, progress=lambda m: None, cancel=lambda: False):
    """Retouche : zone = (x, y, rayon) en fractions -> seule cette zone est redessinée ; None -> toute la créature,
    éditée d'après elle-même (« les yeux en rouge »)."""
    progress("Retouche")
    flat = _flat(image.convert("RGBA")).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    ref = client.upload_png(flat, f"edit_{uuid.uuid4().hex[:8]}.png")
    kw = {}
    if zone:
        kw = dict(init=ref, mask=client.upload_png(zone_mask(flat.size, *zone), f"mask_{uuid.uuid4().hex[:8]}.png"))
    g = build_graph(MODEL, edit_prompt(instruction, bool(zone)), seed, refs=[ref], cut=True, **kw)
    return nbc.run_workflow(client, g, cancel, mode="RGBA")


GENRE_EN = {"griffe": "a slashing claw strike", "morsure": "a lunging bite, jaws wide open", "charge": "a headlong charge",
            "projectile": "spitting a projectile", "souffle": "a breath attack streaming from its mouth",
            "onde": "a shockwave bursting around it", "rayon": "firing an energy beam"}
ELEMENT_EN = {"feu": "fire", "eau": "water", "plante": "plant", "vent": "wind", "roche": "rock", "glace": "ice",
              "foudre": "lightning", "lumière": "light", "ombre": "shadow", "esprit": "spirit", "acier": "steel",
              "poison": "poison"}


def portrait_prompt(move, brief=None, description=""):
    what = GENRE_EN.get(move.get("genre"), "attacking")
    elem = ELEMENT_EN.get(move.get("element"), "")
    return (f"The same creature in a dynamic battle pose, mid-attack: {what}, with {elem} energy. "
            "Dramatic three-quarter front view, large, filling the frame, the entire creature visible. "
            "Keep the identical design, colors, anatomy (same number of heads, eyes, legs, horns) and pixel art style; "
            "every head and body part stays clearly visible, side by side, none hidden behind the body. "
            f"The creature: {describe(description, brief)} "
            "Plain flat light gray background, no text, no scenery, no cast shadow.")


def generate_portrait(client, design, move, seed, progress=lambda m: None, cancel=lambda: False, brief=None,
                      description=""):
    """Le portrait de combat : la créature en pleine attaque (sa 2e attaque, la plus forte), d'après son design."""
    progress("Portrait de combat")
    return render(client, MODEL, portrait_prompt(move, brief, description), seed, refs_img=[design], cancel=cancel, cut=True)


def illustration_prompt(brief=None, description=""):
    return ("A bestiary illustration of this exact creature, like a plate in a naturalist's field guide: the creature "
            "calm, in its natural and most characteristic posture, seen at a three-quarter angle, its whole body and every "
            "part clearly visible and readable, nothing hidden or cropped, large and centered. "
            "Keep the identical design, colors, anatomy (same number of heads, eyes, legs, wings, horns, tentacles) and "
            f"pixel art style. The creature: {describe(description, brief)} "
            "Detailed pixel art, plain flat light gray background, no text, no scenery, no cast shadow.")


def generate_illustration(client, design, seed, progress=lambda m: None, cancel=lambda: False, brief=None, description=""):
    """L'image du bestiaire : la créature au calme, entière et fidèle à sa description, d'après son design."""
    progress("Image du bestiaire")
    return render(client, MODEL, illustration_prompt(brief, description), seed, refs_img=[design], cancel=cancel, cut=True)


def fusion_prompt(description, brief=None):
    return ("Combine the two reference creatures into ONE single new hybrid creature that clearly mixes visible traits "
            f"of both. {STYLE} The hybrid: {describe(description, brief)} {pose_line(brief)}")


def generate_fusion(client, designs, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    progress("Esquisse de l'hybride")
    return render(client, MODEL, fusion_prompt(description, brief), seed, refs_img=list(designs), cancel=cancel, cut=True)


# --------------------------------------------------------------------------- créature complète

MODEL = "klein"
DIRECTIONS = ("bas", "gauche", "droite", "haut")
TRIES = 2  # candidats par vue ; le meilleur est gardé, les autres restent comme versions


def _colors(im):
    """Histogramme 512 cases des pixels opaques (pour comparer les couleurs de deux vues)."""
    small = im.convert("RGBA").resize((96, 96), Image.Resampling.NEAREST)
    h = [0] * 512
    for r, g, b, a in small.getdata():
        if a >= 128:
            h[(r >> 5) << 6 | (g >> 5) << 3 | b >> 5] += 1
    n = sum(h) or 1
    return [v / n for v in h]


def similarity(a, b):
    """0..1 : part de couleurs communes entre deux images détourées."""
    return sum(min(x, y) for x, y in zip(_colors(a), _colors(b)))


def score_view(im, ref, direction):
    """Note d'un candidat : silhouette propre (symétrique de face/dos) + mêmes couleurs que le design."""
    view = {"bas": "face", "haut": "dos"}.get(direction, direction)
    base, _ = nb_auto.score_image(im.convert("RGB"), view)
    return base + 6.0 * similarity(im, ref)


def has_legs(description, brief=None):
    """La marche par édition de pose n'a de sens qu'avec des pattes ; sinon (œil, blob, serpent) : rebond."""
    if brief and brief.get("posture"):
        return brief["posture"] not in FLOATING | {"rampe", "glisse", "roule"} and brief.get("pattes", 0) > 0
    spec = nb_core.analyze("", description)
    if spec.only or "legs" in spec.forbidden or "body" in spec.forbidden:
        return False
    return nb_guides.plan_for(spec) not in ("blob", "serpent")  # inconnu (« chevalier ») : il marche


def bob(im, phase):
    """Rebond procédural : phase -1/+1 = la créature se tasse un peu et descend, ±0.5 = à moitié, 0 = repos."""
    if not phase:
        return im.copy()
    w, h = im.size
    box = im.getbbox() or (0, 0, w, h)
    ch = box[3] - box[1]
    squash = max(1, round(ch * 0.04 * abs(phase)))
    body = im.crop(box).resize((box[2] - box[0], ch - squash), Image.Resampling.NEAREST)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(body, (box[0], box[1] + squash))
    return out


def has_wings(description, brief=None):
    text = " ".join([description, (brief or {}).get("en", "")] + list((brief or {}).get("anatomie", []))).lower()
    return "wing" in text or "aile" in text


def flap(im, direction, phase):
    """Battement d'ailes : les colonnes hors du tronc montent (phase +1) ou descendent (-1), d'autant plus qu'elles
    sont loin du tronc. Face / dos : les deux côtés ; profil (tête à gauche) : seulement l'arrière, où sont les ailes."""
    im = im.convert("RGBA")
    box = im.getbbox()
    if not box or not phase:
        return im.copy()
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    mid = (x0 + x1) / 2
    # shortcut: tronc = 36 % central de la largeur (face) ou moitié avant (profil), sans détecter les ailes
    body, reach = (w * .18, w / 2 - w * .18) if direction in ("bas", "haut") else (w * .1, w / 2 - w * .1)
    amp = max(2, round(h * .07))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for x in range(x0, x1):
        d = (abs(x + .5 - mid) if direction in ("bas", "haut") else x + .5 - mid) - body
        col = im.crop((x, 0, x + 1, im.height))
        out.alpha_composite(col, (x, 0)) if d <= 0 else out.paste(col, (x, -round(phase * amp * d / reach)), col)
    return out


def shape_penalty(im, direction, posture):
    """Un serpent ou un quadrupède de profil est plus large que haut : un profil dressé est un raté."""
    box = im.getbbox()
    if direction != "gauche" or posture not in WIDE or not box:
        return 0.0
    w, h = box[2] - box[0], box[3] - box[1]
    return 0.0 if w >= h * 1.1 else 8.0


def _best(client, prompt, refs, direction, seed, tries, cancel, progress, label, posture=""):
    """refs[0] = le design (sert aussi à noter les couleurs)."""
    ref = refs[0]
    cands = []
    for i in range(tries):
        if cancel():
            raise nbc.ComfyError("annulé")
        progress(f"{label} ({i + 1}/{tries})")
        im = render(client, MODEL, prompt, seed + 1000 * i, refs_img=refs, cancel=cancel, cut=True)
        cands.append((score_view(im, ref, direction) - shape_penalty(im, direction, posture), im))
    cands.sort(key=lambda c: -c[0])
    return [im for _, im in cands]


def generate_design(client, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    progress("Esquisse du design")
    return render(client, MODEL, design_prompt(description, brief), seed, cancel=cancel, cut=True)


def generate_directions(client, design, seed, progress=lambda m: None, cancel=lambda: False, tries=TRIES, legs=False,
                        brief=None, description=""):
    """{direction: [versions, la meilleure d'abord]} ; droite = miroir de gauche (même créature, garanti)."""
    out = {"bas": [design]}
    out["haut"] = _best(client, view_prompt("haut", False, brief, description), [ImageOps.mirror(design)], "haut", seed + 7,
                        tries, cancel, progress, "Vue de dos")
    # à pattes : le design seul (le dos en référence laisse sa raie sur le flanc et tasse le corps) ;
    # sans pattes (œil, pieuvre) : face + dos, sinon le modèle invente un corps à quatre pattes en tournant de 90°
    refs = [design] if legs else [design, out["haut"][0]]
    out["gauche"] = _best(client, view_prompt("gauche", legs, brief, description), refs, "gauche", seed + 7, tries, cancel,
                          progress, "Profil", (brief or {}).get("posture", ""))
    out["droite"] = [ImageOps.mirror(im) for im in out["gauche"]]
    return out


def generate_view(client, refs, direction, seed, progress=lambda m: None, cancel=lambda: False, legs=False,
                  brief=None, description=""):
    """Une nouvelle version d'une vue (« Refaire ») : refs = [design] ou [design, dos] pour le profil."""
    label = {"haut": "Vue de dos", "gauche": "Profil"}[direction]
    if legs:
        refs = refs[:1]
    if direction == "haut":  # vu de dos, la gauche et la droite s'échangent : le bâton tenu à gauche passe à droite
        refs = [ImageOps.mirror(refs[0])]
    return _best(client, view_prompt(direction, legs, brief, description), refs, direction, seed, 1, cancel, progress, label,
                 (brief or {}).get("posture", ""))[0]


def leg_zone(im):
    """Hauteur (en px, depuis le haut de l'image) où commencent les pattes : sous le corps, la silhouette se sépare
    en plusieurs colonnes ou devient nettement plus étroite. Bornée entre 15 % et 45 % du bas de la créature."""
    a = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    box = a.getbbox()
    if not box:
        return None, None
    x0, y0, x1, y1 = box
    h = y1 - y0
    px = a.load()

    def runs(y):
        n, inside, width = 0, False, 0
        for x in range(x0, x1):
            on = px[x, y] > 0
            width += on
            if on and not inside:
                n += 1
            inside = on
        return n, width

    widest = max(runs(y)[1] for y in range(y0, y1, max(1, h // 40)))
    top = y1 - round(h * .15)
    for y in range(y1 - round(h * .15), y1 - round(h * .45), -1):  # on remonte tant que ça ressemble à des pattes
        n, w = runs(y)
        if n >= 2 or w < widest * .55:
            top = y
        else:
            break
    return top, box


def step_frame(im, direction, phase):
    """Un pas procédural à partir de la pose de repos : mêmes pixels, seules les pattes bougent.

    face / dos : les pattes d'un côté se lèvent (phase +1 = côté gauche de l'image, -1 = droit ; ±0.5 = demi-pas).
    profil (tête à gauche) : pattes avant et arrière se balancent en sens opposé (cisaillement du bas des pattes).
    Au pas complet, le corps descend d'un pixel (appui) : la marche se lit mieux.
    """
    im = im.convert("RGBA")
    top, box = leg_zone(im)
    if top is None:
        return im.copy()
    x0, y0, x1, y1 = box
    h, zh = y1 - y0, y1 - top
    body = im.copy()
    body.paste((0, 0, 0, 0), (0, top, im.width, im.height))
    legs = im.copy()
    legs.paste((0, 0, 0, 0), (0, 0, im.width, top))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    mid = (x0 + x1) // 2
    if direction in ("bas", "haut"):
        lift = max(1, round(h * .045 * abs(phase)))
        up = 1 if phase > 0 else -1
        for side, (a, b) in ((1, (0, mid)), (-1, (mid, im.width))):
            part = legs.crop((a, 0, b, im.height))
            out.alpha_composite(part, (a, -lift if side == up else 0))
    else:
        swing = max(2, round(zh * .32))
        for front, (a, b) in ((True, (0, mid)), (False, (mid, im.width))):  # tête à gauche : l'avant est à gauche
            part = legs.crop((a, 0, b, im.height))
            sign = (-1 if front else 1) * phase
            sheared = Image.new("RGBA", part.size, (0, 0, 0, 0))
            for y in range(top, y1):
                dx = round(sign * swing * (y - top) / max(1, zh))
                row = part.crop((0, y, part.width, y + 1))
                sheared.paste(row, (dx, y), row)  # paste accepte un décalage négatif
            out.alpha_composite(sheared, (a, 0))
    out.alpha_composite(body, (0, 1 if abs(phase) >= 1 and h >= 24 else 0))  # le corps passe devant le haut des pattes
    return out


def _rows(im, shift):
    """Chaque ligne y décalée de shift(y) px à l'horizontale."""
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for y in range(im.height):
        row = im.crop((0, y, im.width, y + 1))
        out.paste(row, (shift(y), y), row)
    return out


def _cols(im, shift):
    """Chaque colonne x décalée de shift(x) px à la verticale."""
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for x in range(im.width):
        col = im.crop((x, 0, x + 1, im.height))
        out.paste(col, (x, shift(x)), col)
    return out


def wave(im, direction, phase, amp=.04, waves=1.5):
    """Ondulation (serpent, ver, poisson) : une vague parcourt le corps, nulle à la tête, ample vers la queue.
    Face / dos : balancement de gauche à droite ; profil (tête à gauche) : le corps ondule de haut en bas."""
    im = im.convert("RGBA")
    box = im.getbbox()
    if not box or not phase:
        return im.copy()
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    a = max(2, round(max(w, h) * amp))  # d'après la longueur : un serpent couché est très plat
    off = phase * math.pi / 2
    if direction in ("bas", "haut"):
        def shift(y):
            t = (y - y0) / max(1, h)
            ramp = 1 - t if direction == "bas" else t  # la tête est devant : en bas de face, en haut de dos
            return round(a * ramp * math.sin(2 * math.pi * waves * t + off))
        return _rows(im, shift)

    def shift(x):
        t = (x - x0) / max(1, w)
        return round(a * t * math.sin(2 * math.pi * waves * t + off))
    return _cols(im, shift)


def swim(im, direction, phase):
    return wave(im, direction, phase, amp=.03, waves=.75)


def _rescale(im, sx, sy):
    """La créature étirée (sx, sy), posée au même endroit (bas et centre gardés)."""
    box = im.getbbox()
    if not box:
        return im.copy()
    part = im.crop(box)
    nw, nh = max(1, round(part.width * sx)), max(1, round(part.height * sy))
    part = part.resize((nw, nh), Image.Resampling.NEAREST)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(part, ((box[0] + box[2]) // 2 - nw // 2, box[3] - nh), part)
    return out


def hop(im, direction, phase):
    """Bond : +1 accroupi (tassé, élargi), -1 en extension (étiré, aminci) ; ±0.5 à mi-chemin."""
    t = abs(phase)
    return _rescale(im, 1 + .06 * t, 1 - .1 * t) if phase > 0 else _rescale(im, 1 - .05 * t, 1 + .08 * t) if phase < 0 else im.copy()


def jelly(im, direction, phase):
    """Gelée : elle s'étale puis se resserre en glissant."""
    t = abs(phase)
    return _rescale(im, 1 + .08 * t, 1 - .08 * t) if phase > 0 else _rescale(im, 1 - .04 * t, 1 + .05 * t) if phase < 0 else im.copy()


def roll(im, direction, phase):
    """Boule : de profil elle tourne sur elle-même ; de face et de dos, sa surface défile dans sa silhouette."""
    im = im.convert("RGBA")
    box = im.getbbox()
    if not box or not phase:
        return im.copy()
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if direction not in ("bas", "haut"):
        return im.rotate(25 * phase, Image.Resampling.NEAREST, center=(cx, cy))
    part = im.crop(box)
    k = max(1, round(part.height * .12 * abs(phase))) * (1 if phase > 0 else -1)
    rgb = ImageChops.offset(part, 0, k)  # la texture défile (en boucle), la silhouette reste
    rgb.putalpha(part.getchannel("A"))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(rgb, box[:2], rgb)
    return out


def sway(im, direction, phase):
    """Plante ou créature enracinée : le haut se balance, la base reste plantée."""
    im = im.convert("RGBA")
    box = im.getbbox()
    if not box or not phase:
        return im.copy()
    x0, y0, x1, y1 = box
    base = y0 + (y1 - y0) * .65
    a = max(2, round((x1 - x0) * .06))
    return _rows(im, lambda y: round(phase * a * (base - y) / max(1, base - y0)) if y < base else 0)


MOTION = {"rampe": wave, "nage": swim, "sautille": hop, "roule": roll, "glisse": jelly, "enracine": sway}


def motion(description, brief=None):
    """Le mouvement procédural de la créature, f(image, direction, phase), ou None (elle marche sur ses pattes)."""
    p = (brief or {}).get("posture")
    if has_wings(description, brief) and (p in FLOATING or not has_legs(description, brief)):
        return flap
    if p in MOTION:
        return MOTION[p]
    if not has_legs(description, brief):
        # le décalage de hover() disparaît quand les sprites sont alignés en bas : il faut une forme qui change
        return lambda im, d, ph: bob(im, ph)
    return None


WALK_PHASES = (1, .5, 0, -.5, -1)  # pas A, demi-pas A, repos, demi-pas B, pas B


def generate_walk(client, view, direction, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    """5 images : pas A, demi-pas A, repos, demi-pas B, pas B (lecture repos, ½A, A, ½A, repos, ½B, B, ½B).
    droite : miroir de la marche gauche.

    Les pas sont calculés depuis la pose de repos (pas redessinés par le modèle) : les pattes restent nettes et la
    créature identique d'une image à l'autre. Les demi-pas rendent le mouvement fluide. Sans pattes (œil, blob,
    serpent) : rebond, ondulation… selon la posture."""
    move = motion(description, brief) or step_frame
    return [view.copy() if not p else move(view, direction, p) for p in WALK_PHASES]


def generate_creature(client, description, seed, progress=lambda m: None, cancel=lambda: False):
    """Tout d'un coup : {"design", "directions": {d: [versions]}, "walk": {d: [5 images]}}."""
    design = generate_design(client, description, seed, progress, cancel)
    dirs = generate_directions(client, design, seed, progress, cancel, legs=has_legs(description))
    walk = {}
    for d in ("bas", "haut", "gauche"):
        walk[d] = generate_walk(client, dirs[d][0], d, description, seed, progress, cancel)
    walk["droite"] = [ImageOps.mirror(im) for im in walk["gauche"]]
    return dict(design=design, directions=dirs, walk=walk)
