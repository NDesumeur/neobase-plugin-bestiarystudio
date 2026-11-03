# -*- coding: utf-8 -*-
"""Auto-test du service : lance nb_server.py avec le moteur factice et appelle chaque route.

python test_server.py          (ajouter --real pour le vrai moteur, ComfyUI doit être prêt)
"""
import base64
import io
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
TOKEN = "test-jeton"


def call(port, path, body=None, token=TOKEN, raw=False):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-NB-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
            return r.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait_job(port, timeout=900):
    t = time.time()
    while time.time() - t < timeout:
        _, j = call(port, "/job")
        if j["done"]:
            assert not j["error"], j["error"]
            return j
        time.sleep(0.3)
    raise AssertionError("tâche trop longue")


def main():
    real = "--real" in sys.argv
    lib = tempfile.mkdtemp(prefix="nbtest_")
    cmd = [sys.executable, str(HERE / "nb_server.py"), "--token", TOKEN, "--library", lib] + ([] if real else ["--fake"])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    try:
        port = int(proc.stdout.readline().split()[1])
        assert call(port, "/status", token="faux")[0] == 403, "jeton non vérifié"
        code, st = call(port, "/status")
        assert code == 200 and "comfy" in st, st
        assert call(port, "/create", {"name": "X", "description": ""})[0] == 400, "description vide acceptée"

        code, r = call(port, "/create", {"name": "Chien de feu", "description": "chien de feu blanc et rouge", "seed": 42})
        assert code == 200, r
        slug = r["slug"]
        assert call(port, "/create", {"name": "Autre", "description": "x"})[0] == 400, "deux tâches en même temps"
        wait_job(port)

        _, c = call(port, "/creature?slug=" + slug)
        assert len(c["sprites"]) == 12, c["sprites"]
        assert c["views"]["haut"]["versions"] == 2 and c["views"]["droite"]["file"], c["views"]
        code, png = call(port, f"/file?slug={slug}&path=sprites/sheet.png", raw=True)
        sheet = Image.open(io.BytesIO(png))
        assert sheet.size == (192, 256), sheet.size
        assert call(port, f"/file?slug={slug}&path=../../config.json")[0] == 400, "sortie du dossier possible"

        _, c = call(port, "/choose", {"slug": slug, "key": "haut", "delta": 1})
        assert c["views"]["haut"]["version"] == 2
        _, c = call(port, "/choose", {"slug": slug, "key": "gauche", "delta": 1})
        assert c["views"]["droite"]["versions"] == 1, "le miroir s'empile en versions"

        _, c = call(port, "/lab", {"slug": slug, "opts": {"colors": 8, "outline": False}})
        assert c["lab"]["colors"] == 8 and len(c["palette"]) <= 8, c["palette"]

        red = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        buf = io.BytesIO()
        red.save(buf, "PNG")
        _, c = call(port, "/frame", {"slug": slug, "key": "bas_repos", "png": base64.b64encode(buf.getvalue()).decode()})
        _, c = call(port, "/rebuild", {"slug": slug})
        _, png = call(port, f"/file?slug={slug}&path=sprites/bas_repos.png", raw=True)
        assert Image.open(io.BytesIO(png)).convert("RGBA").getpixel((5, 5)) == (255, 0, 0, 255), "retouche perdue"
        call(port, "/reset-edits", {"slug": slug})

        _, r = call(port, "/redo", {"slug": slug, "dir": "gauche"})
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        assert c["views"]["gauche"]["versions"] == 3, c["views"]["gauche"]

        _, e = call(port, "/export", {"slug": slug})
        meta = json.loads(Path(e["json"]).read_text(encoding="utf-8"))
        assert meta["rows"] == 4 and meta["directions"]["haut"]["row"] == 3 and Path(e["png"]).is_file()

        _, libr = call(port, "/library")
        assert [x["slug"] for x in libr] == [slug] and libr[0]["thumb"]
        call(port, "/delete", {"slug": slug})
        assert call(port, "/library")[1] == [] and (Path(lib) / "corbeille").is_dir()
        print("OK : toutes les routes répondent", "(moteur réel)" if real else "(moteur factice)")
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
