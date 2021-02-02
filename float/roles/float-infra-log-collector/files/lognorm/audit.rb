version=2

# Match audit logs like:
# node=host3 type=SERVICE_START msg=audit(1526160997.363:18883): pid=1 uid=0 auid=4294967295 ses=4294967295 msg='unit=docker-ok-http comm="systemd" exe="/lib/systemd/systemd" hostname=? addr=? terminal=? res=success'

prefix=%[
  {"type": "literal", "text": " node="},
  {"type": "word"},
  {"type": "literal", "text": " type="},
  {"type": "word", "name": "audit_event_type"},
  {"type": "literal", "text": " msg=audit("},
  {"type": "char-to", "extradata": ")"},
  {"type": "literal", "text": "): pid="},
  {"type": "word"},
  {"type": "literal", "text": " uid="},
  {"type": "word", "name": "uid"},
  {"type": "literal", "text": " auid="},
  {"type": "word"},
  {"type": "literal", "text": " ses="},
  {"type": "word"},
  ]%

rule=:%[
  {"type": "literal", "text": " msg='unit="},
  {"type": "word", "name": "service"},
  {"type": "rest"},
  ]%

rule=:%[
  {"type": "literal", "text": " msg='op-PAM:"},
  {"type": "word", "name": "audit_pam_op_type"},
  {"type": "literal", "text": " acct="},
  {"type": "word", "name": "user"},
  {"type": "rest"},
  ]%

prefix=
