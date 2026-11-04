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
    <h1>NeoBestiary <b>Studio</b></h1>
    <div class="nbs-status off" id="st"><i></i><span>Réveil du grimoire…</span></div>
  </header>
  <nav class="nbs-tabs">
    <button class="nbs-tab on" data-p="creer">${ic('creer')}Créer</button>
    <button class="nbs-tab" data-p="dirs">${ic('directions')}Directions</button>
    <button class="nbs-tab" data-p="lab">${ic('lab')}Sprite Lab</button>
    <button class="nbs-tab" data-p="lib">${ic('biblio')}Bibliothèque</button>
    <button class="nbs-tab" data-p="eq">${ic('balance')}Équilibre</button>
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
            <button class="nbs-btn sm" id="inspire" style="margin-left:auto">${ic('etoile')}Inspire-moi</button>
          </div>
          <span class="nbs-hint" id="inspireMsg"></span>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Nom</div>
          <div class="nbs-parch"><input type="text" id="name" maxlength="60" placeholder="Ophidrache, Chien de feu…" spellcheck="false"></div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Décris ta créature</div>
          <div class="nbs-parch"><textarea id="desc" rows="5" placeholder="une pieuvre géante avec un seul grand œil jaune, six tentacules violets…"></textarea></div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go big" id="go">${ic('play')}Invoquer</button>
            <button class="nbs-btn" id="auto" title="Invente, dessine et finit des créatures l'une après l'autre, jusqu'à ce que tu rappuies">${ic('refaire')}Invocation en boucle</button>
            <button class="nbs-btn red" id="cancel" hidden>Arrêter</button>
            <button class="nbs-btn dark sq" id="dice" title="Nouvelle graine">${ic('de')}</button>
            <span class="nbs-hint" id="seedTxt"></span>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-bar"><i id="bar" style="width:0"></i></div>
          <div class="nbs-step" id="step">&nbsp;</div>
          
          <div id="sketches" hidden>
            <div class="nbs-sep"></div>
            <div class="nbs-title">Choisis ton design</div>
            <div class="nbs-row nbs-sketches" id="sketchRow"></div>
            <div class="nbs-hint" id="understood"></div>
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
        <span class="nbs-hint" id="dirHint"></span>
      </div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Variantes de couleur</div>
      <div class="nbs-row nbs-themes" id="forms"></div>
      <div class="nbs-row" style="margin-top:8px">
        <div class="nbs-parch"><select id="varSel"></select></div>
        <button class="nbs-btn dark" id="varAdd">${ic('etoile')}Créer la variante</button>
        <span class="nbs-hint" id="varMsg"></span>
      </div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Attaques</div>
      <div id="attacks"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Animations de combat</div>
      <div id="anims"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Fiche du bestiaire</div>
      <div class="nbs-parch nbs-fiche" id="fiche"></div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="relore">${ic('refaire')}Réécrire la fiche</button>
        <span class="nbs-hint" id="loreMsg"></span>
      </div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="illuRedo">${ic('crayon')}Refaire l'image</button>
        <button class="nbs-btn dark sq" id="iPrev" title="Image précédente">${ic('prev')}</button>
        <span class="nbs-num" id="iVer">—</span>
        <button class="nbs-btn dark sq" id="iNext" title="Image suivante">${ic('next')}</button>
        <button class="nbs-btn dark" id="illuCut">${ic('gomme')}Détourage</button>
        <span class="nbs-hint" id="iNote"></span>
      </div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="portraitRedo">${ic('crayon')}Refaire le portrait</button>
        <button class="nbs-btn dark sq" id="pPrev" title="Portrait précédent">${ic('prev')}</button>
        <span class="nbs-num" id="pVer">—</span>
        <button class="nbs-btn dark sq" id="pNext" title="Portrait suivant">${ic('next')}</button>
        <button class="nbs-btn dark" id="portraitCut">${ic('gomme')}Détourage</button>
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
          <div class="nbs-world" id="world"><div class="road"></div><img class="hero" id="hero" alt=""><img class="fx" id="heroFx" alt=""></div>
          <div class="nbs-keys" style="margin-top:8px">Flèches : marcher · 1 à 4 : attaquer</div>
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
        <button class="nbs-btn dark" id="fuseBtn" title="Inventer l'hybride de deux créatures">${ic('etoile')}Fusionner</button>
        <button class="nbs-btn dark" id="openExports" title="Les créatures exportées, prêtes pour le bestiaire">${ic('dossier')}Exports</button>
      </div>
      <div class="nbs-row nbs-fusebar" id="fuseBar" hidden>
        <span class="nbs-hint" id="fuseMsg">Choisis deux créatures finies.</span>
        <button class="nbs-btn go" id="fuseGo" disabled>${ic('play')}Fusionner ces deux</button>
        <button class="nbs-btn dark" id="fuseStop">Annuler</button>
      </div>
      <div class="nbs-lib" id="lib"></div>
    </section>

    <section class="nbs-page" id="p-eq">
      <div id="eq"><div class="nbs-hint">Lecture du bestiaire…</div></div>
    </section>
  </main>
  <div class="nbs-modal" id="cutout" hidden>
    <div class="nbs-frame nbs-modal-box">
      <div class="nbs-title" id="ctTitle">Détourage</div>
      <div class="nbs-rt-cols">
        <div class="nbs-rt-pic nbs-well nbs-ct-pic" id="ctPic"><img id="ctImg" alt=""><canvas id="ctMask"></canvas></div>
        <div class="nbs-rt-side">
          <div class="nbs-hint">Rouge : à effacer · vert : à restaurer.</div>
          <div class="nbs-row nbs-themes" id="ctTool" style="margin-top:8px">
            <button class="nbs-btn dark sm on" data-t="erase">Gomme</button>
            <button class="nbs-btn dark sm" data-t="keep">Restaurer</button>
          </div>
          <div class="nbs-row nbs-themes" id="ctSize" style="margin-top:8px">
            <button class="nbs-btn dark sm" data-s=".012">Fin</button>
            <button class="nbs-btn dark sm on" data-s=".03">Moyen</button>
            <button class="nbs-btn dark sm" data-s=".07">Large</button>
          </div>
          <div class="nbs-row" style="margin-top:12px">
            <button class="nbs-btn go" id="ctGo">${ic('ok')}Valider</button>
            <button class="nbs-btn dark" id="ctClear">${ic('refaire')}Effacer les traits</button>
            <button class="nbs-btn dark" id="ctClose">Annuler</button>
          </div>
          <div class="nbs-hint" id="ctMsg" style="margin-top:8px"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="nbs-modal" id="retouch" hidden>
    <div class="nbs-frame nbs-modal-box">
      <div class="nbs-title" id="rtTitle">Retouche</div>
      <div class="nbs-rt-cols">
        <div class="nbs-rt-pic nbs-well" id="rtPic"><img id="rtImg" alt=""><i id="rtZone"></i></div>
        <div class="nbs-rt-side">
          <div class="nbs-hint">Clique la zone à changer.</div>
          <div class="nbs-row nbs-themes" id="rtSize" style="margin-top:8px">
            <button class="nbs-btn dark sm" data-r=".06">Petite zone</button>
            <button class="nbs-btn dark sm on" data-r=".1">Moyenne</button>
            <button class="nbs-btn dark sm" data-r=".16">Grande</button>
            <button class="nbs-btn dark sm" data-r="0">Toute la créature</button>
          </div>
          <div class="nbs-title" style="margin-top:12px">Que faut-il changer ?</div>
          <div class="nbs-parch"><input type="text" id="rtText" maxlength="160" placeholder="ajoute une corne ici, les yeux en rouge…" spellcheck="false"></div>
          <div class="nbs-row" style="margin-top:12px">
            <button class="nbs-btn go" id="rtGo">${ic('crayon')}Retoucher</button>
            <button class="nbs-btn dark" id="rtClose">Annuler</button>
          </div>
          <div class="nbs-hint" id="rtMsg" style="margin-top:8px"></div>
        </div>
      </div>
    </div>
  </div>
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
    if (p === 'eq') loadBalance();
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
    say(j.kind === 'sketch' ? 'Choisis ton design ↓' : j.kind === 'edit' ? 'Retouche faite ✓ (nouvelle version)'
      : j.kind === 'portrait' ? 'Portrait de combat prêt ✓ (onglet Directions, fiche)'
      : j.kind === 'illustration' ? 'Image du bestiaire prête ✓ (onglet Directions, fiche)' : 'Créature invoquée ✓');
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

  // ------------------------------------------------------------ invocation en boucle : rappuyer l'arrête après la créature en cours
  $('#auto').onclick = async () => {
    const b = $('#auto');
    if (S.auto) {
      S.auto = 'stop';
      await post('/auto-stop').catch(() => {});
      b.disabled = true; b.lastChild.textContent = 'Arrêt après cette créature…';
      return;
    }
    try { await post('/auto'); } catch (e) { say(e.message, true); return; }
    S.auto = 'on'; $('#go').hidden = true; $('#cancel').hidden = false; $$('.nbs-redo').forEach(x => x.disabled = true);
    b.lastChild.textContent = 'Arrêter la boucle';
    let made = 0;
    const j = await follow(j => {
      $('#bar').style.width = Math.round(j.progress * 100) + '%';
      say(`${S.auto === 'stop' ? 'Dernière créature · ' : ''}${j.step === 'Préparation' ? 'Préparation… (ComfyUI démarre, ~1 min la première fois)' : j.step + '…'} ${Math.round(j.progress * 100)} % · ${j.made || 0} finie${(j.made || 0) > 1 ? 's' : ''}`);
      if ((j.made || 0) > made && j.slug) { made = j.made; open(j.slug).catch(() => {}); }
    });
    S.auto = null; busy(false);
    b.disabled = false; b.lastChild.textContent = 'Invocation en boucle';
    say(j.error ? j.error : `Boucle terminée : ${j.made || made} créature${(j.made || made) > 1 ? 's' : ''} invoquée${(j.made || made) > 1 ? 's' : ''} ✓`, !!j.error);
    if (j.slug) await open(j.slug).catch(() => {});
  };
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

  // ------------------------------------------------------------ forme affichée : la créature ou une de ses variantes
  const form = () => S.cr?.forms?.find(f => f.id === S.form) || S.cr?.forms?.[0] ||
    { id: 'base', nom: S.cr?.name, dossier: 'sprites/', fx: S.cr?.attack_fx || {}, combat: S.cr?.lore?.combat };
  function renderForms() {
    const box = $('#forms'), sel = $('#varSel');
    if (!S.cr?.forms?.length) { box.innerHTML = '<span class="nbs-hint">Les variantes arrivent avec la fiche de combat.</span>'; sel.innerHTML = ''; return; }
    if (!S.cr.forms.some(f => f.id === S.form)) S.form = 'base';
    box.innerHTML = S.cr.forms.map(f => `<span class="nbs-form${f.id === S.form ? ' on' : ''}" data-f="${esc(f.id)}">
      <img src="${src(f.dossier + 'bas_repos.png')}" alt=""><b>${esc(f.id === 'base' ? 'Originale' : f.nom.slice(S.cr.name.length + 1))}</b>
      <span class="nbs-rare r${RAR.indexOf(f.combat.rarete)}">${esc(f.combat.rarete)}</span>
      ${f.id === 'base' ? '' : `<button class="nbs-btn red sq" data-rm="${esc(f.id)}" title="Supprimer la variante">${ic('corbeille')}</button>`}</span>`).join('');
    const have = new Set(S.cr.variants || []);
    sel.innerHTML = (S.cr.variant_choices || []).filter(v => !have.has(v.id)).map(v => `<option value="${esc(v.id)}">${esc(v.id === 'chromatique' ? 'chromatique (rare)' : v.label)}</option>`).join('');
    $$('#forms .nbs-form').forEach(el => el.onclick = async e => {
      const rm = e.target.closest('[data-rm]');
      if (rm) {
        e.stopPropagation();
        try { refresh(await post('/variant-remove', { slug: S.cr.slug, variant: rm.dataset.rm })); } catch (err) { $('#varMsg').textContent = err.message; }
        return;
      }
      S.form = el.dataset.f; renderForms(); renderFiche(); renderAttacks(); renderAnims();
    });
  }
  $('#varAdd').onclick = async () => {
    const v = $('#varSel').value;
    if (!v || !S.cr) return;
    $('#varMsg').textContent = 'Peinture de la variante…';
    try { S.form = v; refresh(await post('/variant', { slug: S.cr.slug, variant: v })); $('#varMsg').textContent = 'Variante prête ✓'; }
    catch (e) { $('#varMsg').textContent = e.message; }
  };
  const RAR = ['commun', 'peu commun', 'rare', 'épique', 'légendaire'];

  // ------------------------------------------------------------ fiche
  function renderFiche() {
    const f = S.cr?.lore, box = $('#fiche'), F = form();
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Aucune créature ouverte.</div>'; return; }
    const big = S.cr.illustration ? src(F.dossier + 'illustration.png') : S.cr.portrait ? src(F.dossier + 'portrait.png') : '';
    const pic = big || src(F.dossier + 'bas_repos.png');
    const pv = S.cr.portrait_version || [0, 0], iv = S.cr.illustration_version || [0, 0];
    $('#pVer').textContent = pv[1] ? `${pv[0]} / ${pv[1]}` : '—';
    $('#iVer').textContent = iv[1] ? `${iv[0]} / ${iv[1]}` : '—';
    $('#iNote').textContent = (S.cr.illustration_note || '').replace(/^bestiaire\s*/, '');
    box.innerHTML = f ? `<div class="nbs-fiche-top">${pic ? `<div class="nbs-fiche-pic nbs-well${big ? ' big' : ''}"><img src="${pic}" alt=""></div>` : ''}
      <div><div class="nbs-fiche-head"><b>${esc(F.nom || S.cr.name)}</b><span class="nbs-type">${esc(F.id === 'base' || F.id === 'chromatique' ? f.type : F.id)}</span></div>
      <dl class="nbs-fiche-stats"><dt>Espèce</dt><dd>${esc(f.espece)}</dd><dt>Taille</dt><dd>${esc(f.taille)}</dd>
      <dt>Poids</dt><dd>${esc(f.poids)}</dd><dt>Habitat</dt><dd>${esc(f.habitat)}</dd></dl></div></div>
      <p class="nbs-read">${esc(f.description)}</p>
      <div class="nbs-story"><div class="nbs-story-t">Légende</div><p class="nbs-read">${esc(f.histoire)}</p></div>${combat(F.combat || f.combat, S.cr.illustration && S.cr.portrait ? src(F.dossier + 'portrait.png') : '')}`
      : '<div class="nbs-hint">Pas encore de fiche : clique « Réécrire la fiche ».</div>';
    const rs = $('#rarSel');
    if (rs) rs.onchange = async () => {
      $('#loreMsg').textContent = 'Nouvelle rareté…';
      try { refresh(await post('/rarity', { slug: S.cr.slug, rarete: rs.value || null })); $('#loreMsg').textContent = ''; }
      catch (e) { $('#loreMsg').textContent = e.message; }
    };
  }
  const STAT = { pv: 'PV', attaque: 'Attaque', defense: 'Défense', vitesse: 'Vitesse' };
  const GENRE = { griffe: 'griffes', morsure: 'morsure', charge: 'charge', fouet: 'fouet', corne: 'corne', dard: 'dard', etreinte: 'étreinte',
    projectile: 'projectile', souffle: 'souffle', rayon: 'rayon', cri: 'cri', rafale: 'rafale', pluie: 'pluie', onde: 'onde',
    explosion: 'explosion', soin: 'soin', renfort: 'renfort' };
  const STATUT = { 'brûlure': 'brûle', poison: 'empoisonne', gel: 'gèle', paralysie: 'paralyse' };
  const moveExtra = a => a.effet?.soin ? `<span class="nbs-pow">soigne ${a.effet.soin} % des PV</span>`
    : a.effet?.attaque ? `<span class="nbs-pow">attaque +${a.effet.attaque} %</span>`
    : `<span class="nbs-pow">puissance ${a.puissance}</span>${a.statut ? ` <span class="nbs-pow">· ${STATUT[a.statut.nom] || esc(a.statut.nom)} (${a.statut.chance} %)</span>` : ''}`;
  function combat(k, portrait) {
    if (!k) return '';
    const chips = (l, cls) => l.map(t => `<span class="nbs-chip ${cls}">${esc(t)}</span>`).join(' ') || '—';
    const base = form().id === 'base';
    const rar = base ? `<select class="nbs-rarsel" id="rarSel" title="Rareté : calculée d'après le prestige, ou choisie à la main">
        <option value="">auto${k.prestige != null ? ` · prestige ${k.prestige}` : ''}</option>
        ${RAR.map(r => `<option value="${r}"${k.rarete_fixe && k.rarete === r ? ' selected' : ''}>${r} (fixée)</option>`).join('')}</select>` : '';
    return `<div class="nbs-combat">${portrait ? `<div class="nbs-fiche-pic nbs-well nbs-combat-pic"><img src="${portrait}" alt="" title="Portrait de combat"></div>` : ''}<div class="nbs-combat-head"><span class="nbs-rare r${RAR.indexOf(k.rarete)}">${esc(k.rarete)}</span>${k.rarete_fixe ? ' <span class="nbs-pow">🔒</span>' : ''} ${rar}</div>
      <div class="nbs-statgrid">${Object.entries(STAT).map(([key, label]) => `<span>${label}</span><i><b style="width:${Math.min(100, k.stats[key])}%"></b></i><em>${k.stats[key]}</em>`).join('')}</div>
      <div class="nbs-read nbs-weak"><b>Faible contre</b> ${chips(k.faiblesses, 'bad')} &nbsp; <b>Résiste à</b> ${chips(k.resistances, 'good')}</div>
      ${k.attaques.map((a, i) => `<div class="nbs-move"><div class="nbs-move-t">${i + 1}. ${esc(a.nom)} <span class="nbs-chip">${esc(a.element)}</span> <span class="nbs-chip">${GENRE[a.genre] || esc(a.genre)}</span> ${moveExtra(a)}</div><p class="nbs-read">${esc(a.description)}</p></div>`).join('')}</div>`;
  }
  // ------------------------------------------------------------ attaques animées (corps + calque d'effet)
  const imgCache = {};
  const pic = url => { if (!imgCache[url]) { const im = new Image(); im.src = url; imgCache[url] = im; } return imgCache[url]; };
  const atkMoves = () => form().combat?.attaques || [];
  function atkFrame(n, d, i) {
    const F = form(), fx = F.fx?.[n]?.[d]?.[i];
    if (!fx) return null;
    return { body: src(`${F.dossier}attaque${n}_${d}_${i}.png`), fx: fx.effect ? src(`${F.dossier}effet${n}_${d}_${i}.png`) : null, off: fx.offset };
  }
  function renderAttacks() {
    const box = $('#attacks'), moves = atkMoves();
    if (!S.cr || !moves.length || !form().fx?.['1']) { box.innerHTML = '<div class="nbs-hint">Les attaques arrivent avec la fiche du bestiaire.</div>'; return; }
    box.innerHTML = moves.map((a, k) => `<div class="nbs-atk"><div class="nbs-atk-t">${k + 1}. ${esc(a.nom)} <span class="nbs-hint">· ${esc(a.element)} · ${GENRE[a.genre] || esc(a.genre)}</span></div>
      <div class="nbs-atk-row">${DIRS.map(d => `<canvas width="192" height="192" class="nbs-atk-cv nbs-well" data-n="${k + 1}" data-d="${d}"></canvas>`).join('')}</div></div>`).join('');
  }
  function drawAttack(cv, n, d, i) {
    const f = atkFrame(n, d, i), g = cv.getContext('2d');
    g.imageSmoothingEnabled = false; g.clearRect(0, 0, 192, 192);
    if (!f) return;
    const b = pic(f.body); if (b.complete) g.drawImage(b, 64, 64);
    if (f.fx) { const e = pic(f.fx); if (e.complete) g.drawImage(e, 64 + f.off[0], 64 + f.off[1]); }
  }
  // ------------------------------------------------------------ animations de combat (planches : une ligne par direction)
  const ANIM_NAMES = { attente: 'Attente', degats: 'Dégâts reçus', ko: 'K.O.' };
  function renderAnims() {
    const box = $('#anims');
    if (!S.cr || S.cr.pending || !S.cr.anims) { box.innerHTML = '<div class="nbs-hint">Elles arrivent avec la créature.</div>'; return; }
    box.innerHTML = Object.keys(ANIM_NAMES).map(a => `<div class="nbs-atk"><div class="nbs-atk-t">${ANIM_NAMES[a]}</div>
      <div class="nbs-atk-row">${DIRS.map(d => `<canvas width="64" height="64" class="nbs-anim-cv nbs-well" data-a="${a}" data-d="${d}"></canvas>`).join('')}</div></div>`).join('');
  }
  function animIndex(ms, t, hold) {  // image à montrer au temps t ; hold : la dernière image reste un moment (K.O.)
    const total = ms.reduce((x, y) => x + y, 0) + hold;
    let k = t % total;
    for (let i = 0; i < ms.length; i++) { if (k < ms[i]) return i; k -= ms[i]; }
    return ms.length - 1;
  }
  function drawAnims() {
    const now = performance.now(), F = form();
    $$('.nbs-anim-cv').forEach(cv => {
      const a = cv.dataset.a, ms = S.cr.anims[a], sheet = pic(src(F.dossier + a + '.png')), g = cv.getContext('2d');
      const i = animIndex(ms, now, a === 'ko' ? 900 : a === 'degats' ? 600 : 0);
      g.imageSmoothingEnabled = false; g.clearRect(0, 0, 64, 64);
      if (sheet.complete) g.drawImage(sheet, i * 64, DIRS.indexOf(cv.dataset.d) * 64, 64, 64, 0, 0, 64, 64);
    });
  }
  // ------------------------------------------------------------ retouche ciblée
  const RT = { key: 'bas', index: null, x: null, y: null, r: .1 };
  const NAMES = { bas: 'la face', haut: 'le dos', gauche: 'le profil' };
  function openRetouch(key, index, url) {
    if (!url) return;
    Object.assign(RT, { key, index, x: null, y: null });
    $('#rtTitle').textContent = index === null ? `Retoucher ${NAMES[key]}` : `Retoucher l'esquisse ${index + 1}`;
    $('#rtImg').src = url; $('#rtText').value = ''; $('#rtMsg').textContent = '';
    drawZone(); $('#retouch').hidden = false; $('#rtText').focus();
  }
  function drawZone() {
    const z = $('#rtZone');
    z.hidden = !RT.r || RT.x === null;
    if (z.hidden) return;
    Object.assign(z.style, { left: RT.x * 100 + '%', top: RT.y * 100 + '%', width: RT.r * 200 + '%', height: RT.r * 200 + '%' });
  }
  $('#rtPic').onclick = e => {
    const b = $('#rtImg').getBoundingClientRect();
    RT.x = Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)); RT.y = Math.max(0, Math.min(1, (e.clientY - b.top) / b.height));
    if (!RT.r) { RT.r = .1; $$('#rtSize .nbs-btn').forEach(x => x.classList.toggle('on', x.dataset.r === '.1')); }
    drawZone();
  };
  $$('#rtSize .nbs-btn').forEach(b => b.onclick = () => {
    RT.r = +b.dataset.r; $$('#rtSize .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); drawZone();
  });
  $('#rtClose').onclick = () => { $('#retouch').hidden = true; };
  $('#rtGo').onclick = () => {
    const instruction = $('#rtText').value.trim();
    if (!instruction) { $('#rtMsg').textContent = 'Écris ce qu\'il faut changer.'; return; }
    if (RT.r && RT.x === null) { $('#rtMsg').textContent = 'Clique sur l\'image pour placer la zone (ou choisis « Toute la créature »).'; return; }
    $('#retouch').hidden = true;
    show('creer');
    runJob(() => post('/edit', { slug: S.cr.slug, key: RT.key, instruction, index: RT.index, zone: RT.r ? [RT.x, RT.y, RT.r] : null }));
  };
  $('#rtText').onkeydown = e => { if (e.key === 'Enter') $('#rtGo').click(); };

  $('#illuRedo').onclick = () => {
    if (!S.cr || S.cr.pending) return;
    show('creer');
    runJob(() => post('/illustration', { slug: S.cr.slug }));
  };
  const illuTurn = async delta => {
    if (!S.cr?.illustration_version?.[1]) return;
    try { refresh(await post('/choose', { slug: S.cr.slug, key: 'illustration', delta })); } catch (e) { $('#loreMsg').textContent = e.message; }
  };
  $('#iPrev').onclick = () => illuTurn(-1);
  $('#iNext').onclick = () => illuTurn(1);
  $('#illuCut').onclick = () => S.cr?.hd?.illustration && openCutout('illustration', src(S.cr.hd.illustration));
  $('#portraitCut').onclick = () => S.cr?.hd?.portrait && openCutout('portrait', src(S.cr.hd.portrait));

  // ------------------------------------------------------------ détourage au pinceau (rouge : effacer, vert : restaurer)
  const CT = { key: '', tool: 'erase', size: .03, down: false };
  const CT_NAMES = { bas: 'la face', haut: 'le dos', gauche: 'le profil', portrait: 'le portrait de combat', illustration: "l'image du bestiaire" };
  function openCutout(key, url) {
    if (!url) return;
    CT.key = key;
    $('#ctTitle').textContent = `Détourage de ${CT_NAMES[key] || key}`;
    $('#ctMsg').textContent = '';
    const img = $('#ctImg'), cv = $('#ctMask');
    img.onload = () => { cv.width = img.naturalWidth; cv.height = img.naturalHeight; placeMask(); };
    img.src = url;
    $('#cutout').hidden = false;
  }
  function placeMask() {  // le calque couvre exactement l'image affichée (object-fit: contain)
    const img = $('#ctImg'), cv = $('#ctMask'), box = $('#ctPic'), W = box.clientWidth, H = box.clientHeight;
    const k = Math.min(W / img.naturalWidth, H / img.naturalHeight), w = img.naturalWidth * k, h = img.naturalHeight * k;
    Object.assign(cv.style, { left: (W - w) / 2 + 'px', top: (H - h) / 2 + 'px', width: w + 'px', height: h + 'px' });
  }
  function ctPaint(e) {
    const cv = $('#ctMask'), b = cv.getBoundingClientRect(), g = cv.getContext('2d');
    const x = (e.clientX - b.left) / b.width * cv.width, y = (e.clientY - b.top) / b.height * cv.height;
    g.fillStyle = CT.tool === 'erase' ? '#ff0000' : '#00ff00';
    g.beginPath(); g.arc(x, y, CT.size * cv.width, 0, Math.PI * 2); g.fill();
  }
  $('#ctMask').onpointerdown = e => { CT.down = true; $('#ctMask').setPointerCapture(e.pointerId); ctPaint(e); };
  $('#ctMask').onpointermove = e => { if (CT.down) ctPaint(e); };
  $('#ctMask').onpointerup = () => { CT.down = false; };
  $$('#ctTool .nbs-btn').forEach(b => b.onclick = () => { CT.tool = b.dataset.t; $$('#ctTool .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); });
  $$('#ctSize .nbs-btn').forEach(b => b.onclick = () => { CT.size = +b.dataset.s; $$('#ctSize .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); });
  $('#ctClear').onclick = () => { const cv = $('#ctMask'); cv.getContext('2d').clearRect(0, 0, cv.width, cv.height); };
  $('#ctClose').onclick = () => { $('#cutout').hidden = true; };
  $('#ctGo').onclick = async () => {
    const b = $('#ctGo'); b.disabled = true; $('#ctMsg').textContent = 'Détourage…';
    try { refresh(await post('/cutout', { slug: S.cr.slug, key: CT.key, mask: $('#ctMask').toDataURL('image/png') })); $('#cutout').hidden = true; }
    catch (e) { $('#ctMsg').textContent = e.message; }
    b.disabled = false;
  };

  $('#portraitRedo').onclick = () => {
    if (!S.cr || S.cr.pending) return;
    show('creer');
    runJob(() => post('/portrait', { slug: S.cr.slug }));
  };
  const portraitTurn = async delta => {
    if (!S.cr?.portrait_version?.[1]) return;
    try { refresh(await post('/choose', { slug: S.cr.slug, key: 'portrait', delta })); } catch (e) { $('#loreMsg').textContent = e.message; }
  };
  $('#pPrev').onclick = () => portraitTurn(-1);
  $('#pNext').onclick = () => portraitTurn(1);
  $('#relore').onclick = async () => {
    if (!S.cr) return;
    const b = $('#relore'); b.disabled = true; $('#loreMsg').textContent = 'La plume écrit…';
    try { refresh(await post('/lore', { slug: S.cr.slug })); $('#loreMsg').textContent = ''; } catch (e) { $('#loreMsg').textContent = e.message; }
    b.disabled = false;
  };
  $('#openExports').onclick = async () => { try { call('openFolder', (await get('/exports')).folder); } catch (e) { say(e.message, true); } };

  // ------------------------------------------------------------ créature ouverte
  async function open(slug) {
    if (S.cr?.slug !== slug) S.form = 'base';
    S.cr = await get('/creature?slug=' + encodeURIComponent(slug));
    S.stamp = Date.now();
    $('#liveTitle').textContent = S.cr.name;
    $('#dirTitle').textContent = S.cr.name + ' · 4 directions × 3 pas · 64×64';
    renderSheet(); renderLab(); renderSketches(); renderForms(); renderFiche(); renderAttacks(); renderAnims();
    if (S.tab === 'lab') loadFrame();
  }
  function renderSketches() {  // esquisses pas encore choisies : on les montre, un clic lance le reste
    const box = $('#sketches'), pending = !!S.cr?.pending;
    box.hidden = !pending;
    if (!pending) return;
    const b = S.cr.brief, P = { quatre_pattes: 'à quatre pattes', deux_jambes: 'debout sur deux jambes', plusieurs_pattes: `sur ${b?.pattes} pattes`,
      flotte: 'flotte dans les airs, sans pattes', vole: 'vole', rampe: 'rampe, sans pattes', nage: 'nage, sans pattes',
      sautille: 'avance par bonds', roule: 'roule en boule', glisse: 'glisse comme une gelée', enracine: 'enracinée dans le sol' };
    $('#understood').textContent = b?.posture ? `Compris : ${P[b.posture] || b.posture}. Le dos et le profil suivront cette posture.` : '';
    // note du contrôle automatique : « esquisse 2 ✓ » ou « esquisse 3 ⚠ 1 tête au lieu de 3 »
    const checkNote = n => { const m = /([✓⚠].*)$/.exec(n || ''); return m ? `<span class="nbs-verdict ${m[1][0] === '✓' ? 'ok' : 'ko'}">${m[1] === '✓' ? '✓ vérifiée' : esc(m[1])}</span>` : ''; };
    $('#sketchRow').innerHTML = S.cr.designs.map((f, i) => `<div class="nbs-sketch" data-i="${i}">
      <img src="${src(f)}" alt="">${checkNote(S.cr.design_notes?.[i])}<button class="nbs-btn go" data-go="${i}">${ic('ok')}Celle-ci</button>
      <button class="nbs-btn dark sm" data-rt="${i}">Retoucher</button></div>`).join('');
    $$('#sketchRow [data-go]').forEach(b => b.onclick = () => {
      box.hidden = true;
      runJob(() => post('/continue', { slug: S.cr.slug, index: +b.dataset.go }));
    });
    $$('#sketchRow [data-rt]').forEach(b => b.onclick = () => openRetouch('bas', +b.dataset.rt, src(S.cr.designs[+b.dataset.rt])));
  }
  const refresh = cr => { S.cr = cr; S.stamp = Date.now(); renderSheet(); renderLab(); renderForms(); renderFiche(); renderAttacks(); renderAnims(); if (S.tab === 'lab') loadFrame(); };

  // ------------------------------------------------------------ directions
  function renderSheet() {
    const box = $('#sheet');
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Invoque ou choisis une créature dans la Bibliothèque.</div>'; return; }
    box.innerHTML = DIRS.map(d => `<div class="lbl">${ARROW[d]} ${d}</div>` +
      FR.map(f => `<div class="cell${S.sel === d + '_' + f ? ' sel' : ''}" data-k="${d}_${f}"><img src="${sprite(d, f)}" alt=""></div>`).join('') +
      `<div class="nbs-row"><div class="nbs-ver"><button class="nbs-btn dark sq" data-v="-1" data-d="${d}">${ic('prev')}</button>` +
      `<span>${verTxt(d)}</span><button class="nbs-btn dark sq" data-v="1" data-d="${d}">${ic('next')}</button></div>` +
      `<button class="nbs-btn dark nbs-redo" data-redo="${d}">${ic('refaire')}Refaire</button>` +
      (d === 'droite' ? '' : `<button class="nbs-btn dark nbs-redo" data-rt="${d}">${ic('crayon')}Retoucher</button>` +
        `<button class="nbs-btn dark nbs-redo" data-ct="${d}">${ic('gomme')}Détourage</button>`) + `</div>`).join('');
    box.querySelectorAll('[data-ct]').forEach(b => b.onclick = () => {
      const k = b.dataset.ct, v = S.cr.views[k];
      openCutout(k, v?.file ? src(v.file) : '');
    });
    box.querySelectorAll('.cell').forEach(c => c.onclick = () => { S.sel = c.dataset.k; renderSheet(); });
    box.querySelectorAll('[data-v]').forEach(b => b.onclick = async () => {
      const d = b.dataset.d, f = S.sel.startsWith(d + '_') ? S.sel.slice(d.length + 1) : 'repos';
      try { refresh(await post('/choose', { slug: S.cr.slug, key: viewKey(d, f), delta: +b.dataset.v })); } catch (e) { $('#dirHint').textContent = e.message; }
    });
    box.querySelectorAll('[data-rt]').forEach(b => b.onclick = () => {
      const k = b.dataset.rt, v = S.cr.views[k];
      openRetouch(k, null, v?.file ? src(v.file) : '');
    });
    box.querySelectorAll('[data-redo]').forEach(b => b.onclick = () => {
      $('#dirHint').textContent = 'Nouvelle version en cours… (suivi dans Créer)';
      runJob(() => post('/redo', { slug: S.cr.slug, dir: b.dataset.redo })).then(() => { $('#dirHint').textContent = ''; });
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
    if (S.cr && S.tab === 'dirs') { $$('.nbs-atk-cv').forEach(cv => drawAttack(cv, cv.dataset.n, cv.dataset.d, Math.min(3, tick % 7))); drawAnims(); }
    if (S.tab !== 'lab' || !S.cr) return;
    const fxImg = $('#heroFx');
    if (hero.atk) {  // une attaque en cours : ses 4 images, puis retour à la marche
      const f = atkFrame(hero.atk, hero.d, hero.atkI++);
      if (f) {
        const h = $('#hero');
        h.src = f.body; h.style.left = hero.x + 'px'; h.style.top = hero.y + 'px';
        fxImg.hidden = !f.fx;
        if (f.fx) { fxImg.src = f.fx; fxImg.style.left = hero.x + f.off[0] * 2 + 'px'; fxImg.style.top = hero.y + f.off[1] * 2 + 'px'; }
        return;
      }
      hero.atk = 0;
    }
    fxImg.hidden = true;
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
    if (/^[1-4]$/.test(e.key) && !hero.atk && S.cr?.attack_fx?.[e.key]) { hero.atk = +e.key; hero.atkI = 0; e.preventDefault(); }
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
      card.classList.toggle('picked', !!S.fuse?.includes(card.dataset.s));
      card.onclick = async e => {
        if (S.fuse) {  // mode fusion : on choisit deux créatures
          const i = S.fuse.indexOf(card.dataset.s);
          if (i >= 0) S.fuse.splice(i, 1); else S.fuse = [...S.fuse, card.dataset.s].slice(-2);
          fuseBar();
          return renderLib();
        }
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
  function fuseBar() {
    $('#fuseBar').hidden = !S.fuse;
    if (!S.fuse) return;
    const names = S.fuse.map(s => libCache.find(c => c.slug === s)?.name || s);
    $('#fuseMsg').textContent = names.length ? names.join(' + ') + (names.length < 2 ? ' + … (choisis-en une autre)' : '') : 'Choisis deux créatures finies.';
    $('#fuseGo').disabled = S.fuse.length !== 2;
  }
  $('#fuseBtn').onclick = () => { S.fuse = S.fuse ? null : []; fuseBar(); renderLib(); };
  $('#fuseStop').onclick = () => { S.fuse = null; fuseBar(); renderLib(); };
  $('#fuseGo').onclick = () => {
    const [a, b] = S.fuse || [];
    if (!b) return;
    S.fuse = null; fuseBar(); show('creer');
    runJob(() => post('/fuse', { a, b }));
  };

  // ------------------------------------------------------------ équilibrage du bestiaire
  async function loadBalance() {
    const box = $('#eq');
    let B;
    try { B = await get('/balance'); } catch (e) { box.innerHTML = `<div class="nbs-hint">${esc(e.message)}</div>`; return; }
    if (!B.total) { box.innerHTML = '<div class="nbs-hint">Aucune créature avec une fiche de combat pour l\'instant.</div>' + (B.alertes.length ? `<ul class="nbs-alerts">${B.alertes.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : ''); return; }
    const pct = n => Math.round(100 * n / B.total);
    box.innerHTML = `<div class="nbs-cols nbs-eq">
      <div class="grow">
        <div class="nbs-title">Raretés · ${B.total} créature${B.total > 1 ? 's' : ''}</div>
        <div class="nbs-eqbars">${B.raretes.map((r, i) => `<span class="nbs-rare r${i}">${esc(r.nom)}</span>
          <i title="attendu : environ ${r.attendu} %"><b class="r${i}" style="width:${pct(r.n)}%"></b><u style="left:${r.attendu}%"></u></i>
          <em>${r.n} · ${pct(r.n)} %</em>`).join('')}</div>
        
        <div class="nbs-title" style="margin-top:14px">Types</div>
        <div class="nbs-eqtypes">${B.types.map(t => `<span class="nbs-eqtype${t.n ? '' : ' none'}"><b>${t.n}</b>${esc(t.type)}</span>`).join('')}</div>
        <div class="nbs-title" style="margin-top:14px">Moyennes</div>
        <div class="nbs-eqavg">${Object.entries(STAT).map(([k, l]) => `<span><b>${B.moyennes[k]}</b>${l}</span>`).join('')}</div>
      </div>
      <div class="grow">
        <div class="nbs-title">À surveiller</div>
        ${B.alertes.length ? `<ul class="nbs-alerts">${B.alertes.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : '<div class="nbs-ok">✓ Bestiaire équilibré</div>'}
        ${B.conseils?.length ? `<div class="nbs-title" style="margin-top:14px">Raretés conseillées</div>
        
        <div class="nbs-eqlist">${B.conseils.map(t => `<div class="nbs-eqrow nbs-tip"><span class="nm">${esc(t.nom)} <span class="nbs-hint">· prestige ${t.prestige}</span></span>
          <span class="nbs-rare r${RAR.indexOf(t.actuelle)}">${esc(t.actuelle)}</span>→<span class="nbs-rare r${RAR.indexOf(t.conseillee)}">${esc(t.conseillee)}</span>
          <button class="nbs-btn dark sm" data-tip="${esc(t.slug)}" data-r="${esc(t.conseillee)}">Appliquer</button></div>`).join('')}</div>` : ''}
        <div class="nbs-title" style="margin-top:14px">Classement</div>
        <div class="nbs-eqlist">${B.creatures.sort((x, y) => y.total - x.total).map(c => `<div class="nbs-eqrow" data-s="${esc(c.slug)}">
          <img src="${U}lib/${encodeURIComponent(c.slug)}/sprites/bas_repos.png" alt=""><span class="nm">${esc(c.nom)}</span>
          <span class="nbs-rare r${RAR.indexOf(c.rarete)}">${esc(c.rarete)}</span><span class="nbs-chip">${esc(c.type)}</span>
          <em>${c.total}</em>${c.variantes ? `<span class="nbs-hint">+${c.variantes} var.</span>` : ''}</div>`).join('')}</div>
      </div></div>`;
    $$('#eq .nbs-eqrow[data-s]').forEach(row => row.onclick = async () => { await open(row.dataset.s); show('dirs'); });
    $$('#eq [data-tip]').forEach(b => b.onclick = async () => {
      b.disabled = true;
      try { await post('/rarity', { slug: b.dataset.tip, rarete: b.dataset.r }); if (S.cr?.slug === b.dataset.tip) refresh(await get('/creature?slug=' + encodeURIComponent(b.dataset.tip))); loadBalance(); }
      catch (e) { b.disabled = false; say(e.message, true); }
    });
  }

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
