geoip-dataset
=============

Maintains a GeoIP (lite) database on the host. This depends on the *geoip-base* role.

Usually included by other services.

Define the following configuration variable to enable it:

* *geoip_account_id*
* *geoip_license_key*
* *geoip_datasets* (default: country)

You will need to register for an account on maxmind.com to obtain
these.
