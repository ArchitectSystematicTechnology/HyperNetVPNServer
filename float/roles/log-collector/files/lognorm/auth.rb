version=2

#prefix=%[
#  {"type": "date-rfc5424"},
#  {"type": "literal", "text": " "},
#  {"type": "word", "name": "host"},
#  {"type": "literal", "text": " "},
#  ]%

# Match sso-server successful logins.
rule=:%[
  {"type": "literal", "text": " successful login for user "},
  {"type": "word", "name": "user"},
  {"type": "rest"},
  ]%

# Match auth-server successful logins.
rule=:%[
  {"type": "literal", "text": " auth: user="},
  {"type": "word", "name": "user"},
  {"type": "literal", "text": " service="},
  {"type": "word", "name": "sso_service"},
  {"type": "literal", "text": " status="},
  {"type": "word", "name": "sso_auth_status"},
  {"type": "rest"},
  ]%

# SSH publickey logins (with key fingerprint).
rule=:%[
  {"type": "literal", "text": " Accepted publickey for "},
  {"type": "word", "name": "user"},
  {"type": "literal", "text": " from "},
  {"type": "word"},
  {"type": "literal", "text": " port "},
  {"type": "word"},
  {"type": "literal", "text": " ssh2: "},
  {"type": "word"},
  {"type": "literal", "text": " "},
  {"type": "word", "name": "ssh_key_fp"}
  ]%

