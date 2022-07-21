#!/bin/sh

get_expiry() {
    local path="$1"
    local expiry="$(openssl x509 -noout -enddate -in ${path} | cut -d= -f2)"
    date --date="${expiry}" +%s
}

# Load the configuration file.
conf_file=/etc/prometheus/service_credentials_map.dat
test -e ${conf_file} || exit 0

(while read service credential role; do
     cert_path=/etc/credentials/x509/${credential}/${role}/cert.pem
     test -e "${cert_path}" || continue
     expiry=$(get_expiry "${cert_path}" 2>/dev/null)
     echo "service_credentials_expiration_time{float_service=\"${service}\",name=\"${credential}\",role=\"${role}\"} ${expiry}"
 done) < ${conf_file}

exit 0
