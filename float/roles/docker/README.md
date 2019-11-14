docker
===

This role manages all container-based services. It only needs to run
once per host. It will simply start the containers assigned to this
host (via systemd service wrappers), and stop the ones that aren't.

## Systemd integration

Docker containers are exposed to the system as systemd services,
using
[systemd-docker](https://github.com/ibuildthecloud/systemd-docker)
(used to move the docker cgroups under systemd). The systemd unit for
a container named *bar* part of service *foo* will be called
*docker-foo-bar.service*.

Images are pulled only on Ansible runs, so that the same mechanism is
used to push new binaries and new configurations.

## Monitoring

In addition to the standard metrics for the systemd service, we export
a number of container-related metrics via the host-level
exporter
[cgroups-exporter](https://git.autistici.org/ale/cgroups-exporter).

## Third-party package repositories

The *docker-ce* package is taken from the Docker public package
repository, instead of the version that ships with Debian itself.
