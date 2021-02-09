Playbook
===

This document describes how to perform some common operations in
*float*.


## Applying changes

### Rolling back the configuration

If you are using a Git repository as your configuration source,
*float* will keep track of which commit has been pushed to production
last, and it will try to prevent you from pushing an old version of
the configuration, failing immediately with an error. This is a simple
check to make sure that people do not inadvertently roll back the
production configuration by pushing from an out-of-date client.

In most cases what you want to do in that case is to simply run *git
pull* and bring your copy of the repository up to date. But if you
really need to push an old version of the configuration in an
emergency, you can do so by setting the *rollback* value to *true* on
the command-line:

```shell
$ float run -e rollback=true site.yml
```


## For administrators

### SSH Client Setup

If you delegated SSH management to float by setting *enable_ssh* to
true (see the [configuration reference](configuration.md)), float will
create a SSH CA to sign all your host keys.

You will find the public key for this CA in the
*credentials/ssh/key.pub* file, it will be created the first time you
run the "init-credentials" playbook.

Assuming that all your target hosts share the same domain (so you can
use a wildcard), you should add the following entry to
*~/.ssh/known_hosts*:

```
@cert_authority *.example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAA....
```

Since all logins happen as root, it may be convenient to also add a
section to your *~/.ssh/config* file like the following:

```
Host *.example.com
    User root
```

### Adding an admin account

Adding a new administrator account is just a matter of editing the
*admins* [configuration variable](configuration.md) and add a new
entry to it.

The first thing you will need is a hashed version of your
password. The authentication service in float supports a number of
legacy hashing schemes, including those supported by the system
crypt(). The most secure hashing scheme supported is Argon2, and you
can use our custom tool to generate a valid hash. To install it:

```shell
$ go install git.autistici.org/ai3/go-common/cmd/pwtool
```

Run the *pwtool* utility with your new password as an argument, as
shown below:

```shell
# Do not save your password in the history of your shell
$ export HISTIGNORE="./pwtool.amd64*"
$ ./pwtool.amd64 PASSWORD
```

where PASSWORD is your desired password.

It will output the hashed password.

Then modify the YAML file *group_vars/all/admins.yml*. At the bare
minimum the new account should have a *name*, *email*, *password* and
*ssh_keys* attributes, e.g.:

```yaml
---
admins:
  - name: "foo"
    email: "foo@example.com"
    password: "$a2$3$32768$4$abcdef...."
    ssh_keys:
      - "ssh-ed25519 AAAAC3Nza..."
```

Here above "ssh_keys:" needs to be populated with your public key,
possibly stripped from the trailing user@hostname text (which may leak
your personal information), and "password:" must be the hashed
password you got from *pwtool* earlier.

### Setting up OTP for an admin account

First you need to manually generate the OTP secret on your computer:

```shell
$ SECRET=$(dd if=/dev/urandom bs=20 count=1 2>/dev/null | base32)
$ echo $SECRET
EVUVNACTWRAIERATIZUQA6YQ4WS63RN2
```

Install the package qrencode, and feed the OTP secret to it.
For example with apt ["apt install qrencode" of course].

```shell
$ EMAIL="sub@krutt.org"
$ qrencode -t UTF8 "otpauth://totp/example.com:${EMAIL}?secret=${SECRET}&issuer=example.com&algorithm=SHA1&digits=6&period=30"
```

and read the qrcode with your favourite app.

Then add it to your user object in *group_vars/all/admins.yml* as the
*totp_secret* attribute:

```yaml
---
admins:
  - name: "foo"
    totp_secret: "EVUVNACTWRAIERATIZUQA6YQ4WS63RN2"
    ...
```

Finally, configure your TOTP client (app, YubiKey, etc.) with the same
secret.

Note that the secret is stored in cleartext in the git repository, so
using a hardware token (U2F) is preferred.

### Registering a U2F hardware token for an admin account

In the *group_vars/all/admins.yml* file, you can add the
*u2f_registrations* attribute to accounts, which is a list of the
allowed U2F device registrations.

To register a new device, you are going to need the *pamu2fcfg* tool
(part of the *pamu2fcfg* Debian package). The following snippet should
produce the two YAML attributes that you need to set:

```shell
$ pamu2fcfg --nouser --appid https://accounts.example.com \
    | tr -d : \
    | awk -F, '{print "key_handle: \"" $1 "\"\npublic_key: \"" $2 "\""}'
```

press enter, touch the key, copy the output and insert it in
*group_vars/all/admins.yml*, the final results should look like:

```yaml
---
admins:
  - name: "foo"
    email: "foo@example.com"
    password: "$a2$3$32768$4$abcdef...."
    ssh_keys:
      - "ssh-ed25519 AAAAC3Nza..."
    u2f_registrations:
      - key_handle: "r4wWRHgzJjl..."
        public_key: "04803e4aff4..."
```

**NOTE**: the above will work with *pam_u2f* version 1.0.7, but it will *not*
work with pam_u2f version 1.1.0 due to changes in the output format!

