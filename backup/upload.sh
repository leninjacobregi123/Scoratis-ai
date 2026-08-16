#!/bin/sh
#
# Ships local dumps to Azure Blob Storage so a lost VM does not mean lost data.
#
# Split from dump.sh because pg_dump and curl do not exist in the same
# prebuilt image, and installing packages at image build time makes the
# backup path depend on a package mirror being up - a bad trade for the one
# component whose entire job is to work on the worst day.
#
# Work is driven off marker files, not "upload what was just dumped". A dump
# whose upload failed is retried on the next pass instead of being silently
# stranded on the VM, which is the failure that matters: a transient network
# blip is exactly when you least want the offsite copy to quietly stop.
#
# Without AZURE_BACKUP_SAS_URL this exits immediately rather than spinning -
# local-only backups are a legitimate dev setup, not an error.

set -u

BACKUP_DIR=/backups
MARKERS="$BACKUP_DIR/.uploaded"
INTERVAL="${UPLOAD_INTERVAL_SECONDS:-3600}"

if [ -z "${AZURE_BACKUP_SAS_URL:-}" ]; then
    echo "AZURE_BACKUP_SAS_URL not set - offsite backup disabled, local dumps only"
    exit 0
fi

mkdir -p "$MARKERS"

# The SAS URL carries its signature in the query string, so the blob name has
# to go between the container path and the query - not appended to the end.
BASE=$(echo "$AZURE_BACKUP_SAS_URL" | cut -d'?' -f1)
QUERY=$(echo "$AZURE_BACKUP_SAS_URL" | cut -d'?' -f2-)

# --upload-file streams; --data-binary would read the whole dump into memory,
# which this container is not sized for and would start failing exactly when
# the database has grown big enough for the backup to matter.
#
# The URL is never echoed: it contains the signature, and container logs are
# not a secret store.
upload() {
    file="$1"
    name=$(basename "$file")

    code=$(curl -sS -o /dev/null -w '%{http_code}' \
        --max-time 900 \
        -H 'x-ms-blob-type: BlockBlob' \
        -H 'Content-Type: application/octet-stream' \
        --upload-file "$file" \
        "$BASE/$name?$QUERY" 2>/dev/null)

    if [ "$code" = "201" ]; then
        touch "$MARKERS/$name"
        echo "offsite ok: $name"
        return 0
    fi

    # 403 is nearly always an expired token rather than anything transient.
    # Saying which is the difference between someone fixing it this week and
    # discovering months later that nothing has left the box since spring.
    if [ "$code" = "403" ]; then
        echo "offsite FAILED: $name (HTTP 403 - SAS token expired, or wrong permissions)" >&2
    else
        echo "offsite FAILED: $name (HTTP $code)" >&2
    fi
    return 1
}

while true; do
    for f in "$BACKUP_DIR"/scoratis-*.dump; do
        [ -e "$f" ] || continue
        [ -e "$MARKERS/$(basename "$f")" ] && continue
        upload "$f" || true
    done
    sleep "$INTERVAL"
done
