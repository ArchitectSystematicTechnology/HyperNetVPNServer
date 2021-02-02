version=2

# liblognorm2 rules for Postfix logs

# use with 'useRawMsg on'.

prefix=%[
	{"type":"literal", "text":" "},
	{"type":"char-to", "name":"postfix_queue_id", "extradata":":"},
	{"type":"literal", "text":": "},
	]%

#  198FB12016D: to=<bobby.johnson@hotmail.com>, relay=0.0.0.0[0.0.0.0]:10025, delay=3.2, delays=3.1/0/0/0.04, dsn=2.0.0, status=sent (250 2.0.0 Ok: queued as 53CCC120171)
rule=:%[
	{"type":"literal", "text":"to=<"},
	{"type":"char-to", "name":"rcpt_to", "extradata":">"},
	{"type":"literal", "text":">,"},

	{"type":"char-to", "extradata":","},
	{"type":"literal", "text":","},

	{"type":"char-to", "extradata":","},
	{"type":"literal", "text":","},

	{"type":"char-to", "extradata":","},
	{"type":"literal", "text":","},

	{"type":"char-to", "extradata":","},
	{"type":"literal", "text":","},
	{"type":"literal", "text":" status=sent "},
	{"type":"rest"}
	]%

#  NOQUEUE: reject: RCPT from unknown[0.0.0.0]: 553 5.7.1 <ludofficinamompracem@canaglie.org>: Sender address rejected: not owned by user ludofficinamompracem@canaglie.org; from=<ludofficinamompracem@canaglie.org> to=<dheeraj@velocityinfo.com> proto=ESMTP helo=<[0.0.0.0]>
rule=:%[
	{"type":"literal", "text":"reject: "},
	{"type":"char-to", "extradata":":"},
	{"type":"literal", "text":": "},
	{"type":"char-to", "extradata":";"},
	{"type":"literal", "text":"; from=<"},
	{"type":"char-to", "name":"rcpt_from", "extradata":">"},
	{"type":"rest"}
	]%

#  885AEE074B: from=<tre@investici.org>, size=563, nrcpt=1 (queue active)
rule=:%[
	{"type":"literal", "text":"from=<"},
	{"type":"char-to", "name":"rcpt_from", "extradata":">"},
	{"type":"literal", "text":">, size="},
	{"type":"rest"}
	]%

prefix=
