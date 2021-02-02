URL blacklists
===

This blacklist allows you to block requests to a specific URL. The
string that is matched is the combination of the hostname and the
request path (without query arguments), i.e. for a request to

```
https://example.com/path/?arg=value
```

this map will attempt to match

```
example.com/path/
```

To block a URL, create or modify a file with a *.conf* extension in
this directory. The files should contain one entry per line, with the
[NGINX map module
syntax](http://nginx.org/en/docs/http/ngx_http_map_module.html):

```
"example.com/path/"  1;
```

The value should always be set to 1.
