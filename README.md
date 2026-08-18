# GreenAnchor

Aggregatore 100% gratuito di campagne ambientali in stile Change, distribuito su GitHub Pages.

GreenAnchor - Campaign Consolidation & Completion Engine.

Non creare un'altra campagna. Portiamone una a termine.

GreenAnchor e un hub indipendente: non crea ne gestisce campagne, ma organizza dati pubblici e rimanda sempre alla fonte originale per partecipare.

## Architettura Tecnica

- Frontend: pagina statica `index.html` + `app.js` + Tailwind CSS da CDN.
- Database: file locale `campagne.json` versionato nel repository.
- Aggiornamento dati: script Python `scripts/update_campaigns.py` eseguito ogni notte via GitHub Actions.
- Motore di ricerca: Fuse.js client-side, senza server e senza backend.

## Evoluzione Prodotto

- GreenAnchor Radar: nuove campagne nelle ultime 24 ore, conteggio attive e urgenti.
- GreenAnchor Focus: top 5 campagne ordinate per completion score, urgenza e concentrazione community.
- Verifica tecnica: score di affidabilita (0-100) e stato `verificata`, `da_verificare`, `fonte_aggregata`.
- Progresso deterministico: percentuale calcolata solo quando la fonte pubblica numeri verificabili.
- Deduplicazione: URL canonico + titolo normalizzato.
- Clustering semantico: individua campagne simili anche su fonti e lingue diverse.
- Filtri avanzati: area (Italia/Europa/Globale), tema, tipo azione, ordinamento per urgenza/recenza/verifica.

## Metriche Deterministiche Di Progresso

- Petizioni: `firme raccolte / target firme`.
- Raccolta fondi: `euro raccolti / target euro`.
- Crowdfunding: `percentuale finanziata` oppure `euro raccolti / target` quando disponibili.
- Raccolta adesioni: `adesioni / target`.
- Eventi o mobilitazioni senza target numerico: nessun punteggio di progresso.

L'AI e usata per classificazione/estrazione; il calcolo finale del progresso e deterministico e spiegabile.

## Architettura Concettuale

Sources -> Data Extraction -> Cleaning -> AI Classification -> Semantic Clustering -> Verification -> Completion Score -> GreenAnchor Focus -> Original Campaign

## Fonti Mappate

- Greenpeace Italia (Attivati)
- WWF Italia
- Legambiente
- Marevivo
- Change.org Italia
- Iniziativa dei Cittadini Europei (ICE)
- Avaaz (Ambiente)
- Greenpeace (Act)
- WWF (Act)
- Change.org
- openPetition

Le fonti italiane sono prioritarie, con estensione a fonti europee e globali per aumentare l'impatto.

## Deploy su GitHub Pages

1. Vai su GitHub -> Settings -> Pages.
2. Source: GitHub Actions.
3. Esegui una push su `main` oppure avvia manualmente il workflow `Deploy GitHub Pages`.
4. Attendi il completamento del job e apri l'URL pubblico.

## Aggiornamento Manuale Dati

```bash
python -m pip install -r scripts/requirements.txt
python scripts/update_campaigns.py
```

## Note

- Lo scraping usa regole conservative su link testuali e potrebbe variare in base ai cambiamenti HTML delle fonti.
- Se nessuna sorgente produce risultati, lo script inserisce un set di fallback per garantire continuita del servizio.
