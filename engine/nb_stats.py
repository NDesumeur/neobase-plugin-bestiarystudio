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
import re

RARITIES = ("commun", "peu commun", "rare", "épique", "légendaire")
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
# élément -> statut infligé (chance selon l'attaque)
STATUS = {"feu": "brûlure", "poison": "poison", "glace": "gel", "foudre": "paralysie"}

# type -> (faiblesses, résistances)
CHART = {
    "feu": (("eau", "roche"), ("plante", "glace")),
    "eau": (("foudre", "plante"), ("feu", "acier")),
    "plante": (("feu", "glace", "poison"), ("eau", "roche")),
    "vent": (("foudre", "roche"), ("plante",)),
    "roche": (("eau", "plante", "acier"), ("feu", "vent")),
    "glace": (("feu", "roche", "acier"), ("glace",)),
    "foudre": (("roche",), ("vent", "acier")),
    "lumière": (("ombre",), ("esprit",)),
    "ombre": (("lumière",), ("esprit", "poison")),
    "esprit": (("ombre",), ("poison",)),
    "acier": (("feu", "foudre"), ("glace", "poison", "plante")),
    "poison": (("esprit", "acier"), ("plante",)),
}
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
    for k, f in LEAN.get(typ, {}).items():
        w[k] *= f
    r = _rng(f"stats:{key}")
    for k in w:
        w[k] *= r.uniform(.88, 1.12)
    budget = BUDGET[RARITIES.index(rare)]
    total = sum(w.values())
    return {k: max(10, round(budget * v / total)) for k, v in w.items()}


def weaknesses(typ):
    weak, strong = CHART.get(typ, ((), ()))
    return dict(faiblesses=list(weak), resistances=list(strong))


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
        chosen.append(dict(nom=GENRE_FR[g].split(" (")[0].capitalize(), genre=g, description=""))
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
    typ = fiche.get("type", "esprit")
    try:
        menace = int(fiche.get("menace", 3))
    except (TypeError, ValueError):
        menace = 3
    prestige = fiche.get("prestige") if isinstance(fiche.get("prestige"), int) else None
    rare = rarity(key, menace, prestige, fixed, others)
    picked = pick_moves(fiche.get("attaques") or [], MOVES[RARITIES.index(rare)], typ, anatomy)
    moves = []
    for i, a in enumerate(picked):
        genre = a["genre"]
        elem = a.get("element") if a.get("element") in CHART else typ
        m = dict(nom=a.get("nom") or GENRE_FR[genre].capitalize(), genre=genre, element=elem,
                 description=a.get("description", ""), puissance=attack_power(key, i, rare, genre, len(picked)),
                 portee=portee(genre))
        if genre == "soin":
            m["effet"] = dict(soin=35)  # % des PV max
        elif genre == "renfort":
            m["effet"] = dict(attaque=30)  # % d'attaque en plus (cumulable 2 fois)
        else:
            status = "poison" if genre == "dard" else STATUS.get(elem)
            if status:
                m["statut"] = dict(nom=status, chance=30 if i == len(picked) - 1 or genre == "dard" else 20)
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
    print("ok", dict(c), dict(tiers), k["rarete"], genres)
