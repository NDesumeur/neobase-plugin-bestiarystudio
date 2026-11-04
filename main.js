// NeoBestiary Studio, volet système (chargé par NeoDex une fois le plugin signé et l'accès complet accordé).
// Il lance le moteur Python (engine/nb_server.py) avec le Python fourni par ComfyUI portable, lui parle en HTTP local
// avec un jeton secret, et sert l'interface (ui/) et les images de la bibliothèque sur neoplugin://neodex.bestiarystudio/.
const { app, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path'), crypto = require('crypto');

const ENGINE = path.join(__dirname, 'engine');
const UI = path.join(__dirname, 'ui');
const LIBRARY = () => path.join(app.getPath('documents'), 'NeoBestiary Studio');
const GUESSES = [  // où ComfyUI portable est souvent posé
  'C:\\AI\\ComfyUI\\ComfyUI_windows_portable_nvidia\\ComfyUI_windows_portable',
  'C:\\ComfyUI_windows_portable', 'C:\\AI\\ComfyUI_windows_portable', 'D:\\ComfyUI_windows_portable',
  path.join(app.getPath('home'), 'ComfyUI_windows_portable'), path.join(app.getPath('desktop'), 'ComfyUI_windows_portable'),
];
const isComfy = d => !!d && fs.existsSync(path.join(d, 'python_embeded', 'python.exe')) && fs.existsSync(path.join(d, 'ComfyUI', 'main.py'));
const TYPES = { '.css': 'text/css; charset=utf-8', '.woff': 'font/woff', '.png': 'image/png', '.json': 'application/json' };
const inside = (base, rel) => { const p = path.resolve(base, rel); return p.startsWith(path.resolve(base) + path.sep) ? p : null; };  // jamais en dehors du dossier

module.exports = ({ ipcMain, protocol, serveFile, readDoc, writeDoc }) => {
  let srv = null;  // { proc, port, token, ready }
  const settings = async () => ({ comfyRoot: '', comfyUrl: 'http://127.0.0.1:8188', ...(readDoc('settings') || {}) });  // readDoc de NeoDex est synchrone, null si absent

  async function comfyRoot() {
    const s = await settings();
    if (isComfy(s.comfyRoot)) return s.comfyRoot;
    const found = GUESSES.find(isComfy);
    if (found) await writeDoc('settings', { ...s, comfyRoot: found });
    return found || '';
  }

  async function start() {
    if (srv) return srv.ready;
    const root = await comfyRoot();
    if (!root) throw new Error('COMFY_INTROUVABLE');
    const s = await settings(), token = crypto.randomBytes(24).toString('hex');
    fs.mkdirSync(LIBRARY(), { recursive: true });
    const py = path.join(root, 'python_embeded', 'python.exe');
    const proc = spawn(py, ['-s', path.join(ENGINE, 'nb_server.py'), '--token', token, '--library', LIBRARY(), '--comfy-root', root, '--comfy-url', s.comfyUrl],
      { cwd: ENGINE, windowsHide: true, env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' } });
    const cur = srv = { proc, token, port: 0 };
    let log = '';
    cur.ready = new Promise((ok, ko) => {
      const t = setTimeout(() => ko(new Error('Le moteur ne démarre pas.')), 30000);
      proc.stdout.on('data', d => {
        const m = /NB_READY (\d+)/.exec(String(d));
        if (m) { cur.port = +m[1]; clearTimeout(t); ok(cur); }
      });
      proc.stderr.on('data', d => { log = (log + d).slice(-4000); });
      proc.on('error', e => { clearTimeout(t); ko(e); });
      proc.on('exit', code => { clearTimeout(t); if (srv === cur) srv = null; ko(new Error('Le moteur s\'est arrêté (' + code + ') ' + log.split('\n').slice(-3).join(' '))); });
    });
    cur.ready.catch(() => { if (srv === cur) srv = null; });
    return cur.ready;
  }

  async function call(method, route, body) {
    const s = await start();
    const r = await fetch(`http://127.0.0.1:${s.port}${route}`, {
      method, headers: { 'X-NB-Token': s.token, 'Content-Type': 'application/json' },
      body: method === 'POST' ? JSON.stringify(body || {}) : undefined, signal: AbortSignal.timeout(300000),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || ('erreur ' + r.status));
    return data;
  }

  ipcMain.handle('get', (_e, route) => call('GET', route));
  ipcMain.handle('post', (_e, route, body) => call('POST', route, body));
  ipcMain.handle('setup', async () => ({ comfyRoot: await comfyRoot(), library: LIBRARY() }));
  ipcMain.handle('pickComfy', async () => {
    const r = await dialog.showOpenDialog({ title: 'Dossier de ComfyUI portable', properties: ['openDirectory'] });
    const d = r.canceled ? '' : r.filePaths[0];
    if (!isComfy(d)) return { ok: false };
    await writeDoc('settings', { ...(await settings()), comfyRoot: d });
    if (srv) { srv.proc.kill(); srv = null; }
    return { ok: true, comfyRoot: d };
  });
  ipcMain.handle('openFolder', (_e, p) => { const d = inside(LIBRARY(), path.relative(LIBRARY(), String(p || ''))); return d ? shell.openPath(d) : 'refusé'; });
  ipcMain.handle('saveSheet', async (_e, slug) => {  // exporter ailleurs : l'utilisateur choisit le dossier
    const r = await dialog.showOpenDialog({ title: 'Exporter la planche dans…', properties: ['openDirectory', 'createDirectory'] });
    if (r.canceled) return null;
    return call('POST', '/export', { slug, dest: r.filePaths[0] });
  });

  // neoplugin://neodex.bestiarystudio/ui/<fichier> | lib/<créature>/<chemin>
  protocol(async req => {
    const u = new URL(req.url), [, kind, ...rest] = u.pathname.split('/'), rel = decodeURIComponent(rest.join('/'));
    const file = kind === 'ui' ? inside(UI, rel) : kind === 'lib' ? inside(path.join(LIBRARY(), 'creatures'), rel) : null;
    if (!file || !fs.existsSync(file)) return new Response('', { status: 404 });
    return serveFile(file, req, TYPES[path.extname(file).toLowerCase()]);
  });

  return () => {  // plugin désactivé ou NeoDex fermé : le moteur arrête le ComfyUI qu'il a lancé, puis s'en va
    const cur = srv; srv = null;
    if (!cur) return;
    fetch(`http://127.0.0.1:${cur.port}/shutdown`, { method: 'POST', headers: { 'X-NB-Token': cur.token }, body: '{}', signal: AbortSignal.timeout(3000) })
      .catch(() => {}).finally(() => setTimeout(() => { try { cur.proc.kill(); } catch {} }, 1500));
  };
};
