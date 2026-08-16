#!/bin/sh
#
# Nightly database backup, local and offsite.
#
# Each cycle does three things in order: dump, ship offsite, prune locally.
#
# The dump is written under a temp name and renamed only after pg_dump exits
# clean. A half-written dump that looks like a good one is worse than no
# backup at all, because you only discover it the day you need it.
#
# Upload is driven off marker files rather than "upload whatever we just
# dumped", so a dump whose upload failed is retried on the next cycle instead
# of being silently stranded on the VM. That is the case that matters - a
# transient network blip is exactly when you least want the offsite copy to
# quietly stop happening.
#
# Local retention is 7 days. Offsite retention is NOT handled here: it is a
# lifecycle policy on the storage account. That is deliberate, and it is why
# the SAS token this uses has no delete permission - a VM that gets
# compromised can add backups but cannot destroy the history.

set -u

BACKUP_DIR=/backups
MARKERS="$BACKUP_DIR/.uploaded"
KEEP="${BACKUP_KEEP_LOCAL:-7}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

PGHOST_="${POSTGRES_HOST:-postgres}"
PGUSER_="${POSTGRES_USER:-scoratis}"
PGDB_="${POSTGRES_DB:-scoratis}"

mkdir -p "$MARKERS"

# Ship one dump to Azure Blob Storage.
#
# --upload-file streams the file; --data-binary would read the whole dump into
# memory, which this container is not sized for and would fail exactly when
# the database has grown enough to matter.
#
# The SAS URL is never echoed - it carries the signature, and container logs
# are not a secret store.
upload() {
    file="$1"
    name=$(basename "$file")

    if [ -z "${AZURE_BACKUP_SAS_URL:-}" ]; then
        return 1
    fi

    base=$(echo "$AZURE_BACKUP_SAS_URL" | cut -d'?' -f1)
    query=$(echo "$AZURE_BACKUP_SAS_URL" | cut -d'?' -f2-)

    code=$(curl -sS -o /dev/null -w '%{http_code}' \
        --max-time 900 \
        -H 'x-ms-blob-type: BlockBlob' \
        -H 'Content-Type: application/octet-stream' \
        --upload-file "$file" \
        "$base/$name?$query" 2>/dev/null)

    if [ "$code" = "201" ]; then
        touch "$MARKERS/$name"
        echo "offsite ok: $name"
        return 0
    fi

    # 403 here almost always means the SAS token expired rather than anything
    # transient, so say so - the generic "it failed" version of this message
    # has cost people their offsite copies for months without anyone noticing.
    if [ "$code" = "403" ]; then
        echo "offsite FAILED: $name (HTTP 403 - SAS token expired or wrong permissions)" >&2
    else
        echo "offsite FAILED: $name (HTTP $code)" >&2
    fi
    return 1
}

while true; do
    ts=$(date -u +%Y%m%d-%H%M%S)
    tmp="$BACKUP_DIR/.in-progress.dump"

    if pg_dump -h "$PGHOST_" -U "$PGUSER_" -d "$PGDB_" -Fc -f "$tmp"; then
        mv "$tmp" "$BACKUP_DIR/scoratis-$ts.dump"
        echo "backup ok: scoratis-$ts.dump"
    else
        rm -f "$tmp"
        echo "backup FAILED at $ts" >&2
    fi

    if [ -n "${AZURE_BACKUP_SAS_URL:-}" ]; then
        for f in "$BACKUP_DIR"/scoratis-*.dump; do
            [ -e "$f" ] || continue
            [ -e "$MARKERS/$(basename "$f")" ] && continue
            upload "$f" || true
        done
    else
        echo "offsite skipped: AZURE_BACKUP_SAS_URL not set (local backups only)"
    fi

    # Prune local dumps past the retention count, and their markers with them
    # so the marker directory cannot grow without bound.
    ls -1t "$BACKUP_DIR"/scoratis-*.dump 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
        rm -f "$old" "$MARKERS/$(basename "$old")"
    done

    sleep "$INTERVAL"
done
