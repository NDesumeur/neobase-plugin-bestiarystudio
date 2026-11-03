# -*- coding: utf-8 -*-
"""NeoBestiary Studio - automatisation : détection de la grille de pixels et note des candidats.

Rien ici ne dépend d'un modèle : ce sont des mesures sur l'image, rapides et déterministes.
"""
from PIL import Image

import nb_sprite as sprite

try:
    import numpy as np
except Exception:  # sans numpy : valeurs par défaut prudentes
    np = None


# ------------------------------------------------------------------ grille de pixels

def detect_pixel_size(img, lo=3, hi=24):
    """Taille des « gros pixels » d'une image de pixel art générée (ex. 8 pour SDXL + Pixel Art XL en 1024).

    Mesure la périodicité des changements de couleur. Retourne (taille, décalage_x, décalage_y, confiance).
    """
    if np is None:
        return 8, 0, 0, 0.0
    a = np.asarray(img.convert("RGB")).astype(np.int32)
    dx = np.abs(np.diff(a, axis=1)).sum(axis=(0, 2)).astype(np.float64)
    dy = np.abs(np.diff(a, axis=0)).sum(axis=(1, 2)).astype(np.float64)
    best = {}
    for p in range(lo, hi + 1):
        def ratio(d):
            sums = np.array([d[i::p].sum() for i in range(p)])
            return sums.max() / max(1e-9, sums.mean()), int(sums.argmax())
        rx, phx = ratio(dx)
        ry, phy = ratio(dy)
        best[p] = ((rx + ry) / 2, phx, phy)
    top = max(v[0] for v in best.values())
    # la plus petite période presque aussi nette que la meilleure (16 est un multiple de 8, etc.)
    for p in sorted(best):
        if best[p][0] >= 0.8 * top:
            r, phx, phy = best[p]
            return p, (phx + 1) % p, (phy + 1) % p, float(r)
    return 8, 0, 0, 0.0


def snap_to_grid(img, colors=32, size=None):
    """Remet l'image sur sa grille réelle : retourne (image native 1 pixel = 1 vrai pixel, taille du pixel)."""
    img = img.convert("RGBA")
    if size is None:
        p, ox, oy, conf = detect_pixel_size(img)
        if conf < 1.6:
            p, ox, oy = 8, 0, 0  # périodicité trop faible : grille standard de Pixel Art XL
    else:
        p, ox, oy = size, 0, 0
    w, h = (img.width - ox) // p, (img.height - oy) // p
    cropped = img.crop((ox, oy, ox + w * p, oy + h * p))
    return sprite.mode_downscale(cropped, w, h, colors), p


def snap_and_upscale(img, colors=32):
    """Grille réelle + agrandissement exact (NEAREST) : pixels parfaitement nets, même taille d'image."""
    small, p = snap_to_grid(img, colors)
    big = small.resize((small.width * p, small.height * p), Image.Resampling.NEAREST)
    bg = sprite.hex_to_rgb(sprite.rgb_to_hex(img.convert("RGB").getpixel((2, 2))))
    out = Image.new("RGB", img.size, bg)
    out.paste(big.convert("RGB"), (0, 0), big)
    return out, small, p


# ------------------------------------------------------------------ note des candidats

def _mask(img, size=128):
    cut = sprite.remove_background(img.convert("RGB").resize((size, size), Image.Resampling.NEAREST), 40)
    return np.asarray(cut.getchannel("A")) >= 128


def _components(mask):
    """Tailles des zones connexes (4 voisins), de la plus grande à la plus petite."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    sizes = []
    for y0 in range(h):
        for x0 in range(w):
            if mask[y0, x0] and not seen[y0, x0]:
                stack, n = [(y0, x0)], 0
                seen[y0, x0] = True
                while stack:
                    y, x = stack.pop()
                    n += 1
                    for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not seen[yy, xx]:
                            seen[yy, xx] = True
                            stack.append((yy, xx))
                sizes.append(n)
    return sorted(sizes, reverse=True)


def _gap_columns(mask):
    """Vrai si la silhouette est coupée en deux par une colonne vide au-dessus des pattes
    (tête et corps dessinés comme deux objets côte à côte)."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return False
    top = ys.min()
    upper = mask[top: top + max(1, int((ys.max() - top) * 0.55))]
    cols = upper[:, xs.min(): xs.max() + 1].any(axis=0)
    inner = cols[2:-2] if len(cols) > 4 else cols
    return bool(len(inner) and not inner.all())


def score_image(img, view="face"):
    """Note sur 10 : une seule créature d'un seul tenant, entière, bien cadrée, symétrique de face/dos.

    Retourne (note, détails). Sert à choisir automatiquement le meilleur candidat.
    """
    if np is None:
        return 5.0, {}
    m = _mask(img)
    total = int(m.sum())
    if total < 30:
        return 0.0, dict(raison="image vide")
    comps = _components(m)
    main = comps[0] / total                    # 1.0 = tout est relié (pas de tête flottante)
    big_parts = sum(1 for c in comps if c > 0.08 * total)
    cover = total / m.size                      # place occupée
    edge = (m[0].mean() + m[-1].mean() + m[:, 0].mean() + m[:, -1].mean()) / 4
    split = _gap_columns(m) if view in ("gauche", "droite", "trois_quarts") else False
    if cover < 0.06:
        cover_s = cover / 0.06
    elif cover > 0.6:
        cover_s = max(0.0, 1 - (cover - 0.6) / 0.3)
    else:
        cover_s = 1.0
    score = 4.0 * main + 2.0 * cover_s - 6.0 * min(1.0, edge * 5) - 1.5 * max(0, big_parts - 1) - (3.0 if split else 0)
    sym = None
    if view in ("face", "dos"):
        ys, xs = np.nonzero(m)
        cx = (xs.min() + xs.max()) / 2
        shift = int(round(m.shape[1] / 2 - cx))
        centered = np.roll(m, shift, axis=1)
        sym = 1 - (centered ^ centered[:, ::-1]).sum() / max(1, 2 * centered.sum())
        score += 4.0 * sym
    else:
        score += 2.0
    return round(max(0.0, min(10.0, score)), 2), dict(relié=round(main, 2), parties=big_parts,
                                                      couverture=round(cover, 2), bord=round(float(edge), 3),
                                                      coupé=split, symétrie=None if sym is None else round(float(sym), 2))
