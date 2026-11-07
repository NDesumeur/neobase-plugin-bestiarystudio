# -*- coding: utf-8 -*-
"""NeoBestiary Studio - variantes de couleur : la même créature, au pixel près, avec une autre palette.

« chromatique » tourne les teintes (angle tiré de la créature, donc stable) et monte la rareté d'un cran ; une
variante d'élément (glace, feu...) repeint la créature dans les couleurs de cet élément et en prend le type.
Le contour presque noir et les reflets presque blancs ne bougent pas : les yeux et le trait restent lisibles.
"""
import colorsys
import hashlib

from PIL import Image

import nb_attack
import nb_moves
import nb_stats

ELEMENTS = tuple(nb_attack.PALETTE)
VARIANTS = ("chromatique",) + ELEMENTS


def label(vid):
    if vid == "chromatique":
        return "chromatique"
    return ("d'" if vid[0] in "aeiouéèêàâîôû" else "de ") + vid


def _angle(key):
    return 120 + int(hashlib.sha1(key.encode()).hexdigest(), 16) % 121  # 120 à 240° : bien différent


def _keep(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return v < .16 or (v > .92 and s < .12)


def _ramp(element):
    """Dégradé de l'élément du plus sombre au plus clair (sans le contour, gardé à part)."""
    return [nb_attack._rgb(h)[:3] for h in nb_attack.PALETTE[element]]


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def color_fn(vid, key, colors):
    """Fonction couleur -> couleur pour toute la créature (mêmes réglages sur toutes ses images)."""
    if vid == "chromatique":
        turn = _angle(key) / 360

        def f(c):
            if _keep(*c):
                return c
            h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
            r, g, b = colorsys.hsv_to_rgb((h + turn) % 1, min(1, s * 1.1), v)
            return round(r * 255), round(g * 255), round(b * 255)
        return f
    ramp = _ramp(vid)
    lums = [_lum(c) for c in colors if not _keep(*c)] or [0, 255]
    lo, hi = min(lums), max(lums)

    def f(c):
        if _keep(*c):
            return c
        t = (_lum(c) - lo) / max(1, hi - lo)  # luminosité étirée sur toute la créature
        t = t * (len(ramp) - 1)
        i = min(int(t), len(ramp) - 2)
        target = _mix(ramp[i], ramp[i + 1], t - i)
        return _mix(target, c, .15)  # un peu de la couleur d'origine : les parties restent distinctes
    return f


def _lum(c):
    return .299 * c[0] + .587 * c[1] + .114 * c[2]


def colors_of(images):
    seen = set()
    for im in images:
        for n, c in im.convert("RGBA").getcolors(CELLS) or []:
            if c[3]:
                seen.add(c[:3])
    return seen


CELLS = 64 * 64 * 16


def recolor(im, f, cache):
    im = im.convert("RGBA")
    out = Image.new("RGBA", im.size)
    src, dst = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = src[x, y]
            if a:
                k = (r, g, b)
                if k not in cache:
                    cache[k] = f(k)
                dst[x, y] = cache[k] + (a,)
    return out


def card(base, vid):
    """La fiche de combat de la variante : chromatique = un cran de rareté de plus ; élément = nouveau type."""
    out = dict(base, stats=dict(base["stats"]), attaques=[dict(a) for a in base["attaques"]])
    if vid == "chromatique":
        if base["rarete"] not in nb_stats.RARITIES:
            return out  # rien au-dessus d'une créature unique
        i = nb_stats.RARITIES.index(base["rarete"])
        out["rarete"] = nb_stats.RARITIES[min(i + 1, len(nb_stats.RARITIES) - 1)]
        return out
    out.update(nb_stats.weaknesses(vid))
    keys = ("coups", "critique", "drain", "effets", "precision", "priorite", "purge", "recul", "soin", "statut")
    for a in out["attaques"]:
        a["element"] = vid
        a.pop("cree", None), a.pop("show", None)  # la planche d'une attaque créée garde ses couleurs : pas pour un autre élément
        old, tech = nb_moves.CATALOG.get(tuple(a.get("id", ":").split(":"))), nb_moves.get(vid, a["genre"])
        if old and tech:  # la technique du même geste dans le nouvel élément (statut, effets…)
            if a["nom"] == old["nom"]:
                a["nom"] = tech["nom"]
            if old["force"]:
                a["puissance"] = round(a["puissance"] * tech["force"] / old["force"])
            for k in keys:
                a.pop(k, None)
            a.update({k: v for k, v in tech.items() if k in keys}, id=tech["id"], technique=tech["nom"],
                     effet_texte=nb_moves.describe(tech))
            if a["genre"] == "soin":
                a["effet"] = dict(soin=tech["soin"])
    return out


if __name__ == "__main__":
    from PIL import ImageDraw
    im = Image.new("RGBA", (64, 64))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, 54, 54), fill=(200, 60, 40, 255), outline=(10, 10, 10, 255), width=2)
    d.rectangle((24, 24, 28, 28), fill=(250, 250, 250, 255))
    cols = colors_of([im])
    for vid in VARIANTS:
        out = recolor(im, color_fn(vid, "x", cols), {})
        assert out.getpixel((1, 1))[3] == 0 and out.getpixel((26, 26)) == (250, 250, 250, 255)  # fond et reflet gardés
        assert out.getpixel((40, 40)) != (200, 60, 40, 255), vid
    assert color_fn("chromatique", "x", cols)((200, 60, 40)) == color_fn("chromatique", "x", cols)((200, 60, 40))
    base = nb_stats.card("loup", dict(type="feu", attaques=[dict(nom="Croc", genre="morsure")]))
    assert card(base, "glace")["faiblesses"] == ["feu", "roche", "acier"] and card(base, "glace")["attaques"][0]["element"] == "glace"
    assert nb_stats.RARITIES.index(card(base, "chromatique")["rarete"]) >= nb_stats.RARITIES.index(base["rarete"])
    assert label("eau") == "d'eau" and label("glace") == "de glace"
    g = card(base, "glace")["attaques"][0]
    assert g["id"] == "glace:morsure" and g["technique"] == "Croc glacé" and g["statut"]["nom"] == "peur", g
    print("ok")
