# -*- coding: utf-8 -*-
"""NeoBestiary Studio - animations d'attaque : le corps (mêmes pixels que le sprite) + un calque d'effet dessiné.

Chaque attaque a 4 images par direction : élan (recul), frappe, impact, retour. Le corps vient du sprite 64x64 de
repos ; seul le haut (au-dessus des pattes) bascule, les pieds restent posés. L'effet est un calque 64x64 séparé,
dessiné au pixel aux couleurs de l'élément, avec un décalage par rapport à la case du corps : un jeu le pose
par-dessus, devant la créature (le JSON d'export donne ces décalages).
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw

import nb_attack_sig as sig

CELL = 64
FRAMES = 4
TIMING = (110, 80, 130, 120)  # ms par image : élan, frappe, impact, retour
FORWARD = {"bas": (0, 1), "haut": (0, -1), "gauche": (-1, 0), "droite": (1, 0)}
LEAN = (-1, 2, 3, 1)  # déplacement du haut du corps vers l'avant (px)
# le geste du corps selon l'attaque : élan vers l'avant (px), ou pulsation sur place (échelle) pour les attaques autour d'elle
LEANS = {"charge": (-2, 4, 6, 1), "corne": (-3, 3, 5, 1), "morsure": (-1, 3, 3, 0), "dard": (-2, 4, 2, 0),
         "etreinte": (-1, 2, 2, 2), "fouet": (1, 2, 1, 0), "projectile": (-1, 1, -1, 0), "souffle": (-2, 1, 1, 0),
         "rayon": (-1, 0, -1, 0), "cri": (0, -1, -2, 0), "rafale": (-1, 2, 0, 0), "pluie": (0, -2, -1, 0)}
PULSE = {"onde": (1, .9, 1.06, 1), "explosion": (1, .86, 1.08, 1), "soin": (1, 1.04, 1.06, 1), "renfort": (1, .94, 1.08, 1.03)}
SELF = {"onde", "explosion", "soin", "renfort"}  # effet centré sur la créature

# élément -> (contour, moyen, clair, cœur)
PALETTE = {
    "feu": ("#5a1a0c", "#e0461f", "#ffa22b", "#fff3a0"), "eau": ("#0f2a5c", "#2f6fd6", "#6fb8ff", "#e6f6ff"),
    "plante": ("#123a12", "#3d9a35", "#8fdc5a", "#e9ffc8"), "vent": ("#2c4a55", "#9fd8e0", "#e4fbff", "#ffffff"),
    "roche": ("#3a2614", "#8a6a3e", "#c4a26a", "#efe0b8"), "glace": ("#1c3f5a", "#6fd0f0", "#c9f4ff", "#ffffff"),
    "foudre": ("#4a3a08", "#f5d020", "#fff27a", "#ffffff"), "lumière": ("#5a4810", "#f2c25b", "#fff0a8", "#ffffff"),
    "ombre": ("#120a1c", "#4a2f5c", "#8a5ab8", "#d8b8ff"), "esprit": ("#2a1f48", "#7a6ae0", "#b9a8ff", "#f2eaff"),
    "acier": ("#22262e", "#8a93a3", "#cfd6e0", "#ffffff"), "poison": ("#2a0f38", "#8a3ab8", "#b8e04a", "#f0ffc0"),
}


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# ------------------------------------------------------------------ corps

def _split(im):
    """(haut du corps, pattes) : coupe au-dessus des pattes si la créature en a, sinon tout bouge."""
    import nb_engine  # import tardif : nb_engine charge ComfyUI, inutile pour dessiner les effets
    top, box = nb_engine.leg_zone(im)
    if top is None:
        return im.copy(), Image.new("RGBA", im.size)
    upper, legs = im.copy(), im.copy()
    upper.paste((0, 0, 0, 0), (0, top, im.width, im.height))
    legs.paste((0, 0, 0, 0), (0, 0, im.width, top))
    return upper, legs


def _pulse(rest, k):
    box = rest.getbbox()
    if not box or k == 1:
        return rest.copy()
    part = rest.crop(box)
    nw, nh = max(1, round(part.width * (2 - k) ** .5)), max(1, round(part.height * k))
    part = part.resize((nw, nh), Image.Resampling.NEAREST)
    out = Image.new("RGBA", rest.size)
    out.paste(part, ((box[0] + box[2]) // 2 - nw // 2, box[3] - nh), part)
    return out


def body_frames(rest, direction, legs=True, genre=""):
    """4 images du corps : le haut bascule vers l'avant (élan en arrière d'abord), sans sortir de la case ; pour une
    attaque autour d'elle, la créature se tasse puis se gonfle."""
    rest = rest.convert("RGBA")
    if genre in PULSE:
        return [_pulse(rest, k) for k in PULSE[genre]]
    upper, feet = _split(rest) if legs else (rest.copy(), Image.new("RGBA", rest.size))
    box = upper.getbbox() or (0, 0, CELL, CELL)
    fx, fy = FORWARD[direction]
    room_fwd = {(0, 1): CELL - box[3], (0, -1): box[1], (-1, 0): box[0], (1, 0): CELL - box[2]}[(fx, fy)]
    room_back = {(0, 1): box[1], (0, -1): CELL - box[3], (-1, 0): CELL - box[2], (1, 0): box[0]}[(fx, fy)]
    out = []
    for lean in LEANS.get(genre, LEAN):
        if not legs:  # sans pattes, le corps entier avance : il ne doit pas sortir de la case
            lean = max(-room_back, min(lean, room_fwd))
        frame = Image.new("RGBA", rest.size)
        frame.alpha_composite(feet)
        shifted = Image.new("RGBA", rest.size)
        shifted.paste(upper, (fx * lean, fy * lean), upper)
        frame.alpha_composite(shifted)
        out.append(frame)
    return out


def front_point(rest, direction):
    """Où naît l'effet dans la case du corps : devant la bouche / la tête."""
    box = rest.getbbox() or (0, 0, CELL, CELL)
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    return {"bas": (cx, y1 - 4), "haut": (cx, y0 + 2), "gauche": (x0 + 2, y0 + (y1 - y0) // 3),
            "droite": (x1 - 2, y0 + (y1 - y0) // 3)}[direction]


# ------------------------------------------------------------------ effets (dessinés vers le bas, ancre en haut)

ANCHOR = (32, 4)


def _fade(im, keep):
    """Disparition en pixel art : on retire des pixels en damier plutôt que de baisser l'opacité."""
    if keep >= 1:
        return im
    a = im.getchannel("A")
    px = a.load()
    step = 2 if keep >= .5 else 3
    for y in range(im.height):
        for x in range(im.width):
            if (x + y) % step:
                px[x, y] = 0
    im.putalpha(a)
    return im


def _outline(im, color):
    a = im.getchannel("A").point(lambda v: 255 if v else 0)
    grown = a
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grown = ImageChops.lighter(grown, ImageChops.offset(a, dx, dy))
    ring = ImageChops.subtract(grown, a)
    out = Image.new("RGBA", im.size)
    out.paste(Image.new("RGBA", im.size, color), mask=ring)
    out.alpha_composite(im)
    return out


def _thick(d, pts, fill, w):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.line((x0, y0, x1, y1), fill=fill, width=w)


def _arc(cx, cy, r, a0, a1, n=12):
    return [(round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n))),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))) for i in range(n + 1)]


def _star(d, cx, cy, r, c1, c2):
    for ang in range(0, 360, 45):
        rr = r if ang % 90 == 0 else r * .55
        x, y = cx + rr * math.cos(math.radians(ang)), cy + rr * math.sin(math.radians(ang))
        d.line((cx, cy, round(x), round(y)), fill=c1, width=2)
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=c2)


def _flame(d, x, y, c1, c2, r):
    d.polygon([(x - r, y + r), (x + r, y + r), (x, y - 2 * r)], fill=c1)
    d.polygon([(x - r // 2, y + r), (x + r // 2, y + r), (x, y - r)], fill=c2)


def _decor(im, element, seed):
    """Motifs de l'élément semés sur l'effet : flammèches, cristaux, bulles, éclairs, feuilles, gouttes…"""
    a = im.getchannel("A")
    pts = [(x, y) for y in range(0, CELL, 3) for x in range(0, CELL, 3) if a.getpixel((x, y))]
    if not pts:
        return im
    dark, mid, light, core = (_rgb(c) for c in PALETTE.get(element, PALETTE["esprit"]))
    r = random.Random(seed)
    d = ImageDraw.Draw(im)
    for x, y in r.sample(pts, min(len(pts), 6)):
        if element == "feu":
            _flame(d, x, y, light, core, 2)
        elif element == "glace":
            d.polygon([(x, y - 4), (x + 2, y), (x, y + 4), (x - 2, y)], fill=core)
            d.line((x - 3, y, x + 3, y), fill=light)
        elif element == "poison":
            d.ellipse((x - 2, y - 2, x + 2, y + 2), outline=light)
            d.point((x - 1, y - 1), fill=core)
        elif element == "foudre":
            d.line([(x - 3, y - 4), (x + 1, y - 1), (x - 1, y + 1), (x + 3, y + 4)], fill=core, width=1)
        elif element == "plante":
            d.ellipse((x - 3, y - 1, x + 3, y + 2), fill=light)
            d.line((x - 3, y + 1, x + 3, y), fill=mid)
        elif element == "eau":
            d.ellipse((x - 2, y - 1, x + 2, y + 3), fill=light)
            d.polygon([(x - 1, y), (x + 1, y), (x, y - 3)], fill=light)
        elif element == "vent":
            d.arc((x - 4, y - 3, x + 4, y + 3), 180, 360, fill=core)
        elif element == "roche":
            d.rectangle((x - 2, y - 2, x + 1, y + 1), fill=mid, outline=dark)
        elif element == "lumière":
            d.line((x - 3, y, x + 3, y), fill=core)
            d.line((x, y - 3, x, y + 3), fill=core)
        elif element == "ombre":
            d.ellipse((x - 2, y - 3, x + 2, y + 1), fill=dark)
            d.point((x, y - 1), fill=light)
        elif element == "esprit":
            d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=core)
        elif element == "acier":
            d.line((x - 3, y + 3, x + 3, y - 3), fill=core, width=1)
            d.point((x + 3, y - 3), fill=light)
    return im


def _effect(genre, element, i, visual=None):
    """Image i (0..3) de l'effet, orientée vers le bas, ancre ANCHOR. None = pas d'effet sur cette image.
    visual : un visuel propre à une créature (NeoMe) ; sinon le visuel signé de (élément, geste) s'il existe."""
    if visual in sig.NEOME_VISUALS:
        im = sig.neome(visual, i)
        return None if im is None else _outline(_fade(im, .5) if i == 3 else im, sig.NEOME[0])
    dark, mid, light, core = (_rgb(c) for c in PALETTE.get(element, PALETTE["esprit"]))
    if (element, genre) in sig.SIGNED:
        im = sig.signed(genre, element, i, (dark, mid, light, core))
        if im is None or not im.getbbox():
            return None
        return _outline(_fade(im, .5) if i == 3 and genre != "projectile" else im, dark)
    im = Image.new("RGBA", (CELL, CELL))
    d = ImageDraw.Draw(im)
    ax, ay = ANCHOR
    if genre == "griffe":
        if i == 0:
            return None
        ln = (10, 26, 26)[i - 1]
        for k in (-8, 0, 8):
            pts = _arc(ax - 18 + k, ay + 2, 22 + k // 2, 10, 10 + ln * 2.6)
            _thick(d, pts, light if i < 3 else mid, 3 if i == 2 else 2)
            _thick(d, pts[2:-2], core, 1)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "morsure":
        if i == 0:
            return None
        gap = (14, 4, 0)[i - 1]
        for sign in (-1, 1):
            y = ay + 18 + sign * gap
            d.line((ax - 14, y, ax + 14, y), fill=light, width=2)
            for x in range(ax - 12, ax + 13, 6):
                d.polygon([(x - 2, y), (x + 2, y), (x, y - sign * 5)], fill=core)
        if i == 2:
            _star(d, ax, ay + 18, 14, mid, core)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "charge":
        if i == 0:
            for x in range(ax - 16, ax + 17, 8):
                d.line((x, ay, x, ay + 6), fill=light, width=1)
        else:
            r = (8, 14, 18)[i - 1]
            _star(d, ax, ay + 10, r, light if i < 3 else mid, core)
            if i == 3:
                im = _fade(im, .5)
    elif genre == "projectile":
        if i == 0:
            d.ellipse((ax - 3, ay - 1, ax + 3, ay + 5), fill=light)
            d.ellipse((ax - 1, ay + 1, ax + 1, ay + 3), fill=core)
        elif i < 3:
            y = ay + (18, 38)[i - 1]
            for t in range(1, 4):  # traînée
                ty = y - t * 5
                d.ellipse((ax - 4 + t, ty - 4 + t, ax + 4 - t, ty + 4 - t), fill=mid)
            d.ellipse((ax - 6, y - 6, ax + 6, y + 6), fill=light)
            d.ellipse((ax - 3, y - 3, ax + 2, y + 2), fill=core)
        else:
            _star(d, ax, ay + 50, 12, light, core)
            im = _fade(im, .7)
    elif genre == "souffle":
        if i == 0:
            for k in (-4, 0, 4):
                d.point((ax + k, ay + 2), fill=light)
        else:
            length = (22, 52, 56)[i - 1]
            spread = (8, 22, 24)[i - 1]
            d.polygon([(ax - 3, ay), (ax + 3, ay), (ax + spread, ay + length), (ax - spread, ay + length)], fill=mid)
            d.polygon([(ax - 2, ay), (ax + 2, ay), (ax + spread // 2, ay + length - 6), (ax - spread // 2, ay + length - 6)],
                      fill=light)
            d.line((ax, ay, ax, ay + length // 2), fill=core, width=2)
            if i == 3:
                im = _fade(im, .5)
    elif genre == "onde":  # anneaux autour de la créature : ancre au centre
        if i == 0:
            return None
        r = (12, 22, 30)[i - 1]
        d.ellipse((32 - r, 32 - r * .6, 32 + r, 32 + r * .6), outline=light, width=2)
        if i > 1:
            r2 = r - 8
            d.ellipse((32 - r2, 32 - r2 * .6, 32 + r2, 32 + r2 * .6), outline=core, width=1)
        if i == 3:
            im = _fade(im, .5)
    elif genre == "rayon":
        if i == 0:
            d.ellipse((ax - 4, ay - 2, ax + 4, ay + 6), fill=light)
        else:
            end = (34, 63, 63)[i - 1]
            w = (3, 7, 3)[i - 1]
            d.rectangle((ax - w // 2 - 1, ay, ax + w // 2 + 1, end), fill=mid)
            d.rectangle((ax - w // 2, ay, ax + w // 2, end), fill=light)
            d.line((ax, ay, ax, end), fill=core, width=1)
    elif genre == "fouet":  # la queue balaie devant elle, d'un côté à l'autre
        if i == 0:
            return None
        a0, a1 = ((-10, 60), (-20, 200), (120, 200))[i - 1]
        pts = _arc(ax, ay + 4, 24, a0, a1, 16)
        _thick(d, pts, light if i < 3 else mid, 4 if i == 2 else 2)
        _thick(d, pts, core, 1)
        if i == 2:
            _star(d, *pts[len(pts) // 2], 7, mid, core)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "corne":  # une pointe qui jaillit
        if i == 0:
            d.point((ax, ay + 2), fill=core)
        else:
            ln = (14, 30, 30)[i - 1]
            d.polygon([(ax - 5, ay), (ax + 5, ay), (ax, ay + ln)], fill=light)
            d.line((ax, ay + 2, ax, ay + ln - 2), fill=core)
            if i >= 2:
                _star(d, ax, ay + ln, (10, 14)[i - 2], mid, core)
            im = _fade(im, .5) if i == 3 else im
    elif genre == "dard":  # un aiguillon qui pique, puis des gouttes de venin
        if i == 0:
            return None
        ln = (18, 34, 34)[i - 1]
        if i < 3:
            d.line((ax, ay, ax, ay + ln), fill=light, width=2)
            d.polygon([(ax - 2, ay + ln - 3), (ax + 2, ay + ln - 3), (ax, ay + ln + 3)], fill=core)
        for k in range(i - 1):
            for dx in (-6, 5):
                y = ay + ln + 4 + 6 * k
                d.ellipse((ax + dx - 2, y - 2, ax + dx + 2, y + 3), fill=mid)
        im = _fade(im, .6) if i == 3 else im
    elif genre == "etreinte":  # des tentacules qui s'enroulent autour de la cible
        if i == 0:
            return None
        for sign in (-1, 1):
            pts = _arc(ax + sign * 10, ay + 4, 14, -90 if sign > 0 else 90, 90 if sign > 0 else 270, 10)
            pts = [(x, y + 6 * (i - 1)) for x, y in pts]
            _thick(d, pts, light, 3)
        if i >= 2:
            for k in range(3):
                y = ay + 22 + 6 * k
                d.ellipse((ax - 12 + 2 * (i - 2), y - 3, ax + 12 - 2 * (i - 2), y + 3), outline=core, width=2)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "cri":  # des ondes sonores en arcs qui avancent
        for k in range(i + 1):
            r = 8 + 12 * k + 4 * i
            d.arc((ax - r, ay - r, ax + r, ay + r), 40, 140, fill=light if k == i else mid, width=2)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "rafale":  # des traits de vent qui filent devant
        if i == 0:
            return None
        for k, x in enumerate((-12, -4, 4, 12)):
            y0 = ay + 4 + 10 * (i - 1) + (k % 2) * 4
            d.line((ax + x, y0, ax + x + (k - 1.5) * 2, y0 + 18), fill=light if k % 2 else core, width=1)
            d.arc((ax + x - 3, y0 + 16, ax + x + 3, y0 + 22), 0, 180, fill=light)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "pluie":  # des projectiles tombent du ciel sur la zone devant elle
        if i == 0:
            return None
        r = random.Random(7)
        for k in range(12):
            x, y = r.randint(8, 56), r.randint(20, 60)
            if i == 1 and y > 40:
                continue
            if i < 3:
                d.line((x + 2, y - 6, x, y), fill=light, width=1)
                d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=core)
            else:
                d.arc((x - 4, y - 1, x + 4, y + 3), 180, 360, fill=mid)
        im = _fade(im, .6) if i == 3 else im
    elif genre == "explosion":  # une boule qui éclate autour d'elle : ancre au centre
        r = (6, 14, 26, 30)[i]
        d.ellipse((32 - r, 32 - r, 32 + r, 32 + r), fill=light if i < 3 else None, outline=mid, width=2)
        if i in (1, 2):
            d.ellipse((32 - r // 2, 32 - r // 2, 32 + r // 2, 32 + r // 2), fill=core)
            _star(d, 32, 32, r + 4, mid, core)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "soin":  # des croix lumineuses qui montent autour d'elle
        if i == 0:
            return None
        for k, (x, y) in enumerate(((16, 44), (46, 40), (28, 30), (40, 52))):
            y -= 8 * i - 4 * (k % 2)
            d.line((x - 3, y, x + 3, y), fill=core, width=2)
            d.line((x, y - 3, x, y + 3), fill=core, width=2)
        im = _fade(im, .5) if i == 3 else im
    elif genre == "renfort":  # une aura et des flèches qui montent
        if i == 0:
            return None
        d.ellipse((10, 34 - 2 * i, 54, 58 - 2 * i), outline=light, width=2)
        for x in (18, 32, 46):
            y = 40 - 6 * i + (x % 3)
            d.polygon([(x - 3, y), (x + 3, y), (x, y - 5)], fill=core)
            d.line((x, y, x, y + 5), fill=core)
        im = _fade(im, .5) if i == 3 else im
    else:
        return None
    if not im.getbbox():
        return None
    if element in PALETTE and genre not in ("soin", "renfort"):
        im = _decor(im, element, hash((genre, element, i)) & 0xffff)
    return _outline(im, dark)


def _orient(im, direction):
    if im is None:
        return None
    return {"bas": im, "haut": im.transpose(Image.Transpose.ROTATE_180),
            "gauche": im.transpose(Image.Transpose.ROTATE_270),
            "droite": im.transpose(Image.Transpose.ROTATE_270).transpose(Image.Transpose.FLIP_LEFT_RIGHT)}[direction]


def _anchor(direction, genre):
    if genre in SELF:
        return (32, 32)
    ax, ay = ANCHOR
    return {"bas": (ax, ay), "haut": (CELL - 1 - ax, CELL - 1 - ay), "gauche": (CELL - 1 - ay, ax),
            "droite": (ay, ax)}[direction]


def attack(rest, direction, genre, element, legs=True, visual=None):
    """[{"body": 64x64, "effect": 64x64 ou None, "offset": (dx, dy)}] x 4 : offset = position de la case d'effet
    par rapport à la case du corps (coin haut-gauche)."""
    bodies = body_frames(rest, direction, legs, genre)
    if genre in SELF:
        bx0, by0, bx1, by1 = rest.getbbox() or (0, 0, CELL, CELL)
        origin = ((bx0 + bx1) // 2, (by0 + by1) // 2)
    else:
        origin = front_point(rest, direction)
    ax, ay = _anchor(direction, genre)
    fx, fy = FORWARD[direction]
    out = []
    for i in range(FRAMES):
        lean = 0 if genre in SELF else LEANS.get(genre, LEAN)[i]
        off = (origin[0] - ax + fx * lean, origin[1] - ay + fy * lean)
        fx_im = _effect(genre, element, i, visual)
        out.append(dict(body=bodies[i], effect=fx_im if genre in SELF else _orient(fx_im, direction), offset=off))
    return out


def compose(frame, pad=64):
    """Aperçu : le corps et son effet dans une même image (case agrandie de pad de chaque côté)."""
    size = CELL + 2 * pad
    im = Image.new("RGBA", (size, size))
    im.alpha_composite(frame["body"], (pad, pad))
    if frame["effect"] is not None:
        im.alpha_composite(frame["effect"], (pad + frame["offset"][0], pad + frame["offset"][1]))
    return im


if __name__ == "__main__":  # auto-test : une créature ronde, chaque genre, chaque direction -> attack_test.png
    import sys
    rest = Image.new("RGBA", (CELL, CELL))
    ImageDraw.Draw(rest).ellipse((14, 20, 50, 62), fill=(120, 80, 160, 255), outline=(10, 10, 20, 255), width=2)
    import nb_stats
    genres = nb_stats.GENRES
    rows = []
    for n, g in enumerate(genres):
        for d in ("bas", "gauche", "haut"):
            fr = attack(rest, d, g, list(PALETTE)[n % len(PALETTE)], legs=False)
            assert len(fr) == FRAMES and all(f["body"].size == (CELL, CELL) for f in fr)
            assert any(f["effect"] is not None for f in fr), (g, d)
            rows.append([compose(f) for f in fr])
    sheet = Image.new("RGBA", (192 * 4, 192 * len(rows)), (60, 60, 70, 255))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            sheet.alpha_composite(im, (c * 192, r * 192))
    if len(sys.argv) > 1:
        sheet.save(sys.argv[1])
    print("ok")
