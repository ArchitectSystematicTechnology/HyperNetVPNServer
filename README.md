# Getting started

Currently, you need at least two different remote machines for the installation process. These can be bare-metal, or virtual machines (eg. KVM). They should have a minimal Debian Buster installation and be reachable by ssh. The machines should be considered to be fully managed by this framework when things have been deployed. It will modify the system-level configuration, install packages, start services, etc. However, it assumes that certain functionality is present, either managed manually or with some external mechanism. Network configuration, partitions, file systems, and logical volumes must be externally (or manually) managed. SSH access and configuration must be externally managed _unless_ you explicitly set enable_ssh=true (and add SSH keys to your admin users), in which case deployment will take over the SSH configuration.

One of the hosts will be a reverse proxy and the VPN gateway. *** You will need two publicly addressable IP addresses for this machine ***. The second machine will run the LEAP web API, its gateway selection service, and the infrastructure that provides monitoring and alerting. 

The float platform will manage DNS hostnames and Let's Encrypt certificates for all of its services it handles. You should pick a subdomain and delegate its DNS for the system to manage. For example, if your domain is `example.com`, then you could delegate, for example, the subdomain `float.example.com`. You would do this by adding a `NS` record for `float.example.com` that points to `ns1.example.com` and then an `A` record for `ns1.example.com` that points to the IP address you use for the reverse proxy host (note: not the gateway IP).

You need to run the following commands ***locally on your computer*** in order to install and deploy the LEAP platfrom on the remote machines.

## 0. Install the float and LEAP platform pre-requisites

You'll need ansible < 2.10 and python3 for the installation process. This installation guide is tested on Debian buster. 
Other Linux distributions might need additional steps to install all requirements in the correct version.

```shell
sudo apt-get install golang bind9utils python3-pysodium python3-jinja2 python3-netaddr python3-openssl python3-yaml python3-six python3-crypto ansible git
go get -u git.autistici.org/ale/x509ca
go get -u git.autistici.org/ale/ed25519gen
go get git.autistici.org/ai3/go-common/cmd/pwtool
export PATH=$PATH:$HOME/go/bin
```

Make sure `$ ansible --version | grep "ansible 2"` shows a version < 2.10.
Make sure `$ ansible --version | grep "python version" shows a python 3 version.

## 1. Clone the float repository

...and enter it

```shell
git clone https://0xacab.org/leap/container-platform/float
cd float
```
    
## 2. Initialize the ansible vault

... by creating a password file:

```shell
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 26 > .ansible_vault_pw
```

_Optionally_: gpg encrypt this file, so only trusted admins can read it. If you do *not* encrypt this file, then this repository should not be shared anywhere public:

```shell
gpg -e .ansible.vault_pw ; rm .ansible.vault_pw
```

The resulting `.ansible.vault_pw.gpg` will be automatically decrypted by Ansible at runtime (use of an agent, such as `gpg-agent` is advised).

Configure your local environment to know where the ansible vault password is located:

```shell
export ANSIBLE_VAULT_PASSWORD_FILE=.ansible_vault_pw
```

_NOTE:_ if you performed the optional encryption step above, you will
need to add .gpg to the end of the file name below:

```shell
export ANSIBLE_VAULT_PASSWORD_FILE=.ansible_vault_pw.gpg
```

This environment variable will only be set for this shell, you will need to add it to your shell environment initialization file so it will be set automatically everytime.

## 3. Customize the environment 

Open _hosts.yml_ and change `floatapp1` to your app host's hostname, and specify the `ansible_host` and `ip` values to be the IP addresses for that host. If you have more than one app server, then you would just create a copy of this block, modifying the values, being sure to keep the 'backend' group assigned to each one.

Configure the front-end reverse proxy with in the same way, change the `floatrp1` hostname to your hostname, and the `ansible_host` and `ip` to the IP it should have, and set the  `location` value to where this server is located. For the gateway_address, put the secondary gateway ip.

Then edit _group_vars/all/config.yml_ and set your `domain_public` to the subdomain name that you delegated (eg. `float.example.com`), the `domain` can be set to `infra.example.com` as this is the internally managed domain. 

The _config.yml_ contains a list of admins, a default hashed password and a set of ssh keys that will be able to connect to the system as root. If you do not change this password, then the user 'admin' and password 'password' are used. To change the hashed password you can run 
```shell
pwtool <type-here-your-password>
``` 
and paste the output into the `password` variable. Have a look at [the common operators playbook](https://git.autistici.org/ai3/float/-/blob/master/docs/playbook.md#adding-an-admin-account) for additional options, such as setting up OTP or U2F tokens.

Then edit _group_vars/all/gateway_locations.yml_, _group_vars/all/provider_config.yml_ to match your environment. 

## 4. Generate credentials 

... by running the init-credentials playbook. This will ansible-vault-encrypt the resulting secret files under _credentials/_. 
_Note:_ this is not the built-in float init-credentials, rather this is the LEAP provided one, which will instantiate the float init-credentials when it is finished.

```shell
float/float run playbooks/init-credentials
```

***You should not see any red text*** in this process, if you do, stop now.

This will generate service-level credentials, which are automatically managed by the toolkit and are encrypted with ansible-vault. These include the internal X509 PKI for TLS service authentication, a SSH PKI for hosts, and application credentials. 

## 5. Consider comitting the generated credentials 

... to git, and pushing them to a repository. All auto-generated credentials are stored in the _credentials_dir_ - you will want to ensure that these are properly encrypted, checked into a git repository and kept private. The secret material is encrypted with ansible-vault, so it cannot be read without the access to the _.ansible_vault_pw_. If you commit these files, and push them to a respository, then you can share them with other admins, but be aware that these are secrets that should not be shared with anyone but trusted admins. If you gpg encrypted the _.ansible_vault_pw_, then that file is also encrypted and could also be committed.

## 6. Ensure SSH access
Be sure you can ssh to the hosts as root with a public key that will not be prompting you for a password every time; you should have also verified and accepted the correct host key.

## 7. Deploy the configuration 

Run: 
```shell
float/float run site.yml 
```
This will take some time to finish, as it needs to download packages and Docker images and configure everything.

## 8. Update servers

Run:

```shell
float/float run float/playbooks/apt-upgrade.yml
```

Congratulations. You have successfully installed and deployed the LEAP platform! You should [read the documentation about how to perform common operations](https://git.autistici.org/ai3/float/-/blob/master/docs/playbook.md).

## Testing

Certificate authority from provider: `leap.ca`

Make a CSR/key

sign cert against CA

make sure the x509 v3 extensions exist: x509.ExtKeyUsageClientAuth x509.KeyUsageDigitalSignature

```shell
/usr/sbin/openvpn --client --remote-cert-tls server --tls-client --remote 37.218.241.84 1194 --proto tcp --verb 3 --auth SHA1 --keepalive 10 30 --tls-version-min 1.0 --dev tun --tun-ipv6 --ca ./ca.pem --cert ./testopenvpn.crt --key ./testopenvpn.key
```

Reference: https://0xacab.org/leap/vpnweb/blob/master/certs.go#L37

        ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
        KeyUsage:    x509.KeyUsageDigitalSignature,
        CommonName: UNLIMITED
        subjectkeyID: random
        serial: random

### Integration Testing
Integration tests can be run to:
            * check that public endpoints for built-in services are reachable
            * check that no Prometheus alerts are firing

These tests can be run from your Ansible directory using the *float*
command-line tool:

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

### Testing float

```shell
    apt install qemu-kvm libvirt-clients libvirt-daemon-system bridge-utils vagrant vagrant-libvirt
    adduser micah libvirt
    adduser micah libvirt-quemu
    float create-env --vagrant --num-hosts 2 test
    cd test; vagrant up
```

### FAQ

***Why is there a '[openvpn]' group, but no host attached to it?***

You might have noticed that site.yml has a hosts parameter with roles assigned to them, and the actual hosts defined in site.yml are connected to the hosts.yml groups parameter. The hosts.yml has floatrp1 with the groups: `[frontend]`, but there is no host which has the `[openvpn]` group attached to it.

For the 'openvpn' service, there is a scheduling_group, which sets the *scope* of the possible hosts that the service will be scheduled onto. Float will create automatically a 'openvpn' group, containing just the hosts that 'openvpn' is running on. We did not define an 'openvpn' group in the hosts.yml ansible inventory, yet such a group is automatically created by float, and you can use it in Ansible. This 'openvpn' group is a subset of the scheduling_group.

***"where can I run openvpn"*** -> scheduling_group (frontend) 

***"where is openvpn actually running"**** -> "openvpn" group

