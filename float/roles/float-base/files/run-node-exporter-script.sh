#!/bin/sh
#
# Execute a metrics-generating script and safely write its
# output to the /var/lib/prometheus/node-exporter directory.
#
# Uses 'runcron' for locking, so don't wrap it in another
# 'runcron' invocation!
#

if [ $# -ne 2 ]; then
    echo "Usage: $0 <snippet-name> <script-path>"
    exit 2
fi

script_name="$1"
script_path="$2"
output_dir="/var/lib/prometheus/node-exporter"

test -d $output_dir || exit 0

umask 022

output_file="${output_dir}/${script_name}.prom"
tmp_file="${output_file}.$$"
trap "rm -f $tmp_file 2>/dev/null" EXIT INT TERM

runcron --no-syslog --no-metrics --splay 60 --name "node-exporter-$script_name" -- \
        "$script_path" > "$tmp_file"
if [ $? -gt 0 ]; then
    rm -f "$tmp_file" 2>/dev/null
    exit 1
else
    mv -f "$tmp_file" "$output_file"
fi

exit $?
