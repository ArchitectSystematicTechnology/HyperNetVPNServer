float
====

*float* è un kit di strumenti minimalista per gestire le
configurazioni di gestione di servizi basati su immagini di container,
installati direttamente su macchine fisiche (ovvero è *un sistema di
orchestrazione di container*). É implementato come una serie di plugin
e di ruoli di Ansible che si possono integrare con le proprie
configurazioni Ansible.

L'obiettivo principale è ottenere un ambiente di container facile da
gestire, con un minimo ma indispensabile numero di caratteristiche,
per preparare i servizi (e pure le persone) a una completa migrazione
a qualcosa di più sofisticato, come Kubernetes.

# Funzionalità

Alcune di queste, specialmente se comparate con soluzioni più sofisticate,
come Kubernetes, sono non-funzionalità:

* *allocazione statica dei servizi* - lo scheduler del servizio non
  migra i container a runtime in caso di fallimento di un host, tutti
  i cambiamenti avvengono solo all'atto della "configurazione" ovvero
  quando si fa andare Ansible.
* *mapping 1:1 di istanze e host* - lo scheduler non assegnerà mai più
  di una istanza di un servizio a ciascun host.
* *allocazione manuale delle porte* - devi manualmente scegliere una
  porta unica per ciascuno dei tuoi servizi, non esiste un meccanismo
  di distribuzione ed assegnazione automatica.
* *protocollo di service discovery* - basato su DNS.
* *gestione PKI* - tutte le comunicazioni service-to-service possono
  essere criptate ed autenticate usando una PKI interna.
* *servizi integrati* - il toolkit fornisce un numero di servizi
  integrati, come il monitoring, alerting, la raccolta ed analisi dei
  log, una relativamente completa funzionalità di audit, networking
  privato. Questi servizi sono configurati automaticamente (ma possano
  essere estesi).

Alcune di queste "funzionalità" sono state scelte nell'idea di
semplificare drasticamente l'implementazione (lo scheduler e il
livello di service discovery sono giusto poche centinaia di righe di
Python tutte insieme), cercando contemporaneamente di minimizzare il
carico cognitivo e operativo. Ma potremmo anche non esserci
riusciti...

# Obiettivo

Dovrebbe essere chiaro dalla lista delle "funzionalità" qui sopra:
questo sistema non punta ad offrire *alta disponibilità*, ma ad avere qualche automazione nei servizi stessi. 
La principale limitazione, rispetto asistemi più evoluti, è il requisito di un'operazione manuale in caso
di cambiamenti dell'ambiente ad alto livello (fallimento di macchine,
cambiamenti nella richiesta/offerta): per fare un esempio, se avete
configurato un servizio con un'unica istanza su un server che poi si
rompe, *float* non potrà fare molto per voi, almeno non
automaticamente. Il sistema non compie azioni a runtime, è infatti
implementato sopra ad un sistema di gestione delle configurazioni.

Però, è possible costruire servizi affidabili usando questa
infrastruttura, usando le primitive fornite da *float*. Con la
*service discovery*, e il livello relativamente robusto di routing del
traffico, si possono costruire servizi avanzati, partizionati o
replicati, potendo scegliere come calibrare il livello necessario di
intervento manuale da parte dell'operatore.

# Documentazione

Una documentazione più dettagliata è disponible nella sottocartella
*docs/*, e nei file README per i singoli ruoli Ansible:

### Documentazione generale

* [Guida di partenza rapida](docs/quickstart.it.md)
* [Guida all'integrazione con Ansible](docs/ansible.it.md)
* [Note sull'uso in produzione](docs/running.it.md)
* [Riferimenti per le configurazioni](docs/configuration.it.md)
* [Protocollo Service discovery](docs/service_mesh.it.md)
* [HTTP router](docs/http_router.it.md)
* [Usare Docker](roles/docker/README.it.md)
* [Usare gli strumenti da CLI](docs/cli.it.md)
* [Sperimentazione](docs/testing.it.md)

### Documentazione dei servizi integrati

* [Monitoring and alerting](roles/prometheus/README.it.md)
* [Gestione ed analisi dei Log](roles/log-collector/README.it.md)
* [DNS pubblici e autoritativi](roles/dns/README.it.md)
* [Gestione dell'identità e delle autorizzazioni](docs/identity_management.it.md)

I servizi integrati sono implementati con ruoli Ansible, e non sono
necessariamente eseguiti dentro container. Ma questo è giusto un
dettaglio dell'implementazione, e in futuro è possibile che un numero
maggiore di essi vengano spostati dentro a dei container, senza per
questo richiedere nessun cambiamento lato client.

# Requisiti

Sulla macchina locale (quella su cui fai andare Ansible), serve
[Ansible](https://ansible.com), ovviamente, e alcuni altri piccoli
tool usati per maneggiare le credenziali. Quegli strumenti dovrebbero
essere compilati nella macchina localmente usando
[Go](https://golang.org):

```shell
sudo apt-get install golang bind9utils
go get -u git.autistici.org/ale/x509ca
go get -u git.autistici.org/ale/ed25519gen
export PATH=$PATH:$HOME/go/bin
```

Nonostante non siano dei requisiti obbligatori, probabilmente vorrete
usare alcuni servizi esterni che non sono forniti da *float* stesso:

* git repository hosting
* un sistema di CI (continuos integration) per creare in proprio le immagini dei container
* un registro Docker
