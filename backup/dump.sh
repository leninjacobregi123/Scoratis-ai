#!/bin/sh
#
# Nightly database dump, written to a volume shared with the offsite uploader.
#
# The dump is written under a temp name and renamed only after pg_dump exits
# clean. A half-written dump that looks like a good one is worse than no
# backup at all, because you only find out the day you need it.
#
# Runs on the same image as the server so pg_dump always matches the server's
# major version - a mismatch there fails at restore time, not at dump time.
#
# Local retention is a rolling count. Offsite retention is a lifecycle policy
# on the storage account, not this script's job, which is why the SAS token
# the uploader uses needs no delete permission.

set -u

BACKUP_DIR=/backups
MARKERS="$BACKUP_DIR/.uploaded"
KEEP="${BACKUP_KEEP_LOCAL:-7}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

mkdir -p "$MARKERS"

while true; do
    ts=$(date -u +%Y%m%d-%H%M%S)
    tmp="$BACKUP_DIR/.in-progress.dump"

    if pg_dump -h "${POSTGRES_HOST:-postgres}" \
               -U "${POSTGRES_USER:-scoratis}" \
               -d "${POSTGRES_DB:-scoratis}" \
               -Fc -f "$tmp"; then
        mv "$tmp" "$BACKUP_DIR/scoratis-$ts.dump"
        echo "backup ok: scoratis-$ts.dump"
    else
        rm -f "$tmp"
        echo "backup FAILED at $ts" >&2
    fi

    # Prune past the retention count, taking each dump's upload marker with
    # it so the marker directory cannot grow without bound.
    #
    # Dropping a dump that never made it offsite is worth saying out loud: it
    # means the uploader has been failing for longer than the retention
    # window, and that copy is now gone for good.
    ls -1t "$BACKUP_DIR"/scoratis-*.dump 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
        name=$(basename "$old")
        if [ -n "${AZURE_BACKUP_SAS_URL:-}" ] && [ ! -e "$MARKERS/$name" ]; then
            echo "pruning $name which was NEVER uploaded offsite - check the uploader" >&2
        fi
        rm -f "$old" "$MARKERS/$name"
    done

    sleep "$INTERVAL"
done
