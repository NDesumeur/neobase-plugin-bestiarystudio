# -*- coding: utf-8 -*-
"""NeoBestiary Studio - moteur d'image moderne (FLUX.2 klein 4B / Z-Image Turbo, nœuds natifs de ComfyUI).

Le texte de l'utilisateur part tel quel (l'encodeur Qwen3 comprend le français) : pas de lexique, pas de
pondérations, pas de négatifs imposés. FLUX.2 klein sait aussi éditer à partir d'images de référence
(ReferenceLatent) : c'est ce qui fait tourner la créature et l'anime en gardant son design.
"""
import uuid

from PIL import Image, ImageOps

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
             "and the back of its head; no face and no eyes are visible."),
    "gauche": ("Turn this exact same creature a full 90 degrees so it faces exactly toward the left edge of the screen: "
               "a pure side profile, in exactly the same posture as in the reference image (a four-legged creature stays on "
               "all fours, an upright one stays upright), its face pointing left, "
               "nothing of it turned toward the viewer."),
}
KEEP = (" Keep the identical design, colors, proportions and pixel art style, and the same top-down camera. "
        "Keep exactly the same body parts and the same number of legs, eyes, horns and tentacles: add nothing, "
        "remove nothing (a creature without legs gets no legs). "
        "Plain flat light gray background, no cast shadow.")


def design_prompt(description):
    return f"{description.strip()}\n\n{STYLE} {FACING['bas']}"


def view_prompt(direction):
    return FACING[direction] + KEEP


def _loaders(g, model):
    cfg = MODELS[model]
    g["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": cfg["unet"], "weight_dtype": "default"}}
    g["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": ENCODER, "type": cfg["clip_type"], "device": "default"}}
    g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": cfg["vae"]}}
    return ["1", 0], ["2", 0], ["3", 0]


def build_graph(model, prompt, seed, *, refs=(), size=SIZE, steps=None, cut=False, prefix="neobestiary/engine"):
    """Graphe texte -> image. refs : noms d'images déjà envoyées à ComfyUI (édition par référence, klein seulement).
    cut : détoure la créature avec BiRefNet et sauve un PNG transparent."""
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
        g["11"] = {"class_type": "SamplerCustomAdvanced",
                   "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["7", 0],
                              "latent_image": ["6", 0]}}
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


def render(client, model, prompt, seed, refs_img=(), cancel=lambda: False, **kw):
    refs = [client.upload_png(_flat(im), f"eref_{uuid.uuid4().hex[:8]}.png") for im in refs_img]
    g = build_graph(model, prompt, seed, refs=refs, **kw)
    return nbc.run_workflow(client, g, cancel, mode="RGBA" if kw.get("cut") else "RGB")


# --------------------------------------------------------------------------- créature complète

MODEL = "klein"
DIRECTIONS = ("bas", "gauche", "droite", "haut")
TRIES = 2  # candidats par vue ; le meilleur est gardé, les autres restent comme versions
STEP = {
    "a": "its left legs step forward while its right legs push back",
    "b": "its right legs step forward while its left legs push back",
}
WALK = ("Show this exact same creature, facing exactly the same direction with the same camera, caught mid-stride "
        "while walking: {step}. Only the legs move; body, head and everything else stay identical." + KEEP)


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


def has_legs(description):
    """La marche par édition de pose n'a de sens qu'avec des pattes ; sinon (œil, blob, serpent) : rebond."""
    spec = nb_core.analyze("", description)
    if spec.only or "legs" in spec.forbidden or "body" in spec.forbidden:
        return False
    return nb_guides.plan_for(spec) not in ("blob", "serpent")  # inconnu (« chevalier ») : il marche


def bob(im, phase):
    """Rebond procédural : phase -1/+1 = la créature se tasse un peu et descend, 0 = repos."""
    if not phase:
        return im.copy()
    w, h = im.size
    box = im.getbbox() or (0, 0, w, h)
    ch = box[3] - box[1]
    squash = max(1, round(ch * 0.04))
    body = im.crop(box).resize((box[2] - box[0], ch - squash), Image.Resampling.NEAREST)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(body, (box[0], box[1] + squash))
    return out


def _best(client, prompt, refs, direction, seed, tries, cancel, progress, label):
    """refs[0] = le design (sert aussi à noter les couleurs)."""
    ref = refs[0]
    cands = []
    for i in range(tries):
        if cancel():
            raise nbc.ComfyError("annulé")
        progress(f"{label} ({i + 1}/{tries})")
        im = render(client, MODEL, prompt, seed + 1000 * i, refs_img=refs, cancel=cancel, cut=True)
        cands.append((score_view(im, ref, direction), im))
    cands.sort(key=lambda c: -c[0])
    return [im for _, im in cands]


def generate_design(client, description, seed, progress=lambda m: None, cancel=lambda: False):
    progress("Esquisse du design")
    return render(client, MODEL, design_prompt(description), seed, cancel=cancel, cut=True)


def generate_directions(client, design, seed, progress=lambda m: None, cancel=lambda: False, tries=TRIES):
    """{direction: [versions, la meilleure d'abord]} ; droite = miroir de gauche (même créature, garanti)."""
    out = {"bas": [design]}
    out["haut"] = _best(client, view_prompt("haut"), [design], "haut", seed + 7, tries, cancel, progress, "Vue de dos")
    # face + dos en références : le modèle comprend le volume et ne réinvente pas le corps en tournant de 90°
    out["gauche"] = _best(client, view_prompt("gauche"), [design, out["haut"][0]], "gauche", seed + 7, tries, cancel,
                          progress, "Profil")
    out["droite"] = [ImageOps.mirror(im) for im in out["gauche"]]
    return out


def generate_view(client, refs, direction, seed, progress=lambda m: None, cancel=lambda: False):
    """Une nouvelle version d'une vue (« Refaire ») : refs = [design] ou [design, dos] pour le profil."""
    label = {"haut": "Vue de dos", "gauche": "Profil"}[direction]
    return _best(client, view_prompt(direction), refs, direction, seed, 1, cancel, progress, label)[0]


def generate_walk(client, view, direction, description, seed, progress=lambda m: None, cancel=lambda: False):
    """3 images : pas A, repos, pas B (lecture A, repos, B, repos). droite : miroir de la marche gauche."""
    if not has_legs(description):
        return [bob(view, 1), view.copy(), bob(view, -1)]
    frames = []
    for k in ("a", "b"):
        if cancel():
            raise nbc.ComfyError("annulé")
        progress(f"Marche {direction} : pas {'1' if k == 'a' else '2'}")
        frames.append(render(client, MODEL, WALK.format(step=STEP[k]), seed + 50 + ord(k), refs_img=[view],
                             cancel=cancel, cut=True))
    return [frames[0], view.copy(), frames[1]]


def generate_creature(client, description, seed, progress=lambda m: None, cancel=lambda: False):
    """Tout d'un coup : {"design", "directions": {d: [versions]}, "walk": {d: [3 images]}}."""
    design = generate_design(client, description, seed, progress, cancel)
    dirs = generate_directions(client, design, seed, progress, cancel)
    walk = {}
    for d in ("bas", "haut", "gauche"):
        walk[d] = generate_walk(client, dirs[d][0], d, description, seed, progress, cancel)
    walk["droite"] = [ImageOps.mirror(im) for im in walk["gauche"]]
    return dict(design=design, directions=dirs, walk=walk)
