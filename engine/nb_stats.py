# -*- coding: utf-8 -*-
"""NeoBestiary Studio - rareté, statistiques, faiblesses et puissance des attaques.

Tout est calculé ici, pas par la plume : un modèle de langage met « légendaire » et 100 partout. La rareté est tirée
au sort (graine de la créature, donc stable), pondérée pour que les légendaires restent rares ; la menace estimée par
la plume ne la décale que d'un cran au plus. Les statistiques se partagent un budget fixé par la rareté.
"""
import hashlib
import random
import re

RARITIES = ("commun", "peu commun", "rare", "épique", "légendaire")
WEIGHTS = (50, 28, 14, 6, 2)  # sur 100 créatures : ~2 légendaires
BUDGET = (180, 205, 230, 255, 285)  # somme PV + ATQ + DEF + VIT
STATS = ("pv", "attaque", "defense", "vitesse")

GENRES = ("griffe", "morsure", "charge", "projectile", "souffle", "onde", "rayon")
RANGED = {"projectile", "souffle", "rayon"}

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


def _rng(key):
    return random.Random(int(hashlib.sha1(str(key).encode()).hexdigest()[:12], 16))


def _number(text, unit):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*" + unit, str(text or "").replace(" ", " "))
    return float(m.group(1).replace(",", ".")) if m else None


def rarity(key, menace=3):
    """Tirage pondéré, stable pour une même créature ; menace 1..5 décale d'un cran au plus."""
    tier = _rng(f"rarete:{key}").choices(range(5), WEIGHTS)[0]
    tier += 1 if menace >= 5 else -1 if menace <= 1 else 0
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
    if posture in ("flotte", "vole"):
        w["vitesse"] *= 1.2
        w["defense"] *= .9
    elif posture == "rampe":
        w["vitesse"] *= .85
    for k, f in LEAN.get(typ, {}).items():
        w[k] *= f
    r = _rng(f"stats:{key}")
    for k in w:
        w[k] *= r.uniform(.88, 1.12)
    budget = BUDGET[RARITIES.index(rare)]
    total = sum(w.values())
    out = {k: max(10, round(budget * v / total)) for k, v in w.items()}
    return out


def weaknesses(typ):
    weak, strong = CHART.get(typ, ((), ()))
    return dict(faiblesses=list(weak), resistances=list(strong))


def attack_power(key, index, rare, genre):
    """1re attaque : rapide et modeste ; 2e : la plus forte. Les attaques à distance frappent un peu moins fort."""
    tier = RARITIES.index(rare)
    lo, hi = ((30, 45), (55, 75))[min(index, 1)]
    p = _rng(f"attaque:{key}:{index}").randint(lo, hi) + 5 * tier
    return round(p * (.9 if genre in RANGED else 1))


def card(key, fiche, posture=""):
    """Le bloc « combat » de la fiche à partir de ce que la plume a écrit (type, poids, menace, attaques)."""
    typ = fiche.get("type", "esprit")
    try:
        menace = int(fiche.get("menace", 3))
    except (TypeError, ValueError):
        menace = 3
    rare = rarity(key, menace)
    moves = []
    for i, a in enumerate((fiche.get("attaques") or [])[:2]):
        genre = a.get("genre") if a.get("genre") in GENRES else ("griffe", "projectile")[i]
        elem = a.get("element") if a.get("element") in CHART else typ
        moves.append(dict(nom=a.get("nom") or ("Coup", "Assaut")[i], genre=genre, element=elem,
                          description=a.get("description", ""), puissance=attack_power(key, i, rare, genre),
                          portee="distance" if genre in RANGED else "contact"))
    return dict(rarete=rare, stats=stats(key, rare, typ, posture, fiche.get("poids"), fiche.get("taille")),
                attaques=moves, **weaknesses(typ))


if __name__ == "__main__":
    from collections import Counter
    c = Counter(rarity(f"c{i}") for i in range(10000))
    assert c["légendaire"] < 400 and c["commun"] > 4000, c  # les rares restent rares
    s = stats("x", "rare", "roche", "quatre_pattes", "540 kg")
    assert abs(sum(s.values()) - BUDGET[2]) <= 4 and s["defense"] > s["vitesse"], s
    assert rarity("abc") == rarity("abc")
    k = card("loup", dict(type="feu", poids="40 kg", menace=3,
                          attaques=[dict(nom="Croc", genre="morsure"), dict(nom="Brasier", genre="souffle", element="feu")]))
    assert k["attaques"][1]["puissance"] > k["attaques"][0]["puissance"] and k["faiblesses"] == ["eau", "roche"], k
    print("ok", dict(c), k)
