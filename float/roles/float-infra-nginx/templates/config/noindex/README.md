URL deindexing
===

This list allows you to prevent bots from indexing specific URLs.
The string that is matched is the combination of the hostname and
the request path (without query arguments), i.e. for a request to

```
https://example.com/path/?arg=value
```

this map will attempt to match

```
example.com/path/
```

To deindex a URL, create or modify a file with a *.conf* extension in
this directory. The files should contain one entry per line, with the
[NGINX map module
syntax](http://nginx.org/en/docs/http/ngx_http_map_module.html):

```
"example.com/path/"  noindex;
```

The value should always be set to `noindex`.

Deindexing via HTTP header is described here:

https://developers.google.com/search/docs/advanced/robots/robots_meta_tag

