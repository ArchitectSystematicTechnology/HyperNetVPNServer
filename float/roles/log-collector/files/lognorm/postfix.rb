version=2

# liblognorm2 rules for Postfix logs

# use with 'useRawMsg on'.

prefix=%[ {"type":"date-rfc5424", "name":"date"},
          {"type":"literal", "text":" "},
          {"type":"word", "name":"host"},
          {"type":"literal", "text":" "},
          {"type":"char-to", "name":"postfix_instance", "extradata":"/"},
          {"type":"literal", "text":"/"},
          {"type":"char-to", "name":"program", "extradata":"["},
          {"type":"literal", "text":"["},
          {"type":"number", "name":"pid"},
          {"type":"literal", "text":"]: "},
          {"type":"string-to", "name":"postfix_queue_id", "extradata":": "},
          {"type":"literal", "text":": "},
        ]%

# Test matching simple Postfix lines.
# {"type":"@postfix_queue_id", "name":"postfix_queue_id"},
rule=:%[
         {"type":"rest", "name":"message"},
      ]%


prefix=
