const state = {
  campaigns: [],
  filtered: [],
  fuse: null
};

const refs = {
  input: document.getElementById('searchInput'),
  sourceFilter: document.getElementById('sourceFilter'),
  stats: document.getElementById('stats'),
  updatedAt: document.getElementById('updatedAt'),
  results: document.getElementById('results'),
  template: document.getElementById('campaignCardTemplate')
};

async function loadCampaigns() {
  try {
    const res = await fetch('campagne.json', { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    state.campaigns = data.campaigns || [];

    state.fuse = new Fuse(state.campaigns, {
      keys: ['title', 'organization', 'summary', 'tags'],
      threshold: 0.33,
      includeScore: false
    });

    hydrateSourceFilter();
    updateUpdatedAt(data.generated_at);
    applyFilters();
  } catch (error) {
    refs.stats.textContent = `Errore caricamento dati: ${error.message}`;
  }
}

function hydrateSourceFilter() {
  const uniqueSources = [...new Set(state.campaigns.map((item) => item.source))].sort();
  uniqueSources.forEach((source) => {
    const option = document.createElement('option');
    option.value = source;
    option.textContent = source;
    refs.sourceFilter.appendChild(option);
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

function applyFilters() {
  const query = refs.input.value.trim();
  const source = refs.sourceFilter.value;

  let result = state.campaigns;

  if (query && state.fuse) {
    result = state.fuse.search(query).map((entry) => entry.item);
  }

  if (source !== 'all') {
    result = result.filter((item) => item.source === source);
  }

  state.filtered = result;
  renderCards();
  refs.stats.textContent = `${state.filtered.length} campagne trovate su ${state.campaigns.length}`;
}

function renderCards() {
  refs.results.innerHTML = '';

  if (state.filtered.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600';
    empty.textContent = 'Nessun risultato: prova una parola diversa o cambia fonte.';
    refs.results.appendChild(empty);
    return;
  }

  state.filtered.forEach((campaign, index) => {
    const node = refs.template.content.cloneNode(true);

    node.querySelector('[data-source]').textContent = campaign.source;
    node.querySelector('[data-title]').textContent = campaign.title;
    node.querySelector('[data-summary]').textContent = campaign.summary || 'Descrizione non disponibile.';

    const tagsBox = node.querySelector('[data-tags]');
    (campaign.tags || []).slice(0, 4).forEach((tag) => {
      const chip = document.createElement('span');
      chip.className = 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700';
      chip.textContent = tag;
      tagsBox.appendChild(chip);
    });

    const cta = node.querySelector('[data-link]');
    cta.href = campaign.action_url;

    const article = node.querySelector('article');
    article.style.animationDelay = `${Math.min(index * 40, 240)}ms`;

    refs.results.appendChild(node);
  });
}

refs.input.addEventListener('input', applyFilters);
refs.sourceFilter.addEventListener('change', applyFilters);

loadCampaigns();
