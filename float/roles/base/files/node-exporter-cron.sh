#!/bin/sh
#
# Periodically execute scripts in
# /etc/prometheus/node-exporter-scripts and dump their output where
# the node-exporter textfile module can read it.
#

script_dir="${1:-/etc/prometheus/node-exporter-scripts}"
output_dir="/var/lib/prometheus/node-exporter"

test -d $script_dir || exit 0

umask 022
for s in "${script_dir}/"* ; do
    test -x "$s" || continue
    script_name=$(basename "$s" | sed -e 's/\.[a-z]*$//')
    outfile="${output_dir}/${script_name}.prom"
    "$s" > "${outfile}.$$"
    if [ $? -gt 0 ]; then
        rm -f "${outfile}.$$"
        continue
    fi
    mv "${outfile}.$$" "${outfile}"
done

exit 0
