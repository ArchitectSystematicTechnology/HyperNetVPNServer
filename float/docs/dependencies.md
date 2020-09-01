Dependencies
===

The *float* infrastructure uses a bunch of software that in most cases
is distributed as Debian packages. In case of emergency it is possible
to build all of this software yourself (using a standard Debian
stretch build host), and distribute it with alternative methods.

### Debian packages

These can normally be built with standard Debian development tools,
such as *dpkg-buildpackage*.

* [ai/sso](https://git.autistici.org/ai/sso)
* [id/auth](https://git.autistici.org/id/auth)
* [id/go-sso](https://git.autistici.org/id/go-sso)
* [id/keystore](https://git.autistici.org/id/keystore)
* [id/usermetadb](https://git.autistici.org/id/usermetadb)

* [ale/zonetool](https://git.autistici.org/ale/zonetool)
* [ai3/tools/cgroups-exporter](https://git.autistici.org/ai3/tools/cgroups-exporter)
* [ai3/tools/runcron](https://git.autistici.org/ai3/tools/runcron)
* [ai3/tools/audisp-json](https://git.autistici.org/ai3/tools/audisp-json)
* [ai3/tools/firewall](https://git.autistici.org/ai3/tools/firewall)
* [ai3/tools/float-debug-proxy](https://git.autistici.org/ai3/tools/float-debug-proxy)
* [ai3/tools/acmeserver](https://git.autistici.org/ai3/tools/acmeserver)
* [ai3/tools/replds](https://git.autistici.org/ai3/tools/replds)
* [ai3/tools/tabacco](https://git.autistici.org/ai3/tools/tabacco)

* [ai3/thirdparty/rsyslog-exporter](https://git.autistici.org/ai3/thirdparty/rsyslog-exporter)
* [ai3/thirdparty/restic](https://git.autistici.org/ai3/thirdparty/restic)

These are distributed via our own package repository at
*deb.autistici.org*, which currently supports the *amd64* and *arm64*
binary architectures.

### Docker images

For Docker images it's just a *docker build*.

* [ai3/tools/float-dashboard](https://git.autistici.org/ai3/tools/float-dashboard)
* [ai3/docker/elasticsearch](https://git.autistici.org/ai3/docker/elasticsearch)
* [ai3/docker/kibana](https://git.autistici.org/ai3/docker/kibana)
* [ai3/docker/grafana](https://git.autistici.org/ai3/docker/grafana)
* [ai3/docker/memcached](https://git.autistici.org/ai3/docker/memcached)
