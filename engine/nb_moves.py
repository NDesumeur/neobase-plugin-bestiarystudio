# -*- coding: utf-8 -*-
"""NeoBestiary Studio - le catalogue des attaques : une par élément et par geste (12 x 17 = 204), chacune avec son nom
et sa mécanique : statut infligé avec un % de chance, statistiques baissées ou montées (chez l'ennemi ou chez soi),
précision, priorité, coups multiples, vol de vie, contrecoup, coups critiques, soins.

Le geste (griffe, souffle…) donne la forme de l'attaque et son animation ; l'élément donne le statut et la couleur.
nb_stats choisit les gestes de la créature, puis prend ici l'attaque qui correspond à (élément, geste).
"""
ELEMENTS = ("feu", "eau", "plante", "vent", "roche", "glace", "foudre", "lumière", "ombre", "esprit", "acier", "poison")
GENRES = ("griffe", "morsure", "charge", "fouet", "corne", "dard", "etreinte", "projectile", "souffle", "rayon", "cri",
          "rafale", "pluie", "onde", "explosion", "soin", "renfort")

# les noms, dans l'ordre de GENRES
NAMES = {
    "feu": ("Griffe ardente", "Croc de braise", "Ruée flamboyante", "Fouet de flammes", "Corne incandescente", "Dard brûlant",
            "Étreinte du brasier", "Boule de feu", "Souffle de fournaise", "Rayon calcinant", "Rugissement volcanique",
            "Bourrasque de cendres", "Pluie de braises", "Onde de chaleur", "Éruption", "Flamme vitale", "Feu intérieur"),
    "eau": ("Griffe d'écume", "Morsure des abysses", "Déferlante", "Fouet aquatique", "Corne de corail", "Dard d'oursin",
            "Étreinte des marées", "Jet d'eau", "Souffle d'embruns", "Hydrocanon", "Chant des sirènes", "Bourrasque marine",
            "Pluie battante", "Raz-de-marée", "Geyser", "Source de jouvence", "Peau ruisselante"),
    "plante": ("Griffe d'épines", "Morsure de ronce", "Charge du chêne", "Liane fouet", "Corne d'écorce", "Dard de chardon",
               "Étreinte des racines", "Mitraille de graines", "Souffle de spores", "Rayon chlorophylle",
               "Bruissement hypnotique", "Tourbillon de feuilles", "Pluie de pétales", "Onde sylvestre",
               "Éclosion explosive", "Sève guérisseuse", "Floraison"),
    "vent": ("Griffe tranchevent", "Bec du cyclone", "Charge aérienne", "Fouet de vent", "Corne du zéphyr", "Dard des nues",
             "Étreinte du tourbillon", "Lame d'air", "Souffle des tempêtes", "Vrille d'air", "Hurlement du vent", "Rafale",
             "Grêle de plumes", "Onde des cimes", "Ouragan", "Brise apaisante", "Vent arrière"),
    "roche": ("Griffe de silex", "Mâchoire de granit", "Charge du rocher", "Fouet de gravier", "Corne de basalte",
              "Dard d'obsidienne", "Étreinte de pierre", "Jet de pierres", "Souffle de poussière", "Rayon de quartz",
              "Grondement tellurique", "Rafale de sable", "Pluie de rochers", "Séisme", "Éboulement", "Cœur de pierre",
              "Carapace minérale"),
    "glace": ("Griffe de givre", "Croc glacé", "Charge du glacier", "Fouet de grésil", "Corne de glace",
              "Dard de stalactite", "Étreinte polaire", "Éclat de glace", "Souffle boréal", "Rayon gelant",
              "Cri du blizzard", "Rafale de neige", "Grêle", "Onde de froid", "Explosion cristalline", "Givre réparateur",
              "Armure de glace"),
    "foudre": ("Griffe électrique", "Croc tonnerre", "Charge foudroyante", "Fouet électrique", "Corne d'éclair",
               "Dard voltaïque", "Étreinte statique", "Boule d'éclair", "Souffle d'orage", "Rayon foudroyant",
               "Coup de tonnerre", "Rafale chargée", "Pluie d'éclairs", "Onde électrique", "Déflagration orageuse",
               "Recharge vitale", "Surtension"),
    "lumière": ("Griffe radieuse", "Morsure de l'aube", "Charge lumineuse", "Fouet de lumière", "Corne sacrée",
                "Dard de soleil", "Étreinte divine", "Orbe lumineux", "Souffle d'aurore", "Rayon sacré", "Chant céleste",
                "Rafale étincelante", "Pluie d'étoiles", "Onde de clarté", "Supernova", "Lumière guérisseuse",
                "Halo protecteur"),
    "ombre": ("Griffe d'ombre", "Morsure nocturne", "Charge des ténèbres", "Fouet ténébreux", "Corne maudite",
              "Dard obscur", "Étreinte des ombres", "Sphère d'ombre", "Souffle de la nuit", "Rayon noir", "Murmure funeste",
              "Rafale de corbeaux", "Pluie de ténèbres", "Onde de terreur", "Implosion obscure", "Festin d'ombres",
              "Pacte nocturne"),
    "esprit": ("Griffe spectrale", "Morsure d'âme", "Charge fantôme", "Fouet psychique", "Corne astrale",
               "Dard des songes", "Étreinte spectrale", "Orbe psychique", "Souffle éthéré", "Rayon psychique",
               "Cri d'outre-tombe", "Rafale astrale", "Pluie d'âmes", "Onde mentale", "Éclatement psychique", "Méditation",
               "Transe"),
    "acier": ("Griffe d'acier", "Mâchoire de fer", "Charge blindée", "Fouet de chaînes", "Corne d'acier", "Dard métallique",
              "Étreinte d'acier", "Mitraille", "Souffle de forge", "Rayon miroir", "Grincement métallique",
              "Rafale de lames", "Pluie de clous", "Onde métallique", "Explosion de scories", "Réparation", "Blindage"),
    "poison": ("Griffe toxique", "Croc venimeux", "Charge putride", "Fouet empoisonné", "Corne de venin", "Dard toxique",
               "Étreinte visqueuse", "Crachat acide", "Souffle toxique", "Rayon corrosif", "Sifflement venimeux",
               "Rafale de miasmes", "Pluie acide", "Onde toxique", "Explosion fétide", "Antidote", "Mue venimeuse"),
}

# le statut de chaque élément (eau : pas de statut, elle trempe et ralentit)
STATUS_OF = {"feu": "brûlure", "glace": "gel", "foudre": "paralysie", "poison": "poison", "plante": "sommeil",
             "vent": "confusion", "esprit": "confusion", "ombre": "saignement", "acier": "saignement", "roche": "peur",
             "lumière": "éblouissement"}
# ce que fait chaque statut (le combat de l'Arène suit ces règles)
STATUSES = {
    "brûlure": "perd 1/16 de ses PV à chaque tour et frappe 25 % moins fort",
    "poison": "perd 1/10 de ses PV à chaque tour",
    "saignement": "perd 1/12 de ses PV à chaque tour, et sa défense baisse d'un cran",
    "gel": "ne peut plus agir, jusqu'à ce que la glace fonde (3 chances sur 10 par tour)",
    "paralysie": "deux fois plus lente, et 1 chance sur 4 de ne pas agir",
    "sommeil": "dort 1 à 3 tours sans agir",
    "confusion": "1 chance sur 3 de se frapper elle-même, pendant 2 à 4 tours",
    "éblouissement": "rate une attaque sur trois pendant 3 tours",
    "peur": "recule et perd son action si elle n'a pas encore joué ce tour-ci",
}
STATS = ("attaque", "defense", "vitesse", "precision")


def _eff(stat, levels, target="cible", chance=100):
    return dict(stat=stat, niveaux=levels, cible=target, chance=chance)


# la mécanique de chaque geste ; force : multiplie la puissance calculée par nb_stats
def _base(genre, elem):
    st = STATUS_OF.get(elem)
    soak = [_eff("vitesse", -1, chance=30)] if elem == "eau" else []  # l'eau trempe : à la place d'un statut
    m = dict(force=1.0)
    if genre == "griffe":
        m.update(critique=3, statut=dict(nom=st, chance=10) if st else None, effets=soak and [_eff("vitesse", -1, chance=15)])
    elif genre == "morsure":
        m.update(statut=dict(nom="poison" if elem == "poison" else "peur", chance=30 if elem == "poison" else 20))
    elif genre == "charge":
        m.update(force=1.18, recul=20, statut=dict(nom="peur", chance=10) if elem in ("roche", "acier") else None)
    elif genre == "fouet":
        m.update(force=.9, effets=[_eff("vitesse", -1, chance=30)])
    elif genre == "corne":
        m.update(force=1.1, precision=90, effets=[_eff("defense", -1, chance=30)])
    elif genre == "dard":
        m.update(force=.8, statut=dict(nom=st or "poison", chance=30), effets=soak)
    elif genre == "etreinte":
        m.update(force=.85, drain=40, effets=[_eff("vitesse", -1, chance=50)])
    elif genre == "projectile":
        m.update(force=.45, coups=[2, 3], statut=dict(nom=st, chance=10) if st else None)
    elif genre == "souffle":
        m.update(precision=90, statut=dict(nom=st, chance=25) if st else None, effets=soak and [_eff("vitesse", -1, chance=40)])
    elif genre == "rayon":
        m.update(force=1.22, precision=85, effets=[_eff("attaque", -1, "soi")])  # tout donner : on s'épuise un peu
    elif genre == "cri":
        m.update(force=.6, effets=[_eff("attaque", -1)],
                 statut=dict(nom=st if st in ("confusion", "sommeil", "peur") else "confusion",
                             chance=30 if elem in ("esprit", "vent", "plante") else 15))
    elif genre == "rafale":
        m.update(force=.8, priorite=1, effets=[_eff("precision", -1, chance=20)])
    elif genre == "pluie":
        m.update(force=.32, coups=[2, 4], precision=90)
    elif genre == "onde":
        m.update(force=.95, effets=[_eff("defense", -1, chance=30)], statut=dict(nom=st, chance=15) if st else None)
    elif genre == "explosion":
        m.update(force=1.35, precision=90, recul=33)
    elif genre == "soin":
        heal = {"plante": 50, "eau": 40, "lumière": 40, "ombre": 30, "esprit": 30, "poison": 30}.get(elem, 35)
        m.update(force=0, soin=heal, purge=elem in ("eau", "lumière", "poison"),
                 effets={"ombre": [_eff("attaque", 1, "soi")], "esprit": [_eff("defense", 1, "soi")],
                         "roche": [_eff("defense", 1, "soi")], "vent": [_eff("vitesse", 1, "soi")]}.get(elem, []))
    elif genre == "renfort":
        m.update(force=0, effets={
            "feu": [_eff("attaque", 2, "soi")], "roche": [_eff("defense", 2, "soi")], "acier": [_eff("defense", 2, "soi")],
            "vent": [_eff("vitesse", 2, "soi")], "foudre": [_eff("vitesse", 1, "soi"), _eff("attaque", 1, "soi")],
            "glace": [_eff("defense", 1, "soi"), _eff("precision", 1, "soi")],
            "lumière": [_eff("precision", 1, "soi"), _eff("defense", 1, "soi")],
            "ombre": [_eff("attaque", 1, "soi"), _eff("vitesse", 1, "soi")],
            "esprit": [_eff("attaque", 1, "soi"), _eff("defense", 1, "soi")],
            "plante": [_eff("defense", 1, "soi")], "eau": [_eff("defense", 1, "soi")],
            "poison": [_eff("attaque", 1, "soi"), _eff("defense", 1, "soi")]}[elem])
        if elem in ("plante", "eau"):
            m["soin"] = 15
    return {k: v for k, v in m.items() if v is not None and v is not False and v != []}


CATALOG = {(e, g): dict(id=f"{e}:{g}", nom=NAMES[e][i], element=e, genre=g, **_base(g, e))
           for e in ELEMENTS for i, g in enumerate(GENRES)}


RARETES = ("commun", "peu commun", "rare", "épique", "légendaire")  # « ??? » : les attaques signature de NeoMe, à lui seul
SHARE = (.50, .28, .14, .06, .02)  # comme les créatures : la moitié communes, 2 % légendaires


def value(m):
    """Ce que vaut une attaque : ses dégâts attendus et tout ce qu'elle fait en plus (statut, stats, priorité, soin…)."""
    if m["genre"] in ("soin", "renfort"):  # sans dégâts : le soin et les crans gagnés font la valeur
        return 50 + m.get("soin", 0) + 15 * m.get("purge", 0) + .2 * sum(e["chance"] * e["niveaux"] for e in m.get("effets") or [])
    hits = sum(m["coups"]) / 2 if m.get("coups") else 1
    v = 100 * m.get("force", 1) * hits + 10 * m.get("priorite", 0) + .3 * m.get("drain", 0) + 2 * m.get("critique", 0)
    v -= .2 * m.get("recul", 0) + .3 * (100 - m.get("precision", 100))
    if m.get("statut"):
        v += .5 * m["statut"]["chance"]
    for e in m.get("effets") or []:  # un cran baissé chez l'ennemi ou gagné chez soi : un plus ; perdu chez soi : un moins
        v += .1 * e["chance"] * abs(e["niveaux"]) * (1 if (e["cible"] == "soi") == (e["niveaux"] > 0) else -1)
    return v


def _rarities():
    ranked = sorted(CATALOG.values(), key=lambda m: (value(m), m["id"]))
    for i, m in enumerate(ranked):
        top, k = 1 - i / len(ranked), 0
        while k < 4 and top <= sum(SHARE[k + 1:]):
            k += 1
        m["rarete"] = RARETES[k]


_rarities()


def get(element, genre):
    return CATALOG.get((element, genre))


def describe(m):
    """Une ligne lisible : ce que fait l'attaque, avec ses chances."""
    out = []
    if m.get("soin"):
        out.append(f"soigne {m['soin']} % des PV" + (" et guérit les statuts" if m.get("purge") else ""))
    if m.get("coups"):
        out.append(f"frappe {m['coups'][0]} à {m['coups'][1]} fois")
    if m.get("priorite"):
        out.append("agit en premier")
    if m.get("critique"):
        out.append("coups critiques fréquents")
    if m.get("drain"):
        out.append(f"vole {m['drain']} % des dégâts")
    if m.get("recul"):
        out.append(f"contrecoup de {m['recul']} %")
    if m.get("statut"):
        s = m["statut"]
        out.append(f"{s['chance']} % de chance : {s['nom']}")
    for e in m.get("effets", []):
        word = {"attaque": "attaque", "defense": "défense", "vitesse": "vitesse", "precision": "précision"}[e["stat"]]
        who = "la sienne" if e["cible"] == "soi" else "de l'ennemi"
        move = f"{word} {'+' if e['niveaux'] > 0 else '−'}{abs(e['niveaux'])} ({who})"
        out.append(move if e["chance"] >= 100 else f"{e['chance']} % de chance : {move}")
    if m.get("precision", 100) < 100:
        out.append(f"précision {m['precision']} %")
    return " · ".join(out)


if __name__ == "__main__":
    names = [m["nom"] for m in CATALOG.values()]
    assert len(CATALOG) == 204 and len(set(names)) == 204, [n for n in names if names.count(n) > 1]
    assert all(len(NAMES[e]) == len(GENRES) for e in ELEMENTS)
    assert all(describe(m) or m["genre"] in ("charge",) for m in CATALOG.values())
    from collections import Counter
    r = Counter(m["rarete"] for m in CATALOG.values())
    assert r["commun"] > 90 and 2 <= r["légendaire"] <= 6 and len(r) == 5, r
    assert get("feu", "explosion")["rarete"] != "commun" and get("eau", "pluie")["rarete"] in ("commun", "peu commun")
    print(r, [m["nom"] for m in CATALOG.values() if m["rarete"] == "légendaire"])
    kinds = {k for m in CATALOG.values() for k in m} - {"id", "nom", "element", "genre", "force", "rarete"}
    print("ok", len(CATALOG), "attaques ;", sorted(kinds))
    for k in (("glace", "souffle"), ("feu", "renfort"), ("eau", "soin"), ("vent", "rafale")):
        print(CATALOG[k]["nom"], "-", describe(CATALOG[k]))
