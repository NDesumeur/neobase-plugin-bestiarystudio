# -*- coding: utf-8 -*-
"""NeoBestiary Studio - rareté, statistiques, faiblesses et attaques de combat.

Tout est calculé ici, pas par la plume : un modèle de langage met « légendaire » et 100 partout. La plume donne
seulement un prestige (0 à 100 : à quel point la créature impressionne) ; la rareté en découle, d'après des seuils
quand le bestiaire est petit, d'après le classement des créatures entre elles quand il est grand (les proportions
restent celles de WEIGHTS), avec un peu de hasard (un cran, une fois sur huit). Sans prestige (anciennes fiches) :
tirage pondéré, décalé d'un cran par la menace. Les statistiques se partagent un budget fixé par la rareté ; le
nombre d'attaques aussi (2 à 4).
"""
import hashlib
import random
import math
import re

import nb_moves

RARITIES = ("commun", "peu commun", "rare", "épique", "légendaire")
UNIQUE = "???"  # au-dessus de tout : une créature unique (n° 0, NeoMe), sa fiche est écrite à la main et ne se recalcule jamais
WEIGHTS = (50, 28, 14, 6, 2)  # sur 100 créatures : ~2 légendaires
THRESHOLDS = (40, 60, 75, 88)  # prestige -> rareté, tant que le bestiaire est trop petit pour un classement
RANKED = 10  # à partir de combien de créatures la rareté vient du classement
BUDGET = (180, 205, 230, 255, 285)  # somme PV + ATQ + DEF + VIT
MOVES = (2, 3, 3, 4, 4)  # nombre d'attaques selon la rareté
STATS = ("pv", "attaque", "defense", "vitesse")

GENRES = ("griffe", "morsure", "charge", "fouet", "corne", "dard", "etreinte", "projectile", "souffle", "rayon", "cri",
          "rafale", "pluie", "onde", "explosion", "soin", "renfort")
RANGED = {"projectile", "souffle", "rayon", "cri", "rafale", "pluie"}
AREA = {"onde", "explosion"}  # autour de la créature
SUPPORT = {"soin", "renfort"}  # sur elle-même, sans dégâts
CONTACT = set(GENRES) - RANGED - AREA - SUPPORT
# ce que chaque genre veut dire, pour la plume (et l'interface)
GENRE_FR = {
    "griffe": "coup de griffes", "morsure": "morsure", "charge": "charge du corps entier", "fouet": "coup de queue ou de liane",
    "corne": "coup de corne ou de défense", "dard": "piqûre d'un dard ou d'un aiguillon", "etreinte": "étreinte de tentacules ou d'anneaux",
    "projectile": "projectile lancé ou craché", "souffle": "souffle en cône", "rayon": "rayon d'énergie", "cri": "cri ou onde sonore",
    "rafale": "rafale de vent des ailes", "pluie": "pluie de projectiles qui tombe sur l'ennemi", "onde": "onde de choc autour d'elle",
    "explosion": "explosion autour d'elle", "soin": "soin (elle récupère des PV)", "renfort": "renfort (son attaque augmente)",
}
# parties du corps -> genres qu'elles permettent (pour remplacer un genre en double)
BODY = (("tail", "fouet"), ("horn", "corne"), ("tusk", "corne"), ("sting", "dard"), ("tentacle", "etreinte"),
        ("wing", "rafale"), ("fang", "morsure"), ("jaw", "morsure"), ("mouth", "morsure"), ("claw", "griffe"),
        ("talon", "griffe"), ("vine", "fouet"))
BY_TYPE = {"feu": "souffle", "eau": "projectile", "plante": "fouet", "vent": "rafale", "roche": "pluie", "glace": "pluie",
           "foudre": "rayon", "lumière": "rayon", "ombre": "onde", "esprit": "cri", "acier": "charge", "poison": "dard"}
STATUS = nb_moves.STATUS_OF  # élément -> statut infligé (la chance dépend de l'attaque : voir nb_moves)

# table des types, façon Pokémon : élément de l'attaque -> (×2 contre, ×½ contre, ×0 contre). Un double type multiplie
# les deux (×4, ×¼, ou une faiblesse que l'autre résiste : ×1). L'Arène lit les multiplicateurs dans la fiche de combat.
EFF = {  # chaque case a sa raison : « une attaque de <ligne> contre une créature de <type> ». Équilibrée : voir le test en bas
    "feu": (("plante", "glace", "acier"), ("feu", "eau", "roche", "lumière"), ()),  # brûle les plantes, fond la glace et le métal ; l'eau l'éteint, la pierre ne brûle pas, la lumière est déjà flamme
    "eau": (("feu", "roche", "acier"), ("eau", "plante", "glace"), ()),  # éteint le feu, use la pierre, rouille le métal ; les plantes la boivent, la glace la fige
    "plante": (("eau", "roche"), ("feu", "plante", "vent", "acier", "poison"), ()),  # boit l'eau, ses racines fendent la roche ; le venin la flétrit
    "vent": (("plante", "poison"), ("roche", "acier", "vent"), ()),  # couche les plantes, chasse les miasmes ; la pierre et le métal ne bougent pas
    "roche": (("feu", "glace", "vent", "foudre"), ("roche", "acier", "plante"), ()),  # étouffe le feu, brise la glace, abat ce qui vole, met la foudre à la terre ; les racines l'enserrent
    "glace": (("plante", "vent", "roche"), ("feu", "eau", "glace", "acier"), ()),  # gèle les plantes et les ailes, le gel fend la pierre
    "foudre": (("eau", "vent", "acier"), ("plante", "foudre", "esprit"), ("roche",)),  # l'eau, l'air et le métal conduisent ; la terre l'absorbe, un esprit n'a pas de corps
    "lumière": (("ombre", "esprit"), ("lumière", "plante", "feu"), ()),  # chasse les ténèbres et les fantômes ; les plantes s'en nourrissent, le feu brille déjà
    "ombre": (("lumière", "esprit"), ("ombre",), ()),  # éteint la lumière, dévore les esprits
    "esprit": (("poison", "ombre"), ("lumière", "esprit", "acier"), ()),  # purifie le poison, dissipe les cauchemars ; une machine n'a pas d'âme
    "acier": (("glace", "roche"), ("feu", "eau", "foudre", "acier"), ()),  # brise la glace et la pierre ; fond, rouille, conduit
    "poison": (("plante", "eau"), ("poison", "acier", "ombre"), ()),  # empoisonne les plantes et l'eau ; ronge mal le métal et ce qui n'a pas de chair
}


def mult(element, typ):
    """Multiplicateur d'une attaque de cet élément contre ce type (simple ou double)."""
    m = 1.0
    for t in split(typ):
        up, down, none = EFF.get(element, ((), (), ()))
        m *= 2 if t in up else .5 if t in down else 0 if t in none else 1
    return m


# type -> (faiblesses, résistances) d'un type simple, tiré de la table
CHART = {t: (tuple(e for e in EFF if t in EFF[e][0]), tuple(e for e in EFF if t in EFF[e][1] or t in EFF[e][2])) for t in EFF}
OPPOSED = {"ombre": "lumière", "lumière": "ombre"}  # « ombre et lumière » : NeoMe seul
# penchant de chaque type (multiplie le poids d'une statistique)
LEAN = {"feu": {"attaque": 1.25}, "eau": {"pv": 1.2}, "plante": {"pv": 1.2, "defense": 1.1},
        "vent": {"vitesse": 1.35}, "roche": {"defense": 1.4, "vitesse": .8}, "glace": {"defense": 1.15},
        "foudre": {"vitesse": 1.3, "attaque": 1.1}, "lumière": {"attaque": 1.1, "vitesse": 1.1},
        "ombre": {"attaque": 1.25, "defense": .9}, "esprit": {"vitesse": 1.15}, "acier": {"defense": 1.4},
        "poison": {"pv": 1.1, "attaque": 1.1}}
# posture -> penchant
POSTURE_LEAN = {"flotte": {"vitesse": 1.2, "defense": .9}, "vole": {"vitesse": 1.2, "defense": .9}, "rampe": {"vitesse": .85},
                "sautille": {"vitesse": 1.15}, "roule": {"defense": 1.15}, "glisse": {"pv": 1.2, "vitesse": .8},
                "enracine": {"defense": 1.3, "pv": 1.1, "vitesse": .6}, "nage": {"vitesse": 1.1}}
# ce que chaque type veut dire (pour la plume) et les mots qui le trahissent dans une description
TYPE_FR = {
    "feu": "flammes, lave, volcans, braises, chaleur, dragons cracheurs", "eau": "mer, rivières, poissons, coquillages, nage",
    "plante": "végétaux, fleurs, champignons, mousse, forêts, racines", "vent": "oiseaux, ailes, plumes, ciel, tempêtes, vol",
    "roche": "pierre, montagnes, cristaux bruts, carapaces minérales, grottes, terre",
    "glace": "froid, neige, givre, banquise, hiver", "foudre": "électricité, orage, éclairs, étincelles",
    "lumière": "soleil, aube, sacré, anges, éclat, or", "ombre": "nuit, ténèbres, cauchemars, prédateurs nocturnes",
    "esprit": "fantômes, âmes, magie de l'esprit, rêves, psychique", "acier": "métal, armures, machines, lames, rouages",
    "poison": "venin, toxines, marais putrides, acide, insectes piqueurs",
}
KEYWORDS = {
    "feu": r"feu|flamm|braise|brasier|lave|volcan|ardent|incandesc|brûl|cendre|fournaise|soufre|magma|chaleur|phénix|salamandre",
    "eau": r"\beau\b|mer\b|marin|océan|rivière|lac\b|poisson|nage|nageoire|écaille|coquill|crabe|pieuvre|corail|vague|aquat|requin|baleine|grenouill|algue",
    "plante": r"plante|fleur|feuill|racine|champignon|mousse|liane|arbre|écorce|bois\b|forêt|pétale|graine|bourgeon|ronce|épine|sève|lierre|cactus",
    "vent": r"vent|aile|plume|oiseau|ciel|nuage|tempête|tornade|vol\b|vole|aigle|chouette|hibou|corbeau|harpie|griffon|bec\b",
    "roche": r"roche|rocher|pierre|granit|caillou|montagne|grotte|cristal|gemme|golem|sable|terre\b|argile|boue|fossile|minéral|basalte",
    "glace": r"glace|givr|neige|gel[ée]?\b|froid|hiver|banquise|polaire|blizzard|yéti|stalact|frimas|boréal",
    "foudre": r"foudre|éclair|électri|orage|tonnerre|étincel|voltaï|statique|anguille",
    "lumière": r"lumi|soleil|solaire|aube|aurore|doré|\bor\b|sacré|divin|ange|halo|étoile|céleste|radieu|éclat",
    "ombre": r"ombre|ténèbr|nuit|noctur|obscur|cauchemar|sombre|noir|vampire|chauve-souris|corbeau|loup-garou|démon",
    "esprit": r"esprit|fantôme|spectr|âme|psych|rêve|songe|astral|hant|ectoplasm|mage|magie|illusion|médium|feu follet",
    "acier": r"acier|métal|fer\b|armure|lame|rouage|engrenage|machine|mécani|automate|chaîne|cuivre|bronze|robot",
    "poison": r"poison|venin|venim|toxi|acide|putri|pourri|marais|vase|limace|scorpion|araignée|crapaud|miasme|bave|guêpe|frelon",
}


def split(typ):
    """« feu et vent » -> ["feu", "vent"] : un double type s'écrit comme celui de NeoMe (« ombre et lumière »)."""
    return [t for t in str(typ or "").split(" et ") if t in CHART]


def type_scores(text):
    text = str(text or "").lower()
    return {t: len(re.findall(r"\b(?:" + KEYWORDS[t] + ")", text)) for t in KEYWORDS}  # début de mot : « étrange » n'est pas un ange


def choose_type(description, lore_text="", proposed=(), counts=None, exclude=()):
    """Le type de la créature. La plume en propose (du plus au moins crédible) ; les mots de la description comptent
    triple. Quand plusieurs types se valent, celui qui manque au bestiaire l'emporte : la plume choisit sinon
    presque toujours ombre ou esprit, et certains types n'apparaissent jamais."""
    score = {t: 0.0 for t in CHART if t not in exclude}
    for t, n in type_scores(description).items():
        if t in score:
            score[t] += 3 * min(n, 3)
    for t, n in type_scores(lore_text).items():
        if t in score:
            score[t] += min(n, 3)
    for i, t in enumerate(p for p in proposed if p in score):
        score[t] += (3, 2, 1)[i] if i < 3 else 0
    counts = counts or {}
    total = sum(counts.values()) or 1
    share = {t: counts.get(t, 0) / total for t in score}
    best = max(score.values())
    if best <= 0:  # rien ne parle de type : le moins représenté (jamais « esprit » par défaut)
        return min(score, key=lambda t: (share[t], t == "esprit", t))
    near = [t for t in score if score[t] >= best - 1.5 and score[t] > 0]
    # entre types qui se valent : le moins représenté, avec un léger avantage au score
    return max(near, key=lambda t: (score[t] - 6 * share[t], -share[t]))


def choose_types(description, lore_text="", proposed=(), counts=None, dual=False):
    """Un type, ou deux (« feu et vent ») : le 2e est le meilleur des autres, choisi de la même façon."""
    first = choose_type(description, lore_text, proposed, counts)
    if not dual:
        return first
    return first + " et " + choose_type(description, lore_text, proposed, counts, exclude=(first, OPPOSED.get(first)))


TOP = (50, 22, 8, 2)  # % du haut du classement : peu commun et mieux, rare et mieux, épique et mieux, légendaire


def _rng(key):
    return random.Random(int(hashlib.sha1(str(key).encode()).hexdigest()[:12], 16))


def _number(text, unit):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*" + unit, str(text or "").replace(" ", " "))
    return float(m.group(1).replace(",", ".")) if m else None


def tier_of(prestige, others=()):
    """Rareté (0..4) méritée par ce prestige : seuils fixes, ou rang parmi les autres créatures (bestiaire assez grand)."""
    others = [p for p in others if isinstance(p, (int, float))]
    if len(others) + 1 < RANKED:
        return sum(prestige >= t for t in THRESHOLDS)
    above = sum(p > prestige for p in others) + .5 * sum(p == prestige for p in others)
    top = 100 * above / len(others)  # % des autres créatures plus prestigieuses
    return sum(top < t for t in TOP)


def rarity(key, menace=3, prestige=None, fixed=None, others=()):
    """La rareté de la créature (stable pour une même créature et un même bestiaire)."""
    if fixed in RARITIES:
        return fixed
    r = _rng(f"rarete:{key}")
    if prestige is None:  # ancienne fiche : tirage pondéré, menace 1..5 décale d'un cran au plus
        tier = r.choices(range(5), WEIGHTS)[0]
        tier += 1 if menace >= 5 else -1 if menace <= 1 else 0
    else:
        tier = tier_of(prestige, others)
        roll = r.random()
        tier += 1 if roll < .06 else -1 if roll < .12 else 0  # un peu de hasard : un cran, une fois sur huit
    return RARITIES[max(0, min(4, tier))]


def stats(key, rare, typ, posture="", poids=None, taille=None):
    """{pv, attaque, defense, vitesse} : le budget de la rareté, réparti selon le gabarit, la posture et le type."""
    w = dict(pv=1.0, attaque=1.0, defense=1.0, vitesse=1.0)
    kg = _number(poids, "kg") or (_number(poids, "t") or 0) * 1000 or None
    if kg:
        heavy = max(-1.0, min(1.0, (len(str(int(kg))) - 2) / 2))  # 1 kg -> -0.5, 100 kg -> 0.5, 10 t -> 1
        w["pv"] *= 1 + .3 * heavy
        w["defense"] *= 1 + .25 * heavy
        w["vitesse"] *= 1 - .3 * heavy
    for k, f in POSTURE_LEAN.get(posture, {}).items():
        w[k] *= f
    for i, t in enumerate(split(typ)):  # le 2e type penche moitié moins
        for k, f in LEAN.get(t, {}).items():
            w[k] *= f ** (1 if i == 0 else .5)
    r = _rng(f"stats:{key}")
    for k in w:
        w[k] *= r.uniform(.88, 1.12)
    budget = BUDGET[RARITIES.index(rare)]
    total = sum(w.values())
    return {k: max(10, round(budget * v / total)) for k, v in w.items()}


def weaknesses(typ):
    """Faiblesses (×2, ×4), résistances (×½, ×¼), immunités (×0) et tous les multiplicateurs différents de 1."""
    m = {e: mult(e, typ) for e in EFF}
    by = lambda keep, rev: sorted((e for e in EFF if keep(m[e])), key=lambda e: -m[e] if rev else m[e])
    return dict(faiblesses=by(lambda v: v > 1, True), resistances=by(lambda v: 0 < v < 1, False), immunites=by(lambda v: v == 0, False),
                multiplicateurs={e: v for e, v in m.items() if v != 1})


def portee(genre):
    return "distance" if genre in RANGED else "zone" if genre in AREA else "soi" if genre in SUPPORT else "contact"


def attack_power(key, index, rare, genre, count=2):
    """De la plus rapide (1re) à la plus forte (dernière) ; à distance et en zone, un peu moins fort ; soutien : 0."""
    if genre in SUPPORT:
        return 0
    tier = RARITIES.index(rare)
    t = index / max(1, count - 1)
    lo, hi = round(30 + 28 * t), round(45 + 32 * t)
    p = _rng(f"attaque:{key}:{index}").randint(lo, hi) + 5 * tier
    return round(p * (.9 if genre in RANGED else .85 if genre in AREA else 1))


def _options(anatomy, typ):
    """Genres que le corps et le type rendent crédibles, du plus évident au plus général."""
    text = " ".join(anatomy or []).lower()
    out = [g for part, g in BODY if part in text]
    out += [BY_TYPE.get(typ, "onde"), "charge", "projectile", "onde", "cri", "griffe", "rayon", "explosion"]
    return list(dict.fromkeys(out))


def pick_moves(written, count, typ, anatomy=()):
    """count attaques parmi celles écrites (de la plus faible à la plus forte) : la 1re et les plus fortes, chacune
    d'un genre différent, au moins une au contact et une à distance ou en zone, le soutien jamais en premier."""
    moves = [dict(a) for a in written if isinstance(a, dict)]
    for a in moves:
        if a.get("genre") not in GENRES:
            a["genre"] = None
    chosen = moves[:1] + moves[1:][-(count - 1):] if len(moves) > count else moves
    used, opts = set(), _options(anatomy, typ)
    for a in chosen:  # genre manquant ou en double : un autre que le corps permet
        if not a["genre"] or a["genre"] in used:
            a["genre"] = next((g for g in opts if g not in used), "charge")
        used.add(a["genre"])
    while len(chosen) < min(count, 2):  # la plume en a écrit trop peu
        g = next(g for g in opts if g not in used)
        used.add(g)
        chosen.append(dict(nom="", genre=g, description=""))  # nom : celui du catalogue
    if chosen and chosen[0]["genre"] in SUPPORT and len(chosen) > 1:  # pas de soin pour ouvrir
        chosen.append(chosen.pop(0))
    kinds = {portee(a["genre"]) for a in chosen}
    if "contact" not in kinds and chosen:
        chosen[0]["genre"] = next((g for g in opts if g in CONTACT and g not in used), "charge")
    elif not kinds & {"distance", "zone"} and len(chosen) > 1:
        chosen[-1]["genre"] = next((g for g in opts if g in RANGED | AREA and g not in used), "projectile")
    return chosen


def card(key, fiche, posture="", fixed=None, others=(), anatomy=()):
    """Le bloc « combat » de la fiche à partir de ce que la plume a écrit (type, poids, prestige, attaques)."""
    typ = fiche.get("type") if split(fiche.get("type")) else "esprit"
    types = split(typ)
    try:
        menace = int(fiche.get("menace", 3))
    except (TypeError, ValueError):
        menace = 3
    prestige = fiche.get("prestige") if isinstance(fiche.get("prestige"), int) else None
    rare = rarity(key, menace, prestige, fixed, others)
    picked = pick_moves(fiche.get("attaques") or [], MOVES[RARITIES.index(rare)], types[0], anatomy)
    elems = [a.get("element") if a.get("element") in CHART else types[i % len(types)] for i, a in enumerate(picked)]
    if len(types) == 2 and types[1] not in elems and len(elems) > 1:  # double type : au moins une attaque du 2e
        elems[next((i for i in range(1, len(elems)) if picked[i]["genre"] not in SUPPORT), 1)] = types[1]
    moves = []
    for i, a in enumerate(picked):
        genre = a["genre"]
        elem = elems[i]
        tech = nb_moves.get(elem, genre)  # la mécanique : statut, baisses de stats, précision, coups multiples…
        power = attack_power(key, i, rare, genre, len(picked))
        m = dict(nom=a.get("nom") or tech["nom"], genre=genre, element=elem, description=a.get("description", ""),
                 puissance=round(power * tech["force"]), portee=portee(genre), technique=tech["nom"], id=tech["id"])
        m.update({k: v for k, v in tech.items() if k not in ("id", "nom", "element", "genre", "force")})
        m["effet_texte"] = nb_moves.describe(tech)
        if genre == "soin":
            m["effet"] = dict(soin=tech["soin"])  # % des PV max (anciennes versions de l'Arène)
        elif genre == "renfort":
            m["effet"] = dict(attaque=30)  # % d'attaque en plus (anciennes versions de l'Arène)
        moves.append(m)
    return dict(rarete=rare, rarete_fixe=fixed in RARITIES, prestige=prestige,
                stats=stats(key, rare, typ, posture, fiche.get("poids"), fiche.get("taille")),
                attaques=moves, **weaknesses(typ))


if __name__ == "__main__":
    from collections import Counter
    c = Counter(rarity(f"c{i}") for i in range(10000))
    assert c["légendaire"] < 400 and c["commun"] > 4000, c  # les rares restent rares
    s = stats("x", "rare", "roche", "quatre_pattes", "540 kg")
    assert abs(sum(s.values()) - BUDGET[2]) <= 4 and s["defense"] > s["vitesse"], s
    assert rarity("abc") == rarity("abc")
    # prestige : un dragon ancien n'est jamais commun, un rat jamais légendaire
    assert all(rarity(f"d{i}", prestige=95) in ("épique", "légendaire") for i in range(200))
    assert all(rarity(f"r{i}", prestige=10) in ("commun", "peu commun") for i in range(200))
    assert rarity("x", prestige=10, fixed="épique") == "épique"
    # classement : sur un grand bestiaire, le plus prestigieux est en haut, le moins en bas, proportions de WEIGHTS
    pool = list(range(0, 100, 5))
    assert tier_of(99, pool) == 4 and tier_of(0, pool) == 0, (tier_of(99, pool), tier_of(0, pool))
    tiers = Counter(tier_of(p, [q for q in range(100) if q != p]) for p in range(100))
    assert 45 <= tiers[0] <= 55 and 1 <= tiers[4] <= 3, tiers
    written = [dict(nom="Croc", genre="morsure"), dict(nom="Croc 2", genre="morsure"),
               dict(nom="Soin", genre="soin"), dict(nom="Brasier", genre="souffle", element="feu")]
    k = card("loup", dict(type="feu", poids="40 kg", prestige=50, attaques=written), anatomy=["1 tail: long"])
    genres = [a["genre"] for a in k["attaques"]]
    assert len(genres) == MOVES[RARITIES.index(k["rarete"])] and len(set(genres)) == len(genres), k
    assert k["attaques"][-1]["puissance"] > k["attaques"][0]["puissance"] and k["faiblesses"] == ["eau", "roche"], k
    assert k["attaques"][-1].get("statut", {}).get("nom") == "brûlure", k
    for n in (2, 3, 4):
        ms = pick_moves(written, n, "feu", ["1 tail"])
        assert len(ms) == n and ms[0]["genre"] not in SUPPORT and len({m["genre"] for m in ms}) == n, ms
        kinds = {portee(m["genre"]) for m in ms}
        assert kinds & {"distance", "zone"} and "contact" in kinds, ms
    assert len(pick_moves([], 2, "eau")) == 2
    gel = card("yeti", dict(type="glace", prestige=50, attaques=[dict(nom="Coup", genre="griffe"), dict(nom="Givre", genre="souffle")]))["attaques"]
    assert any(a.get("statut", {}).get("nom") == "gel" for a in gel) and gel[1]["precision"] == 90, gel
    assert card("x", dict(type="eau", attaques=[]))["attaques"][0]["nom"] in [m["nom"] for m in nb_moves.CATALOG.values()]
    lib = dict(ombre=24, esprit=21, eau=19, plante=15, feu=10, poison=4, roche=2)
    assert choose_type("un golem de pierre et de cristal", proposed=["esprit"], counts=lib) == "roche"
    assert choose_type("une créature étrange", proposed=["ombre", "glace"], counts=lib) == "glace"
    assert choose_type("un oiseau d'orage aux plumes qui crépitent d'éclairs", proposed=["vent", "foudre"], counts=lib) in ("vent", "foudre")
    assert choose_type("une chose", counts=lib) not in lib
    assert choose_type("un dragon de lave", proposed=["ombre"], counts=lib) == "feu"  # le texte prime
    d = card("oiseau", dict(type="vent et foudre", prestige=50, attaques=written[:2]))
    assert d["multiplicateurs"]["roche"] == 4 and d["faiblesses"][0] == "roche", d  # vent et foudre : la roche ×4
    w = weaknesses("roche et eau")
    assert w["immunites"] == ["foudre"] and w["multiplicateurs"]["plante"] == 4, w  # la roche ne craint pas la foudre, même mouillée
    w = weaknesses("plante et glace")
    assert w["multiplicateurs"]["feu"] == 4 and w["faiblesses"][0] == "feu", w  # double faiblesse : ×4
    w = weaknesses("feu et eau")
    assert w["multiplicateurs"]["feu"] == .25 and "plante" not in w["multiplicateurs"], w  # ×¼ ; plante : ×2 et ×½ -> ×1
    assert mult("poison", "acier") == .5 and mult("feu", "plante") == 2 and mult("eau", "eau") == .5
    assert [a["element"] for a in d["attaques"]][:2] == ["vent", "foudre"], d["attaques"]
    e = card("goule", dict(type="ombre et acier", prestige=50, attaques=[dict(nom="A", genre="morsure", element="ombre"), dict(nom="B", genre="cri", element="ombre")]))
    assert [a["element"] for a in e["attaques"]] == ["ombre", "acier"], e["attaques"]  # la plume n'a écrit que de l'ombre
    assert weaknesses("feu")["faiblesses"] == ["eau", "roche"] and set(weaknesses("feu")["resistances"]) == {"feu", "plante", "glace", "acier", "lumière"}
    for t in EFF:  # chaque type a au moins une faiblesse et deux résistances ou immunités
        w = weaknesses(t)
        assert w["faiblesses"] and len(w["resistances"]) + len(w["immunites"]) >= 2, (t, w)
        lg = lambda v: math.log2(v) if v else -2  # équilibre : attaque (×2 = +1, ×½ = -1, ×0 = -2) + défense, entre -2 et +2
        score = sum(lg(mult(t, d)) for d in EFF) - sum(lg(mult(a, t)) for a in EFF)
        assert abs(score) <= 2, (t, score)
    two = choose_types("un oiseau d'orage aux plumes qui crépitent d'éclairs", proposed=["vent", "foudre"], counts=lib, dual=True)
    assert set(split(two)) == {"vent", "foudre"} and " et " in two, two
    assert "lumière" not in choose_types("une ombre de la nuit noire, un démon solaire doré radieux", proposed=["ombre", "lumière"], dual=True)  # NeoMe seul
    assert split("ombre et lumière") == ["ombre", "lumière"] and split("") == []
    print("ok", dict(c), dict(tiers), k["rarete"], genres)
