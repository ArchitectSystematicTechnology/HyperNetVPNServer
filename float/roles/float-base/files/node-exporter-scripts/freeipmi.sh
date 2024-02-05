#!/bin/sh

ipmi-sensors | awk -f /usr/lib/float/node-exporter-freeipmi.awk
