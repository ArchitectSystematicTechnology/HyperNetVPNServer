float
====

*float* is a minimalistic configuration management toolkit to manage
container-based services on bare-metal hardware (a.k.a. *container
orchestration framework*). It is implemented as a series of Ansible
plugins and roles that you should use from your own Ansible
configuration.

Its main purpose is to provide a simple container-oriented
environment, with minimal but complete features, to prepare services
(and developers) for a full migration to something more sophisticated
like Kubernetes.


# Features

Some of these, especially when comparing against full-featured
solutions like Kubernetes, are non-features:

* *static service allocation* - the service scheduler does not move
  containers at runtime in response to host failures, all changes
  happen at "configuration time" when running Ansible.
* *1:1 instance/host mapping* - the scheduler won't run more than one
  instance of a service on each host.
* *manual port assignments* - you must manually pick a unique port for
  your services, there's no automatic allocation.
* *service discovery protocol* - DNS based.
* *PKI management* - all service-to-service communication can be
  encrypted and authenticated using a private PKI.
* *builtin services* - the toolkit provides a number of built-in
  services, such as monitoring, alerting, log collection and analysis,
  thorough audit functionality, private networking. These services are
  automatically configured and managed (though they can be extended).

Some of these "features" were selected in order to massively simplify
the implementation (the scheduler and the service discovery layer are
just a few hundred lines of Python all together), while trying to
minimize cognitive and operational load. We may have failed on both
those accounts.

# Target

It should be clear from the list of "features" above, but this system
isn't meant to provide high availability without some smartness in the
services themselves. Its major limitation is the requirement for
manual operator action in face of high-level environmental changes
(loss of machines, changes in load/demand), so for instance it won't
do much for a singly-homed service on a host that is dead. The system
doesn't perform reactive actions at runtime (it is, in fact,
implemented on top of a configuration management system).

However, it is possible to build reliable services on this
infrastructure with cooperation from the service itself, by making the
service use the available infrastructure primitives. Just with service
discovery, and a relatively robust traffic routing layer, it's
relatively straightforward to build partitioned or replicated
services, where one can arbitrarily tune the threshold for manual
operator intervention.

# Documentation

More detailed documentation is available in the *docs/* subdirectory,
and in README files for individual Ansible roles:

### General Documentation

* [Quick start guide](docs/quickstart.md)
* [Guide to Ansible integration](docs/ansible.md)
* [Notes on running in production](docs/running.md)
* [Configuration reference](docs/configuration.md)
* [Service discovery protocol](docs/service_mesh.md)
* [HTTP router](docs/http_router.md)
* [Docker usage](roles/docker/README.md)
* [Overview of built-in services](docs/builtin_services.md)
* [CLI tool usage](docs/cli.md)
* [Testing](docs/testing.md)

### Built-in services documentation

* [Monitoring and alerting](roles/prometheus/README.md)
* [Log management and analysis](roles/log-collector/README.md)
* [Authoritative public DNS](roles/dns/README.md)
* [Authentication and identity management](docs/identity_management.md)

Built-in services are currently implemented with Ansible roles, and do
not run in containers. But this is just an implementation detail, and
in the future they could be moved to containers without requiring any
changes in the clients.

# Requirements

On the local machine (the one that will run Ansible), you're going to
need [Ansible](https://ansible.com), obviously, and a few small other
custom tools used to manage credentials. These tools should be built
on the local machine using [Go](https://golang.org):

```shell
sudo apt-get install golang bind9utils
go get -u git.autistici.org/ale/x509ca
go get -u git.autistici.org/ale/ed25519gen
export PATH=$PATH:$HOME/go/bin
```

Altough not strictly a requirement, you will probably want to use a
number of external services that are not provided by *float* itself:

* git repository hosting
* CI system to build container images
* a Docker registry
