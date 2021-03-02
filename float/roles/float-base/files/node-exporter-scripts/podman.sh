#!/bin/sh

# Dump a map of container name -> image digest, to track
# container "versions".

podman ps --format='{{.Names}} {{.ImageID}}' 2>/dev/null \
| while read name image_id; do
    digest=$(podman image inspect --format='{{.Digest}}' ${image_id} 2>/dev/null | cut -d: -f2 | cut -c1-7)
    [ -z "$digest" ] && continue
    echo "container_digest{service=\"docker-${name}\",digest=\"${digest}\"} 1"
  done

exit 0
