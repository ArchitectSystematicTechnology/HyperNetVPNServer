Install self-signed certs for all the public credentials (those
derived from float service definitions in *services.yml*) on the
current host, if they don't already have valid ACME-generated
certificates.

Call this role to pull in the public credentials of the desired type
or service, by defining either the *credentials_type* or the
*credentials_service* (only for non-http endpoints) variable.

Usually to be applied together with the *acme-storage* Ansible role:
while *public-credentials* installs self-signed certificates,
*acme-storage* will synchronize the right credentials as they are
obtained and managed by the ACME automation.

It is ultimately just a way to run the *public-ssl-cert* role with the
list of CN derived from the float configuration. To manage your own
certs you can just directly call *public-ssl-cert* in a loop.
