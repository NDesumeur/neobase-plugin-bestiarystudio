# -*- coding: utf-8 -*-
"""NeoBestiary Studio - animations d'attaque : le corps (mêmes pixels que le sprite) + un calque d'effet dessiné.

Chaque attaque a 4 images par direction : élan (recul), frappe, impact, retour. Le corps vient du sprite 64x64 de
repos ; seul le haut (au-dessus des pattes) bascule, les pieds restent posés. L'effet est un calque 64x64 séparé,
dessiné au pixel aux couleurs de l'élément, avec un décalage par rapport à la case du corps : un jeu le pose
par-dessus, devant la créature (le JSON d'export donne ces décalages).
"""
import math

from PIL import Image, ImageChops, ImageDraw

CELL = 64
FRAMES = 4
TIMING = (110, 80, 130, 120)  # ms par image : élan, frappe, impact, retour
FORWARD = {"bas": (0, 1), "haut": (0, -1), "gauche": (-1, 0), "droite": (1, 0)}
LEAN = (-1, 2, 3, 1)  # déplacement du haut du corps vers l'avant (px)

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


def body_frames(rest, direction, legs=True):
    """4 images du corps : le haut bascule vers l'avant (élan en arrière d'abord), sans sortir de la case."""
    rest = rest.convert("RGBA")
    upper, feet = _split(rest) if legs else (rest.copy(), Image.new("RGBA", rest.size))
    box = upper.getbbox() or (0, 0, CELL, CELL)
    fx, fy = FORWARD[direction]
    room_fwd = {(0, 1): CELL - box[3], (0, -1): box[1], (-1, 0): box[0], (1, 0): CELL - box[2]}[(fx, fy)]
    room_back = {(0, 1): box[1], (0, -1): CELL - box[3], (-1, 0): CELL - box[2], (1, 0): box[0]}[(fx, fy)]
    out = []
    for lean in LEAN:
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


def _effect(genre, element, i):
    """Image i (0..3) de l'effet, orientée vers le bas, ancre ANCHOR. None = pas d'effet sur cette image."""
    dark, mid, light, core = (_rgb(c) for c in PALETTE.get(element, PALETTE["esprit"]))
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
    else:
        return None
    if not im.getbbox():
        return None
    return _outline(im, dark)


def _orient(im, direction):
    if im is None:
        return None
    return {"bas": im, "haut": im.transpose(Image.Transpose.ROTATE_180),
            "gauche": im.transpose(Image.Transpose.ROTATE_270),
            "droite": im.transpose(Image.Transpose.ROTATE_270).transpose(Image.Transpose.FLIP_LEFT_RIGHT)}[direction]


def _anchor(direction, genre):
    if genre == "onde":
        return (32, 32)
    ax, ay = ANCHOR
    return {"bas": (ax, ay), "haut": (CELL - 1 - ax, CELL - 1 - ay), "gauche": (CELL - 1 - ay, ax),
            "droite": (ay, ax)}[direction]


def attack(rest, direction, genre, element, legs=True):
    """[{"body": 64x64, "effect": 64x64 ou None, "offset": (dx, dy)}] x 4 : offset = position de la case d'effet
    par rapport à la case du corps (coin haut-gauche)."""
    bodies = body_frames(rest, direction, legs)
    if genre == "onde":
        bx0, by0, bx1, by1 = rest.getbbox() or (0, 0, CELL, CELL)
        origin = ((bx0 + bx1) // 2, (by0 + by1) // 2)
    else:
        origin = front_point(rest, direction)
    ax, ay = _anchor(direction, genre)
    fx, fy = FORWARD[direction]
    out = []
    for i in range(FRAMES):
        lean = LEAN[i] if genre != "onde" else 0
        off = (origin[0] - ax + fx * lean, origin[1] - ay + fy * lean)
        fx_im = _effect(genre, element, i)
        out.append(dict(body=bodies[i], effect=fx_im if genre == "onde" else _orient(fx_im, direction), offset=off))
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
    genres = ("griffe", "morsure", "charge", "projectile", "souffle", "onde", "rayon")
    rows = []
    for g in genres:
        for d in ("bas", "gauche", "haut"):
            fr = attack(rest, d, g, "feu", legs=False)
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
