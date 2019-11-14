auth-server-users
===

This role dumps the static admin users map to
/etc/auth-server/users.yml. It is used by the auth-server role, but
it's a separate role because we want to restrict the distribution of
this data very carefully, and not all instances of auth-server need
it.
