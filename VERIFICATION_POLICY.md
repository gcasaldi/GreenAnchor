# GreenAnchor — protocollo di selezione delle azioni (v2)

GreenAnchor **non crea petizioni, non raccoglie firme e non certifica il risultato** di alcuna campagna. L'obiettivo è aiutare le persone a trovare azioni ambientali già esistenti, mostrando la provenienza di ogni collegamento.

## Come vengono selezionate le schede

1. Un processo automatico raccoglie link da siti di organizzazioni e piattaforme pubbliche.
2. Un filtro limita le schede a indirizzi HTTPS con una struttura compatibile con una **singola azione**; vengono escluse directory, homepage, blog, notizie e pagine generiche.
3. Per piattaforme aperte a tutti (es. openPetition e Change.org) è richiesto anche un riferimento ambientale nel titolo. Non è un'analisi semantica esaustiva.
4. I link duplicati sono eliminati; il dataset e la data di generazione sono conservati in `campagne.json`.
5. L'interfaccia riporta fonte, dominio e timestamp dello snapshot e offre una scheda "Verifica scheda" con i limiti dei controlli.
6. L'utente partecipa **solo sul sito originale**, dopo avere controllato lì destinatari, condizioni e stato.

## Che cosa NON viene verificato

- L'identità reale o l'affidabilità degli autori di una petizione su piattaforma aperta.
- L'attualità di una campagna, la presenza di firme reali, le adesioni o l'effettiva scadenza.
- L'accuratezza delle affermazioni, la legittimità del progetto e l'impatto ambientale misurato.
- Il fatto che ogni pagina sia accessibile in ogni Paese o che accetti ancora adesioni.

La dicitura **"Sito organizzazione"** indica soltanto che il dataset associa la scheda a una fonte organizzativa e che l'URL appartiene a un dominio previsto. **Non** significa "campagna verificata" o "campagna consigliata".

La mappa è esplorativa: mostra punti rappresentativi di organizzazioni e dati raggruppati per area, **non** la posizione fisica esatta delle azioni. L'etichetta "snapshot" indica un aggiornamento periodico del dataset: **non** si tratta di monitoraggio in tempo reale.

## Trasparenza e privacy

Il sito è statico, senza registrazione utente o raccolta diretta di firme. L'elenco "salvate" e la preferenza di tema sono memorizzati nel browser tramite `localStorage`, quando disponibile. Il sito carica librerie, font e tasselli mappa da fornitori esterni: visitando la pagina si possono effettuare richieste di rete verso tali servizi. Aprire una campagna porta a un dominio terzo con proprie regole e informative.

## Manutenzione e limiti del catalogo

Il filtro è intenzionalmente conservativo: alcune iniziative valide possono non apparire. Se il processo di aggiornamento non trova azioni ammissibili, GreenAnchor deve mostrare **zero azioni**, non riempire la pagina con link generici presentati come campagne. Il catalogo non è esaustivo e non contiene un punteggio di impatto scientificamente validato.

Codice e dati: [gcasaldi/GreenAnchor](https://github.com/gcasaldi/GreenAnchor). Le segnalazioni di errori sono benvenute tramite GitHub Issues.
