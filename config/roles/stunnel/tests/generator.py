#!/usr/bin/env python

import yaml

ignore = ['stunnel_services', 'stunnel_version', 'stunnel_conf']

with open("defaults/main.yml", 'r') as stream:
	configs = yaml.load(stream)

with open("vars/main.yml", 'r') as stream:
	keywords = yaml.load(stream)

key_global = keywords['stunnel_global_key']
key_service = keywords['stunnel_services_key']

for k, v in configs.iteritems():
	if k in ignore:
		continue

	print "{{% if {0} is defined and {0}|string|length > 0 %}}".format(k)
	print "{{% if {0} is not string and {0} is not number %}}".format(k)
	print "{{% for item in {0} %}}".format(k)
	print "{0} = {{{{ item }}}}".format(key_global[k])
	print "{% endfor %}"
	print "{% else %}"
	print "{0} = {{{{ {1} }}}}".format(key_global[k], k)
	print "{% endif %}"


	print "{% endif %}"

service = configs['stunnel_services'][0]
service.pop("name", None)

print ""
print "{% for service in stunnel_services %}"
print "[{{ service.name }}]"
for k, v in service.iteritems():
	print "{{% if service.{0} is defined and service.{0}|string|length > 0 %}}".format(k)
	print "{{% if service.{0} is not string and service.{0} is not number %}}".format(k)
	print "{{% for item in service.{0} %}}".format(k)
	print "{0} = {{{{ item }}}}".format(key_service[k])
	print "{% endfor %}"
	print "{% else %}"
	print "{0} = {{{{ service.{1} }}}}".format(key_service[k], k)
	print "{% endif %}"

	print "{% endif %}"
print "{% endfor %}"
