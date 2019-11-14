User Identity Management
===

This document describes the built-in authentication and authorization
services in the *float* infrastructure.

The basic infrastructure provides a full AAA solution that is used by
all the built-in services, and that can be easily integrated with your
services (or at least that would be the intention). It aims to
implement modern solutions, and support moderately complex scenarios,
while keeping things as simple as possible -- an area that could still
see some improvement. It offers the following features:

* supports users and groups (mostly *admins* and eventually *users*)
* supports multiple backends (file, LDAP, possibly SQL, ...)
* mechanisms for account recovery (currently poor, via secondary
  password, other mechanisms should be implemented)
* transparent upgrade of password hashing mechanisms (for
  future-proofing) (somewhat TODO)
* *single sign-on* for HTTP services
* TOTP and U2F authentication mechanisms for HTTP services
* supports passwords tied to specific services (wrongly called
  *application-specific*) for non-HTTP services
* manages secrets (encryption keys) encrypted with the user password,
  in a way that works even over single sign-on
* supports partitioned services
* configurable rate limits and blacklists for brute-force protection
* tracks logins and user devices without storing PII
* it is modular, and can be adapted to the desired scale / shape

However it is important to note that it comes with a very long list of
caveats as well:

* the single sign-on system is implemented with bearer tokens (signed
  HTTP cookies), which have numerous weaknesses, even if one ignores
  the possible implementation failures:
  * bearer tokens are vulnerable to exfiltration (in logs, in user
    browser histories, caches, etc.), which can be partially mitigated
    by short token lifetimes
  * logout is a somewhat ill-defined operation (the current
    implementation relies on borderline-*adtech* techniques in order to
    delete cookies on other services' domains)
  * they rely on a complex chain of HTTP redirects and HTTP headers
    being set in the right place

Most of these features do not have immediate use in the basic services
built-in into the infrastructure, but they are meant instead for the
primary use case for *float*: the implementation of a large-ish email
and hosting provider.

It should therefore be clear that the chosen design involves numerous
trade-offs, some of which we have tried to document here, that are
tailored to the above use case, and might very well not be suitable to
your particular scenario.

# Structure

This is a breakdown of the various identity services components. In
most cases, since some of the software used is non-standard, there is
a brief "why not X?" section explaining why other more well-known
alternatives were not chosen.

## Authentication

All credentials-based authentication (passwords, OTP, U2F) goes
through the main authentication daemon
[auth-server](https://git.autistici.org/id/auth). It translates
authentication requests, containing service name, user name, password,
and other authentication parameters, into database requests to
retrieve the authentication primaries and verify them.

An authentication response has one of three possible states: failure,
success, and the request for further authentication with a second
factor (OTP or U2F, in which case the response will also contain U2F
challenge parameters). On a successful response, the auth-server might
return additional data such as an email address. The auth-server
listens on a UNIX socket, so it usually runs on all machines, and
speaks a simple line-based protocol. There is also a [PAM
module](https://git.autistici.org/id/auth-pam) available to help
integrate your services.

Database lookup queries can be configured separately for each
supported service, along with a number of other parameters.

The default setup in *float* uses a file-based backend for
administrator accounts (in the *admin* group), and eventually a LDAP
database for user accounts (LDAP was a requirement of the main float
use case, SQL support should be added instead).

The auth-server can log authentication events and the associated
client and device information to long-term storage, and it can detect
anomalies and take action (the standard use case is "send an email
when you see a login from a new device").

Why not PAM? PAM is not exactly a nice interface, furthermore it isn't
exactly easy to pass arbitrary information through its conversation
API (required for OTP/U2F). Furthermore, there are many advantages in
using a standalone authentication server: centralization of rate
limits across different services, a single point for logging, auditing
and monitoring, and a single ownership of database authorization
credentials.

### References

* [git.autistici.org/id/auth](https://git.autistici.org/id/auth),
  the main auth-server code.
* [git.autistici.org/id/usermetadb](https://git.autistici.org/id/usermetadb),
  a privacy-preserving long-term user-focused audit data store (lots
  of words for a SQL database with a simple API).

## Single sign-on

The single sign-on functionality is implemented using
[sso](https://git.autistici.org/ai/sso), a very simple scheme based on
Ed25519 signatures. The SSO functionality is split between a bunch of
libraries that implement token validation for various languages and
environments (including a PAM library and an Apache module), and a
server that handles all the HTTP authentication workflows. For
simplicity, this server also serves the login page itself.

Why not SAML, or any of the other SSO technologies available? Well,
first of all nothing fit exactly the "simplicity" requirement... (and
most of the client SAML libraries available are somewhat awful) but in
the end what we have isn't very different from SAML, except without
all the XML and weird enterprise edge cases.

### References

* [git.autistici.org/ai/sso](https://git.autistici.org/ai/sso)
  original C implementation and design reference, Python bindings, PAM
  / Apache2 modules.
* [git.autistici.org/id/go-sso](https://git.autistici.org/id/go-sso)
  SSO server and SSO proxy implementation.
* [the sso-server role README](../roles/sso-server/README.md) has
  details about the Ansible configuration of SSO parameters.

## User encrypted secrets

There is functionality to maintain a secret associated with every
user, usually a private key used for encrypting user data, in such a
way that it can only be decrypted by the user itself, using the
password (or any other equivalent form of authentication primary).

The implementation maintains a number of copies of the encrypted
password, each encrypted with one of the authentication primaries: the
user's main password, the secondary password used for recovery, and
the various application-specific passwords if present. This way, each
service that successfully authenticates the user can immediately
decrypt the secret by trying all the available encrypted secrets with
the password it has.

Single sign-on integration is provided by a dedicated service that
decrypts keys when the user initially logs in on the SSO server (the
only time in the SSO workflow when we have access to the password),
and keeps it around until the login expires.

### References

* [git.autistici.org/id/keystore](https://git.autistici.org/id/keystore),
  the key storage service, includes a dedicated Dovecot dict proxy
  interface (Dovecot is the primary use case for the encrypted secrets
  feature).


# Authentication workflows

In this section we try to document step-by-step the various
authentication workflows, to illustrate the interactions between the
various authentication-related services described above.

## Single sign-on

![SSO workflow](sso.png)

1. The first time a user connects to *service1*, it is redirected to
   the IP (*identity provider*).
2. The IP handles the authentication UX (form with username and
   password, OTP, U2F, etc).
3. The IP verifies the credentials with the authentication server.
4. The authentication server verifies the credentials against what is
   in the database. If the credentials are good but incomplete
   (i.e. we have the right password but no 2FA), go back to step 2 and
   ask for the second factor.
5. The IP uses the user password to unlock the user's key by calling
   the keystore service.
6. The keystore fetches the key from the database, decrypts it, and
   caches it in memory.

When the SSO token for *service1* expires, and the user is once again
redirected back to the IP, the identity provider can skip the
authentication process (if it recognizes the user) and simply create a
new valid token straight away. This process is transparent to the user
(well, for GET requests at least).

## Non-HTTP service login

Let's take *dovecot* as an example of a non-HTTP service.

![Non-HTTP login workflow](auth.png)

1. The user connects to dovecot using an IMAP client. The client sends
   credentials that look like a password, which are either:
   * the user's primary password (for users without 2FA), or
   * a service-specific password valid for the *dovecot* service
2. Dovecot verifies the credentials with the authentication server,
   using PAM (dovecot supports many ways to plug in a custom
   authentication protocol, PAM is just one of them).
3. The authentication server verifies the credentials against what is
   in the database. There is no support for "incomplete" credentials
   here because the IMAP protocol is not conversational.
4. Dovecot fetches the (decrypted) user encryption key from
   keylookupd, sending it the credentials used in the IMAP login. It
   will keep this key in memory for the duration of the IMAP
   connection.
5. Keylookupd fetches the (encrypted) user encryption key from the
   database and decrypts it using the credentials.

## Third-party service authentication

Let's examine a more complex interaction, where a HTTP-based service
(*roundcube*, a webmail application) needs to access internally a
different service (dovecot, in order to read the user's email).

![Third-party authentication workflow](auth2.png)

1. The user has a valid SSO token for the *roundcube* service, and
   connects to the roundcube web application.
2. Roundcube exchanges the user SSO token for another one that is
   valid for the *dovecot* service, by using the "exchange" API of the
   IP (identity provider).
3. The IP verifies that the roundcube SSO token is valid, and that the
   roundcube -\> dovecot transition is authorized (via a
   whitelist). It signs a new token for the same user with the new
   service "dovecot".
4. Roundcube talks to dovecot and logs in on behalf of the user
   providing this new SSO token as the password.
5. Dovecot verifies that the username and SSO token are valid (using
   *pam_sso*), and retrieves the (decrypted) user encryption key from
   the keystore.
6. The keystore already has the (decrypted) user encryption key cached
   in memory because at some point in time *before* accessing the
   roundcube web application, the user has logged in to the IP, which
   has unlocked the key in keystore (see the "single sign-on" workflow
   description above, step 6).
