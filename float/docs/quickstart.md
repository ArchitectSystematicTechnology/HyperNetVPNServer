Quick start guide
===

In this document we will set up a very simple *float* configuration,
and use it to run a trivial HTTP service on a virtual machine, using
Vagrant and Virtualbox.

We are going to use
[docker/okserver](https://git.autistici.org/ai3/docker/okserver), a
very simple HTTP server that replies "OK" to all requests, as our
example service.

## Step 1: Install required dependencies

You're going to need a relatively recent version of
[Ansible](https://ansible.com) (>= 2.7), the virtual machine
management tools (Vagrant and Virtualbox), and a few small other
custom tools used to manage credentials, that we will build ourselves.

Furthermore, if your system uses a different Python version than the
one it uses to run Ansible, as in the case of Debian Buster (Python
2.7 is the default but Ansible uses Python 3), you'll need to install
some Python packages that would normally be installed along with
Ansible such as Jinja2 and PyYAML.

*NOTE*: the Ansible version packaged with Debian buster (2.7.7) needs
a patch if your service configuration includes MySQL instances, see
the `ansible-buster.patch` file in the top-level directory for
instructions.

The latest Debian stable as of this writing (*buster*) no longer
packages Virtualbox, so you're going to have to [download and install
it manually](https://www.virtualbox.org/wiki/Linux_Downloads). The
other dependencies can be installed with the following commands:

```shell
sudo apt install golang ansible vagrant
go get -u git.autistici.org/ale/x509ca
go get -u git.autistici.org/ale/ed25519gen
export PATH=$PATH:$HOME/go/bin
```

*Float* should work equally well with both Python 2 and Python 3, and
it supports scenarios where the Python interpreter used by Ansible is
different from the system's default.

### Alternative: libvirt

If you don't like Virtualbox and don't want to install it manually,
you could use *libvirt* instead. On Debian, install the following
packages to set up a local libvirt environment that will work with
Vagrant:

```shell
sudo apt install libvirt-clients libvirt-daemon-system vagrant-libvirt
```

## Step 2: Set up a new environment

An *environment* is just a name for a specific configuration of hosts
and services: for convenience, since it consists of a number of
different configuration files, we're going to store it in its own
directory.

Let's assume you have downloaded the *float* sources in `$HOME/float`,
and that we want to create the configuration to run our test
environment in the directory `$HOME/float-test`. We can create our
test environment configs using the `float` command-line tool:

```shell
$HOME/float/float create-env \
    --domain=example.com --net=192.168.10.0 \
    --num-hosts=1 \
    $HOME/float-test
```

The *create-env* command will create a bunch of configuration files in
the *float-test* directory. Here we told it to use *example.com* as
the base domain name for our public and internal services, and to
generate a Vagrant-based host configuration consisting of a single VM,
using the private network 192.168.10.0/24 (used for VMs to talk to
each other). The *create-env* Vagrant automation will assign IPs on
that network to VMs, starting at number 10, so our test VM will have
the address 192.168.10.10.

The *float-test* directory should now contain various configuration
files for Ansible and Vagrant, with default values filled in by
*create-env*. Let's look more closely at what they are:

* `ansible.cfg` is the Ansible configuration file, which tells Ansible
  where to find the float plugins
* `Vagrantfile` is the Vagrant configuration file describing our
  single VM (base image, ip, memory,...).
* `config.yml` is the main *float* configuration file, which mostly
  just points at the location of the other configs. There is nothing
  to change here, as *create-env* already wrote sensible defaults.
* `hosts.yml` is the Ansible inventory file (in the YAML format
  required by *float*), and it already contains our test VM.
* `passwords.yml` describes application credentials for Ansible roles,
  but we aren't using those so you can leave it untouched.
* `services.yml` contains the description of the service we want to
  run (none for now).
* `site.yml` is our top-level Ansible playbook.
* `group_vars/all/config.yml` contains global Ansible configuration,
  including the credentials for administrative users (operators):
  *create-env* automatically generates a default *admin* user, with
  password *password*.

You can read the [configuration reference](configuration.md) for
details on the configuration file syntax and what the various options
mean.

## Step 3: Customize the environment

We want to tell *float* to run an instance of our simple HTTP service
behind its public HTTP router, and to make it available as
*ok.example.com*. The service is available as a Docker image with the
name *registry.git.autistici.org/ai3/docker/okserver*.

Now, what *float create-env* generated isn't enough for a functional
environment, you need to create some more files manually, to describe
the services you want to run:

* `passwords.yml`, which contains the list of secrets that float will
  automatically generate for us. Since our service does not require
  any additional secrets, we can just tell it to include float's
  default *passwords.yml* file, which describes secrets for the
  built-in default services:

```yaml
---

- include: "../float/passwords.yml.default"
```

* `services.yml` describes the services to run. In our case, we're
  going to run a container with our image, and since all float
  services need statically assigned ports, let's pick port 3100 (which
  we know is available). We also need to include the default float
  services:

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

* `site.yml` is the Ansible playbook, and it is where you would
  establish the association between float services (and their
  auto-generated Ansible groups) and Ansible roles. Since the okserver
  does not require any configuration, beyond the PORT environment
  variable, we're not going to need to write an Ansible role for it,
  and this file can just include the default float playbook (which you
  should always do):

```yaml
---

- import_playbook: "../float/playbooks/all.yml"
```

The environment directory is also your Ansible top-level directory, so
it is possible to add host_vars, group_vars, etc. as you see fit. We
are not going to need those features in this example.

The above is all the configuration we need in order to set up the
okserver service and export it via the public HTTP router.

## Step 4: Initialize the credentials

Now that the configuration is ready, we need to initialize the
long-term credentials such as the PKI and SSO root keys, and the
application passwords. This is a separate step (using a dedicated
Ansible playbook), as long-term credentials can be generated once and
kept forever. This separation isn't particularly important right now
given that we are working on a test environment, but it's useful to
unify test and production workflows in this respect. For the same
reason, even if there is no strict need to do so for a test
environment, we are going to use Ansible Vault to encrypt the
autogenerated credentials.

First, let's pick an Ansible Vault passphrase and save it to a
file. You could also use GPG to encrypt this file (remembering to give
it a `.gpg` extension), but we are not going to do that now:

```shell
cd $HOME/float-test
echo -n passphrase > .ansible_vault_pw
export ANSIBLE_VAULT_PASSWORD_FILE=$PWD/.ansible_vault_pw
```

You can pick any passphrase you want, of course. The
*ANSIBLE_VAULT_PASSWORD_FILE* environment variable is how we tell
Ansible which passphrase to use, you're going to need to set it
whenever you invoke Ansible via *float*. Note that
ANSIBLE_VAULT_PASSWORD_FILE can also point to an executable (like a
script), which can be useful for integration with gpg or password
managers.

We can now initialize the credentials, which by default will be stored
below the *float-test/credentials/* directory (the value of
*credentials_dir* in *config.yml*):

```shell
cd $HOME/float-test
$HOME/float/float run init-credentials
```

Float will look for its configuration file in *config.yml* in the
current directory by default, so there is no need to pass a
*--config=* option in this case.

Which will result in the creation of a number of files below
*float-test/credentials/*, with secrets encrypted with your Ansible
Vault passphrase.

## Step 5: Running Ansible

You are now ready to bring up the test VM and run Ansible to configure
it with our service:

```shell
cd $HOME/float-test
vagrant up
$HOME/float/float run site.yml
```

When Ansible terminates successfully (it is going to take a few
minutes the first time it runs, to download packages and Docker
images), the test virtual machine will be properly configured to serve
*ok.example.com* using our service!

## Step 6: Verify that it works

The ok.example.com service should be served by the public HTTP router
at our test host's public IP, which in the default Vagrant setup is
192.168.10.10:

```shell
curl -k --resolve ok.example.com:443:192.168.10.10 https://ok.example.com
```

If this command returns "OK", the service is working
properly. However, if there are problems, you might want to debug
where things went wrong! There are a number of tools you could use to
do so:

On testing environments, we set up a SOCKS5 proxy on port 9051 of the
first host of the *frontend* group (so in this case, still
192.168.10.10). This is very useful to simulate proper DNS resolution
and browse the builtin services without complex changes to your host
environment, for instance by starting a browser with:

```shell
chromium --proxy-server=socks5://192.168.10.10:9051
```

An alternative could be to add all the built-in services to your
*/etc/hosts* file, pointing at 192.168.10.10.

Useful built-in services for debugging:

* https://logs.example.com/ points at the Kibana UI for the
  centralized log collection service
* https://grafana.example.com/ has monitoring dashboards
* https://monitor.example.com/ is the low-level UI to the Prometheus
  monitoring system

Obviously you can also log in the virtual machine itself (*vagrant ssh
host1*) and examine the state of things there. On testing
environments, syslog logs are also dumped to files below
*/var/log/remote/*, which might be simpler than using the Kibana UI.

To manage the VM running, for example to suspend the VM for lack of memory,
you can use this commands:

```shell
vagrant suspend
vagrant resume
```

When you finish the testing, not forget to destroy the virtual machine, running this command 
in the CLI (always inside of the directory of test enviroment):

```shell
vagrant destroy -f
```


# Next steps

Read on to [running float in a production environment](running.md),
and the [configuration reference](configuration.md)!

# Appendix: But it's so slow!

Yes, Ansible is generally pretty slow at doing its thing, for a number
of reasons (among those the fact that we create a large number of
tasks due to our possibly sub-optimal usage of loops). But there are a
couple of things that can be done to help:

1. Install
   [Mitogen](https://mitogen.networkgenomics.com/ansible_detailed.html),
   which in our case makes Ansible run about 5-10 times faster. To
   enable it, just modify your *ansible.cfg* file as shown in the
   Mitogen docs, or simply pass the *--mitogen=PATH* command-line
   option to the *float create-env* invocation.
2. Set up an APT cache (for instance with *apt-cacher-ng*). Set the
   Ansible variable *apt_proxy* to the host:port of the cache. When
   using Vagrant like in the example provided above, keep in mind that
   your host is always reachable from the VMs as the .1 IP in the
   private network (so it would be 192.168.10.1 in the example).

Still, the first-time run time will still be dominated by network
transfers and package installation (the Docker images are
unfortunately quite large).
