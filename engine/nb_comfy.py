# -*- coding: utf-8 -*-
"""NeoBestiary Studio - pilotage direct de ComfyUI (bibliothèque standard + Pillow).

Les graphes reprennent les nœuds intégrés utilisés par le générateur d'origine (aucun nœud personnalisé) et ses
modèles : SDXL 1.0 + Pixel Art XL (+ LCM pour le mode rapide). Trois graphes :
  - guide    : img2img depuis une silhouette-guide (fixe la caméra et le plan corporel)
  - inpaint  : toile [design maître | zone masquée] -> la zone masquée est redessinée avec le maître en contexte
  - txt2img  : secours sans guide
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageOps

DEFAULT_MODELS = dict(
    checkpoint="sd_xl_base_1.0.safetensors", lora="pixel-art-xl.safetensors", lora_strength=1.2,
    lora_clip_strength=1.0, lcm_lora="lcm-lora-sdxl.safetensors", lcm_strength=1.0,
    quality=dict(steps=30, cfg=6.0, sampler="dpmpp_2m", scheduler="karras"),
    fast=dict(steps=8, cfg=1.5, sampler="lcm", scheduler="sgm_uniform"),
)


class ComfyError(RuntimeError):
    pass


def load_model_settings(generator_dir):
    """Noms de modèles et réglages lus dans config/profiles.json du générateur (sinon valeurs par défaut)."""
    cfg = json.loads(json.dumps(DEFAULT_MODELS))
    try:
        data = json.loads((Path(generator_dir) / "config" / "profiles.json").read_text(encoding="utf-8"))
        q, f = data["profiles"]["quality"]["params"], data["profiles"]["fast"]["params"]
        cfg.update(checkpoint=q["checkpoint"], lora=q["lora"], lora_strength=q.get("lora_strength", 1.2),
                   lora_clip_strength=q.get("lora_clip_strength", 1.0), lcm_lora=f.get("lcm_lora", cfg["lcm_lora"]),
                   lcm_strength=f.get("lcm_strength", 1.0))
        cfg["quality"] = dict(steps=q["steps"], cfg=q["cfg"], sampler=q["sampler"], scheduler=q["scheduler"])
        cfg["fast"] = dict(steps=f["steps"], cfg=f["cfg"], sampler=f["sampler"], scheduler=f["scheduler"])
    except Exception:
        pass
    return cfg


# --------------------------------------------------------------------------- client

class ComfyClient:
    def __init__(self, url="http://127.0.0.1:8188", timeout=30):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.client_id = uuid.uuid4().hex

    def _request(self, path, data=None, timeout=None):
        body = None if data is None else json.dumps(data).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=body,
                                     headers={"Content-Type": "application/json"} if body else {})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
        return json.loads(raw) if "json" in ctype else raw

    def is_up(self):
        try:
            self._request("/system_stats", timeout=3)
            return True
        except Exception:
            return False

    def object_info(self, node_class):
        try:
            return self._request("/object_info/" + urllib.parse.quote(node_class)).get(node_class)
        except Exception:
            return None

    def choices(self, node_class, input_name):
        """Liste des fichiers proposés par un nœud (ex. LoraLoader.lora_name)."""
        info = self.object_info(node_class)
        try:
            spec = info["input"]["required"][input_name]
            if spec[0] == "COMBO":  # format des nœuds récents : ["COMBO", {"options": [...]}]
                return list(spec[1].get("options", []))
            return list(spec[0])
        except Exception:
            return []

    def upload_png(self, img, name, subfolder="neobestiary"):
        buf = io.BytesIO()
        img.save(buf, "PNG")
        boundary, crlf = uuid.uuid4().hex, "\r\n"
        parts = []
        for k, v in (("overwrite", "true"), ("subfolder", subfolder), ("type", "input")):
            parts.append(f'--{boundary}{crlf}Content-Disposition: form-data; name="{k}"{crlf}{crlf}{v}{crlf}'.encode())
        head = (f'--{boundary}{crlf}Content-Disposition: form-data; name="image"; filename="{name}"{crlf}'
                f'Content-Type: image/png{crlf}{crlf}')
        parts.append(head.encode() + buf.getvalue() + crlf.encode())
        parts.append(f"--{boundary}--{crlf}".encode())
        req = urllib.request.Request(self.url + "/upload/image", data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            res = json.loads(resp.read())
        return f"{res['subfolder']}/{res['name']}" if res.get("subfolder") else res["name"]

    def queue(self, workflow):
        try:
            res = self._request("/prompt", {"prompt": workflow, "client_id": self.client_id})
        except urllib.error.HTTPError as e:
            raise ComfyError("ComfyUI a refusé le graphe : " + _summarize_error(e.read().decode("utf-8", "replace"))) from None
        if res.get("node_errors"):
            raise ComfyError("Erreurs de nœuds ComfyUI : " + json.dumps(res["node_errors"])[:1500])
        return res["prompt_id"]

    def wait(self, prompt_id, timeout=1200, poll=0.7, cancel=lambda: False):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if cancel():
                try:
                    self._request("/interrupt", {})
                except Exception:
                    pass
                raise ComfyError("annulé")
            hist = self._request("/history/" + prompt_id)
            entry = hist.get(prompt_id) if isinstance(hist, dict) else None
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyError("génération en échec : " + _execution_error(status))
                if status.get("completed", True):
                    return entry
            time.sleep(poll)
        raise ComfyError("délai dépassé (GPU occupé ou mémoire vidéo insuffisante ?)")

    def fetch_image(self, image):
        q = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""),
                                    "type": image.get("type", "output")})
        return self._request("/view?" + q, timeout=120)


def _summarize_error(detail):
    try:
        d = json.loads(detail)
        parts = [d.get("error", {}).get("message", "")]
        for nid, ne in (d.get("node_errors") or {}).items():
            for err in ne.get("errors", []):
                parts.append(f"nœud {nid} ({ne.get('class_type')}) : {err.get('message')} {err.get('details', '')}")
        return " ; ".join(p for p in parts if p)
    except Exception:
        return detail[:800]


def _execution_error(status):
    for kind, data in status.get("messages", []):
        if kind == "execution_error":
            return f"{data.get('node_type')} (nœud {data.get('node_id')}) : {str(data.get('exception_message', '')).strip()}"
    return json.dumps(status)[:800]


# --------------------------------------------------------------------------- processus ComfyUI

class ComfyManager:
    """Utilise un ComfyUI déjà lancé ; sinon démarre la version portable et la garde pour la session."""

    def __init__(self, url, root, log=print):
        self.client = ComfyClient(url)
        self.root = Path(root)
        self.log = log
        self.proc = None

    def ensure_up(self, timeout=240):
        if self.client.is_up():
            return
        portable = self.root / "python_embeded" / "python.exe"
        main_py = self.root / "ComfyUI" / "main.py"
        if not (portable.exists() and main_py.exists()):
            raise ComfyError(f"ComfyUI ne répond pas sur {self.client.url} et aucune version portable n'a été trouvée "
                             f"dans {self.root}. Lance ComfyUI (run_nvidia_gpu.bat) ou corrige le chemin dans Réglages.")
        port = urllib.parse.urlparse(self.client.url).port or 8188
        cmd = [str(portable), "-s", "ComfyUI/main.py", "--windows-standalone-build", "--port", str(port),
               "--reserve-vram", "1.5"]
        self.log("Démarrage de ComfyUI (30 à 60 s)…")
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if sys.platform == "win32" else 0
        logf = open(self.root / "neobestiary_comfyui.log", "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(cmd, cwd=str(self.root), stdout=logf, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise ComfyError(f"ComfyUI s'est arrêté au démarrage (code {self.proc.returncode}). "
                                 f"Voir {self.root / 'neobestiary_comfyui.log'}")
            if self.client.is_up():
                self.log("ComfyUI est prêt.")
                return
            time.sleep(1)
        raise ComfyError("ComfyUI ne répond pas après le démarrage.")

    def stop_if_started(self):
        if self.proc and self.proc.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
                else:
                    self.proc.terminate()
            except Exception:
                pass


# --------------------------------------------------------------------------- graphes

def _model_chain(g, m, quality_key, extra_loras):
    """Checkpoint -> Pixel Art LoRA -> LoRA(s) supplémentaires -> (LCM). Retourne (model_ref, clip_ref)."""
    g["4"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["checkpoint"]}}
    g["10"] = {"class_type": "LoraLoader", "inputs": {"model": ["4", 0], "clip": ["4", 1], "lora_name": m["lora"],
                                                       "strength_model": m["lora_strength"],
                                                       "strength_clip": m["lora_clip_strength"]}}
    model, clip = ["10", 0], ["10", 1]
    for i, (name, strength) in enumerate(extra_loras or []):
        nid = str(30 + i)
        g[nid] = {"class_type": "LoraLoader", "inputs": {"model": model, "clip": clip, "lora_name": name,
                                                         "strength_model": strength, "strength_clip": strength}}
        model, clip = [nid, 0], [nid, 1]
    if quality_key == "fast":
        g["11"] = {"class_type": "LoraLoader", "inputs": {"model": model, "clip": clip, "lora_name": m["lcm_lora"],
                                                          "strength_model": m["lcm_strength"],
                                                          "strength_clip": m["lcm_strength"]}}
        g["12"] = {"class_type": "ModelSamplingDiscrete", "inputs": {"model": ["11", 0], "sampling": "lcm", "zsnr": False}}
        model, clip = ["12", 0], ["11", 1]
    return model, clip


IPA_MODEL = "ip-adapter-plus_sdxl_vit-h.safetensors"
IPA_VISION = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"


def ipadapter_ready(client):
    """Vrai si le nœud IP-Adapter et ses deux modèles sont présents dans ComfyUI (install_ipadapter.py)."""
    return (IPA_MODEL in client.choices("IPAdapterModelLoader", "ipadapter_file")
            and IPA_VISION in client.choices("CLIPVisionLoader", "clip_name"))


def _ipadapter(g, model, ref):
    """Référence image : le design de face guide l'identité (couleurs, motifs, traits) de la vue générée.
    ref : dict(image, weight, weight_type)."""
    g["40"] = {"class_type": "LoadImage", "inputs": {"image": ref["image"]}}
    g["41"] = {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_MODEL}}
    g["42"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": IPA_VISION}}
    g["43"] = {"class_type": "IPAdapterAdvanced",
               "inputs": {"model": model, "ipadapter": ["41", 0], "image": ["40", 0], "clip_vision": ["42", 0],
                          "weight": float(ref.get("weight", 0.8)), "weight_type": ref.get("weight_type", "style transfer"),
                          "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0, "embeds_scaling": "V only"}}
    return ["43", 0]


def _regional_conditioning(g, clip, regions):
    """Prompt par zones (nœuds intégrés) : chaque zone ajoute son propre texte à la conditioning globale.
    regions : liste de dict(text, x, y, w, h, strength) en fractions (0-1) de l'image."""
    cond = ["6", 0]
    for i, r in enumerate(regions or []):
        t, a, cb = f"{60 + i * 3}", f"{61 + i * 3}", f"{62 + i * 3}"
        g[t] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": r["text"]}}
        g[a] = {"class_type": "ConditioningSetAreaPercentage",
                "inputs": {"conditioning": [t, 0], "width": float(r["w"]), "height": float(r["h"]),
                           "x": float(r["x"]), "y": float(r["y"]), "strength": float(r.get("strength", 1.0))}}
        g[cb] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": cond, "conditioning_2": [a, 0]}}
        cond = [cb, 0]
    return cond


def build_workflow(kind, m, *, quality, positive, negative, seed, prefix, width=1024, height=1024,
                   image=None, mask=None, denoise=0.92, extra_loras=None, regions=None, reference=None):
    """kind : 'guide' | 'inpaint' | 'txt2img'. reference : dict IP-Adapter (voir _ipadapter) ou None."""
    s = m[quality]
    g = {}
    model, clip = _model_chain(g, m, quality, extra_loras)
    if reference:
        model = _ipadapter(g, model, reference)
    g["6"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": positive}}
    g["7"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": negative}}
    pos_cond = _regional_conditioning(g, clip, regions)
    tile = {"tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}
    sampler = {"model": model, "positive": pos_cond, "negative": ["7", 0], "seed": int(seed), "steps": s["steps"],
               "cfg": s["cfg"], "sampler_name": s["sampler"], "scheduler": s["scheduler"]}
    if kind == "txt2img":
        g["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}}
        g["3"] = {"class_type": "KSampler", "inputs": dict(sampler, latent_image=["5", 0], denoise=1.0)}
        g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}}
        out = ["8", 0]
    elif kind == "guide":
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        g["21"] = {"class_type": "ImageScale", "inputs": {"image": ["20", 0], "upscale_method": "bilinear",
                                                           "width": width, "height": height, "crop": "center"}}
        g["5"] = {"class_type": "VAEEncodeTiled", "inputs": dict({"pixels": ["21", 0], "vae": ["4", 2]}, **tile)}
        g["3"] = {"class_type": "KSampler", "inputs": dict(sampler, latent_image=["5", 0], denoise=float(denoise))}
        g["8"] = {"class_type": "VAEDecodeTiled", "inputs": dict({"samples": ["3", 0], "vae": ["4", 2]}, **tile)}
        out = ["8", 0]
    elif kind == "inpaint":
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        g["21"] = {"class_type": "LoadImageMask", "inputs": {"image": mask, "channel": "red"}}
        g["5"] = {"class_type": "VAEEncodeTiled", "inputs": dict({"pixels": ["20", 0], "vae": ["4", 2]}, **tile)}
        g["22"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["5", 0], "mask": ["21", 0]}}
        g["3"] = {"class_type": "KSampler", "inputs": dict(sampler, latent_image=["22", 0], denoise=float(denoise))}
        g["8"] = {"class_type": "VAEDecodeTiled", "inputs": dict({"samples": ["3", 0], "vae": ["4", 2]}, **tile)}
        g["23"] = {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["20", 0], "source": ["8", 0],
                                                                    "x": 0, "y": 0, "resize_source": False,
                                                                    "mask": ["21", 0]}}
        out = ["23", 0]
    else:
        raise ValueError(kind)
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": out, "filename_prefix": prefix}}
    return g


def check_graph(g):
    """Contrôle statique : chaque lien [id, sortie] pointe vers un nœud existant. Retourne la liste des erreurs."""
    errors = []
    for nid, node in g.items():
        for key, val in node["inputs"].items():
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                if val[0] not in g:
                    errors.append(f"nœud {nid}.{key} -> {val[0]} introuvable")
    return errors


# --------------------------------------------------------------------------- étapes de haut niveau

def run_workflow(client, wf, cancel=lambda: False, mode="RGB"):
    errs = check_graph(wf)
    if errs:
        raise ComfyError("graphe invalide : " + "; ".join(errs))
    pid = client.queue(wf)
    entry = client.wait(pid, cancel=cancel)
    images = []
    for nid, out in entry.get("outputs", {}).items():
        if wf.get(nid, {}).get("class_type") == "SaveImage":
            images.extend(out.get("images", []))
    if not images:
        raise ComfyError("ComfyUI n'a renvoyé aucune image.")
    return Image.open(io.BytesIO(client.fetch_image(images[0]))).convert(mode)


def estimate_background(img):
    """Couleur de fond estimée à partir des bords de l'image."""
    img = img.convert("RGB")
    w, h = img.size
    pts = [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3), (w // 2, 2), (w // 2, h - 3), (2, h // 2), (w - 3, h // 2)]
    px = [img.getpixel(p) for p in pts]
    return tuple(sorted(c[i] for c in px)[len(px) // 2] for i in range(3))


def upload_reference(client, img, weight=0.8, weight_type="style transfer"):
    """Envoie le design de face à ComfyUI ; retourne le dict `reference` de build_workflow."""
    name = client.upload_png(img.convert("RGB"), f"ref_{uuid.uuid4().hex[:8]}.png")
    return dict(image=name, weight=weight, weight_type=weight_type)


def make_master(client, m, guide, *, quality, positive, negative, seed, denoise, extra_loras=None,
                cancel=lambda: False, size=1024, regions=None, reference=None):
    """Design maître (vue de face) : img2img depuis la silhouette-guide, ou txt2img si guide=None.
    reference : design de face en référence IP-Adapter (pour les autres vues)."""
    if guide is None:
        wf = build_workflow("txt2img", m, quality=quality, positive=positive, negative=negative, seed=seed,
                            prefix="neobestiary/master", width=size, height=size, extra_loras=extra_loras,
                            regions=regions, reference=reference)
    else:
        name = client.upload_png(guide.resize((size, size)), f"guide_{uuid.uuid4().hex[:8]}.png")
        wf = build_workflow("guide", m, quality=quality, positive=positive, negative=negative, seed=seed,
                            prefix="neobestiary/master", width=size, height=size, image=name, denoise=denoise,
                            extra_loras=extra_loras, regions=regions, reference=reference)
    return run_workflow(client, wf, cancel)


def make_view(client, m, master, guide, *, quality, positive, negative, seed, denoise, extra_loras=None,
              cancel=lambda: False, cell=768, regions=None, reference=None):
    """Autre vue : toile [maître | guide masqué]. Le maître reste en contexte (identité), le guide fixe la caméra."""
    from nb_guides import recolor_background
    bg = estimate_background(master)
    ref = ImageOps.contain(master.convert("RGB"), (cell, cell))
    left = Image.new("RGB", (cell, cell), bg)
    left.paste(ref, ((cell - ref.width) // 2, (cell - ref.height) // 2))
    right = recolor_background(guide.resize((cell, cell)), bg) if guide is not None else Image.new("RGB", (cell, cell), bg)
    canvas = Image.new("RGB", (cell * 2, cell))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (cell, 0))
    mask = Image.new("RGB", (cell * 2, cell), (0, 0, 0))
    mask.paste((255, 255, 255), (cell, 0, cell * 2, cell))
    tag = uuid.uuid4().hex[:8]
    n_img = client.upload_png(canvas, f"sheet_{tag}.png")
    n_mask = client.upload_png(mask, f"mask_{tag}.png")
    wf = build_workflow("inpaint", m, quality=quality, positive=positive, negative=negative, seed=seed,
                        prefix="neobestiary/view", width=cell * 2, height=cell, image=n_img, mask=n_mask,
                        denoise=denoise, extra_loras=extra_loras, regions=regions, reference=reference)
    result = run_workflow(client, wf, cancel)
    return result.crop((cell, 0, cell * 2, cell)), wf
