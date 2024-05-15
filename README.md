# Introduction

Lilypad is put together using the [float configuration management toolkit for container-based services](https://git.autistici.org/ai3/float). It is a series of [Ansible](https://www.ansible.com) plugins and roles glued together to provide a simple container-oriented environment. This can be rolled into your own Ansible configuration, or used separately.

Monitoring, alerting, log-collection and analysis, DNS and Let's Encrypt certificates for all of the services included are handled automatically. Please see the [float reference documentation](https://git.autistici.org/ai3/float/-/blob/master/docs/reference.md) for further details.

## Pre-requisites

  - **Three different machines**: 
     reverse-proxy, backend, gateway/s(at least one, more the merrier) 

    These can be bare-metal, or virtual machines (eg. KVM). They should have a minimal Debian 12 (Bookworm) installation and be reachable by SSH. 
  
  - **You will need to pick a subdomain and delegate the DNS to the system to manage.**
    
    For example, if your domain is `example.com`, then you could delegate the subdomain `float.example.com`. 
    You would do this on your nameserver or DNS provider: add a `NS` record for `float.example.com` that points to `ns1.example.com` 
    and then an `A` record for `ns1.example.com` that points to the IP address you use for the reverse proxy host (note: not the gateway IP). 
    
    like:

|Domain | Type | Destination|
|--|--|--|
|float.example.com	|NS	|ns1.example.com |
|ns1.example.com	  |A	| \<IP of ReverseProxy instance>|


## Architecture

 - Reverse Proxy: runs nginx, DNS nameserver and provide the infrastructure front-end. 
 - Backend: runs the application services that the reverse proxy talks to, it runs, among other things, the LEAP web API, the gateway selection service, and the infrastructure that provides monitoring and alerting.  
 - Gateway/s: These run openvpn and act as **VPN gateways, which ideally require two publicly addressable IP addresses, one for ingress and one for egress.**
 - Bridge: runs a [obfsvpn](https://0xacab.org/leap/obfsvpn) service, can run on the same machine as the gateway.


## How to provision a new provider?

The machines should be considered to be fully managed by this framework when things have been deployed. It will modify the system-level configuration, install packages, start services, etc. However, it assumes that certain functionality is present, either managed manually or with some external mechanisms: network configuration, partitions, file systems, and logical volumes must be externally (or manually) managed. SSH access and configuration must be externally managed _unless_ you explicitly set `enable_ssh=true` in _lilypad/group_vars/all/config.yml_ (and add SSH keys to your admin users), in which case deployment will take over the SSH configuration.


The following commands should be run  ***locally on your computer*** in order to install and deploy Lilypad on the remote machines.

### 0. Clone the float repository

...and enter it

```shell
git clone https://0xacab.org/leap/container-platform/lilypad
cd lilypad
```

### 1. Install the float and LEAP platform pre-requisites

This installation guide is tested on Debian Bookworm.
Other Linux distributions might need additional steps to install all requirements in the correct version.

```shell
sudo apt-get install golang build-essential bind9utils git libsodium23 virtualenv

# for golang version lower than 1.16 and use go get instead of go install after running export GO111MODULE=on 

go install git.autistici.org/ale/x509ca@latest
go install git.autistici.org/ale/ed25519gen@latest
go install git.autistici.org/ai3/go-common/cmd/pwtool@latest
export PATH=$PATH:$HOME/go/bin
```

We'll use [virtualenv](https://virtualenv.pypa.io/en/latest/) to manage and install python packages:
```
virtualenv -p /usr/bin/python3 venv
source ./venv/bin/activate
pip install -r ./requirements.txt
```

This will create a virtual environment where we can install and version control specific python dependencies.

When working on this project, if you're in a new shell, you'll need to run the `source ./venv/bin/activate` command again to re-enter the virtual environment.

### 2. Initialize the ansible vault

... by creating a password file. Keep the public user ID / email address of your OpenPGP keys at hand:

```shell
# If you don't have PGP keys yet, generate a new one using
# gpg --full-generate-key

tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 26 | gpg -ea -o .ansible_vault_pw.gpg
```

The resulting _.ansible_vault_pw.gpg_ will be automatically decrypted by Ansible at runtime (use of an agent, such as `gpg-agent` is advised).

Configure your local environment to know where the ansible vault password is located. To do so add it to your shell environment initialization file (_~/.bashrc_) so it will be set automatically everytime:

```shell
# Add it to ~/.bashrc
export ANSIBLE_VAULT_PASSWORD_FILE=<path-to-lilypad-repo>/.ansible_vault_pw.gpg
# Reload your bashrc for the change to take effect
source ~/.bashrc
```

### 3. Customize the environment 

#### 3.1. Configure the ansible host file
Open _hosts.yml_ and change `floatapp1` to your app host's hostname, and specify the `ansible_host` and `ip` values to be the IP address for that host. If you have more than one app server, then you would just create a copy of this block, modifying the values, being sure to keep the 'backend' group assigned to each one.

Configure the front-end reverse proxy and the gateway sections in the same way. Change the `floatrp1` to your hostname, and the `ansible_host` and `ip` to the IP it should have. Same for the gateway section: change `gateway1` to your gateway server's hostname and put the respective IP address under `ansible_host` and `ip`. Also set the `location` value to where this server is located. It's important to have two different IP addresses for the gateway server for ingress and egress traffic. Put the secondary gateway IP address in the `egress_ip` variable. If you have more than one gateway, just copy the whole block and modify its values respectively.

_NOTE:_ If you use IPv6 addresses uncomment and adapt the gateway example given in the section `gateway2`.

#### 3.2. Configure _config.yml_ :)
Edit _group_vars/all/config.yml_ and set your `domain_public` to the subdomain name that you delegated (eg. `float.example.com`), the `domain` can be set to `infra.example.com` as this is the internally managed domain. 

The _config.yml_ contains a list of admins and a default hashed password. If you do not change this password, then the user 'admin' and password 'password' are used. To change the hashed password you can run 
```shell
pwtool <type-here-your-password>
``` 
and paste the output into the `password` variable. Have a look at [the common operators playbook](https://git.autistici.org/ai3/float/-/blob/master/docs/playbook.md#adding-an-admin-account) for additional options, such as setting up OTP or U2F tokens.

Next specify ssh keys that will be able to connect to the system as root in the `admin` section under `ssh_keys`.

This _config.yml_ also contains the credentials for an updated geoip database. The `geoip_account_id` and `geoip_license_key` values must be changed, you can register for an account on maxmind.com to obtain these. The geoip service helps end users to choose a gateway near them (usually faster).

#### 3.3. Specify your gateway locations

Edit _group_vars/all/gateway_locations.yml_ to match your environment. The value of `location` in the gateway section in _hosts.yml_ must match the key for a location in _gateway_locations.yml_. And the `name` variable in _gateway_locations.yml_ **must** match exactly one of [these city names](https://github.com/tidwall/cities/blob/master/cities.go). Make sure to have one corresponding entry in the _gateway_locations.yml_ for each gateway location configured in _hosts.yml_.

#### 3.4. Specify your provider details

Edit _group_vars/all/provider_config.yml_: choose a name and description for your provider and fill in your domain name instead of "example.com" in all other lines.

### 4. Generate credentials 

... by running the init-credentials playbook. This will ansible-vault-encrypt the resulting secret files under _credentials/_. 
_Note:_ this is not the built-in float init-credentials, rather this is the LEAP provided one, which will instantiate the float init-credentials when it is finished.

```shell
float/float run playbooks/init-credentials
```

***You should not see any red text*** in this process, if you do, stop now, doublecheck the configurations and try again.

This will generate service-level credentials, which are automatically managed by the toolkit and are encrypted with ansible-vault. These include the internal X509 PKI for TLS service authentication, a SSH PKI for hosts, and application credentials. 

### 5. Consider comitting the generated credentials 

... to git, and pushing them to a repository. All auto-generated credentials are stored in the _credentials_dir_ - you will want to ensure that these are properly encrypted, checked into a git repository and kept private. The secret material is encrypted with ansible-vault, so it cannot be read without the access to the _.ansible_vault_pw_. If you commit these files, and push them to a respository, then you can share them with other admins, but be aware that these are secrets that should not be shared with anyone but trusted admins. If you gpg encrypted the _.ansible_vault_pw_, then that file is also encrypted and could also be committed.

### 6. Ensure SSH access
Make sure you can ssh to all hosts (backend, reverse-proxy, gateway(s)) as root without being prompted for a password every time after having verified and accepted the correct host key. Try to login to each of your hosts by running:
```shell
ssh root@<host-ip>
```

### 7. Deploy the configuration 

Run: 
```shell
float/float run site.yml 
```
This will take some time to finish, as it needs to download packages and Docker images and configure everything.

### 8. Update servers

Run:

```shell
float/float run float/playbooks/apt-upgrade.yml
```

Congratulations. You have successfully installed and deployed the LEAP platform! You should [read the documentation about how to perform common operations](https://git.autistici.org/ai3/float/-/blob/master/docs/playbook.md).

### Testing

make sure the x509 v3 extensions exist: x509.ExtKeyUsageClientAuth x509.KeyUsageDigitalSignature

```
# Fetch ca-certificate
$ curl -vsL -o ca.crt https://api.float.example.com/ca.crt
# Fetch  openvpn.pem
$ curl -vL --cacert ca.crt -o openvpn.pem https://api.float.example.com:4430/3/cert
```

```shell
/usr/sbin/openvpn --client --remote-cert-tls server --tls-client --remote <gateway-IP> 80 --proto tcp --verb 3 --auth SHA1 --keepalive 10 30 --tls-version-min 1.2 --dev tun --tun-ipv6 --ca ./ca.crt --cert ./openvpn.pem --key ./openvpn.pem
```

Reference: https://0xacab.org/leap/vpnweb/-/blob/ecaa22111ee8e34111080139e1e8a92b90e30158/pkg/web/certs.go#L56

        ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
        KeyUsage:    x509.KeyUsageDigitalSignature,
        CommonName: UNLIMITED
        subjectkeyID: random
        serial: random

#### Integration Testing
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

#### Testing float

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

