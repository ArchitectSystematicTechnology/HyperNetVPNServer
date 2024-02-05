Guida di partenza rapida
===

In questo documento useremo *float* con delle semplici configurazioni,
e per usarlo con un servizio HTTP basico su una macchina virtuale, usando
Vagrant e Virtualbox.

Useremo come servizio di esempio
[docker/okserver](https://git.autistici.org/ai3/docker/okserver), un
server HTTP davvero semplice, che risponde "OK" a tutte le richieste.

## Passo 1: Dipendenze di installazione necessarie

Avrai bisogno di una versione di ansible aggiornata
[Ansible](https://ansible.com) (>= 2.7), gli strumenti di gestione
delle virtual machine (Vagrant and Virtualbox), ed altri piccoli
strumenti personalizzati per gestire le credenziali, che ci andremo a
costruire.

Inoltre, se il tuo sistema operativo usa una differente versione di
Python rispetto a quella che usa Ansible, come nel caso di Debian
Buster (Python 2.7 è di default ma Ansible usa Python 3), ti toccherà
installare alcuni pacchetti Python che dovrebbero essere normalmente
già installati cone Ansible, come Jinja2 e PyYAML.

L'ultima versione di Debian stable al momento (*bus
git@git.autistici.org:ai3/float.gitter*) non pacchettizza più
Virtualbox, quindi dovrai [scaricarlo e installarlo a
mano](https://www.virtualbox.org/wiki/Linux_Downloads). Il resto delle
dipendenze possono essere installate con questo comando:

```shell
sudo apt install golang ansible vagrant
go install git.autistici.org/ale/x509ca@latest
go install git.autistici.org/ale/ed25519gen@latest
export PATH=$PATH:$HOME/go/bin
```

*Float* dovrebbe lavorare ugualmente bene sia con Python 2 che con
Python 3, e supportare lo scenario in cui l'interprete Python usato da
Ansible è differente da quello che il sistema operativo usa di
default.

### Alternativa: libvirt

Se davvero non ti piace Virtualbox e non vuoi installarlo manualmente,
c'è l'opzione di utilizzare al suo posto *libvirt*. In Debian,
installa i seguenti pacchetti per configurare un ambiente locale per
libvirt:

```shell
sudo apt install libvirt-clients libvirt-daemon-system vagrant-libvirt
```

Nel resto di questo documento indicheremo con la tag *\[libvirt\]*
qualora vi fossero dei passaggi specifici per un ambiente libvirt.

## Passo 2: Configurare un nuovo ambiente

Un *ambiente* è soltanto un nome per una specifica configurazione di
hosts e servizi: per convenienza, poichè è fatto da un consistente
numero di file di configurazione, lo andremo a mettere in una cartella
dedicata, che porta il suo nome.

Assumiamo di aver scaricato il codice di *float* in `$HOME/float`, e
di voler creare le configurazioni per fare andare il nostro ambiente
di test nella cartella `$HOME/float-test`. Possiamo creare le
configurazioni del nostro ambiente di test usando il comando `float`
dal teminale (CLI):

```shell
$HOME/float/float create-env \
    --domain=example.com --net=192.168.10.0 \
    --vagrant --num-hosts=1 \
    $HOME/float-test
```

> \[libvirt\] Aggiunti nella riga di comando l'opzione 
> *--libvirt=localhost* 
> nell'invocazione del comando sopra "float create-env".

Il comando *create-env* creerà un gruppo di file di configurazioni
nella cartella *float-test*. Qui noi gli abbiam detto di usare
*example.com* come dominio di base per i nostri servizi pubblici e
interni, e per generare una configurazione host basata su Vagrant di
una singola VM, usando il network privato 192.168.10.0/24 (usato dalle
VMs per parlare una con l'altra). La configurazione di Vagrant
assegnerà automaticamente degli IP da questo network alle VM,
iniziando dal numero 10, quindi la tua VM di test avrà l'indirizzo
192.168.10.10.

La cartella *float-test* dovrebbe ora contenere vari file di
configurazione per Ansible e Vagrant, riempiti con valori di default
da *create-env*. Andiamo a dare una occhiata più da vicino che cosa
sono:

* `ansible.cfg` è il file di configurazione di Ansible, che dice ad Ansible
 dove trovare il plugin float
* `Vagrantfile` è il file di configurazione di Vagrant che descrive la
  nostra singola VM (SO, ip, memory,...).
* `config.yml` è il principale file di configurazione di *float* che
  ha lo scopo principale di puntare agli altri file di
  configurazione. Non c'è niente da cambiare qui, *create-env* ha già
  scritto dei default ragionevoli.
* `hosts.yml` è il file di inventario di Ansible (in formato YAML come
  richiesto da *float*), che già contiene le nostre VM di test.
* `passwords.yml` descrive le credenziali dell'applicazione per i
  ruoli di Ansible. Il nostro server di prova non ha bisogno di
  particolari credenziali, quindi puoi lasciarlo intonso.
* `services.yml` contiene la descrizione dei servizi che vogliamo far
  andare (nessuno per il momento).
* `site.yml` è il nostro playbook di Ansible principale.
* `group_vars/all/config.yml` contine le configurazini globali di Ansible,
  incluse le credentiali per gli utenti amministrativi (operators):
  *create-env* automaticamente genera di default un utente "admin", con
  password "password".

Si può leggere [Riferimenti per le
configurazioni](configuration.it.md) per la sintassi dei file di
configurazione e cosa significano le varie opzioni.

Questa cartella è anche la tua cartella top-level di Ansible, così è
possibile aggiungere host_vars, group_vars, etc. come vuoi. Noi non
andiamo a vedere e non ci servono quelle funzionalità per questo
esempio.

## Passo 3: Personalizzare l'ambiente

Vogliamo dire a *float* di far andare una istanza del nostro semplice
servizio HTTP dietro al suo router HTTP pubblico, ed averla
disponibile pubblicamente come *ok.example.com*. Il servizio è
disponibile come immagine Docker, con il nome
*registry.git.autistici.org/ai3/docker/okserver*.

Andiamo ad aggiungere il servizio specifico al file *services.yml* che
è stato automaticamente creato dentro alla cartella *float-test*. Dato
che tutti i servizi in float hanno le porte assegnate staticamente,
scegliamo arbitrariamente la porta 3100 (che sappiamo essere
libera). Il file *services.yml* già contiene una sezione "include" che
include la definizione per tutti i servizi integrati, quindi abbiamo
bisogno di aggiungere solo un pezzettino alla fine del file YAML:

```yaml
ok:
  scheduling_group: all
  num_instances: 1
  containers:
    - name: http
      image: registry.git.autistici.org/ai3/docker/okserver:master
      port: 3100
      env:
        PORT: 3100
  public_endpoints:
    - name: ok
      port: 3100
      scheme: http
```

Queste sono tutte le configurazioni di cui abbiamo bisogno per
impostare il servizio ed esportarlo tramite il router HTTP pubblico.

## Passo 4: Inizializzare le credenziali

Ora che le configurazioni sono pronte, bisogna inizializzare le
credenziali a lungo termine come il PKI e la chiave di root dell'SSO,
nonché le password dell'applicazione. Questo è uno step separato (che
usa un playbook Ansible dedicato), in quanto le credenziali a lungo
temine possono essere generate una volta e poi conservate per
sempre. Questa separazione non è molto importante ora dato che stiamo
lavorando in un ambiente di test, ma è utile per unificare i
rispettivi workflow di test e di produzione. Per la stessa ragione,
anche se non è strettamente necessario, useremo Ansible Vault per
cifrare le credenziali autogenerate.

Come prima cosa, salviamo la passphrase di Ansible Vault in
un file:

```shell
cd $HOME/float-test
echo -n passphrase > .ansible_vault_pw
export ANSIBLE_VAULT_PASSWORD_FILE=$PWD/.ansible_vault_pw
```

La passphrase può essere qualsiasi (preferibilmente non "passphrase"
come nell'esempio qui sopra). La variabile di ambiente
*ANSIBLE_VAULT_PASSWORD_FILE* serve per dire ad Ansible quale
passphrase deve usare, e bisognerà impostarla tutte le volte che
vogliamo invocare Ansible, tramite *float* o meno.

Fatto questo, possiamo inizializzare le credenziali, che di default
saranno archiviate dentro la cartella *float-test/credentials/* (il
valore indicato in *credentials_dir* in *config.yml*):

```shell
cd $HOME/float-test
$HOME/float/float run init-credentials
```

Float cerca la sua configurazione in *config.yml* nella directory
corrente di default, quindi non c'è bisogno di passare l'opzione
*--config=*.

Il comando qui sopra avrà come risultato la creazione di un numero di
file dentro a *float-test/credentials/*, con i segreti cifrati con la
tua passphrase di Ansible Vault.

## Passo 5: Far partire Ansible

Ora siam pronti a tirare su la VM di test e fa andare Ansible su di
essa per configurare i nostri servizi:

```shell
cd $HOME/float-test
vagrant up
$HOME/float/float run site.yml
```

> \[libvirt\] dovresti mettere l'opzione *--provider=libvirt* al comando
> "vagrant up".

Quando Ansible termina con successo (e ci metterà qualche minuto la
prima volta, per scaricare i pacchetti e l'immagine Docker), la
macchina virtuale di test è propriamente configurata per servirci il
nostro servizio *ok.example.com*!

## Passo 6: Verificare che funzioni

Il servizio ok.example.com dovrebbe essere servito dal router HTTP
pubblico al nostro IP pubblico del nostro host di test, che Vagrant ha
impostato come default che è 192.168.10.10:

```shell
curl -k --resolve ok.example.com:443:192.168.10.10 https://ok.example.com
```

Se il comando risponde "OK", il servizio funziona a dovere. Se invece
ci sono problemi, bisognerà debuggare cosa è andato storto! Ci sono un
buon numero di strumenti che potresti usare per farlo:

Nell'ambiente di test, abbiamo impostato un SOCKS5 proxy sulla porta
9051 nel primo host del gruppo di *frontend* (quindi in questo caso,
comunque 192.168.10.10). Questo è molto utile per simulare se la
risoluzione dei DNS è appropriata e per navigare i servizi integrati
senza complessi cambi all'ambiente dei tuoi host, puoi per esempio far
partire un browser con:

```shell
chromium --proxy-server=socks5://192.168.10.10:9051
```

Una alternativa può essere aggiungere tutti i servizi integrati al tuo
file */etc/hosts*, puntando a 192.168.10.10.

Utili servizi integrati per debugging:

* https://logs.example.com/ punta alla Kibana UI per il servizio di collettore di log centralizzato
* https://grafana.example.com/ è un pannello di monitoring
* https://monitor.example.com/ è l'interfaccia grafica minimale del sistema di monitoring di Prometheus

Ovviamente puoi anche loggarti nella macchina virtuale stessa
(*vagrant ssh host1*) ed esaminare lo stato delle cose da
là. Nell'ambiente di test, syslog logs sono copiati nel file
*/var/log/remote/*, che a volte potrebbe essere più semplice da vedere
che la UI di Kibana.

Una volta completati i test, non dimenticarsi di fermare le virtual
machines lanciando (sempre dalla directory dell'ambiente di test):

```shell
vagrant destroy -f
```

Per controllare l'esecuzione delle VM, ad esempio per sospendere le VM in
mancanza di memoria i comandi sono questi:

```shell
vagrant suspend
vagrant resume
```

# Prossimi passi

Vai a leggere  [Note sull'uso in produzione](running.it.md),
e i [Riferimenti per le configurazioni](docs/configuration.it.md)!

# Appendice: ma è così lento!

Si, Ansible è generalmente abbastanza lento a fare le cose, per un
numero di ragioni (tra queste i lfatto che creiamo un gran numero di
task magari dato dalla possibilità che non usiamo in modo ottimale i
loop). Ma ci sono un po di cose che è possibile fare che aiutono un
poco:

1. Installa
   [Mitogen](https://mitogen.networkgenomics.com/ansible_detailed.html),
   che nel nostro caso rende Ansible circa 5-10 più veloce. Per
   attivarlo, bisogna solo modificare le tue configurazioni nel file
   *ansible.cfg* come è mostrato nella documentazione di Mitogen docs,
   o semplicemente fa *--mitogen=PATH* nella linea di comandocome
   opzione dopo l'invocazione di *float create-env*.
2. Imposta una APT cache (per esempio con *apt-cacher-ng*). Imposta la
   variabile Ansible *apt_proxy* con host:port della cache. Quando usi
   Vagrant come nell'esempio fatto sopra, tieni in considerazione che
   il tuo host è sempre raggiungibile dalla VMs come IP .1 IP nel
   network privato (quindi dovrebbe essere 192.168.10.1 nell'esempio).

Inoltre, la prima volta che lanci *float*, ci saranno da scaricare un
sacco di pacchetti Debian ed immagini Docker, che sfortunatamente sono
piuttosto grosse.
