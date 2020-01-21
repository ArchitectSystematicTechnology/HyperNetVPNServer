Testing
===

This repository contains some integration tests that use Vagrant to
spin up virtual machines and run Ansible against them. The virtual
machines will be destroyed and re-created every time the tests run, so
it would be a good idea to use a local caching proxy for Debian
packages (such as *apt-cacher-ng*).

## Networking

The virtual machines used in tests make use of a randomly determined
/24 network (so we can run multiple overlapping tests in the same
host). To pick a specific network you can use the *--network* option
to *run-test.sh*. On this network, the local (host) machine will have
the address "x.x.x.1".

## Running tests

To run a test, go to the *test* subdirectory of this repository, and
run the *run-test.sh* command, with the name of the test
environment. Right now only two such test environments are defined,
*base* (including just the *frontend* role and a sample HTTP server),
and *full* (including all builtin services) (replace x.x.x with the
test network):

```shell
cd test
./run-test.sh --apt-proxy x.x.x.1:3142 base
```

These tests will set up a very simple Vagrant environment, turn up
services using Ansible, and verify their functionality using the
built-in integration test suite (see below).

The test environment created by the *run-test.sh* script will be
automatically removed when the script terminates, unless the *--keep*
option is specified.

## Integration tests

Float comes with a suite of integration tests, meant to be run on a
live environment (test or otherwise). These tests can be run from your
Ansible directory using the *float* command-line tool:

```shell
/path/to/float/float run integration-test
```

The test suite requires a small amount of configuration in order to
run on a non-test environment, as it needs admin credentials in order
to automatically test SSO-protected services. This is stored in a YAML
file, you can point the test suite at your own test parameters using
the `TEST_PARAMS` environment variable, e.g.:

```shell
env TEST_PARAMS=my-params.yml /path/to/float/float run integration-test
```

The built-in test parameters configuration uses the credentials for
the default admin user used in test environments (*admin*/*password*):

```yaml
---
priv_user:
  name: admin
  password: password
```

The integration test suite runs the following checks:

* check that public endpoints for built-in services are reachable
* check that no Prometheus alerts are firing

More tests will be added.
