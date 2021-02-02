sso-server
===

This role sets up a couple of services implementing the *single
sign-on* workflow for HTTP-based services. This includes:

* [sso-server](https://git.autistici.org/id/go-sso)
* [user-meta-server](https://git.autistici.org/id/usermetadb)

These services are configured in *services.yml*, but they are not
containerized and they need some system-level configuration managed by
Ansible.

The *sso-server* service is stateless and can be configured with an
arbitrary *num_replicas* count. There should be only one global
instance of the *user-meta-server* instead.

## Configuration

The only configuration parameter available is the following:

`enable_keystore` (bool), if true enables unlocking a user's storage
private key on login by
calling [keystore](https://git.autistici.org/id/keystore), which must
be separately configured in *services.yml* as a service named
*keystore*.

The SSO server needs some run-time credentials for cookie encryption,
which should be defined in your *passwords.yml* file with something
like:

```
- name: sso_session_auth_secret
  description: sso-server cookie auth key
  type: binary
  length: 64
- name: sso_session_enc_secret
  description: sso-server cookie encryption key
  type: binary
  length: 16
- name: sso_csrf_secret
  description: sso-server cookie-based CSRF secret
  type: binary
  length: 64
- name: sso_device_manager_auth_secret
  description: sso-server cookie-based device manager secret
  type: binary
  length: 64
```
