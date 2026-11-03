# -*- coding: utf-8 -*-
"""NeoBestiary Studio - traitement d'image pour sprites (Pillow uniquement)."""
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat, ImageOps

SENTINEL = (255, 0, 255)


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


def luminance(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


# ------------------------------------------------------------------ fond

def _drop_shadow(rgb, mask, seeds):
    """Ombre portée au sol : gris neutre plus sombre que le fond et collé à lui. Le contour sombre du sprite l'arrête."""
    bg = [rgb.getpixel(s) for s in seeds]
    if max(max(c) - min(c) for c in bg) > 24:
        return mask  # fond coloré : pas d'ombre grise à chercher
    bg_lum = sorted(luminance(c) for c in bg)[len(bg) // 2]
    r, g, b = rgb.split()
    spread = ImageChops.subtract(ImageChops.lighter(ImageChops.lighter(r, g), b), ImageChops.darker(ImageChops.darker(r, g), b))
    lo, hi = bg_lum * 0.5, bg_lum + 12
    lum_ok = rgb.convert("L").point(lambda v: 255 if lo <= v <= hi else 0)
    cand = ImageChops.lighter(mask, ImageChops.darker(spread.point(lambda v: 255 if v <= 20 else 0), lum_ok))
    for s in seeds:
        if cand.getpixel(s) == 255:
            ImageDraw.floodfill(cand, s, 128, thresh=0)
    return cand.point(lambda v: 255 if v == 128 else 0)


def remove_background(img, tolerance=40, global_key=False, shadow=True):
    """Supprime le fond en partant des bords (remplissage par diffusion).

    tolerance : écart de couleur accepté (somme des écarts RGB).
    global_key : supprime aussi les zones fermées de la même couleur de fond.
    shadow : retire aussi l'ombre portée grise sous la créature.
    """
    img = img.convert("RGBA")
    if img.getchannel("A").getextrema()[0] < 255:
        return img  # déjà transparent
    rgb = img.convert("RGB")
    w, h = rgb.size
    work = rgb.copy()
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    for seed in seeds:
        if work.getpixel(seed) == SENTINEL:
            continue
        ImageDraw.floodfill(work, seed, SENTINEL, thresh=tolerance)
    r, g, b = work.split()
    mask = ImageChops.darker(ImageChops.darker(r.point(lambda v: 255 if v == 255 else 0),
                                               g.point(lambda v: 255 if v == 0 else 0)),
                             b.point(lambda v: 255 if v == 255 else 0))
    if shadow:
        mask = _drop_shadow(rgb, mask, seeds)
    if global_key:
        corner = rgb.getpixel((0, 0))
        diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, corner))
        dr, dg, db = diff.split()
        total = ImageChops.add(ImageChops.add(dr, dg), db)
        mask = ImageChops.lighter(mask, total.point(lambda v: 255 if v <= tolerance else 0))
    alpha = ImageChops.invert(mask)
    out = img.copy()
    out.putalpha(alpha)
    return out


def crop_to_content(img, padding=0):
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return img
    cropped = img.crop(bbox)
    if padding:
        canvas = Image.new("RGBA", (cropped.width + 2 * padding, cropped.height + 2 * padding), (0, 0, 0, 0))
        canvas.paste(cropped, (padding, padding))
        return canvas
    return cropped


# ------------------------------------------------------------ pixels nets

try:
    import numpy as _np
except Exception:  # numpy facultatif : repli en Python pur
    _np = None


def mode_downscale(img, width, height, colors=32):
    """Réduction « pixels nets » : chaque pixel de sortie = couleur dominante de son bloc d'origine.

    Contrairement à une moyenne (qui mélange les tons et donne du flou), la couleur dominante garde des
    teintes franches ; avec numpy, les petits détails contrastés (yeux) sont gardés (voir _salient_downscale).
    """
    img = img.convert("RGBA")
    bx = max(1, round(img.width / width))
    by = max(1, round(img.height / height))
    if _np is not None:
        return _salient_downscale(img.resize((width * bx, height * by), Image.Resampling.NEAREST), width, height, bx, by)
    q = quantize_colors(img, colors)
    q = q.resize((width * bx, height * by), Image.Resampling.NEAREST)
    # repli Python pur
    from collections import Counter
    px = q.load()
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    po = out.load()
    for y in range(height):
        for x in range(width):
            cnt, opq = Counter(), 0
            for yy in range(y * by, (y + 1) * by):
                for xx in range(x * bx, (x + 1) * bx):
                    r, g, b, a = px[xx, yy]
                    if a >= 128:
                        opq += 1
                        cnt[(r, g, b)] += 1
            if opq * 2 >= bx * by and cnt:
                c = cnt.most_common(1)[0][0]
                po[x, y] = (c[0], c[1], c[2], 255)
    return out


DETAIL = 10.0  # poids d'un détail qui tranche sur son voisinage (yeux, pupilles, gemmes)


def _salient_downscale(img, width, height, bx, by, detail=DETAIL):
    """Couleur dominante de chaque bloc, mais un détail contrasté qui couvre au moins 12 % du bloc l'emporte.

    Pas de réduction de palette avant : sur une image 1024, un œil fait 0,4 % des pixels et une palette de 48
    couleurs le fondait dans la peau. Les couleurs sont regroupées par cases (4 bits par canal) et chaque bloc reçoit
    la couleur moyenne de sa case gagnante."""
    a = _np.asarray(img).reshape(height, by, width, bx, 4).transpose(0, 2, 1, 3, 4).reshape(height * width, by * bx, 4)
    opaque = a[..., 3] >= 128
    n_op = opaque.sum(1)
    blk = _np.broadcast_to(_np.arange(height * width)[:, None], opaque.shape)[opaque]
    rgb = a[..., :3][opaque].astype(_np.int64)
    out = _np.zeros((height * width, 4), _np.uint8)
    if not len(rgb):
        return Image.fromarray(out.reshape(height, width, 4), "RGBA")
    key = blk * 4096 + ((rgb[:, 0] >> 4) << 8 | (rgb[:, 1] >> 4) << 4 | rgb[:, 2] >> 4)
    u, inv, cnt = _np.unique(key, return_inverse=True, return_counts=True)
    mean = _np.stack([_np.bincount(inv, rgb[:, c]) for c in range(3)], -1) / cnt[:, None]
    ub = u // 4096
    bmean = _np.stack([_np.bincount(blk, rgb[:, c], height * width) for c in range(3)], -1) / _np.maximum(n_op, 1)[:, None]
    grid = _np.pad(bmean.reshape(height, width, 3), ((1, 1), (1, 1), (0, 0)), mode="edge")
    neigh = sum(grid[1 + dy:1 + dy + height, 1 + dx:1 + dx + width] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    dist = _np.linalg.norm(mean - neigh.reshape(-1, 3)[ub], axis=1) / 255
    share = cnt / _np.maximum(n_op[ub], 1)
    score = share * _np.where(share >= .12, 1 + detail * dist ** 2, 1)
    order = _np.lexsort((score, ub))
    last = order[_np.r_[ub[order][1:] != ub[order][:-1], True]]  # meilleure case de chaque bloc
    out[ub[last], :3] = mean[last].round().astype(_np.uint8)
    out[:, 3] = _np.where(n_op * 2 >= by * bx, 255, 0)
    return Image.fromarray(out.reshape(height, width, 4), "RGBA")


def match_colors(img, ref):
    """Recale les couleurs de img sur celles de ref (histogramme par canal, pixels opaques seulement).

    Pour un pas de marche généré depuis sa pose de repos : même créature, mêmes surfaces, mais le modèle dérive
    un peu (plus clair, plus rose). Sans numpy : image rendue telle quelle.
    """
    if _np is None:
        return img
    a, r = _np.asarray(img.convert("RGBA")).copy(), _np.asarray(ref.convert("RGBA"))
    ma, mr = a[..., 3] >= 128, r[..., 3] >= 128
    if ma.sum() < 16 or mr.sum() < 16:
        return img
    for c in range(3):
        src, dst = a[..., c][ma], r[..., c][mr]
        sv, si, sc = _np.unique(src, return_inverse=True, return_counts=True)
        dv, dc = _np.unique(dst, return_counts=True)
        sq, dq = _np.cumsum(sc) / src.size, _np.cumsum(dc) / dst.size
        ch = a[..., c]
        ch[ma] = _np.interp(sq, dq, dv)[si].round().astype(_np.uint8)
    return Image.fromarray(a, "RGBA")


def pixel_clean(img, grid=128, colors=28):
    """Nettoie une génération SDXL : grille de `grid` pixels, `colors` couleurs, bords nets, puis agrandit
    chaque pixel (NEAREST) à la taille d'origine pour garder un fichier de même format."""
    img = img.convert("RGBA")
    small = mode_downscale(img, grid, grid, colors)
    return small.resize(img.size, Image.Resampling.NEAREST)


# ------------------------------------------------------------ redimension

SHARP = "Pixels nets (recommandé)"
RESAMPLE = {
    SHARP: None,
    "Moyenne (doux)": Image.Resampling.BOX,
    "Pixel le plus proche": Image.Resampling.NEAREST,
    "Lanczos (doux)": Image.Resampling.LANCZOS,
    "Bilinéaire": Image.Resampling.BILINEAR,
}


def _resize(img, new_w, new_h, method):
    if method == SHARP or method not in RESAMPLE:
        if new_w >= img.width and new_h >= img.height:
            return img.resize((new_w, new_h), Image.Resampling.NEAREST)
        return mode_downscale(img, new_w, new_h, 48)
    return img.resize((new_w, new_h), RESAMPLE[method])


def fit_to_canvas(img, width, height, method=SHARP, align="Centré", margin=0):
    """Redimensionne en conservant les proportions et centre sur un canevas width x height."""
    img = img.convert("RGBA")
    max_w, max_h = max(1, width - 2 * margin), max(1, height - 2 * margin)
    scale = min(max_w / img.width, max_h / img.height)
    new_w, new_h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    resized = _resize(img, new_w, new_h, method)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = (width - new_w) // 2
    y = (height - new_h) // 2 if align == "Centré" else height - new_h - margin
    canvas.paste(resized, (x, y))
    return canvas


def binarize_alpha(img, threshold=128):
    img = img.convert("RGBA")
    alpha = img.getchannel("A").point(lambda v: 255 if v >= threshold else 0)
    out = img.copy()
    out.putalpha(alpha)
    # supprime les couleurs fantômes sous les pixels transparents
    clear = Image.new("RGBA", img.size, (0, 0, 0, 0))
    clear.paste(out, mask=alpha)
    return clear


# ---------------------------------------------------------------- couleurs

RARE = 60  # écart (RVB) au-delà duquel un pixel garde sa couleur : la palette médiane avale les petits détails


def quantize_colors(img, n_colors, keep_rare=False):
    """Réduit le nombre de couleurs en gardant la transparence. keep_rare : un pixel que la palette dénature
    (un œil jaune sur une peau verte) garde sa couleur ; pour les sprites, pas pour une grande image bruitée."""
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    solid = alpha.point(lambda v: 255 if v >= 128 else 0)
    if not solid.getbbox():
        return img
    rgb = img.convert("RGB")
    mean = tuple(int(x) for x in ImageStat.Stat(rgb, mask=solid).mean[:3])
    filled = Image.new("RGB", rgb.size, mean)
    filled.paste(rgb, mask=solid)
    q = filled.quantize(colors=max(2, n_colors), method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.NONE).convert("RGB")
    out = q.convert("RGBA")
    out.putalpha(alpha)
    if keep_rare and _np is not None:
        o, src = _np.asarray(out).copy(), _np.asarray(img)
        far = (_np.linalg.norm(o[..., :3].astype(float) - src[..., :3], axis=-1) > RARE) & (src[..., 3] >= 128)
        o[far, :3] = src[far, :3]
        out = Image.fromarray(o, "RGBA")
    return out


def extract_palette(img, n_colors=8):
    """Palette (hex) extraite des pixels opaques, triée du plus sombre au plus clair."""
    img = img.convert("RGBA")
    q = quantize_colors(img, n_colors, keep_rare=True)
    colors = {}
    px = q.load()
    for y in range(q.height):
        for x in range(q.width):
            r, g, b, a = px[x, y]
            if a >= 128:
                colors[(r, g, b)] = colors.get((r, g, b), 0) + 1
    ordered = sorted(colors, key=luminance)
    return [rgb_to_hex(c) for c in ordered]


def apply_palette(img, palette_hex, mode="Par luminosité (recolorer)"):
    """Impose une palette. 'Par luminosité' remappe les tons : vraie recoloration."""
    pal = [hex_to_rgb(c) for c in palette_hex]
    if not pal:
        return img
    pal_sorted = sorted(pal, key=luminance)
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    if mode.startswith("Par lumin"):
        lums = []
        for y in range(h):
            for x in range(w):
                if px[x, y][3] >= 128:
                    lums.append(luminance(px[x, y]))
        if not lums:
            return img
        lums.sort()
        lo = lums[int(len(lums) * 0.02)]
        hi = lums[min(len(lums) - 1, int(len(lums) * 0.98))]
        span = max(1.0, hi - lo)
        flat = hi - lo < 8  # image d'un seul ton (guide « blob ») : ton moyen, sinon tout tombait sur le plus sombre
        n = len(pal_sorted)
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a >= 128:
                    t = 0.5 if flat else min(1.0, max(0.0, (luminance((r, g, b)) - lo) / span))
                    c = pal_sorted[min(n - 1, int(t * n))]
                    px[x, y] = (c[0], c[1], c[2], a)
    else:
        cache = {}
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a >= 128:
                    key = (r, g, b)
                    if key not in cache:
                        cache[key] = min(pal, key=lambda c: (c[0] - r) ** 2 * 0.30 + (c[1] - g) ** 2 * 0.59 + (c[2] - b) ** 2 * 0.11)
                    c = cache[key]
                    px[x, y] = (c[0], c[1], c[2], a)
    return img


def add_outline(img, color_hex="#0b0b12"):
    """Contour de 1 pixel (4 voisins) autour de la silhouette. L'image doit avoir 1px de marge."""
    img = img.convert("RGBA")
    padded = Image.new("RGBA", (img.width + 2, img.height + 2), (0, 0, 0, 0))
    padded.paste(img, (1, 1))
    alpha = padded.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    grown = alpha
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grown = ImageChops.lighter(grown, ImageChops.offset(alpha, dx, dy))
    ring = ImageChops.subtract(grown, alpha)
    out = Image.new("RGBA", padded.size, (0, 0, 0, 0))
    out.paste(Image.new("RGBA", padded.size, hex_to_rgb(color_hex) + (255,)), mask=ring)
    out.alpha_composite(padded)
    return out


# ---------------------------------------------------------------- pipeline

DEFAULT_OPTS = dict(bg_remove=True, bg_tol=40, bg_global=False, crop=True, width=64, height=64,
                    resample=SHARP, align="Centré", colors=0, palette=None,
                    palette_mode="Par luminosité (recolorer)", alpha_threshold=128,
                    outline=False, outline_color="#0b0b12", margin=1)


def run_pipeline(img, opts, bg_cache=None, token=None):
    """Applique la chaîne complète. bg_cache + token : réutilisent le détourage entre deux réglages."""
    o = dict(DEFAULT_OPTS)
    o.update(opts)
    img = img.convert("RGBA")
    if o["bg_remove"]:
        key = (token, o["bg_tol"], o["bg_global"])
        if bg_cache is not None and token is not None and bg_cache.get("key") == key:
            img = bg_cache["img"]
        else:
            res = remove_background(img, o["bg_tol"], o["bg_global"])
            if bg_cache is not None and token is not None:
                bg_cache["key"], bg_cache["img"] = key, res
            img = res
    if o["crop"]:
        img = crop_to_content(img)
    margin = max(o["margin"], 1 if o["outline"] else 0)
    out_w, out_h = int(o["width"]), int(o["height"])
    inner_w, inner_h = out_w - (2 if o["outline"] else 0), out_h - (2 if o["outline"] else 0)
    img = fit_to_canvas(img, inner_w, inner_h, o["resample"], o["align"], max(0, margin - (1 if o["outline"] else 0)))
    img = binarize_alpha(img, o["alpha_threshold"])
    if o["colors"] and o["colors"] >= 2:
        img = quantize_colors(img, int(o["colors"]))
    if o["palette"]:
        img = apply_palette(img, o["palette"], o["palette_mode"])
    if o["outline"]:
        img = add_outline(img, o["outline_color"])
    return img


def run_batch(images, opts, master_key="face", lock_palette=True, shared_scale=True):
    """Traite plusieurs vues d'une même créature de façon cohérente.

    images : liste de (clé, image). shared_scale : même facteur d'échelle pour toutes les vues (mêmes proportions
    relatives, pieds alignés). lock_palette : la palette est extraite de la vue maître puis imposée à toutes les vues.
    Retourne une liste de (clé, sprite).
    """
    o = dict(DEFAULT_OPTS)
    o.update(opts)
    prepped = []
    for key, im in images:
        im = im.convert("RGBA")
        if o["bg_remove"]:
            im = remove_background(im, o["bg_tol"], o["bg_global"])
        if o["crop"]:
            im = crop_to_content(im)
        prepped.append((key, im))
    ow, oh = int(o["width"]), int(o["height"])
    pad = 2 if o["outline"] else 0
    iw, ih = ow - pad, oh - pad
    margin = max(0, o["margin"] - (1 if o["outline"] else 0))
    iw, ih = max(1, iw - 2 * margin), max(1, ih - 2 * margin)
    common = min(min(iw / im.width, ih / im.height) for _, im in prepped)
    sprites = []
    for key, im in prepped:
        sc = common if shared_scale else min(iw / im.width, ih / im.height)
        new = (max(1, round(im.width * sc)), max(1, round(im.height * sc)))
        small = _resize(im, new[0], new[1], o["resample"])
        canvas = Image.new("RGBA", (ow - pad, oh - pad), (0, 0, 0, 0))
        x = (canvas.width - new[0]) // 2
        y = (canvas.height - new[1]) // 2 if o["align"] == "Centré" else canvas.height - new[1] - margin
        canvas.paste(small, (x, y))
        sprites.append((key, binarize_alpha(canvas, o["alpha_threshold"])))
    ncol = int(o["colors"] or 0)
    if o["palette"]:
        sprites = [(k, apply_palette(im, o["palette"], o["palette_mode"])) for k, im in sprites]
    elif ncol >= 2:
        idx = next((i for i, (k, _) in enumerate(sprites) if k == master_key), 0)
        if lock_palette:
            master_q = quantize_colors(sprites[idx][1], ncol, keep_rare=True)
            pal = extract_palette(master_q, ncol + 16)  # master_q a déjà ses couleurs : on les reprend toutes
            sprites = [(k, master_q if i == idx else apply_palette(im, pal, "Couleur la plus proche"))
                       for i, (k, im) in enumerate(sprites)]
        else:
            sprites = [(k, quantize_colors(im, ncol, keep_rare=True)) for k, im in sprites]
    if o["outline"]:
        sprites = [(k, add_outline(im, o["outline_color"])) for k, im in sprites]
    return sprites


# ---------------------------------------------------------------- planche

def contact_sheet(items, cell=128, cols=None, bg=(19, 24, 39, 255), label_font=None, scale_nearest=True):
    """items : liste de (label, PIL.Image). Retourne une planche PNG."""
    if not items:
        return None
    cols = cols or len(items)
    rows = (len(items) + cols - 1) // cols
    pad = 8
    sheet = Image.new("RGBA", (cols * (cell + pad) + pad, rows * (cell + pad) + pad), bg)
    for i, (_label, im) in enumerate(items):
        im = im.convert("RGBA")
        s = min(cell / im.width, cell / im.height)
        if s >= 1:
            s = max(1, int(s))
        new = (max(1, int(im.width * s)), max(1, int(im.height * s)))
        im = im.resize(new, Image.Resampling.NEAREST if scale_nearest else Image.Resampling.LANCZOS)
        cx, cy = i % cols, i // cols
        x = pad + cx * (cell + pad) + (cell - new[0]) // 2
        y = pad + cy * (cell + pad) + (cell - new[1]) // 2
        sheet.alpha_composite(im, (x, y))
    return sheet


def spritesheet_strip(images, cell_w, cell_h):
    """Bande horizontale sans marge, pour un moteur de jeu."""
    sheet = Image.new("RGBA", (cell_w * len(images), cell_h), (0, 0, 0, 0))
    for i, im in enumerate(images):
        sheet.paste(im.convert("RGBA"), (i * cell_w, 0))
    return sheet


# ---------------------------------------------------------------- affichage

_checker_cache = {}


def checkerboard(width, height, cell=10, c1=(34, 41, 60), c2=(26, 32, 48)):
    key = (width, height, cell, c1, c2)
    if key in _checker_cache:
        return _checker_cache[key].copy()
    tile = Image.new("RGB", (cell * 2, cell * 2), c1)
    d = ImageDraw.Draw(tile)
    d.rectangle([cell, 0, cell * 2 - 1, cell - 1], fill=c2)
    d.rectangle([0, cell, cell - 1, cell * 2 - 1], fill=c2)
    out = Image.new("RGB", (width, height))
    for y in range(0, height, cell * 2):
        for x in range(0, width, cell * 2):
            out.paste(tile, (x, y))
    if len(_checker_cache) > 8:
        _checker_cache.clear()
    _checker_cache[key] = out
    return out.copy()


def render_zoom(img, zoom, grid=False):
    """Image zoomée (NEAREST) sur damier, prête pour PhotoImage."""
    zoom = max(1, int(zoom))
    img = img.convert("RGBA")
    big = img.resize((img.width * zoom, img.height * zoom), Image.Resampling.NEAREST)
    bg = checkerboard(big.width, big.height, cell=max(8, zoom if zoom <= 12 else 12))
    bg.paste(big, (0, 0), big)
    if grid and zoom >= 6:
        d = ImageDraw.Draw(bg, "RGBA")
        for x in range(0, big.width + 1, zoom):
            d.line([(x, 0), (x, big.height)], fill=(255, 255, 255, 38))
        for y in range(0, big.height + 1, zoom):
            d.line([(0, y), (big.width, y)], fill=(255, 255, 255, 38))
    return bg


def thumbnail(path_or_img, size, bg=(19, 24, 39)):
    im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    im = im.convert("RGBA")
    s = min(size[0] / im.width, size[1] / im.height)
    new = (max(1, int(im.width * s)), max(1, int(im.height * s)))
    im = im.resize(new, Image.Resampling.NEAREST if s >= 1 else Image.Resampling.LANCZOS)
    canvas = checkerboard(size[0], size[1], cell=8)
    canvas.paste(im, ((size[0] - new[0]) // 2, (size[1] - new[1]) // 2), im)
    return canvas
