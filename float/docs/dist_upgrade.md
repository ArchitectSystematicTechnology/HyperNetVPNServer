Upgrading the Debian distribution used for *float*
===

Float generally targets the current Debian *stable* distribution, but
it uses explicit distribution names (*stretch*, *buster*, etc) to
avoid unexpected dist-upgrades.

Whenever the Debian stable version changes, you should probably
upgrade your servers too. There is support for this as a multi-step
process:

* Set *float_debian_dist* to the new codename (e.g. "buster") in your
  group_vars/all configuration.
* Run *float*, which will install the correct APT sources for the new
  release.
* Run *apt dist-upgrade* manually or via Ansible. This part is not
  automated yet due to the large variety in possible scenarios.
* Run *float* again: it will now detect that the distribution has
  changed and reconfigure packages as needed.
