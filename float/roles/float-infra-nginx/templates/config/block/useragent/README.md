User agent blacklists
===

Add a blocked user agent regexp by creating or modifying a file with a
*.conf* extension in this directory. The files should contain one
entry per line, with the [NGINX map module
syntax](http://nginx.org/en/docs/http/ngx_http_map_module.html):

```
"~*\bsomeverybaduseragentname\b"  1;
```

Use regular expressions (identified by the prefix `~\*`) delimited by
the word delimiter `\b` to match the specified token in the user agent
string. The value should always be set to 1.
