# -*- coding: utf-8 -*-
"""NeoBestiary Studio - les effets signés : un visuel propre à chaque attaque (élément x geste), au lieu de la forme
commune du geste repeinte aux couleurs de l'élément.

Chaque élément a son motif dessiné au pixel (flammèche, goutte, feuille, volute, éclat de roche, cristal, éclair,
étincelle, ombre, orbe, lame, bulle) ; chaque geste a sa façon de le disposer et de le faire bouger sur les 4 images
(élan, frappe, impact, retour) : griffes, mâchoires, charge, fouet, projectile, souffle, rayon, pluie, onde, explosion.
12 éléments x 10 gestes = 120 visuels. Plus les 4 visuels de NeoMe (créature n° 0), qui n'appartiennent qu'à lui.
Les gestes sans visuel signé (corne, dard, étreinte, cri, rafale, soin, renfort) gardent leur forme commune.
Dessiné vers le bas, ancre en haut (32, 4), comme nb_attack ; onde et explosion sont centrées (32, 32).
"""
import math
import random

from PIL import Image, ImageDraw

CELL = 64
AX, AY = 32, 4


# ------------------------------------------------------------------ les motifs des éléments
# (d, x, y, s, k, pal) : centré en (x, y), taille s (2..10), variante k ; pal = (contour, moyen, clair, cœur)
def _feu(d, x, y, s, k, p):
    d.polygon([(x - s, y + s), (x + s, y + s), (x + (k % 3 - 1), y - 2 * s)], fill=p[1])
    d.polygon([(x - s // 2, y + s), (x + s // 2, y + s), (x, y - s)], fill=p[2])
    d.point((x, y + s // 2), fill=p[3])


def _eau(d, x, y, s, k, p):
    d.polygon([(x, y - 2 * s + 1), (x - s, y), (x + s, y)], fill=p[2])
    d.ellipse((x - s, y - s, x + s, y + s), fill=p[2], outline=p[1])
    d.point((x - s // 2, y - s // 2), fill=p[3])


def _plante(d, x, y, s, k, p):
    a = math.radians(35 + 50 * (k % 4))
    ux, uy, vx, vy = math.cos(a) * s * 1.6, math.sin(a) * s * 1.6, -math.sin(a) * s * .6, math.cos(a) * s * .6
    d.polygon([(x - ux, y - uy), (x + vx, y + vy), (x + ux, y + uy), (x - vx, y - vy)], fill=p[2])
    d.line((x - ux, y - uy, x + ux, y + uy), fill=p[1])


def _vent(d, x, y, s, k, p):
    d.arc((x - s, y - s, x + s, y + s), 200 + 30 * (k % 3), 520 + 30 * (k % 3), fill=p[3], width=1)
    d.arc((x - s // 2, y - s // 2, x + s // 2, y + s // 2), 0, 270, fill=p[2])


def _roche(d, x, y, s, k, p):
    r = random.Random(k * 31 + s)
    pts = [(x + math.cos(t) * s * r.uniform(.7, 1.1), y + math.sin(t) * s * r.uniform(.7, 1.1)) for t in
           [i * math.pi / 3 for i in range(6)]]
    d.polygon(pts, fill=p[1], outline=p[0])
    d.polygon([pts[3], pts[4], (x, y)], fill=p[2])


def _glace(d, x, y, s, k, p):
    d.polygon([(x, y - s - 1), (x + s // 2 + 1, y), (x, y + s + 1), (x - s // 2 - 1, y)], fill=p[2], outline=p[1])
    d.line((x, y - s, x, y + s), fill=p[3])
    if s > 3:
        d.line((x - s, y, x + s, y), fill=p[3])


def _foudre(d, x, y, s, k, p):
    sg = 1 if k % 2 else -1
    pts = [(x - sg * s, y - s - 1), (x + sg * 1, y - 1), (x - sg * 1, y + 1), (x + sg * s, y + s + 1)]
    d.line(pts, fill=p[2], width=2)
    d.line(pts, fill=p[3], width=1)


def _lumiere(d, x, y, s, k, p):
    d.line((x - s, y, x + s, y), fill=p[2])
    d.line((x, y - s, x, y + s), fill=p[2])
    d.line((x - s // 2, y - s // 2, x + s // 2, y + s // 2), fill=p[1])
    d.line((x - s // 2, y + s // 2, x + s // 2, y - s // 2), fill=p[1])
    d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=p[3])


def _ombre(d, x, y, s, k, p):
    d.ellipse((x - s, y - s, x + s, y + s), fill=p[1])
    o = (k % 3 - 1) * max(1, s // 3)
    d.ellipse((x - s + 2 + o, y - s + 1, x + s - 2 + o, y + s - 3), fill=p[0])
    d.point((x + o, y - s + 1), fill=p[2])


def _esprit(d, x, y, s, k, p):
    d.ellipse((x - s, y - s, x + s, y + s), outline=p[3])
    d.ellipse((x - s // 2, y - s // 2, x + s // 2, y + s // 2), fill=p[2])
    d.point((x, y), fill=p[3])


def _acier(d, x, y, s, k, p):
    a = math.radians(45 + 90 * (k % 2))
    ux, uy = math.cos(a) * s * 1.4, math.sin(a) * s * 1.4
    d.polygon([(x - ux, y - uy), (x + uy * .3, y - ux * .3), (x + ux, y + uy)], fill=p[2], outline=p[1])
    d.line((x - ux, y - uy, x + ux, y + uy), fill=p[3])


def _poison(d, x, y, s, k, p):
    d.ellipse((x - s, y - s, x + s, y + s), fill=p[1], outline=p[2])
    d.ellipse((x - s // 2, y - s // 2, x, y), fill=p[2])
    d.point((x - s // 2, y - s // 2), fill=p[3])
    if s > 3:
        d.line((x + s // 2, y + s, x + s // 2, y + s + 2), fill=p[1])


MOTIF = {"feu": _feu, "eau": _eau, "plante": _plante, "vent": _vent, "roche": _roche, "glace": _glace,
         "foudre": _foudre, "lumière": _lumiere, "ombre": _ombre, "esprit": _esprit, "acier": _acier, "poison": _poison}
MOTIF = {e: (lambda f: lambda d, x, y, s, k, p: f(d, x, y, max(2, s), k, p))(f) for e, f in MOTIF.items()}  # 2 px au moins


# ------------------------------------------------------------------ les gestes : où vont les motifs, image par image
def _along(pts, step):
    """Des points régulièrement espacés le long d'une ligne brisée."""
    out, carry = [], 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = carry
        while t <= L:
            out.append((x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L))
            t += step
        carry = t - L
    return out


def _arc(cx, cy, r, a0, a1, n=12):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def _put(d, m, pts, s, p, k0=0):
    for k, (x, y) in enumerate(pts):
        m(d, round(x), round(y), s, k + k0, p)


def _griffe(d, m, i, p, e):
    if i == 0:
        return False
    ln = (12, 28, 28)[i - 1]
    for n, k in enumerate((-9, 0, 9)):
        pts = _arc(AX - 18 + k, AY + 2, 22 + k // 2, 10, 10 + ln * 2.6)
        _put(d, m, _along(pts, 6), 2 if i == 3 else 3, p, n)
    return True


def _morsure(d, m, i, p, e):
    if i == 0:
        return False
    gap = (14, 5, 1)[i - 1]
    for sign in (-1, 1):
        y = AY + 18 + sign * gap
        _put(d, m, [(x, y) for x in range(AX - 14, AX + 15, 7)], 3, p, sign + 1)
    if i == 2:
        _put(d, m, _arc(AX, AY + 18, 12, 0, 315, 7), 2, p)
    return True


def _charge(d, m, i, p, e):
    if i == 0:
        _put(d, m, [(AX + x, AY + 3) for x in (-12, 0, 12)], 2, p)
        return True
    w, y = (10, 18, 22)[i - 1], AY + (8, 12, 14)[i - 1]
    _put(d, m, [(AX - w, y - 6), (AX - w // 2, y), (AX, y + 4), (AX + w // 2, y), (AX + w, y - 6)], (3, 4, 3)[i - 1], p)
    if i >= 2:
        _put(d, m, _arc(AX, y + 8, (8, 14)[i - 2], 0, 330, 11), 2, p)
    return True


def _fouet(d, m, i, p, e):
    if i == 0:
        return False
    a0, a1 = ((-10, 60), (-20, 200), (120, 200))[i - 1]
    pts = _along(_arc(AX, AY + 4, 24, a0, a1, 16), 6)
    _put(d, m, pts, 3 if i == 2 else 2, p)
    return True


def _projectile(d, m, i, p, e):
    if i == 0:
        m(d, AX, AY + 3, 2, 0, p)
    elif i < 3:
        y = AY + (18, 38)[i - 1]
        for t in range(1, 4):
            m(d, AX + (t % 2) * 2 - 1, y - t * 6, max(1, 4 - t), t, p)
        m(d, AX, y, 7, i, p)
    else:
        _put(d, m, _arc(AX, AY + 50, 10, 0, 315, 7), 3, p)
    return True


def _souffle(d, m, i, p, e):
    if i == 0:
        _put(d, m, [(AX - 3, AY + 2), (AX + 3, AY + 2)], 1, p)
        return True
    length, spread = (22, 52, 56)[i - 1], (8, 22, 24)[i - 1]
    r = random.Random(hash((e, i)) & 0xffff)
    pts = []
    for _ in range((6, 16, 12)[i - 1]):
        t = r.uniform(.15, 1)
        pts.append((AX + r.uniform(-1, 1) * spread * t, AY + length * t))
    pts.sort(key=lambda q: q[1])
    for k, (x, y) in enumerate(pts):
        m(d, round(x), round(y), 2 + round(3 * (y - AY) / length), k, p)
    return True


def _rayon(d, m, i, p, e):
    if i == 0:
        m(d, AX, AY + 3, 3, 0, p)
        return True
    end = (34, 63, 63)[i - 1]
    w = (2, 5, 2)[i - 1]
    d.rectangle((AX - w // 2 - 1, AY, AX + w // 2 + 1, end), fill=p[1])
    d.rectangle((AX - w // 2, AY, AX + w // 2, end), fill=p[2])
    if e == "foudre":  # la foudre zigzague autour du rayon
        pts = [(AX + (5 if k % 2 else -5), AY + 6 * k) for k in range(end // 6 + 1)]
        d.line(pts, fill=p[3], width=1)
    else:
        _put(d, m, [(AX + (4 if k % 2 else -4), y) for k, y in enumerate(range(AY + 6, end, 10))], 2, p)
    return True


def _pluie(d, m, i, p, e):
    if i == 0:
        return False
    r = random.Random(11)
    for k in range(11):
        x, y = r.randint(8, 56), r.randint(14, 58) - (2 - i) * 10
        if y < 8:
            continue
        m(d, x, y, 3 if i < 3 else 2, k, p)
    return True


def _onde(d, m, i, p, e):  # anneau de motifs autour de la créature (centre 32, 32)
    if i == 0:
        return False
    r = (12, 21, 29)[i - 1]
    _put(d, m, [(32 + r * math.cos(t), 32 + r * .6 * math.sin(t)) for t in [k * math.pi / 5 for k in range(10)]],
         (2, 3, 2)[i - 1], p)
    return True


def _explosion(d, m, i, p, e):  # éclat de motifs qui jaillit du centre (32, 32)
    r = (4, 12, 22, 28)[i]
    if i == 0:
        m(d, 32, 32, 4, 0, p)
        return True
    n = 8 if i < 3 else 12
    _put(d, m, [(32 + r * math.cos(t), 32 + r * math.sin(t)) for t in [k * 2 * math.pi / n + i * .3 for k in range(n)]],
         (4, 4, 2)[i - 1], p)
    if i == 1:
        m(d, 32, 32, 6, 1, p)
    return True


LAYOUT = {"griffe": _griffe, "morsure": _morsure, "charge": _charge, "fouet": _fouet, "projectile": _projectile,
          "souffle": _souffle, "rayon": _rayon, "pluie": _pluie, "onde": _onde, "explosion": _explosion}
# les attaques qui ont leur visuel signé : (élément, geste)
SIGNED = {(e, g) for e in MOTIF for g in LAYOUT}


def signed(genre, element, i, pal):
    """L'image i (0..3) du visuel signé (élément, geste), ou None : pas d'effet sur cette image. pal : 4 couleurs RGBA."""
    im = Image.new("RGBA", (CELL, CELL))
    if not LAYOUT[genre](ImageDraw.Draw(im), MOTIF[element], i, pal, element):
        return None
    return im


# ------------------------------------------------------------------ NeoMe, créature n° 0 : ses 4 visuels à lui
# ombre (violet, magenta) et lumière (or, blanc), comme ses yeux et sa coquille
NEOME = ((20, 16, 42, 255), (122, 47, 208, 255), (255, 79, 216, 255), (255, 240, 255, 255))
GOLD = ((90, 72, 16, 255), (242, 194, 91, 255), (255, 216, 74, 255), (255, 255, 255, 255))
NEOME_VISUALS = ("eclipse", "regard", "casque", "coquille")
SELF_VISUALS = {"eclipse", "coquille"}  # centrés sur NeoMe


def _note(d, x, y, c):
    d.rectangle((x, y, x + 2, y + 1), fill=c)
    d.line((x + 2, y - 5, x + 2, y), fill=c)
    d.line((x + 2, y - 5, x + 4, y - 4), fill=c)


def neome(visual, i):
    im = Image.new("RGBA", (CELL, CELL))
    d = ImageDraw.Draw(im)
    dark, mid, light, core = NEOME
    if visual == "eclipse":  # un disque d'ombre cerclé d'or, qui s'ouvre en anneau mi-nuit mi-jour
        r = (7, 15, 25, 30)[i]
        d.ellipse((32 - r, 32 - r, 32 + r, 32 + r), outline=GOLD[2], width=2)
        d.pieslice((32 - r + 2, 32 - r + 2, 32 + r - 2, 32 + r - 2), 90, 270, fill=mid if i else dark)
        if i in (1, 2):
            d.ellipse((32 - r // 2, 32 - r // 2, 32 + r // 2, 32 + r // 2), fill=dark, outline=light)
            for k in range(8):
                t = k * math.pi / 4
                c = GOLD[2] if k % 2 else light
                d.line((32 + (r + 2) * math.cos(t), 32 + (r + 2) * math.sin(t), 32 + (r + 6) * math.cos(t),
                        32 + (r + 6) * math.sin(t)), fill=c, width=2)
        if i == 0:
            d.ellipse((30, 30, 34, 34), fill=core)
    elif visual == "regard":  # ses deux yeux lumineux lancent deux rayons jumeaux
        if i == 0:
            for x in (AX - 5, AX + 5):
                d.ellipse((x - 3, AY - 1, x + 3, AY + 5), fill=light)
                d.ellipse((x - 1, AY + 1, x + 1, AY + 3), fill=core)
        else:
            end, w = (30, 63, 63)[i - 1], (2, 4, 2)[i - 1]
            for x in (AX - 5, AX + 5):
                d.rectangle((x - w // 2 - 1, AY, x + w // 2 + 1, end), fill=light)
                d.rectangle((x - w // 2, AY, x + w // 2, end), fill=core)
            if i == 2:
                for x in (AX - 5, AX + 5):
                    d.line((x - 4, 58, x + 4, 58), fill=GOLD[2])
                    d.line((x, 54, x, 62), fill=GOLD[2])
    elif visual == "casque":  # le son de son casque : des arcs et des notes qui avancent
        for k in range(i + 1):
            r = 8 + 12 * k + 3 * i
            d.arc((AX - r, AY - r, AX + r, AY + r), 40, 140, fill=light if k == i else mid, width=2)
        for k in range(i):
            _note(d, AX - 12 + 16 * (k % 2), AY + 14 + 14 * k + 2 * i, core if k % 2 else light)
    elif visual == "coquille":  # des éclats de sa coquille se dressent autour de lui, puis se referment en bouclier
        if i == 0:
            return None
        r = (14, 24, 28)[i - 1]
        for k in range(9):
            t = math.pi + k * math.pi / 8
            x, y = 32 + r * math.cos(t), 46 + (r * .9) * math.sin(t) - (i - 1) * 3
            d.polygon([(x - 4, y + 3), (x + 4, y + 3), (x + 2, y - 3), (x, y), (x - 2, y - 4)], fill=core, outline=mid)
            if k % 3 == 1:
                d.point((round(x), round(y)), fill=light)
        if i >= 2:
            for x, y in ((20, 26), (44, 24)):
                d.line((x - 3, y - (i - 2) * 4, x + 3, y - (i - 2) * 4), fill=GOLD[2], width=2)
                d.line((x, y - 3 - (i - 2) * 4, x, y + 3 - (i - 2) * 4), fill=GOLD[2], width=2)
    else:
        return None
    return im if im.getbbox() else None


if __name__ == "__main__":  # planche de contrôle : python nb_attack_sig.py planche.png
    import sys
    import nb_attack
    rows = [(e, g) for e in MOTIF for g in LAYOUT]
    assert len(rows) == 120 and len(SIGNED) == 120
    sheet = Image.new("RGBA", (64 * 4 * 6 + 5 * 8, 64 * ((len(rows) + 5) // 6 + 1)), (40, 36, 52, 255))
    for n, (e, g) in enumerate(rows):
        pal = tuple(nb_attack._rgb(c) for c in nb_attack.PALETTE[e])
        frames = [signed(g, e, i, pal) for i in range(4)]
        assert any(f is not None and f.getbbox() for f in frames), (e, g)
        for i, f in enumerate(frames):
            if f is not None:
                sheet.alpha_composite(nb_attack._outline(f, pal[0]), ((n % 6) * (256 + 8) + i * 64, (n // 6) * 64))
    y = 64 * ((len(rows) + 5) // 6)
    for n, v in enumerate(NEOME_VISUALS):
        for i in range(4):
            f = neome(v, i)
            if f is not None:
                sheet.alpha_composite(nb_attack._outline(f, NEOME[0]), (n * (256 + 8) + i * 64, y))
    if len(sys.argv) > 1:
        sheet.save(sys.argv[1])
    print("ok", len(rows), "visuels signés +", len(NEOME_VISUALS), "pour NeoMe")
