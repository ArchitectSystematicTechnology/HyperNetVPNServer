Running *float*
===

This document collects a number of things to be aware of when running
*float* in production, or generally on machines with real public IP
addresses.

## General system setup

Float only supports targets running a Debian distribution (currently
both Stretch and Buster should be supported). Furthermore, in order to
run Ansible, both the *python* and *python-apt* packages need to be
installed.

Float likes to think it "owns" the machines it's deployed on: it will
assume it can modify the system-level configuration, install packages,
start services, etc.

However, it assumes that certain functionality is present, either
managed manually or with some external mechanism (your own Ansible
roles, for instance):

* Network configuration must be externally managed, except for the
  [network overlays](service_mesh.md#network-overlays) explicitly
  configured in *float*.

* Partitions, file systems, LVs must be externally managed, with the
  exception of the volumes explicitly defined in your configuration,
  which will be created by *float* when necessary. See the [relevant
  configuration reference](configuration.md#volumes).

* SSH access and configuration must be externally managed **unless**
  you explicitly set *enable_ssh=true* (and add SSH keys to your admin
  users), in which case *float* will take over SSH configuration and
  you might need to modify your Ansible SSH configuration after the
  first run. See the [relevant configuration
  reference](configuration.md#ssh).

Float does not use, and does not modify, the hostname of the servers
it manages: it only references the host names used in the
inventory. Things will be less confusing if you ensure that the names
match, but it is not a strict requirement.

## Choosing a domain

Float assumes it has full control of the DNS zone you configure in the
*domain* global configuration variable
([ref.](configuration.md#global-configuration-variables)). It is best to
pick a new sub-domain of a zone you control for this purpose, so that
you can eventually set up a NS record for it and delegate it to the
*float*-managed frontends.

## Disable testing features

Float runs a lot of testing-only features that are useful for
debugging but should be disabled in production, or whenever the target
machines are publicly accessible.

Remember to explicitly set

```yaml
testing: false
```

in your configuration (somewhere in *group_vars/all/* for instance),
to disable all testing-related features.

In test environments (the default, i.e. when *testing* is true), the
following happens:

* a SOCKS proxy will run on a frontend host on port 9051, open to the
  world
* the ACME automation will generate self-signed certificates
* logs will be dumped on the filesystem on *log-collector* nodes, in
  addition to Elasticsearch
* *float* might load test data onto databases and such
