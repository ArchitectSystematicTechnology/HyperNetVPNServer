credentials
===

Ansible role that installs all the [service
credentials](../docs/service_mesh.md#mutual-service-authentication) on
the hosts where they're needed. This role works in combination with
the 'x509' action plugin.

Private keys never leave the target host, we create a CSR and sign it
on the Ansible host.

X509 credentials are stored in /etc/credentials/x509 under directories
named after the services. Every service directory contains a copy of
the public CA certificate, so it can be bind-mounted in a container
easily. There will be separate client and server certificates.

Private keys have mode 440, are owned by root and by a dedicated group
named *service*-credentials. When the service is actually installed,
later, maybe by an Ansible role, it can add the service user to this
group.

Use by including this role and setting the *credentials* variable to a
list of entries specifying the desired credentials. This is already
done once system-wide by the *float-credentials* role with the
credentials automagically derived from the service definitions by
*float*.

## Multiple PKIs

The role supports credentials from different PKI CAs, each identified
by a separate *tag*, with *x509* being the tag of the default internal
float CA.

Additional PKIs are expected to have their CA credentials in the
*credentials_dir*/*tag* local directory, and will have their
certificates installed below /etc/credentials/*tag*.

There are two ways, when invoking this role, to specify that a
different CA from the default should be used:

* By setting the *ca_tag* attribute in the *credentials* map of any of
  the values passed in the *credentials* variable (yes that's
  credentials nested twice). This is how float passes the
  *service_credentials* metadata, so you can just set *ca_tag* there.
* By setting the *ca_tag* variable in Ansible when including this
  role, if you are creating certificates manually rather than relying
  on *service_credentials*.
  
