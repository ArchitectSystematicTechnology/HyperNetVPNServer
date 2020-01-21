The *float* command-line tool
===

While it is perfectly possible to use *float* just as an Ansible
"library", using your normal Ansible workflow and running
*ansible-playbook*, we provide a simple command-line wrapper for
convenience. This wrapper is also called *float*, and you can find it
in the root directory of this repository. The tool also contains some
useful functionality for generating configuration templates for your
environments.

Since it is basically a wrapper for *ansible-playbook*, it only
requires Python and Ansible to be installed and introduces no
additional dependencies.

The *float* tool has a command-based syntax. The known commands are:

## `create-env`

The *create-env* command generates a configuration template for a new
*float* environment. You must pass it the path to a (new) directory
where the configuration files will be written. Command-line flags
control some details of the generated configuration:

* *--domain* defines the base domain for the environment. The default
  is *example.com*. The internal domain used for service discovery is
  derived from this value by prepending the *infra* component.

* *--vagrant* is a boolean flag that tells float to generate a
  Vagrantfile and an inventory file with a number of VMs controlled by
  the *--num-hosts* flag (by default 3).

* *--mitogen* is an optional flag that should point at a directory
  containing the [Mitogen](https://mitogen.readthedocs.io/) source
  repository. When this flag is specified, the generated *ansible.cfg*
  will include the Mitogen plugin, and it will specify the
  *mitogen_linear* strategy. We've found Mitogen to dramatically
  increase Ansible performance and we use it often, so this option
  saves from further editing of the *ansible.cfg* file.

There are many other options used to control specific parameters of
the generated Vagrant configuration (including support for *libvirt*
and other features), check out "float create-env --help" for more
details.

## `run`

The *run* command executes a playbook, and it's basically a wrapper to
*ansible-playbook* that simplifies setting up the environment
variables required for the *float* plugins to work. In practical
terms, this means:

* auto-location of built-in playbooks: if the playbook path passed to
  *float run* does not exist, the tool will look for it in the
  [playbooks](../playbooks) directory of the float source repository,
  possibly adding the *.yml* extension if missing. This makes it
  possible to, for instance, invoke the
  [docker](../playbooks/docker.yml) built-in playbook simply by
  running:

```shell
/path/to/float/float run docker
```

The *run* command will read the float configuration from the
*config.yml* file in the current directory by default. You can use the
*--config* command-line flag to point it at a different configuration
file.

Some *ansible-playbook* options are supported, though not all of them,
including *--diff*, *--check*, and *--verbose*.

The above command is pretty much equivalent to:

```shell
ansible-playbook -i config.yml playbooks/docker.yml
```

so it is possible that, as functionality is removed from the wrapper,
the *run* command might eventually disappear.

### Built-in playbooks

You can invoke any valid Ansible playbook with "float run", but there
are specific playbooks bundled with *float* that are meant to perform
specific tasks:

* `init-credentials.yml` initializes the long-term credentials
  associated with a float environment. Must be run first thing before
  any other float playbooks can run.

* `apt-upgrade.yml` upgrades all packages and removes unused ones.
