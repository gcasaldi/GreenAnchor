/* GreenAnchor — Impact Intelligence, curated client-side layer.
   URL/domain and page-type checks are heuristics, NOT independent verification
   of a campaign's status, impact, accuracy, or present availability. */
(() => {
  'use strict';
  const state = {campaigns: [], focus: [], scope:'all', query:'', savedOnly:false, generatedAt:null};
  const $ = id => document.getElementById(id);
  const h = value => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const domains = ['greenpeace.org','openpetition.eu','change.org','citizens-initiative.europa.eu','legambiente.it','marevivo.it','wwf.it','wwf.panda.org','avaaz.org'];
  const environmentalTerms = /(?:klima|klima|grün|gruen|wald|natur|umwelt|erde|oekolog|ökol|biodivers|meer|ozean|plastik|tierschutz|forest|climat|ocean|wildlife|environment|green|polluti|species|nature|fossil|sea|mining|dairy|meat|planet|marine|energia|ambiente|foreste|oceani|inquinament|animali|mare|cambiament)/i;
  const slugToTopic = {
    'stop-deep-sea-mining':'Oceani',
    'stop-fossil-gas':'Clima',
    'stop-big-meat-and-dairy':'Clima',
    'support-migrant-fishers':'Oceani'
  };
  const urlOf = value => {
    try {
      const url = new URL(String(value||''));
      if (url.protocol !== 'https:') return null;
      const host = url.hostname.toLowerCase();
      if (!domains.some(d => host === d || host.endsWith('.'+d))) return null;
      return url;
    } catch (_) { return null; }
  };
  function actionable(item) {
    if (!item || typeof item.title !== 'string' || item.title.trim().length < 12) return false;
    const u = urlOf(item.action_url);
    if (!u) return false;
    const p = u.pathname.toLowerCase().replace(/\/$/,'');
    const host = u.hostname;
    const title = item.title.toLowerCase();
    if (host.endsWith('greenpeace.org')) {
      return /^\/(?:international|italy)\/act\/[\w-]+$/.test(p);
    }
    if (host.endsWith('openpetition.eu')) {
      return /^\/petition\/online\/[\w%-]+$/.test(p) && environmentalTerms.test(title);
    }
    if (host.endsWith('change.org')) {
      return /^\/p\/[\w%-]+$/.test(p) && environmentalTerms.test(title);
    }
    if (host.endsWith('citizens-initiative.europa.eu')) {
      return p.includes('/initiatives/details/') && environmentalTerms.test(title);
    }
    if (host.endsWith('legambiente.it')) {
      return /^\/campagne\/[\w-]+$/.test(p);
    }
    if (host.endsWith('marevivo.it')) {
      return /^\/(?:campagne|progetti|petizioni)\/[\w-]+$/.test(p);
    }
    if (host.endsWith('wwf.it')) {
      return /^\/(?:petizioni|campagne)\/[\w-]+$/.test(p);
    }
    if (host.endsWith('wwf.panda.org')) {
      return /^\/act\/[\w-]+$/.test(p);
    }
    if (host.endsWith('avaaz.org') || host.endsWith('secure.avaaz.org')) {
      return /^\/campaign\/[\w-]+\/[\w-]+$/.test(p) && environmentalTerms.test(title);
    }
    return false;
  }
  const scopeOf = item => {
    const value = String(item.scope || item.country || '').toLowerCase();
    if (value === 'it' || value.includes('ital')) return 'italia';
    if (value === 'eu' || value.includes('europ')) return 'europa';
    return 'globale';
  };
  const scopeLabel = scope => ({italia:'Italia',europa:'Europa',globale:'Globale'})[scope] || 'Globale';
  const domainOf = item => urlOf(item.action_url)?.hostname.replace(/^www\./,'') || '—';
  const orgSite = item => Boolean(item.verified_organization === true && urlOf(item.action_url));
  const validDate = raw => {
    if (!raw) return null;
    const d = new Date(raw);
    return Number.isFinite(d.getTime()) ? d : null;
  };
  const dateText = raw => {
    const d = validDate(raw);
    return d ? new Intl.DateTimeFormat('it-IT',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(d) : 'Non disponibile';
  };
  const deadlineDays = item => {
    const end = validDate(item.deadline);
    return end ? Math.ceil((end.getTime() - Date.now()) / 86400000) : null;
  };
  const countUrgent = items => items.filter(x => {
    const days=deadlineDays(x);
    return days !== null && days >= 0 && days <= 7;
  }).length;
  const countNew = items => items.filter(x => {
    const dt=validDate(x.first_seen);
    return dt && Date.now() - dt.getTime() >= 0 && Date.now() - dt.getTime() <= 86400000;
  }).length;
  function selectFocus(items) {
    const ordered = items.slice().sort((a,b) => {
      const ad=deadlineDays(a),bd=deadlineDays(b);
      const aUrg=ad!==null && ad>=0 && ad<=30 ? ad : 10000;
      const bUrg=bd!==null && bd>=0 && bd<=30 ? bd : 10000;
      if (aUrg !== bUrg) return aUrg-bUrg;
      return Number(orgSite(b))-Number(orgSite(a)) || a.title.localeCompare(b.title);
    });
    const taken=new Set(), selected=[];
    for (const item of ordered) {
      const topic = topicOf(item);
      if (!taken.has(topic)) {taken.add(topic);selected.push(item);}
      if (selected.length === 3) return selected;
    }
    for (const item of ordered) {
      if (!selected.includes(item)) selected.push(item);
      if (selected.length === 3) break;
    }
    return selected;
  }
  function topicOf(item) {
    const url=urlOf(item.action_url);
    const slug=url?.pathname.split('/').filter(Boolean).slice(-1)[0] || '';
    if (slugToTopic[slug]) return slugToTopic[slug];
    const words=[item.title,item.theme,(item.tags||[]).join(' ')].join(' ');
    if (/oceani|ocean|marine|mare|sea|mining|fish/i.test(words))return 'Oceani';
    if (/clima|climate|fossil|gas|dairy|meat|energy/i.test(words))return 'Clima';
    if (/wald|foreste|forest|grün|natur|biodivers/i.test(words))return 'Natura';
    return 'Ambiente';
  }
  function summaryOf(item) {
    const raw=String(item.summary||item.objective||'').trim();
    if (!raw || /Obiettivo: supportare un'azione ambientale concreta rilevata da/i.test(raw)) {
      return 'Azione individuata su una piattaforma esterna. Consulta la pagina originale per dettagli, requisiti e disponibilità.';
    }
    return raw.length > 250 ? raw.slice(0,247)+'…' : raw;
  }
  function card(item,index) {
    const id=String(item.id || '');
    const url=urlOf(item.action_url)?.href || '#';
    const deadline=deadlineDays(item);
    const progress=typeof item.progress_percent==='number' && Number.isFinite(item.progress_percent) && item.progress_percent>=0 && item.progress_percent<=100 ? item.progress_percent:null;
    const saved=isSaved(item);
    const proof=orgSite(item);
    return `<article class="campaign-card" data-id="${h(id)}" data-scope="${scopeOf(item)}">
      <div class="campaign-header">
        <div class="campaign-topline"><span class="campaign-index">GA / SIGNAL ${String(index+1).padStart(2,'0')}</span>
          <span class="badge ${proof?'badge-check':'badge-review'}">${proof?'◈ Sito organizzazione':'◇ Fonte da verificare'}</span>
        </div>
        <div class="campaign-overline">${h(topicOf(item))} · ${h(scopeLabel(scopeOf(item)))}</div>
        <h3 class="campaign-title">${h(item.title)}</h3>
        <div class="campaign-meta"><span class="badge badge-source">${h(item.source)}</span><span class="badge">${h(domainOf(item))}</span></div>
      </div>
      <div class="campaign-body">
        <p class="campaign-summary">${h(summaryOf(item))}</p>
        ${progress!==null?`<div class="progress-section"><div class="progress-label"><span>Avanzamento dichiarato dalla fonte</span><strong>${progress}%</strong></div><div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div></div>`:''}
        ${deadline!==null&&deadline>=0?`<div class="campaign-deadline">◷ Scadenza indicata: ${h(dateText(item.deadline))}</div>`:''}
        <div class="campaign-footer">
          <button class="btn-action" type="button" data-details="${h(id)}">Verifica scheda ↗</button>
          <a class="btn-action btn-action-primary" href="${h(url)}" target="_blank" rel="noopener noreferrer" aria-label="Apri fonte originale: ${h(item.title)}">Vai alla fonte ↗</a>
          <button class="card-save ${saved?'saved':''}" type="button" data-save="${h(id)}" aria-label="${saved?'Rimuovi dai salvati':'Salva campagna'}" title="Salva sul dispositivo">${saved?'★':'☆'}</button>
        </div>
      </div>
    </article>`;
  }
  let saved = new Set();
  function readSaved() {
    try { const raw=JSON.parse(localStorage.getItem('greenanchor_saved_v1')||'[]');saved=new Set(Array.isArray(raw)?raw.map(String):[]);}catch(_){saved=new Set();}
  }
  const isSaved = item => saved.has(String(item.id || item.action_url));
  function toggleSaved(id) {
    const item=state.campaigns.find(x=>String(x.id)===id);
    if(!item)return;
    const key=String(item.id||item.action_url);
    if(saved.has(key))saved.delete(key);else saved.add(key);
    try{localStorage.setItem('greenanchor_saved_v1',JSON.stringify([...saved]));}catch(_){}
    renderLists();
    toast(saved.has(key)?'Azione salvata su questo dispositivo':'Azione rimossa dai salvati');
  }
  function byFilters(items) {
    return items.filter(item=>{
      if(state.scope!=='all' && scopeOf(item)!==state.scope)return false;
      if(state.savedOnly && !isSaved(item))return false;
      if(state.query){
        const hay=[item.title,item.source,item.summary,topicOf(item),scopeLabel(scopeOf(item))].join(' ').toLocaleLowerCase();
        if(!hay.includes(state.query))return false;
      }
      return true;
    });
  }
  function renderLists() {
    const focus=byFilters(state.focus),all=byFilters(state.campaigns);
    $('focusCampaigns').innerHTML=focus.length?focus.map(card).join(''):'<div class="empty-state"><h3>Nessun segnale prioritario</h3><p>Prova un altro filtro o esplora tutte le azioni disponibili.</p></div>';
    $('allCampaigns').innerHTML=all.length?all.map(card).join(''):'<div class="empty-state"><h3>Nessuna azione trovata</h3><p>Modifica la ricerca o i filtri. Le directory generiche non sono conteggiate come campagne.</p></div>';
    const count=$('resultCount');
    if(count)count.textContent=`${all.length} azioni mostrate · ${state.campaigns.length} collegamenti diretti selezionati · elenco non esaustivo`;
    $('bookmarkFilter')?.classList.toggle('active',state.savedOnly);
    $('bookmarkFilter')?.setAttribute('aria-pressed',String(state.savedOnly));
    document.querySelectorAll('#filtersContainer [data-filter]').forEach(b=>{
      const active=b.dataset.filter===state.scope;
      b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));
    });
    document.querySelectorAll('#impactControls [data-view]').forEach(b=>{
      const active=b.dataset.view===(state.scope==='all'?'global':state.scope);
      b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));
    });
  }
  function populateMetrics() {
    const items=state.campaigns, active=items.length, urgent=countUrgent(items), news=countNew(items);
    const src=new Set(items.map(x=>x.source).filter(Boolean)).size;
    const metrics={radarCampaigns:active,radarActive:items.filter(orgSite).length,radarUrgent:urgent,radarNew:news,panelActive:active,panelUrgent:urgent,panelSources:src,panelPulse:news};
    for(const [id,value] of Object.entries(metrics)){if($(id))$(id).textContent=String(value);}
    document.querySelector('.stat-campaigns').textContent=String(active);
    document.querySelector('.stat-active').textContent=String(items.filter(orgSite).length);
    document.querySelector('.stat-urgent').textContent=String(urgent);
    if($('signalTotal'))$('signalTotal').textContent=String(active).padStart(2,'0');
    if($('signalSources'))$('signalSources').textContent=String(src);
    if($('signalSync'))$('signalSync').textContent=dateText(state.generatedAt);
    if($('impactAlert'))$('impactAlert').textContent='Le schede sono selezionate con controlli automatici su URL e tipologia di pagina. Le adesioni e lo stato delle campagne vanno confermati alla fonte originale.';
    if($('syncNotice'))$('syncNotice').textContent='Snapshot dei dati: '+dateText(state.generatedAt)+' · non è un feed in tempo reale.';
    if($('lastUpdate'))$('lastUpdate').textContent='Ultimo aggiornamento dei dati: '+dateText(state.generatedAt);
    const old=state.generatedAt&&validDate(state.generatedAt)&&Date.now()-new Date(state.generatedAt).getTime()>36*3600000;
    const status=$('dataStatus');
    if(status)status.textContent=old?'DATI DA AGGIORNARE':'SNAPSHOT AGGIORNATO';
  }
  function safeMapData() {
    return {campaigns:state.campaigns.map(item=>({
      ...item,
      title:h(item.title),
      summary:h(summaryOf(item)),
      objective:h(item.objective||''),
      action_url:urlOf(item.action_url)?.href||'#'
    }))};
  }
  function toast(message) {
    const el=document.querySelector('[data-toast]');if(!el)return;
    el.textContent=message;el.classList.add('visible');
    clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('visible'),2400);
  }
  function showDetails(id) {
    const item=state.campaigns.find(x=>String(x.id)===id);
    const dlg=$('verificationDialog');if(!item||!dlg)return;
    const u=urlOf(item.action_url);
    const fields=[
      ['Origine dati',item.source||'Non dichiarata'],
      ['Dominio destinazione',u?.hostname||'Non disponibile'],
      ['Tipologia verifica',orgSite(item)?'Dominio di organizzazione nota':'Controllo manuale consigliato'],
      ['Ultima importazione',dateText(state.generatedAt)],
      ['Scadenza',item.deadline?dateText(item.deadline):'Non comunicata'],
      ['Tipo di azione',item.action_type||'Non determinato']
    ];
    $('verificationContent').innerHTML=`<div class="dialog-head"><div><span class="dialog-kicker">GreenAnchor / Verification Layer</span><h2>${h(item.title)}</h2></div>
      <button class="dialog-close" type="button" data-close-dialog aria-label="Chiudi">×</button></div>
      <div class="dialog-fields">${fields.map(([a,b])=>`<div class="dialog-field"><span>${h(a)}</span><strong>${h(b)}</strong></div>`).join('')}</div>
      <p class="dialog-note"><strong>Che cosa significa?</strong> GreenAnchor controlla la struttura del collegamento e distingue le pagine di azione dalle directory. Non verifica in modo indipendente la veridicità, le firme, l'efficacia o lo stato corrente della campagna. Prima di aderire, consulta sempre la pagina originale.</p>
      <div class="dialog-actions"><a class="main-action" href="${h(u?.href||'#')}" target="_blank" rel="noopener noreferrer">Apri pagina originale ↗</a>
      <button type="button" data-copy-url="${h(u?.href||'')}">Copia link</button></div>`;
    if(typeof dlg.showModal==='function')dlg.showModal();else dlg.setAttribute('open','');
  }
  function bindEvents() {
    $('searchInput')?.addEventListener('input',e=>{state.query=String(e.target.value||'').trim().toLocaleLowerCase();renderLists();});
    $('filtersContainer')?.addEventListener('click',e=>{
      const b=e.target.closest('[data-filter]');if(!b)return;
      state.scope=b.dataset.filter;renderLists();
    });
    $('impactControls')?.addEventListener('click',e=>{
      const b=e.target.closest('[data-view]');if(!b)return;
      state.scope=b.dataset.view==='global'?'all':b.dataset.view;renderLists();
      $('focusSectionContainer')?.scrollIntoView({behavior:'smooth',block:'start'});
    });
    $('bookmarkFilter')?.addEventListener('click',()=>{state.savedOnly=!state.savedOnly;renderLists();});
    document.querySelector('main')?.addEventListener('click',e=>{
      const s=e.target.closest('[data-save]');if(s){toggleSaved(s.dataset.save);return;}
      const b=e.target.closest('[data-details]');if(b)showDetails(b.dataset.details);
    });
    $('verificationDialog')?.addEventListener('click',async e=>{
      if(e.target.closest('[data-close-dialog]'))$('verificationDialog').close();
      const copy=e.target.closest('[data-copy-url]');
      if(copy){
        try{await navigator.clipboard.writeText(copy.dataset.copyUrl);toast('Link copiato');}
        catch(_){toast('Apri la fonte originale per copiare il collegamento');}
      }
      if(e.target===$('verificationDialog'))$('verificationDialog').close();
    });
    $('themeToggle')?.addEventListener('click',()=>{
      const isLight=document.body.classList.toggle('light-theme');
      try{localStorage.setItem('greenanchor_theme',isLight?'light':'dark');}catch(_){}
      $('themeToggle').setAttribute('aria-pressed',String(isLight));
    });
  }
  async function initGreenAnchorMission() {
    readSaved();bindEvents();
    try{if(localStorage.getItem('greenanchor_theme')==='light')document.body.classList.add('light-theme');}catch(_){}
    try {
      const response=await fetch('campagne.json',{cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const data=await response.json();
      if(!Array.isArray(data.campaigns))throw new Error('Struttura dati non valida');
      const unique=new Map();
      for(const item of data.campaigns){
        if(!actionable(item))continue;
        const key=urlOf(item.action_url)?.href;
        if(key&&!unique.has(key))unique.set(key,item);
      }
      state.campaigns=[...unique.values()];
      state.focus=selectFocus(state.campaigns);
      state.generatedAt=data.generated_at||data.radar?.generated_at||null;
      populateMetrics();renderLists();
      if(typeof updateGlobalMapDataLayers==='function')updateGlobalMapDataLayers(safeMapData());
    }catch(error){
      console.error('GreenAnchor dataset unavailable:',error);
      for(const id of ['focusCampaigns','allCampaigns']){
        if($(id))$(id).innerHTML='<div class="empty-state"><h3>Dati temporaneamente non disponibili</h3><p>Non vengono mostrati numeri o campagne non verificabili. Riprova più tardi oppure visita le fonti ufficiali elencate in fondo.</p></div>';
      }
      if($('impactAlert'))$('impactAlert').textContent='Impossibile caricare lo snapshot. Nessun dato simulato.';
      if($('dataStatus'))$('dataStatus').textContent='DATI NON DISPONIBILI';
    }
  }
  window.initGreenAnchorMission=initGreenAnchorMission;
})();
