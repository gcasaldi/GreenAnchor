# GreenAnchor

Aggregatore 100% gratuito di campagne ambientali in stile Change, distribuito su GitHub Pages.

## Architettura Tecnica

- Frontend: pagina statica `index.html` + `app.js` + Tailwind CSS da CDN.
- Database: file locale `campagne.json` versionato nel repository.
- Aggiornamento dati: script Python `scripts/update_campaigns.py` eseguito ogni notte via GitHub Actions.
- Motore di ricerca: Fuse.js client-side, senza server e senza backend.

## Fonti Mappate

- Iniziativa dei Cittadini Europei (ICE)
- Avaaz (Ambiente)
- Greenpeace (Act)
- WWF (Act)
- Change.org
- openPetition

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
