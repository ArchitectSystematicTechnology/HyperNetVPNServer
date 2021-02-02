version=2

# liblognorm2 rule base for HTTP logs as emitted by the ai3 NGINX
# setup. The incoming log message starts with a space, the remote host
# name, and the tag "nginx_access:". Does not index client IP.

# The NGINX log line includes both the server_name and the Host header
# sent by the client. The 'vhost' field is set to the latter.

rule=:%[
  {"type": "char-to", "extradata": ":"},
  {"type": "literal", "text": ": "},
  {"type": "word"},
  {"type": "literal", "text": " "},
  {"type": "word", "name": "vhost"},
  {"type": "literal", "text": " "},
  {"type": "word"},
  {"type": "literal", "text": " "},
  {"type": "word", "name": "ident"},
  {"type": "literal", "text": " "},
  {"type": "word", "name": "auth"},
  {"type": "literal", "text": " ["},
  {"type": "char-to", "extradata": "]"},
  {"type": "literal", "text": "] \""},
  {"type": "word", "name": "verb"},
  {"type": "literal", "text": " "},
  {"type": "word", "name": "request"},
  {"type": "literal", "text": " HTTP/"},
  {"type": "float", "name": "httpversion"},
  {"type": "literal", "text": "\" "},
  {"type": "number", "name": "status"},
  {"type": "literal", "text": " "},
  {"type": "number", "name": "bytes"},
  {"type": "literal", "text": " \""},
  {"type": "char-to", "name": "referrer", "extradata": "\""},
  {"type": "literal", "text": "\" \""},
  {"type": "char-to", "name": "agent", "extradata": "\""},
  {"type": "literal", "text": "\" "},
  {"type": "word", "name": "backend"},
  {"type": "rest"}
  ]%
