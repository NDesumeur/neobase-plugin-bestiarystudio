# -*- coding: utf-8 -*-
"""Télécharge les modèles dans ComfyUI portable : image (FLUX.2 klein 4B, Z-Image Turbo), détourage, musique (ACE-Step 1.5).

python install_models.py <dossier ComfyUI portable> [klein] [zimage] [detour] [musique]   (sans nom : tous)
Source : huggingface.co/Comfy-Org (licence Apache 2.0, sans compte). Les fichiers déjà présents sont gardés.
"""
import sys
import urllib.request
from pathlib import Path


def say(msg):
    print(msg, flush=True)


def download(url, dest, label, on=None):
    """Téléchargement en .part puis renommage : un fichier coupé en route n'est jamais pris pour un modèle complet."""
    say(f"Téléchargement : {label}")
    req = urllib.request.Request(url, headers={"User-Agent": "NeoBestiaryStudio-installer"})
    tmp = Path(str(dest) + ".part")
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if on:
                on(done, total)
            elif total:
                print(f"\r  {done * 100 // total:3d} %  ({done >> 20} / {total >> 20} Mo)", end="", flush=True)
    print()
    tmp.replace(dest)

HF = "https://huggingface.co/Comfy-Org/{}/resolve/main/{}"
ENCODER = ("text_encoders", "qwen_3_4b.safetensors", "Flux-2-Klein-4B", 7.49)  # identique pour les deux modèles
MODELS = {
    "klein": [ENCODER, ("diffusion_models", "flux-2-klein-4b.safetensors", "Flux-2-Klein-4B", 7.22),
              ("vae", "flux2-vae.safetensors", "Flux-2-Klein-4B", 0.31)],
    "zimage": [ENCODER, ("diffusion_models", "z_image_turbo_int8_convrot.safetensors", "z_image_turbo", 5.78),
               ("vae", "ae.safetensors", "z_image_turbo", 0.31)],
    "detour": [("background_removal", "birefnet.safetensors", "BiRefNet", 0.41)],  # licence MIT
    "musique": [("diffusion_models", "acestep_v1.5_turbo.safetensors", "ACE-Step-1.5", 4.46),  # licence Apache 2.0
                ("text_encoders", "qwen_0.6b_ace15.safetensors", "ACE-Step-1.5", 1.11),
                ("text_encoders", "qwen_1.7b_ace15.safetensors", "ACE-Step-1.5", 3.45),
                ("vae", "ace_1.5_vae.safetensors", "ACE-Step-1.5", 0.31)],
}
REQUIRED = ("klein", "detour")  # sans eux, le Studio ne dessine rien ; la musique s'installe ensuite, sans bloquer
PREFIX = {"BiRefNet": ""}  # les autres dépôts rangent leurs fichiers sous split_files/


def missing(comfy_root, which=REQUIRED):  # Z-Image : seulement si demandé
    """Fichiers absents : [(dossier, nom, dépôt, Go)] sans doublon."""
    models = Path(comfy_root) / "ComfyUI" / "models"
    out = []
    for key in which:
        for item in MODELS[key]:
            f = models / item[0] / item[1]
            if item not in out and not (f.is_file() and f.stat().st_size > item[3] * 0.95 * 2 ** 30):
                out.append(item)
    return out


def main():
    if len(sys.argv) < 2:
        say(__doc__)
        return 2
    root = Path(sys.argv[1])
    which = [w for w in sys.argv[2:] if w in MODELS] or list(MODELS)
    for folder, name, repo, gb in missing(root, which):
        dest = root / "ComfyUI" / "models" / folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            download(HF.format(repo, f"{PREFIX.get(repo, 'split_files/')}{folder}/{name}"), dest, f"{name} (~{gb} Go)")
        except Exception as exc:
            say(f"ERREUR {name} : {exc}")
            return 1
    say("TERMINÉ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
