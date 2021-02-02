#!/bin/bash

#!/usr/bin/env bash
set -eu

for MD_DEVICE in /dev/md/*; do
  # Subshell to avoid eval'd variables from leaking between iterations
  (
    # Resolve symlink to discover device, e.g. /dev/md127
    MD_DEVICE_NUM=$(readlink -f "${MD_DEVICE}")

    # Remove /dev/ prefix
    MD_DEVICE_NUM=${MD_DEVICE_NUM#/dev/}
    MD_DEVICE=${MD_DEVICE#/dev/md/}

    # Query sysfs for info about md device
    SYSFS_BASE="/sys/devices/virtual/block/${MD_DEVICE_NUM}/md"
    MD_LAYOUT=$(cat "${SYSFS_BASE}/layout")
    MD_LEVEL=$(cat "${SYSFS_BASE}/level")
    MD_METADATA_VERSION=$(cat "${SYSFS_BASE}/metadata_version")
    MD_NUM_RAID_DISKS=$(cat "${SYSFS_BASE}/raid_disks")

    # Remove 'raid' prefix from RAID level
    MD_LEVEL=${MD_LEVEL#raid}

    # Output RAID array informational metric.
    # NOTE: Metadata version is a label rather than a separate metric because the version can be a string
    echo "node_md_info{md_device=\"${MD_DEVICE_NUM}\", md_name=\"${MD_DEVICE}\", raid_level=\"${MD_LEVEL}\", md_metadata_version=\"${MD_METADATA_VERSION}\"} 1"

    # Fetch sync state and metrics.
    SYNC_STATE=$(cat "${SYSFS_BASE}/sync_action")
    echo "node_md_sync_state{md_device=\"${MD_DEVICE_NUM}\",sync_state=\"${SYNC_STATE}\"} 1"
    SYNC_SPEED=$(cat "${SYSFS_BASE}/sync_speed")
    if [ "$SYNC_SPEED" = "none" ]; then
        SYNC_SPEED=0
    fi
    echo "node_md_sync_speed{md_device=\"${MD_DEVICE_NUM}\"} ${SYNC_SPEED}"

    DEGRADED=$(cat "${SYSFS_BASE}/degraded")
    echo "node_md_degraded{md_device=\"${MD_DEVICE_NUM}\"} ${DEGRADED}"
  )
done
