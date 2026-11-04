# -*- coding: utf-8 -*-
"""NeoBestiary Studio - animations de combat hors attaques : attente (respiration, clignement), dégâts, K.O.

Tout part du sprite 64x64 de repos de chaque direction, au pixel près, sans GPU : la créature reste identique.
"""
from PIL import Image

import nb_attack

CELL = 64
EYE = 70  # écart de luminosité avec le corps pour être un œil (pupille sombre ou reflet clair)
ANIMS = {  # nom -> durée de chaque image (ms)
    "attente": (380, 420, 380, 140),  # repos, inspiration, repos, clignement
    "degats": (70, 110, 110, 120),  # flash blanc, recul teinté, recul, repos
    "ko": (140, 150, 190, 300),  # bascule, chute, à terre, disparition
}


def _lum(c):
    return .299 * c[0] + .587 * c[1] + .114 * c[2]


# ------------------------------------------------------------------ attente

def breathe(im):
    """Inspiration : le haut du corps s'étire d'un pixel (la moitié haute monte), les pieds ne bougent pas."""
    box = im.getbbox()
    if not box:
        return im.copy()
    x0, y0, x1, y1 = box
    mid = y0 + (y1 - y0) // 2
    if y0 == 0:
        return im.copy()
    out = im.copy()
    out.paste((0, 0, 0, 0), (0, 0, CELL, mid))
    out.alpha_composite(im.crop((0, y0, CELL, mid + 1)), (0, y0 - 1))
    return out


def eyes(im):
    """Les yeux : petites taches très claires ou très sombres à l'intérieur du corps, dans sa moitié haute.
    [] si rien de net (dos, texture trop chargée) : la créature ne cligne pas plutôt que de cligner faux."""
    box = im.getbbox()
    if not box:
        return []
    px = im.load()
    x0, y0, x1, y1 = box
    limit = y0 + (y1 - y0) * .6
    opaque = lambda x, y: 0 <= x < CELL and 0 <= y < CELL and px[x, y][3] >= 128
    body = [px[x, y] for y in range(y0, y1) for x in range(x0, x1) if opaque(x, y)]
    mean = sum(_lum(c) for c in body) / max(1, len(body))
    seen, comps = set(), []
    for y in range(y0, int(limit)):
        for x in range(x0, x1):
            if (x, y) in seen or not opaque(x, y):
                continue
            if abs(_lum(px[x, y]) - mean) < EYE:
                continue
            stack, comp, ok = [(x, y)], [], True
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if not opaque(nx, ny):
                        ok = False  # touche le bord : c'est le contour, pas un œil
                        continue
                    if (nx, ny) not in seen and abs(_lum(px[nx, ny]) - mean) >= EYE:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            if ok and 1 <= len(comp) <= 12:
                comps.append(comp)
    return comps if 1 <= len(comps) <= 8 else []


def blink(im, comps=None):
    """Clignement : chaque œil prend la couleur de la peau autour, avec un trait de paupière sombre au milieu."""
    comps = eyes(im) if comps is None else comps
    out = im.copy()
    px, src = out.load(), im.load()
    dark = min((src[x, y] for y in range(CELL) for x in range(CELL) if src[x, y][3] >= 128), key=_lum, default=None)
    for comp in comps:
        cs = set(comp)
        ring = [src[nx, ny] for x, y in comp for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if (nx, ny) not in cs and 0 <= nx < CELL and 0 <= ny < CELL and src[nx, ny][3] >= 128]
        if not ring:
            continue
        skin = max(set(ring), key=ring.count)
        for x, y in comp:
            px[x, y] = skin
        ys = sorted({y for _, y in comp})
        mid = ys[len(ys) // 2]
        for x, y in comp:
            if y == mid:
                px[x, y] = dark
    return out


def idle(rest):
    rest = rest.convert("RGBA")
    return [rest.copy(), breathe(rest), rest.copy(), blink(rest)]


# ------------------------------------------------------------------ dégâts

def _shift_in(im, dx, dy):
    """Décale sans sortir de la case."""
    box = im.getbbox()
    if not box:
        return im.copy()
    dx = max(-box[0], min(dx, CELL - box[2]))
    dy = max(-box[1], min(dy, CELL - box[3]))
    out = Image.new("RGBA", im.size)
    out.paste(im, (dx, dy), im)
    return out


def _tint(im, color, amount):
    flat = Image.new("RGBA", im.size, color + (255,))
    out = Image.blend(im, flat, amount)
    out.putalpha(im.getchannel("A"))
    return out


def hurt(rest, direction):
    rest = rest.convert("RGBA")
    fx, fy = nb_attack.FORWARD[direction]
    flash = Image.new("RGBA", rest.size, (255, 255, 255, 255))
    flash.putalpha(rest.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    back = _tint(_shift_in(rest, -fx * 3, -fy * 3), (230, 40, 40), .45)
    return [flash, back, _shift_in(rest, -fx, -fy), rest.copy()]


# ------------------------------------------------------------------ K.O.

def _squash(im, ratio):
    """Écrase la créature vers ses pieds (elle s'effondre)."""
    box = im.getbbox()
    if not box:
        return im.copy()
    part = im.crop(box)
    h = max(1, round(part.height * ratio))
    part = part.resize((part.width, h), Image.Resampling.NEAREST)
    out = Image.new("RGBA", im.size)
    out.alpha_composite(part, (box[0], box[3] - h))
    return out


def _darken(im, amount):
    return _tint(im, (20, 16, 30), amount)


def ko(rest, direction):
    rest = rest.convert("RGBA")
    fx = nb_attack.FORWARD[direction][0] or 1
    tilt = rest.rotate(12 * fx, resample=Image.Resampling.NEAREST, center=(32, (rest.getbbox() or (0, 0, 0, 63))[3]))
    fall = _darken(_squash(rest, .7), .2)
    down = _darken(_squash(rest, .45), .35)
    gone = nb_attack._fade(_darken(_squash(rest, .45), .35), .3)
    return [tilt, fall, down, gone]


def build(rest, direction):
    """{nom: [images 64x64]} pour une direction."""
    return {"attente": idle(rest), "degats": hurt(rest, direction), "ko": ko(rest, direction)}


if __name__ == "__main__":  # auto-test : une créature ronde avec deux yeux
    from PIL import ImageDraw
    r = Image.new("RGBA", (CELL, CELL))
    d = ImageDraw.Draw(r)
    d.ellipse((14, 20, 50, 62), fill=(120, 80, 160, 255), outline=(10, 10, 20, 255), width=2)
    for x in (24, 38):
        d.rectangle((x, 32, x + 2, 34), fill=(250, 250, 250, 255))
        d.point((x + 1, 33), fill=(10, 10, 10, 255))
    assert len(eyes(r)) == 2, eyes(r)
    b = blink(r)
    assert b.getpixel((25, 32)) == (120, 80, 160, 255) and b.getpixel((25, 33))[0] < 30
    for direction in ("bas", "haut", "gauche", "droite"):
        anims = build(r, direction)
        for name, frames in anims.items():
            assert len(frames) == len(ANIMS[name]) and all(f.size == (CELL, CELL) for f in frames), name
    assert hurt(r, "bas")[1].getbbox()[1] < r.getbbox()[1]  # recule vers le haut quand elle regarde en bas
    assert ko(r, "bas")[3].getchannel("A").histogram()[255] < r.getchannel("A").histogram()[255] // 2
    print("ok")
