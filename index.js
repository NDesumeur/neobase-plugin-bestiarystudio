// NeoBestiary Studio : une description en français -> une créature pixel art 64x64, 4 directions, marche en 3 images.
// La page parle au moteur (main.js -> engine/nb_server.py) ; tout le dessin de l'interface est dans ui/ (sprites faits main).
const ID = 'neobase.bestiarystudio', U = 'neoplugin://' + ID + '/';
const DIRS = ['bas', 'gauche', 'droite', 'haut'], FR = ['pas1', 'repos', 'pas2'], CYCLE = ['pas1', 'repos', 'pas2', 'repos'];
const ARROW = { bas: '↓', gauche: '←', droite: '→', haut: '↑' };
const ic = n => `<i class="ic" style="background-image:url(${U}ui/i_${n}.png)"></i>`;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const viewKey = (d, f) => f === 'repos' ? d : d + '_' + f;

const HTML = `<link rel="stylesheet" href="${U}ui/studio.css">
<div class="nbs">
  <i class="dust" style="left:8%;top:95%;animation-delay:-3s,0s"></i><i class="dust" style="left:37%;top:100%;animation-delay:-9s,-.4s"></i>
  <i class="dust" style="left:71%;top:97%;animation-delay:-1s,-.8s"></i><i class="dust" style="left:90%;top:99%;animation-delay:-6s,-.2s"></i>
  <header class="nbs-head">
    <i class="emb"></i>
    <div><h1>NeoBestiary <b>Studio</b></h1><small>Grimoire des créatures · sprites 64×64 · 4 directions</small></div>
    <div class="nbs-status off" id="st"><i></i><span>Réveil du grimoire…</span></div>
  </header>
  <nav class="nbs-tabs">
    <button class="nbs-tab on" data-p="creer">${ic('creer')}Créer</button>
    <button class="nbs-tab" data-p="dirs">${ic('directions')}Directions</button>
    <button class="nbs-tab" data-p="lab">${ic('lab')}Sprite Lab</button>
    <button class="nbs-tab" data-p="lib">${ic('biblio')}Bibliothèque</button>
  </nav>
  <main class="nbs-frame">
    <section class="nbs-page" id="p-setup">
      <div class="nbs-title">Préparer le grimoire</div>
      <div id="setupBody"></div>
    </section>

    <section class="nbs-page on" id="p-creer">
      <div class="nbs-cols">
        <div class="grow">
          <div class="nbs-title">Inspiration</div>
          <div class="nbs-row nbs-themes" id="themes">
            <button class="nbs-btn dark sm on" data-t="melange">Mélange</button>
            <button class="nbs-btn dark sm" data-t="lovecraft">Lovecraft</button>
            <button class="nbs-btn dark sm" data-t="animaux">Animaux</button>
            <button class="nbs-btn dark sm" data-t="monstres">Monstres</button>
            <button class="nbs-btn dark sm" data-t="folklore">Folklore</button>
          </div>
          <div class="nbs-row" style="margin-top:8px">
            <button class="nbs-btn" id="inspire">${ic('etoile')}Inspire-moi</button>
            <span class="nbs-hint" id="inspireMsg">Une idée de créature, écrite clairement pour le dessin.</span>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Nom</div>
          <div class="nbs-parch"><input type="text" id="name" maxlength="60" placeholder="Ophidrache, Chien de feu…" spellcheck="false"></div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Décris ta créature</div>
          <div class="nbs-parch"><textarea id="desc" rows="5" placeholder="une pieuvre géante avec un seul grand œil jaune, six tentacules violets…"></textarea></div>
          <div class="nbs-hint" style="margin-top:6px">Écris simplement : « juste un œil », « sans pattes », « un seul œil »… tout est respecté.</div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go big" id="go">${ic('play')}Invoquer</button>
            <button class="nbs-btn red" id="cancel" hidden>Arrêter</button>
            <button class="nbs-btn dark sq" id="dice" title="Nouvelle graine">${ic('de')}</button>
            <span class="nbs-hint" id="seedTxt"></span>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-bar"><i id="bar" style="width:0"></i></div>
          <div class="nbs-step" id="step">&nbsp;</div>
          <div class="nbs-hint" id="stepHint">D'abord 3 esquisses (une demi-minute) : tu choisis la plus fidèle, puis 2 à 3 minutes pour le dos, le profil et la marche.</div>
          <div id="sketches" hidden>
            <div class="nbs-sep"></div>
            <div class="nbs-title">Choisis ton design</div>
            <div class="nbs-row nbs-sketches" id="sketchRow"></div>
            <div class="nbs-hint">Aucune ne va ? Change la graine ou ta description et invoque à nouveau.</div>
          </div>
        </div>
        <div>
          <div class="nbs-title" id="liveTitle">Grimoire vivant</div>
          <div class="nbs-grid4" id="stages"></div>
        </div>
      </div>
    </section>

    <section class="nbs-page" id="p-dirs">
      <div class="nbs-title" id="dirTitle">Planche 4 directions × 3 pas · 64×64</div>
      <div class="nbs-sheet" id="sheet"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-row">
        <button class="nbs-btn dark" id="toLab">${ic('oeil')}Voir en jeu</button>
        <span class="nbs-hint" id="dirHint">Clique une image puis ◀ ▶ pour changer sa version.</span>
      </div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Fiche du bestiaire</div>
      <div class="nbs-parch nbs-fiche" id="fiche"></div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="relore">${ic('refaire')}Réécrire la fiche</button>
        <span class="nbs-hint" id="loreMsg"></span>
      </div>
    </section>

    <section class="nbs-page" id="p-lab">
      <div class="nbs-cols">
        <div>
          <div class="nbs-title">Outils</div>
          <div class="nbs-tools" id="tools">
            <button class="nbs-btn dark sq on" data-t="pen" title="Crayon">${ic('crayon')}</button>
            <button class="nbs-btn dark sq" data-t="erase" title="Gomme">${ic('gomme')}</button>
            <button class="nbs-btn dark sq" data-t="pick" title="Pipette">${ic('pipette')}</button>
            <button class="nbs-btn dark sq" data-t="fill" title="Seau">${ic('seau')}</button>
            <button class="nbs-btn dark sq" id="undo" title="Annuler (Ctrl+Z)">${ic('undo')}</button>
            <button class="nbs-btn dark sq" id="redo" title="Refaire (Ctrl+Y)">${ic('redo')}</button>
            <button class="nbs-btn dark sq on" id="gridBtn" title="Grille">${ic('grille')}</button>
            <button class="nbs-btn dark sq" id="resetEd" title="Oublier les retouches">${ic('refaire')}</button>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Palette</div>
          <div class="nbs-swatches" id="sw"></div>
          <div class="nbs-row" style="margin-top:10px"><span class="nbs-cur" id="cur"></span><input type="color" id="colorIn" title="Autre couleur"></div>
        </div>
        <div>
          <div class="nbs-title" id="fLabel">Image</div>
          <div class="nbs-canvas grid" id="cv"><canvas width="64" height="64" id="ed"></canvas></div>
          <div class="nbs-row" style="margin-top:14px">
            <button class="nbs-btn dark sq" id="fprev">${ic('prev')}</button>
            <span class="nbs-num" id="fnum">1 / 12</span>
            <button class="nbs-btn dark sq" id="fnext">${ic('next')}</button>
          </div>
        </div>
        <div class="grow">
          <div class="nbs-title">Aperçu en jeu</div>
          <div class="nbs-world" id="world"><div class="road"></div><img class="hero" id="hero" alt=""></div>
          <div class="nbs-keys" style="margin-top:8px">Flèches du clavier : fais marcher ta créature</div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Réglages</div>
          <div class="nbs-opt" data-o="outline"><span class="nbs-check"></span>Contour sombre</div>
          <div class="nbs-opt" data-o="lock_palette" style="margin-top:6px"><span class="nbs-check"></span>Palette verrouillée sur les 12 images</div>
          <div class="nbs-opt" data-o="mirror" style="margin-top:6px"><span class="nbs-check"></span>Droite = miroir de gauche</div>
          <div class="nbs-opt" style="margin-top:6px">Couleurs <button class="nbs-btn dark sq" id="cminus">-</button><span class="nbs-num" id="cnum">24</span><button class="nbs-btn dark sq" id="cplus">+</button></div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go" id="exp">${ic('exporter')}Exporter PNG + JSON</button>
            <button class="nbs-btn dark" id="expTo" title="Exporter dans un autre dossier">${ic('dossier')}Ailleurs…</button>
          </div>
          <div class="nbs-hint" id="expMsg" style="margin-top:6px"></div>
        </div>
      </div>
    </section>

    <section class="nbs-page" id="p-lib">
      <div class="nbs-row" style="margin-bottom:12px">
        <div class="nbs-parch" style="flex:1"><input type="text" id="q" placeholder="Chercher une créature…" spellcheck="false"></div>
        <button class="nbs-btn dark" id="openExports" title="Les créatures exportées, prêtes pour le bestiaire">${ic('dossier')}Exports</button>
      </div>
      <div class="nbs-lib" id="lib"></div>
    </section>
  </main>
</div>`;

export default async function (ctx) {
  const view = ctx.view;
  if (!ctx.host) { view.textContent = "Ce plugin doit être approuvé par NeoBase pour s'ouvrir."; return; }
  view.innerHTML = HTML;
  const $ = s => view.querySelector(s), $$ = s => [...view.querySelectorAll(s)];
  const call = (n, ...a) => ctx.neo.pluginMain(ID, n, ...a);
  const get = r => call('get', r), post = (r, b) => call('post', r, b || {});
  const S = { tab: 'creer', cr: null, stamp: 0, seed: Math.floor(Math.random() * 1e6), sel: 'bas_repos', frame: 1, alive: true };
  const src = p => p && S.cr ? `${U}lib/${encodeURIComponent(S.cr.slug)}/${p}?v=${S.stamp}` : '';
  const sprite = (d, f) => S.cr?.sprites?.[d + '_' + f] ? src(S.cr.sprites[d + '_' + f]) : '';
  const say = (msg, bad) => { $('#step').textContent = msg || ' '; $('#step').style.color = bad ? 'var(--red)' : ''; };

  // ------------------------------------------------------------ onglets
  const show = p => {
    S.tab = p;
    $$('.nbs-tab').forEach(t => t.classList.toggle('on', t.dataset.p === p));
    $$('.nbs-page').forEach(x => x.classList.toggle('on', x.id === 'p-' + p));
    if (p === 'lib') loadLib();
    if (p === 'lab') loadFrame();
  };
  $$('.nbs-tab').forEach(t => t.onclick = () => show(t.dataset.p));

  // ------------------------------------------------------------ préparation (ComfyUI, modèles)
  async function setup() {
    const body = $('#setupBody');
    const s = await call('setup');
    if (!s.comfyRoot) {
      show('setup');
      body.innerHTML = `<p>NeoBestiary Studio dessine avec <b>ComfyUI portable</b> (carte NVIDIA, 8 Go de mémoire vidéo).</p>
        <p class="nbs-hint">Installe la version portable depuis github.com/comfyanonymous/ComfyUI (Releases), décompresse-la, puis montre-moi son dossier.</p>
        <div class="nbs-row"><button class="nbs-btn go" id="pick">${ic('dossier')}Choisir le dossier de ComfyUI</button><span class="nbs-hint" id="pickMsg"></span></div>`;
      $('#pick').onclick = async () => {
        const r = await call('pickComfy');
        if (r.ok) setup(); else $('#pickMsg').textContent = "Ce dossier n'est pas ComfyUI portable (il doit contenir python_embeded).";
      };
      return false;
    }
    const st = await get('/status');
    status(st);
    if (st.missing.length) {
      show('setup');
      const gb = st.missing.reduce((a, m) => a + m.gb, 0);
      body.innerHTML = `<p>Il manque les modèles du grimoire (licences libres, téléchargés depuis Hugging Face) :</p>
        <div class="nbs-parch">${st.missing.map(m => `<div>${esc(m.name)} <span class="nbs-hint">· ${m.gb} Go</span></div>`).join('')}</div>
        <div class="nbs-sep"></div>
        <div class="nbs-row"><button class="nbs-btn go" id="inst">${ic('exporter')}Installer (${gb.toFixed(1)} Go)</button></div>
        <div class="nbs-sep"></div><div class="nbs-bar"><i id="ibar" style="width:0"></i></div><div class="nbs-step" id="istep">&nbsp;</div>`;
      $('#inst').onclick = async () => {
        $('#inst').disabled = true;
        try { await post('/install-models'); } catch (e) { $('#istep').textContent = e.message; return; }
        await follow(j => { $('#ibar').style.width = j.progress * 100 + '%'; $('#istep').textContent = j.step; });
        setup();
      };
      return false;
    }
    if (S.tab === 'setup') show('creer');
    return true;
  }
  function status(st) {
    $('#st').classList.toggle('off', st.comfy !== 'prêt');
    $('#st span').textContent = st.comfy === 'prêt' ? `ComfyUI prêt · ${st.model}` : st.comfy === 'arrêté' ? 'ComfyUI démarre à la première invocation' : 'ComfyUI introuvable';
  }

  // ------------------------------------------------------------ tâches (création, refaire, installation)
  async function follow(onTick) {
    for (;;) {
      const j = await get('/job');
      onTick(j);
      if (j.done || !S.alive) return j;
      await new Promise(r => setTimeout(r, 600));
    }
  }
  const busy = on => { $('#go').hidden = on; $('#cancel').hidden = !on; $$('.nbs-redo').forEach(b => b.disabled = on); };
  async function runJob(start) {
    busy(true);
    try { await start(); } catch (e) { busy(false); say(e.message, true); return null; }
    const j = await follow(j => {
      $('#bar').style.width = Math.round(j.progress * 100) + '%';
      say(j.step === 'Préparation' ? 'Préparation… (ComfyUI démarre, ~1 min la première fois)' : `${j.step}… ${Math.round(j.progress * 100)} %`);
    });
    busy(false);
    if (j.error) { say(j.error, true); return null; }
    say(j.kind === 'sketch' ? 'Choisis ton design ↓' : 'Créature invoquée ✓');
    get('/status').then(status).catch(() => {});
    if (j.slug) await open(j.slug);
    return j;
  }

  // ------------------------------------------------------------ créer
  const seedTxt = () => $('#seedTxt').textContent = 'graine ' + S.seed;
  seedTxt();
  $('#dice').onclick = () => { S.seed = Math.floor(Math.random() * 1e6); seedTxt(); };
  $('#go').onclick = () => {
    const description = $('#desc').value.trim();
    if (!description) { say('Décris ta créature d\'abord.', true); $('#desc').focus(); return; }
    runJob(() => post('/create', { name: $('#name').value.trim() || description.split(/[,.]/)[0].slice(0, 40), description, seed: S.seed }))
      .then(j => { if (j) { S.seed = Math.floor(Math.random() * 1e6); seedTxt(); } });
  };
  $('#cancel').onclick = () => post('/cancel');
  $('#stages').innerHTML = DIRS.map((d, i) => `<div class="nbs-stage${i % 3 ? ' path' : ''}"><img class="w" data-d="${d}" alt=""><span class="tag">${ARROW[d]} ${d}</span></div>`).join('');

  // ------------------------------------------------------------ inspiration
  S.theme = 'melange';
  $$('#themes [data-t]').forEach(b => b.onclick = () => {
    S.theme = b.dataset.t;
    $$('#themes [data-t]').forEach(x => x.classList.toggle('on', x === b));
  });
  $('#inspire').onclick = async () => {
    const b = $('#inspire'), msg = $('#inspireMsg');
    b.disabled = true; msg.textContent = 'La plume réfléchit… (une minute la première fois)';
    try {
      const i = await post('/inspire', { theme: S.theme });
      if (i.name) $('#name').value = i.name;
      $('#desc').value = i.description;
      msg.textContent = 'Idée prête : retouche-la si tu veux, puis Invoquer.';
    } catch (e) { msg.textContent = e.message; }
    b.disabled = false;
  };

  // ------------------------------------------------------------ fiche
  function renderFiche() {
    const f = S.cr?.lore, box = $('#fiche');
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Aucune créature ouverte.</div>'; return; }
    box.innerHTML = f ? `<div class="nbs-fiche-head"><b>${esc(S.cr.name)}</b><span class="nbs-type">${esc(f.type)}</span></div>
      <div class="nbs-fiche-sub">${esc(f.espece)} · ${esc(f.taille)} · ${esc(f.poids)}</div>
      <p><i>Habitat.</i> ${esc(f.habitat)}</p><p>${esc(f.description)}</p><p class="nbs-story">${esc(f.histoire)}</p>`
      : '<div class="nbs-hint">Pas encore de fiche : clique « Réécrire la fiche ».</div>';
  }
  $('#relore').onclick = async () => {
    if (!S.cr) return;
    const b = $('#relore'); b.disabled = true; $('#loreMsg').textContent = 'La plume écrit…';
    try { refresh(await post('/lore', { slug: S.cr.slug })); $('#loreMsg').textContent = ''; } catch (e) { $('#loreMsg').textContent = e.message; }
    b.disabled = false;
  };
  $('#openExports').onclick = async () => { try { call('openFolder', (await get('/exports')).folder); } catch (e) { say(e.message, true); } };

  // ------------------------------------------------------------ créature ouverte
  async function open(slug) {
    S.cr = await get('/creature?slug=' + encodeURIComponent(slug));
    S.stamp = Date.now();
    $('#liveTitle').textContent = S.cr.name;
    $('#dirTitle').textContent = S.cr.name + ' · 4 directions × 3 pas · 64×64';
    renderSheet(); renderLab(); renderSketches(); renderFiche();
    if (S.tab === 'lab') loadFrame();
  }
  function renderSketches() {  // esquisses pas encore choisies : on les montre, un clic lance le reste
    const box = $('#sketches'), pending = !!S.cr?.pending;
    box.hidden = !pending;
    if (!pending) return;
    $('#sketchRow').innerHTML = S.cr.designs.map((f, i) => `<button class="nbs-sketch" data-i="${i}" title="Continuer avec celle-ci">
      <img src="${src(f)}" alt=""><span class="nbs-btn go">${ic('ok')}Celle-ci</span></button>`).join('');
    $$('#sketchRow .nbs-sketch').forEach(b => b.onclick = () => {
      box.hidden = true;
      runJob(() => post('/continue', { slug: S.cr.slug, index: +b.dataset.i }));
    });
  }
  const refresh = cr => { S.cr = cr; S.stamp = Date.now(); renderSheet(); renderLab(); renderFiche(); if (S.tab === 'lab') loadFrame(); };

  // ------------------------------------------------------------ directions
  function renderSheet() {
    const box = $('#sheet');
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Invoque ou choisis une créature dans la Bibliothèque.</div>'; return; }
    box.innerHTML = DIRS.map(d => `<div class="lbl">${ARROW[d]} ${d}</div>` +
      FR.map(f => `<div class="cell${S.sel === d + '_' + f ? ' sel' : ''}" data-k="${d}_${f}"><img src="${sprite(d, f)}" alt=""></div>`).join('') +
      `<div class="nbs-row"><div class="nbs-ver"><button class="nbs-btn dark sq" data-v="-1" data-d="${d}">${ic('prev')}</button>` +
      `<span>${verTxt(d)}</span><button class="nbs-btn dark sq" data-v="1" data-d="${d}">${ic('next')}</button></div>` +
      `<button class="nbs-btn dark nbs-redo" data-redo="${d}">${ic('refaire')}Refaire</button></div>`).join('');
    box.querySelectorAll('.cell').forEach(c => c.onclick = () => { S.sel = c.dataset.k; renderSheet(); });
    box.querySelectorAll('[data-v]').forEach(b => b.onclick = async () => {
      const d = b.dataset.d, f = S.sel.startsWith(d + '_') ? S.sel.slice(d.length + 1) : 'repos';
      try { refresh(await post('/choose', { slug: S.cr.slug, key: viewKey(d, f), delta: +b.dataset.v })); } catch (e) { $('#dirHint').textContent = e.message; }
    });
    box.querySelectorAll('[data-redo]').forEach(b => b.onclick = () => {
      $('#dirHint').textContent = 'Nouvelle version en cours… (suivi dans Créer)';
      runJob(() => post('/redo', { slug: S.cr.slug, dir: b.dataset.redo })).then(() => { $('#dirHint').textContent = 'Clique une image puis ◀ ▶ pour changer sa version.'; });
    });
  }
  function verTxt(d) {
    const f = S.sel.startsWith(d + '_') ? S.sel.slice(d.length + 1) : 'repos', v = S.cr.views[viewKey(d, f)];
    return v && v.versions ? `${f === 'repos' ? 'vue' : f} v${v.version}/${v.versions}` : '—';
  }
  $('#toLab').onclick = () => show('lab');

  // ------------------------------------------------------------ animation (scènes + aperçu en jeu)
  const hero = { x: 160, y: 64, d: 'bas', step: 0, keys: new Set() };
  const KEYS = { ArrowDown: ['bas', 0, 1], ArrowUp: ['haut', 0, -1], ArrowLeft: ['gauche', -1, 0], ArrowRight: ['droite', 1, 0] };
  let tick = 0;
  const anim = setInterval(() => {
    if (!view.isConnected) { clearInterval(anim); S.alive = false; return; }
    tick++;
    if (S.cr) $$('img.w').forEach(i => { const s = sprite(i.dataset.d, CYCLE[tick % 4]); if (i.getAttribute('src') !== s) i.src = s; i.style.visibility = s ? '' : 'hidden'; });
    if (S.tab !== 'lab' || !S.cr) return;
    const k = [...hero.keys].pop(), world = $('#world');
    if (k) {
      const [d, dx, dy] = KEYS[k];
      hero.d = d; hero.step++;
      hero.x = Math.max(-32, Math.min(world.clientWidth - 96, hero.x + dx * 8));
      hero.y = Math.max(-32, Math.min(world.clientHeight - 96, hero.y + dy * 8));
    } else hero.step = 1;
    const h = $('#hero'), s = sprite(hero.d, CYCLE[hero.step % 4]);
    if (h.getAttribute('src') !== s) h.src = s;
    h.style.left = hero.x + 'px'; h.style.top = hero.y + 'px';
  }, 150);
  const onKey = e => {
    if (!view.isConnected) { removeEventListener('keydown', onKey, true); removeEventListener('keyup', onUp, true); return; }
    if (S.tab !== 'lab' || /INPUT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    if (KEYS[e.key]) { hero.keys.add(e.key); e.preventDefault(); }
    if (e.ctrlKey && e.key.toLowerCase() === 'z') { undo(); e.preventDefault(); }
    if (e.ctrlKey && e.key.toLowerCase() === 'y') { redo(); e.preventDefault(); }
  };
  const onUp = e => hero.keys.delete(e.key);
  addEventListener('keydown', onKey, true);
  addEventListener('keyup', onUp, true);

  // ------------------------------------------------------------ sprite lab : réglages
  function renderLab() {
    if (!S.cr) return;
    const lab = S.cr.lab;
    $$('.nbs-opt[data-o]').forEach(o => o.querySelector('.nbs-check').classList.toggle('on', !!lab[o.dataset.o]));
    $('#cnum').textContent = lab.colors;
    $('#sw').innerHTML = (S.cr.palette || []).map(c => `<i style="background:${c}" data-c="${c}" class="${c === ed.color ? 'on' : ''}"></i>`).join('');
    $('#sw').querySelectorAll('i').forEach(i => i.onclick = () => setColor(i.dataset.c));
    if (!ed.color && S.cr.palette?.length) setColor(S.cr.palette[0]);
  }
  const setLab = async opts => {
    if (!S.cr) return;
    $('#expMsg').textContent = 'Recalcul des 12 images…';
    try { refresh(await post('/lab', { slug: S.cr.slug, opts })); $('#expMsg').textContent = ''; } catch (e) { $('#expMsg').textContent = e.message; }
  };
  $$('.nbs-opt[data-o]').forEach(o => o.onclick = () => setLab({ [o.dataset.o]: !S.cr?.lab[o.dataset.o] }));
  $('#cminus').onclick = () => S.cr && setLab({ colors: Math.max(2, S.cr.lab.colors - 2) });
  $('#cplus').onclick = () => S.cr && setLab({ colors: Math.min(64, S.cr.lab.colors + 2) });
  $('#resetEd').onclick = async () => { if (S.cr) refresh(await post('/reset-edits', { slug: S.cr.slug })); };
  $('#exp').onclick = async () => {
    if (!S.cr) return;
    try {
      const r = await post('/export', { slug: S.cr.slug });
      $('#expMsg').innerHTML = `Exporté dans Exports : planche, JSON, fiche et portrait · <a href="#" id="openf">ouvrir le dossier</a>`;
      $('#openf').onclick = e => { e.preventDefault(); call('openFolder', r.folder); };
    } catch (e) { $('#expMsg').textContent = e.message; }
  };
  $('#expTo').onclick = async () => {
    if (!S.cr) return;
    try { const r = await call('saveSheet', S.cr.slug); if (r) $('#expMsg').textContent = 'Exporté dans ' + r.folder; } catch (e) { $('#expMsg').textContent = e.message; }
  };

  // ------------------------------------------------------------ sprite lab : éditeur pixel 64x64
  const cv = $('#ed'), g = cv.getContext('2d', { willReadFrequently: true });
  const ed = { tool: 'pen', color: '', undo: [], redo: [], down: false, dirty: false };
  const KEYS12 = DIRS.flatMap(d => FR.map(f => d + '_' + f));
  function setColor(c) { ed.color = c; $('#cur').style.background = c; $('#colorIn').value = c; $$('#sw i').forEach(i => i.classList.toggle('on', i.dataset.c === c)); }
  $('#colorIn').oninput = e => setColor(e.target.value);
  $$('#tools [data-t]').forEach(b => b.onclick = () => { ed.tool = b.dataset.t; $$('#tools [data-t]').forEach(x => x.classList.toggle('on', x === b)); });
  $('#gridBtn').onclick = () => { $('#cv').classList.toggle('grid'); $('#gridBtn').classList.toggle('on'); };
  $('#undo').onclick = () => undo();
  $('#redo').onclick = () => redo();
  $('#fprev').onclick = () => { S.frame = (S.frame + 11) % 12; loadFrame(); };
  $('#fnext').onclick = () => { S.frame = (S.frame + 1) % 12; loadFrame(); };

  function loadFrame() {
    const key = KEYS12[S.frame], [d, f] = key.split('_');
    $('#fnum').textContent = `${S.frame + 1} / 12`;
    $('#fLabel').textContent = `${ARROW[d]} ${d} · ${f === 'repos' ? 'repos' : f === 'pas1' ? 'pas 1' : 'pas 2'}`;
    g.clearRect(0, 0, 64, 64);
    ed.undo = []; ed.redo = [];
    if (!S.cr) return;
    const im = new Image();
    im.onload = () => { g.clearRect(0, 0, 64, 64); g.drawImage(im, 0, 0); };
    im.src = sprite(d, f);
  }
  const hex = (r, g2, b) => '#' + [r, g2, b].map(v => v.toString(16).padStart(2, '0')).join('');
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  function at(e) { const r = cv.getBoundingClientRect(); return [Math.floor((e.clientX - r.left) / r.width * 64), Math.floor((e.clientY - r.top) / r.height * 64)]; }
  function plot(x, y) {
    if (x < 0 || y < 0 || x > 63 || y > 63) return;
    if (ed.tool === 'erase') g.clearRect(x, y, 1, 1);
    else { g.fillStyle = ed.color || '#0b0b12'; g.fillRect(x, y, 1, 1); }
    ed.dirty = true;
  }
  function fill(x, y) {
    const img = g.getImageData(0, 0, 64, 64), p = img.data, i0 = (y * 64 + x) * 4;
    const from = [p[i0], p[i0 + 1], p[i0 + 2], p[i0 + 3]], to = [...rgb(ed.color || '#0b0b12'), 255];
    if (from.every((v, i) => v === to[i])) return;
    const same = i => p[i] === from[0] && p[i + 1] === from[1] && p[i + 2] === from[2] && p[i + 3] === from[3];
    const stack = [[x, y]];
    while (stack.length) {
      const [cx, cy] = stack.pop(), i = (cy * 64 + cx) * 4;
      if (cx < 0 || cy < 0 || cx > 63 || cy > 63 || !same(i)) continue;
      p.set(to, i);
      stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
    g.putImageData(img, 0, 0);
    ed.dirty = true;
  }
  let last = null;
  cv.onpointerdown = e => {
    if (!S.cr) return;
    const [x, y] = at(e);
    if (ed.tool === 'pick') {
      const d = g.getImageData(x, y, 1, 1).data;
      if (d[3]) setColor(hex(d[0], d[1], d[2]));
      return;
    }
    ed.undo.push(g.getImageData(0, 0, 64, 64)); if (ed.undo.length > 60) ed.undo.shift(); ed.redo = [];
    if (ed.tool === 'fill') { fill(x, y); save(); return; }
    ed.down = true; cv.setPointerCapture(e.pointerId); plot(x, y); last = [x, y];
  };
  cv.onpointermove = e => {
    if (!ed.down) return;
    const [x, y] = at(e), [lx, ly] = last, n = Math.max(Math.abs(x - lx), Math.abs(y - ly));
    for (let i = 1; i <= n; i++) plot(Math.round(lx + (x - lx) * i / n), Math.round(ly + (y - ly) * i / n));  // trait continu même si la souris va vite
    last = [x, y];
  };
  cv.onpointerup = () => { if (ed.down) { ed.down = false; save(); } };
  function undo() { if (!ed.undo.length) return; ed.redo.push(g.getImageData(0, 0, 64, 64)); g.putImageData(ed.undo.pop(), 0, 0); ed.dirty = true; save(); }
  function redo() { if (!ed.redo.length) return; ed.undo.push(g.getImageData(0, 0, 64, 64)); g.putImageData(ed.redo.pop(), 0, 0); ed.dirty = true; save(); }
  let saving = Promise.resolve();
  function save() {  // chaque trait est gardé (retouche conservée même si on change les réglages ensuite)
    if (!ed.dirty || !S.cr) return;
    ed.dirty = false;
    const png = cv.toDataURL('image/png'), key = KEYS12[S.frame], slug = S.cr.slug;
    saving = saving.then(() => post('/frame', { slug, key, png })).then(cr => { if (S.cr?.slug === slug) { S.cr = cr; S.stamp = Date.now(); renderSheet(); } })
      .catch(e => { $('#expMsg').textContent = e.message; });
  }

  // ------------------------------------------------------------ bibliothèque
  let libCache = [];
  async function loadLib() {
    try { libCache = await get('/library'); } catch (e) { $('#lib').textContent = e.message; return; }
    renderLib();
  }
  function renderLib() {
    const q = $('#q').value.trim().toLowerCase();
    const list = libCache.filter(c => !q || c.name.toLowerCase().includes(q));
    $('#lib').innerHTML = list.length ? list.map(c => `<div class="nbs-card" data-s="${esc(c.slug)}">
      ${c.thumb ? `<img src="${U}lib/${encodeURIComponent(c.slug)}/${c.thumb}?v=${c.updated}" alt="">` : '<div class="nbs-thumb-empty">?</div>'}
      <div class="nm">${esc(c.name)}</div><div class="meta">${c.versions} version${c.versions > 1 ? 's' : ''}</div>
      <button class="nbs-btn red sq nbs-del" title="Mettre à la corbeille">${ic('corbeille')}</button></div>`).join('')
      : '<div class="nbs-hint">Aucune créature pour l\'instant : invoque la première dans Créer.</div>';
    $$('#lib .nbs-card').forEach(card => {
      card.onclick = async e => {
        const del = e.target.closest('.nbs-del');
        if (del) {
          e.stopPropagation();
          if (!del.classList.contains('sure')) { del.classList.add('sure'); del.title = 'Clique encore pour confirmer'; setTimeout(() => del.classList.remove('sure'), 3000); return; }
          await post('/delete', { slug: card.dataset.s });
          if (S.cr?.slug === card.dataset.s) { S.cr = null; renderSheet(); }
          return loadLib();
        }
        await open(card.dataset.s);
        show(S.cr.pending ? 'creer' : 'dirs');
      };
    });
  }
  $('#q').oninput = renderLib;

  // ------------------------------------------------------------ démarrage
  renderSheet();
  try {
    if (await setup()) {
      const lib = await get('/library');
      if (lib.length) await open(lib[0].slug);
    }
  } catch (e) {
    $('#st span').textContent = 'Moteur indisponible : ' + e.message;
  }
}
