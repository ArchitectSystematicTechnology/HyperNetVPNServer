nginx
===

The *nginx* role serves as the public frontend for HTTP-based
services, operating as a reverse proxy. It can be configured
statically or dynamically (see the documentation for the
*public_endpoints* service metadata attribute):

* the static configuration is just a list of all the upstream
  host:port pairs, with equal weight.

* the dynamic configuration performs a DNS lookup (A records right
  now) to resolve a list of host:port pairs to use as
  upstreams. Unfortunately at the moment stock NGINX can't really do
  this very well (the paid version does): the DNS lookup is only
  performed once at startup time. It appears that id could be possible
  to implement this functionality with a pile of LUA (including
  maintaining a DNS cache, basically).

# Single Sign-On

Along with nginx, we run an instance
of [sso-proxy](https://git.autistici.org/id/go-sso) to provide SSO
authentication to services that only offer a non-authenticated HTTP
endpoint. Every nginx instance only talks to the sso-proxy on
localhost.

# Cache

The HTTP cache is located in */var/cache/nginx* (you may want to mount
a separate volume here).

NGINX will set the X-Cache-Status header on responses, so you can
check if the response was cached or not.

The cache TTL is low (10 minutes), and there is currently no way to
purge the cache.

# Extending the configuration

In order to support integration with custom automation mechanisms,
nginx will also load virtualhost configs from the
*/etc/nginx/sites-auto* directory (along with the standard
*sites-enabled* directory).

If you are creating NGINX vhost configurations manually, they should
probably follow this pattern:

```
server {
    listen [::]:443 http2 ssl;
    server_name <name>;
    ssl_certificate /etc/credentials/public/<name>/fullchain.pem;
    ssl_certificate_key /etc/credentials/public/<name>/privkey.pem;
    include /etc/nginx/snippets/site-common.conf;
    
    location / {
        include /etc/nginx/snippets/block.conf;
        include /etc/nginx/snippets/proxy.conf;
        proxy_pass <backend_url>;
    }
}
```

The included files hook in the necessary global configuration and
functionality.

# Configurable parameters

`nginx_global_custom_headers` - a dictionary of {header: value} pairs
corresponding to HTTP headers that must be set on *every* response.

`nginx_top_level_domain_redirects` - a dictionary of {domain: target}
tuples used for redirecting top-level domains to specific destinations
(DNS must be managed manually).



