const state = {
  campaigns: [],
  filtered: [],
  spotlight: [],
  radar: null,
  fuse: null,
  favorites: new Set(JSON.parse(localStorage.getItem('greenanchor-favorites') || '[]')),
  searchScores: new Map()
};

const refs = {
  input: document.getElementById('searchInput'),
  sourceFilter: document.getElementById('sourceFilter'),
  scopeFilter: document.getElementById('scopeFilter'),
  themeFilter: document.getElementById('themeFilter'),
  actionTypeFilter: document.getElementById('actionTypeFilter'),
  sortFilter: document.getElementById('sortFilter'),
  stats: document.getElementById('stats'),
  updatedAt: document.getElementById('updatedAt'),
  results: document.getElementById('results'),
  template: document.getElementById('campaignCardTemplate'),
  spotlight: document.getElementById('spotlight'),
  spotlightTemplate: document.getElementById('spotlightTemplate'),
  radarNew: document.getElementById('radarNew'),
  radarActive: document.getElementById('radarActive'),
  radarUrgent: document.getElementById('radarUrgent'),
  radarClusters: document.getElementById('radarClusters')
};

function parseDate(value) {
  if (!value) {
    return null;
  }
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function fmtDate(value) {
  const dt = parseDate(value);
  if (!dt) {
    return 'n.d.';
  }
  return dt.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' });
}

function enrichCampaign(raw) {
  const campaign = { ...raw };
  campaign.scope = campaign.scope || (campaign.country === 'IT' ? 'Italia' : campaign.country === 'EU' ? 'Europa' : 'Globale');
  campaign.theme = campaign.theme || (campaign.tags && campaign.tags[0]) || 'ambiente';
  campaign.action_type = campaign.action_type || 'petizione';
  campaign.status = campaign.status || 'attiva';
  campaign.last_verified = campaign.last_verified || campaign.last_seen || null;
  campaign.verification_score = Number(campaign.verification_score || 70);
  campaign.verification_status = campaign.verification_status || 'da_verificare';
  campaign.completion_score = Number(campaign.completion_score || campaign.verification_score || 60);
  campaign.objective = campaign.objective || campaign.summary || 'Obiettivo non disponibile.';
  campaign._id = campaign.id || `${campaign.source}:${campaign.action_url}`;
  return campaign;
}

async function loadCampaigns() {
  try {
    const res = await fetch('campagne.json', { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    state.campaigns = (data.campaigns || []).map(enrichCampaign);
    state.spotlight = (data.greenanchor_focus || data.spotlight || []).map(enrichCampaign);
    state.radar = data.radar || null;

    state.fuse = new Fuse(state.campaigns, {
      keys: ['title', 'organization', 'summary', 'objective', 'theme', 'action_type', 'tags'],
      threshold: 0.32,
      includeScore: true
    });

    hydrateSelect(refs.sourceFilter, [...new Set(state.campaigns.map((item) => item.source))].sort());
    hydrateSelect(refs.themeFilter, [...new Set(state.campaigns.map((item) => item.theme))].sort());
    hydrateSelect(refs.actionTypeFilter, [...new Set(state.campaigns.map((item) => item.action_type))].sort());

    renderRadar();
    renderSpotlight();
    updateUpdatedAt(data.generated_at);
    applyFilters();
  } catch (error) {
    refs.stats.textContent = `Errore caricamento dati: ${error.message}`;
  }
}

function hydrateSelect(select, values) {
  values.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function updateUpdatedAt(isoString) {
  if (!isoString) {
    refs.updatedAt.textContent = 'Aggiornamento: data non disponibile';
    return;
  }

  const date = new Date(isoString);
  refs.updatedAt.textContent = `Aggiornato: ${date.toLocaleString('it-IT', { dateStyle: 'medium', timeStyle: 'short' })}`;
}

function renderRadar() {
  refs.radarNew.textContent = state.radar?.new_campaigns_24h ?? '-';
  refs.radarActive.textContent = state.radar?.active_campaigns ?? '-';
  refs.radarUrgent.textContent = state.radar?.urgent_campaigns ?? '-';
  refs.radarClusters.textContent = state.radar?.fragmented_topics ?? '-';
}

function renderSpotlight() {
  refs.spotlight.innerHTML = '';
  state.spotlight.slice(0, 5).forEach((campaign) => {
    const node = refs.spotlightTemplate.content.cloneNode(true);
    const urgentLabel = campaign.deadline ? `URGENTE · ${campaign.scope}` : `${campaign.scope.toUpperCase()} · FOCUS`;
    node.querySelector('[data-spotlight-label]').textContent = urgentLabel;
    node.querySelector('[data-spotlight-title]').textContent = campaign.title;
    const progress = campaign.progress_current && campaign.progress_target
      ? ` · ${campaign.progress_current.toLocaleString('it-IT')}/${campaign.progress_target.toLocaleString('it-IT')}`
      : '';
    node.querySelector('[data-spotlight-meta]').textContent = `${campaign.action_type} · Completion ${campaign.completion_score}/100${progress}`;
    node.querySelector('[data-spotlight-link]').href = campaign.action_url;
    refs.spotlight.appendChild(node);
  });
}

function searchAndRank(query) {
  state.searchScores = new Map();
  if (!query || !state.fuse) {
    return state.campaigns;
  }

  return state.fuse.search(query).map((entry) => {
    state.searchScores.set(entry.item._id, entry.score || 0);
    return entry.item;
  });
}

function deadlineUrgency(campaign) {
  const deadline = parseDate(campaign.deadline);
  if (!deadline) {
    return 999;
  }
  const ms = deadline.getTime() - Date.now();
  if (ms < 0) {
    return 998;
  }
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function applySorting(list) {
  const sortMode = refs.sortFilter.value;
  const sorted = [...list];

  if (sortMode === 'urgency') {
    sorted.sort((a, b) => deadlineUrgency(a) - deadlineUrgency(b));
  } else if (sortMode === 'recent') {
    sorted.sort((a, b) => (parseDate(b.last_verified)?.getTime() || 0) - (parseDate(a.last_verified)?.getTime() || 0));
  } else if (sortMode === 'verification') {
    sorted.sort((a, b) => (b.completion_score || 0) - (a.completion_score || 0));
  } else {
    sorted.sort((a, b) => (state.searchScores.get(a._id) || 1) - (state.searchScores.get(b._id) || 1));
  }

  return sorted;
}

function applyFilters() {
  const query = refs.input.value.trim();
  const source = refs.sourceFilter.value;
  const scope = refs.scopeFilter.value;
  const theme = refs.themeFilter.value;
  const actionType = refs.actionTypeFilter.value;

  let result = searchAndRank(query);

  if (source !== 'all') {
    result = result.filter((item) => item.source === source);
  }
  if (scope !== 'all') {
    result = result.filter((item) => item.scope === scope);
  }
  if (theme !== 'all') {
    result = result.filter((item) => item.theme === theme);
  }
  if (actionType !== 'all') {
    result = result.filter((item) => item.action_type === actionType);
  }

  state.filtered = applySorting(result);
  renderCards();
  refs.stats.textContent = `${state.filtered.length} campagne su ${state.campaigns.length} | Focus Italia/Europa/Globale, verifica e urgenza`;
}

function verificationBadge(campaign) {
  const status = campaign.verification_status;
  if (status === 'verificata') {
    return '🟢 Verificata';
  }
  if (status === 'da_verificare') {
    return '🟡 Da verificare';
  }
  return '⚪ Fonte aggregata';
}

function persistFavorites() {
  localStorage.setItem('greenanchor-favorites', JSON.stringify([...state.favorites]));
}

function toggleFavorite(campaignId, button) {
  if (state.favorites.has(campaignId)) {
    state.favorites.delete(campaignId);
  } else {
    state.favorites.add(campaignId);
  }
  button.textContent = state.favorites.has(campaignId) ? '★' : '☆';
  persistFavorites();
}

function buildMailto(campaign) {
  const subject = encodeURIComponent(`Segnalazione campagna GreenAnchor: ${campaign.title}`);
  const body = encodeURIComponent(`Ciao GreenAnchor,%0D%0Asegnalo questa campagna da verificare o aggiornare:%0D%0A${campaign.action_url}`);
  return `mailto:greenanchor.project@gmail.com?subject=${subject}&body=${body}`;
}

async function shareCampaign(campaign) {
  const payload = {
    title: campaign.title,
    text: `GreenAnchor | ${campaign.organization}`,
    url: campaign.action_url
  };
  if (navigator.share) {
    try {
      await navigator.share(payload);
      return;
    } catch {
      // Fallback to clipboard below.
    }
  }
  await navigator.clipboard.writeText(campaign.action_url);
}

function renderCards() {
  refs.results.innerHTML = '';

  if (state.filtered.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600';
    empty.textContent = 'Nessun risultato: modifica filtri o cerca un altro tema.';
    refs.results.appendChild(empty);
    return;
  }

  state.filtered.forEach((campaign, index) => {
    const node = refs.template.content.cloneNode(true);
    const article = node.querySelector('article');

    node.querySelector('[data-source]').textContent = campaign.source;
    node.querySelector('[data-title]').textContent = campaign.title;
    node.querySelector('[data-organization]').textContent = campaign.organization;
    node.querySelector('[data-location]').textContent = `📍 ${campaign.scope}`;
    node.querySelector('[data-theme]').textContent = `🌿 ${campaign.theme}`;
    node.querySelector('[data-action-type]').textContent = `🎯 ${campaign.action_type}`;
    node.querySelector('[data-status]').textContent = `🟢 ${campaign.status}`;
    node.querySelector('[data-verification]').textContent = `✓ ${verificationBadge(campaign)} · ${campaign.verification_score}/100`;
    const completion = campaign.progress_current && campaign.progress_target
      ? ` · ${campaign.progress_current.toLocaleString('it-IT')}/${campaign.progress_target.toLocaleString('it-IT')}`
      : '';
    node.querySelector('[data-last-verified]').textContent = `📅 Ultima verifica: ${fmtDate(campaign.last_verified)} · Completion ${campaign.completion_score}/100${completion}`;
    node.querySelector('[data-objective]').textContent = campaign.objective;

    const tagsBox = node.querySelector('[data-tags]');
    (campaign.tags || []).slice(0, 5).forEach((tag) => {
      const chip = document.createElement('span');
      chip.className = 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700';
      chip.textContent = tag;
      tagsBox.appendChild(chip);
    });

    const cta = node.querySelector('[data-link]');
    cta.href = campaign.action_url;

    const favoriteBtn = node.querySelector('[data-favorite]');
    favoriteBtn.textContent = state.favorites.has(campaign._id) ? '★' : '☆';
    favoriteBtn.addEventListener('click', () => toggleFavorite(campaign._id, favoriteBtn));

    node.querySelector('[data-share]').addEventListener('click', async () => {
      try {
        await shareCampaign(campaign);
      } catch {
        // Ignore share/clipboard errors.
      }
    });

    node.querySelector('[data-report]').addEventListener('click', () => {
      window.location.href = buildMailto(campaign);
    });

    article.style.animationDelay = `${Math.min(index * 30, 240)}ms`;
    refs.results.appendChild(node);
  });
}

refs.input.addEventListener('input', applyFilters);
refs.sourceFilter.addEventListener('change', applyFilters);
refs.scopeFilter.addEventListener('change', applyFilters);
refs.themeFilter.addEventListener('change', applyFilters);
refs.actionTypeFilter.addEventListener('change', applyFilters);
refs.sortFilter.addEventListener('change', applyFilters);

loadCampaigns();
