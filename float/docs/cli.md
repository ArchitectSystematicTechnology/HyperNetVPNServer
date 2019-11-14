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

* support for GPG encryption of the Ansible Vault passphrase file:
  when the `ANSIBLE_VAULT_PASSWORD_FILE` environment variable points
  at a file with a *.gpg* extension, *float run* will reset the
  variable to point at the
  [get-vault-password](../scripts/get-vault-password) script and set
  another environment variable (FLOAT_VAULT_PASSWORD_FILE) to point at
  the original file.

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

Some *ansible-playbook* options are supported, though not many,
including *--diff*, *--check*, and *--verbose*.

## `init-credentials`

The *init-credentials* command is just a shorthand notation for *run
init-credentials*, which invokes the Ansible playbook
[init-credentials.yml](../playbooks/init-credentials.yml) to
initialize the long-term credentials associated with a float
environment.
