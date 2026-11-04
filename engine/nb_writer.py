# -*- coding: utf-8 -*-
"""NeoBestiary Studio - la plume : idées de créatures et fiches de bestiaire, écrites par un modèle de langage local.

Le texte passe par Ollama (http://127.0.0.1:11434), s'il est installé avec un modèle. Rien ne part sur Internet.
"""
import json
import random
import urllib.request

import nb_archetypes
import nb_stats

OLLAMA = "http://127.0.0.1:11434"
PREFERRED = ("mistral-nemo", "mistral-small", "mistral", "qwen3:8b", "qwen2.5", "llama3.1", "gemma3", "gemma2")
TYPES = ("feu", "eau", "plante", "vent", "roche", "glace", "foudre", "lumière", "ombre", "esprit", "acier", "poison")

# des graines d'inspiration tirées au hasard : sans elles le modèle ressort toujours les mêmes idées
THEMES = {
    "lovecraft": ("horreur cosmique façon Lovecraft", [
        "tentacules", "dizaines d'yeux", "bouche verticale bordée de dents", "chair translucide", "poisson des abysses",
        "crustacé difforme", "ailes membraneuses déchirées", "masse de chair qui rampe", "pieuvre à tête humaine",
        "méduse géante", "corail vivant", "coquillage spiralé", "silhouette voûtée sous une robe", "ver segmenté",
        "étoile de mer debout", "cerveau ailé", "batracien bipède", "grappe d'yeux", "squelette d'algues", "seiche"]),
    "animaux": ("animal réel transformé en créature de jeu", [
        "renard", "hibou", "loup", "cerf", "tortue", "crapaud", "salamandre", "sanglier", "lynx", "chauve-souris",
        "scarabée", "araignée", "crabe", "hérisson", "lièvre", "corbeau", "serpent", "caméléon", "ours", "taupe",
        "lézard", "escargot", "papillon de nuit", "raie", "bouquetin", "fourmi", "mante religieuse", "loutre"]),
    "monstres": ("monstre de jeu de rôle", [
        "golem", "gargouille", "hydre", "chimère", "troll", "goule", "gelée", "coffre mimique", "liche", "basilic",
        "manticore", "harpie", "minotaure", "cyclope", "spectre", "squelette guerrier", "épouvantail vivant",
        "armure hantée", "champignon géant", "plante carnivore", "dragon miniature", "démon cornu", "élémentaire de pierre"]),
    "folklore": ("créature du folklore et des légendes du monde", [
        "renard à plusieurs queues", "esprit de la forêt", "dame blanche", "korrigan", "vouivre", "tarasque",
        "kappa des rivières", "tengu", "wendigo", "lutin", "farfadet", "sirène des lacs", "cerf spectral",
        "dragon serpent d'Asie", "oiseau de feu", "chat-garou", "chien noir des landes", "golem d'argile",
        "esprit des marais", "gardien de pierre", "baba yaga", "lycanthrope", "fée des champignons"]),
}
THEMES["melange"] = ("mélange libre de toutes ces sources", [w for _, ws in THEMES.values() for w in ws])

SYS_IDEA = (
    "Tu inventes des créatures originales pour un jeu vidéo en pixel art vu de dessus. Tu écris en français. "
    "Ta description sert directement de consigne à un générateur d'images : elle doit être CLAIRE et VISUELLE. "
    "Règles : une seule créature, décrite en UNE phrase de 20 à 35 mots ; commence par ce qu'elle est et sa posture "
    "(à quatre pattes, debout sur deux jambes, qui flotte, qui rampe) ; donne les nombres exacts quand ils comptent "
    "(yeux, pattes, têtes, cornes, tentacules, ailes) et vérifie qu'ils ne se contredisent pas ; deux ou trois couleurs "
    "principales ; un ou deux détails marquants. Pas d'histoire, pas de décor, pas de mots abstraits (« mystérieux », "
    "« ancien »), pas de nom de jeu ou de personnage existant. "
    "Exemple de bonne description : « un crapaud géant à quatre pattes, peau violette couverte de verrues jaunes, trois yeux "
    "rouges alignés sur le front et une longue langue fourchue qui pend ». Réponds uniquement en JSON.")

SYS_LORE = (
    "Tu es l'auteur d'un bestiaire de jeu vidéo, à la manière d'un Pokédex : des fiches courtes, évocatrices, un peu "
    "romancées et mystérieuses. Tu écris toujours dans un français impeccable, quel que soit le nom de la créature. "
    "Tu réponds uniquement en JSON.")


class WriterError(RuntimeError):
    pass


def _get(path, timeout=3):
    with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
        return json.loads(r.read())


def model():
    """Le modèle de texte à utiliser, ou None si Ollama n'est pas là (ou n'a aucun modèle)."""
    try:
        names = [m["name"] for m in _get("/api/tags").get("models", [])]
    except Exception:
        return None
    for want in PREFERRED:
        for n in names:
            if n.split(":")[0] == want or n == want:
                return n
    return names[0] if names else None


def _ask(system, prompt, seed, temperature=0.8, keep_alive=None):
    m = model()
    if not m:
        raise WriterError("Pour écrire, installe Ollama (ollama.com) puis un modèle : « ollama pull mistral-nemo ».")
    body = {"model": m, "system": system, "prompt": prompt, "format": "json", "stream": False, "think": False,
            "options": {"temperature": temperature, "seed": int(seed), "num_predict": 1000}}
    if keep_alive is not None:  # 0 : le modèle de texte rend la carte tout de suite au dessin
        body["keep_alive"] = keep_alive
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            text = json.loads(r.read())["response"]
        return json.loads(text)
    except WriterError:
        raise
    except Exception as exc:
        raise WriterError(f"La plume n'a pas répondu ({exc}).")


def _clean(v, limit=600):
    return " ".join(str(v or "").split())[:limit]


def idea(theme="melange", seed=None):
    """{"name", "description"} : une créature inventée, décrite comme une consigne claire pour le dessin."""
    seed = random.randrange(10 ** 6) if seed is None else int(seed)
    label, words = THEMES.get(theme, THEMES["melange"])
    rnd = random.Random(seed)
    sparks = rnd.sample(words, 2)
    prompt = (f"Thème : {label}. Inspiration de départ : {sparks[0]}, avec une touche de {sparks[1]}.\n"
              "Invente une créature originale. JSON avec exactement deux clés : "
              "\"nom\" (un nom inventé, court, qui sonne bien en français) et \"description\" (la consigne de dessin).")
    out = _ask(SYS_IDEA, prompt, seed, temperature=0.95)
    name, desc = _clean(out.get("nom"), 60), _clean(out.get("description"), 400)
    if not desc:
        raise WriterError("La plume n'a rien proposé, réessaie.")
    return dict(name=name, description=desc, theme=theme)


POSTURES = ("quatre_pattes", "deux_jambes", "plusieurs_pattes", "flotte", "vole", "rampe", "nage")
SYS_BRIEF = (
    "Tu es directeur artistique pour un jeu vidéo : tu prépares la consigne d'un générateur d'images à partir d'une "
    "créature décrite en français. Tu connais très bien les monstres et créatures des jeux de rôle, de la mythologie, "
    "du folklore et de Lovecraft, les animaux réels et les objets vivants (hydre, cerbère, chimère, mimique, tyrannœil, "
    "golem, kitsune, gargouille, liche…) : quand la description en nomme un, tu donnes ses traits visuels typiques "
    "(une hydre a plusieurs têtes sur des cous séparés, une mimique est un coffre avec des dents et une langue). "
    "Tu ne contredis jamais la description : ses nombres et ses couleurs priment sur la tradition. "
    "Tu réponds uniquement en JSON.")


def _anatomy(items):
    """[{"partie", "nombre", "ou"}] -> lignes anglaises lisibles (« 3 heads: each on its own neck… »)."""
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        part, where = _clean(it.get("partie") or it.get("part"), 40), _clean(it.get("ou") or it.get("where"), 160)
        try:
            n = int(it.get("nombre", it.get("count")))
        except (TypeError, ValueError):
            n = None
        if part and n is not None and 0 < n <= 100:
            out.append(f"{n} {part}" + (f": {where}" if where else ""))
    return out[:10]


def brief(description, seed=1):
    """Ce que la description veut dire pour le dessin : posture, pattes, anatomie (chaque partie, son nombre, sa
    place), description anglaise précise.

    Le modèle d'image comprend mieux l'anglais, dessine mieux les nombres quand on les place (« trois têtes, chacune
    sur son cou ») et les vues de dos et de profil en ont besoin : sans elle il ne voit que l'image de face."""
    refs = nb_archetypes.match(description)
    known = "".join(f"\n- {t}" for _, t in refs)
    prompt = (f"Description : « {description} »\n"
              + (f"Référence visuelle fiable de ce qu'elle nomme (à suivre, sauf ce que la description précise "
                 f"autrement) :{known}\n" if known else "")
              + "\nRéponds en JSON avec exactement ces clés :\n"
              f"\"posture\" (un seul mot parmi : {', '.join(POSTURES)} ; « flotte » si elle lévite ou flotte dans les airs "
              "sans toucher le sol, « rampe » pour un serpent, un ver ou une limace, « nage » pour un poisson),\n"
              "\"pattes\" (le nombre de pattes ou de jambes qui touchent le sol, 0 si elle n'en a pas ; les tentacules, "
              "bras et ailes ne comptent pas),\n"
              "\"silhouette\" (en anglais, quelques mots : ce qu'elle est dans l'ensemble, ex. « a three-headed ghoul "
              "hound », « a living treasure chest »),\n"
              "\"anatomie\" (liste de TOUTES les parties visibles qui se comptent : têtes, yeux, bouches, cornes, "
              "pattes, bras, ailes, queues, tentacules, défenses… Chaque élément : {\"partie\": nom anglais au pluriel "
              "ou singulier, \"nombre\": entier, \"ou\": en anglais, où elles sont et comment elles sont disposées, "
              "ex. « each on its own long neck, side by side », « 3 on the middle head and 2 on each side head »} ; "
              "les nombres de la description sont exacts ; une partie qui va par paire chez l'animal mais qui est "
              "unique ici est placée (« a single horn in the middle of the forehead »)),\n"
              "\"en\" (la description complète en anglais, précise et visuelle : forme, posture, parties et leurs "
              "nombres, couleurs, matières ; 2 à 4 phrases ; rien qui la contredise),\n"
              "\"profil\" (en anglais, une phrase : à quoi ressemble sa silhouette vue de son côté gauche, "
              "y compris ce qu'il y a sous son corps).")
    out = _ask(SYS_BRIEF, prompt, seed, temperature=0.2, keep_alive=0)
    posture = _clean(out.get("posture"), 30).lower().replace(" ", "_")
    posture = posture if posture in POSTURES else next((p for p in POSTURES if p.split("_")[0] in posture), "")
    try:
        legs = max(0, min(int(out.get("pattes", 0)), 100))
    except (TypeError, ValueError):
        legs = 0
    en = _clean(out.get("en"), 800)
    if not posture or not en:
        raise WriterError("La plume n'a pas compris la description.")
    ref_posture = next((p for p, _ in refs if p), None)
    if ref_posture and not nb_archetypes.says_posture(description):  # le tyrannœil flotte, même si la plume hésite
        posture = ref_posture
    if posture in ("flotte", "rampe", "nage"):
        legs = 0
    return dict(posture=posture, pattes=legs, en=en, silhouette=_clean(out.get("silhouette"), 120),
                anatomie=_anatomy(out.get("anatomie")), profil=_clean(out.get("profil"), 300))


VISION = ("qwen2.5vl", "qwen3-vl", "gemma3", "llama3.2-vision", "minicpm-v", "llava")
LOOK = ("Look at this creature. Count carefully, one by one: how many heads, how many eyes in total, how many "
        "tentacles, and how many legs (jointed limbs with feet or paws that it could walk on; tentacles, fins, tails "
        "and dangling strands are NOT legs)? Answer in JSON with integer keys: heads, eyes, tentacles, legs.")


def vision_model():
    """Un modèle d'Ollama qui voit les images (gemma3, qwen2.5vl…), ou None."""
    try:
        names = [m["name"] for m in _get("/api/tags").get("models", [])]
    except Exception:
        return None
    for want in VISION:
        for n in names:
            if n.split(":")[0] == want:
                return n
    return None


def look(images, keep_alive=0):
    """Ce que le modèle de vision compte sur chaque image : [{"heads", "eyes", "legs"}] (vide si pas de modèle)."""
    import base64
    import io
    from PIL import Image
    m = vision_model()
    if not m:
        return []
    out = []
    for k, im in enumerate(images):
        im = im.convert("RGBA")
        box = im.getbbox() or (0, 0, *im.size)
        bg = Image.new("RGB", im.size, (200, 200, 200))
        bg.paste(im, mask=im.getchannel("A"))
        bg = bg.crop(box).resize((448, 448))
        buf = io.BytesIO()
        bg.save(buf, "PNG")
        body = {"model": m, "prompt": LOOK, "images": [base64.b64encode(buf.getvalue()).decode()], "format": "json",
                "stream": False, "think": False, "options": {"temperature": 0, "num_predict": 80},
                "keep_alive": keep_alive if k == len(images) - 1 else "2m"}
        req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out.append(json.loads(json.loads(r.read())["response"]))
        except Exception as exc:
            raise WriterError(f"Le modèle de vision n'a pas répondu ({exc}).")
    return out


def lore(name, description, seed=1):
    """Fiche façon Pokédex : type, espèce, taille, poids, habitat, description, histoire."""
    prompt = (f"Créature : « {name} » — {description}\n\nRédige sa fiche en JSON avec exactement ces clés :\n"
              f"\"type\" (un seul mot parmi : {', '.join(TYPES)}),\n"
              "\"espece\" (« la créature … » en 2 à 4 mots, comme « le Pokémon Graine »),\n"
              "\"taille\" (en mètres, ex. « 1,2 m »),\n\"poids\" (ex. « 85 kg »),\n\"habitat\" (une phrase),\n"
              "\"description\" (2 phrases, comme un naturaliste qui l'a observée : son allure ET son comportement "
              "(ce qu'elle mange, comment elle chasse ou se cache), avec tes propres mots ; ne recopie pas la description),\n"
              "\"histoire\" (2 ou 3 phrases : une légende, une croyance ou une anecdote, façon Pokédex),\n"
              "\"menace\" (entier de 1 à 5 : 1 = inoffensive, 3 = dangereuse, 5 = fléau d'une région ; sois juste, "
              "la plupart des créatures valent 2 ou 3),\n"
              f"\"attaques\" (exactement 2 attaques qu'elle utilise vraiment, d'après son corps : la 1re rapide, la 2e "
              f"sa plus forte. Chacune : {{\"nom\": nom court en français, \"genre\": un mot parmi {', '.join(nb_stats.GENRES)}, "
              f"\"element\": un mot parmi {', '.join(TYPES)}, \"description\": une phrase}}).")
    out = _ask(SYS_LORE, prompt, seed)
    fiche = {k: _clean(out.get(k)) for k in ("type", "espece", "taille", "poids", "habitat", "description", "histoire")}
    t = fiche["type"].lower()
    fiche["type"] = t if t in TYPES else next((x for x in TYPES if x in t), "esprit")
    fiche["menace"] = out.get("menace", 3)
    fiche["attaques"] = [dict(nom=_clean(a.get("nom"), 40), genre=_clean(a.get("genre"), 20).lower(),
                              element=_clean(a.get("element"), 20).lower(), description=_clean(a.get("description"), 200))
                         for a in (out.get("attaques") or []) if isinstance(a, dict)][:2]
    if not fiche["description"] or not fiche["histoire"]:
        raise WriterError("La fiche est incomplète, réessaie.")
    return fiche


if __name__ == "__main__":  # auto-test (Ollama requis) : python nb_writer.py
    print("modèle :", model())
    for d in ("une sphère de chair violette qui flotte dans les airs avec un seul œil géant", "une vache avec une corne centrale"):
        b = brief(d)
        print(b)
        assert b["posture"] in POSTURES and b["en"], b
    i = idea("lovecraft", 4)
    print(i)
    f = lore(i["name"] or "Créature", i["description"])
    assert f["type"] in TYPES and f["histoire"], f
    print(json.dumps(f, ensure_ascii=False, indent=1))
