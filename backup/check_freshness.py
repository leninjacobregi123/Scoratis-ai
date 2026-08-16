#!/usr/bin/env python3
"""
Dead-man's switch for the offsite database backups.

Asks one question: is there a recent backup in Azure Blob Storage? That
single check covers every way backups can stop - pg_dump failing, the upload
failing, either container being dead, the SAS token expiring, the VM being
gone entirely - because all of them end with no fresh blob arriving.

The alternative, watching container logs for errors, has a hole in exactly
the case that matters most: if the VM is dead there is nothing left to write
an error, so the alert that should scream stays quiet. Absence of a good
outcome is the signal, not presence of a bad one.

This deliberately runs off the VM (GitHub Actions), for the same reason. A
checker that lives on the box it is checking dies with it.

Exits non-zero on any problem, so the calling workflow fails and GitHub
raises it. Uses a list-only SAS token: it can enumerate names, sizes and
timestamps, and can neither read a backup's contents nor write anything.
"""

import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

LIST_URL_ENV = "AZURE_BACKUP_LIST_SAS_URL"
DEFAULT_MAX_AGE_HOURS = 36.0


def fail(message):
    # ::error:: makes it show up on the workflow run itself, not just buried
    # in the step log where nobody scrolling a failure notification will look.
    print(f"::error::{message}")
    sys.exit(1)


def list_blobs(sas_url):
    """Return [(name, last_modified, size_bytes)] from the List Blobs API."""
    base, _, query = sas_url.partition("?")
    url = f"{base}?restype=container&comp=list&{query}"

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        # 403 on a list is nearly always the token having expired. Naming that
        # is the difference between a five-minute fix and a week of confusion.
        if exc.code == 403:
            fail(
                "Cannot list backups: HTTP 403. The list SAS token has most "
                "likely expired - regenerate it and update the "
                f"{LIST_URL_ENV} secret."
            )
        fail(f"Cannot list backups: HTTP {exc.code} from Azure.")
    except Exception as exc:  # noqa: BLE001 - any failure here is alert-worthy
        fail(f"Cannot reach Azure Blob Storage to check backups: {exc}")

    blobs = []
    for blob in ElementTree.fromstring(body).iter("Blob"):
        name = blob.findtext("Name") or ""
        if not name.endswith(".dump"):
            continue
        props = blob.find("Properties")
        if props is None:
            continue
        modified = props.findtext("Last-Modified")
        size = props.findtext("Content-Length") or "0"
        if modified:
            blobs.append((name, parsedate_to_datetime(modified), int(size)))

    return sorted(blobs, key=lambda b: b[1], reverse=True)


def main():
    sas_url = os.environ.get(LIST_URL_ENV, "").strip()
    if not sas_url:
        fail(f"{LIST_URL_ENV} is not set, so backup freshness cannot be checked.")

    try:
        max_age_hours = float(
            os.environ.get("MAX_AGE_HOURS", "").strip() or DEFAULT_MAX_AGE_HOURS
        )
    except ValueError:
        max_age_hours = DEFAULT_MAX_AGE_HOURS

    blobs = list_blobs(sas_url)

    if not blobs:
        fail(
            "No database backups exist in Azure at all. Offsite backup is not "
            "working - check the scoratis-backup-offsite container."
        )

    newest_name, newest_time, newest_size = blobs[0]
    age_hours = (datetime.now(timezone.utc) - newest_time).total_seconds() / 3600

    print(f"{len(blobs)} backup(s) offsite. Most recent {min(len(blobs), 5)}:")
    for name, modified, size in blobs[:5]:
        hours = (datetime.now(timezone.utc) - modified).total_seconds() / 3600
        print(f"  {name}  {size:>12,} bytes  {hours:6.1f}h old")

    # An empty dump file is a successful-looking backup of nothing, which is
    # the kind of thing you want to hear about before you need to restore it.
    if newest_size == 0:
        fail(f"The most recent backup {newest_name} is 0 bytes.")

    if age_hours > max_age_hours:
        fail(
            f"No fresh database backup. The most recent is {newest_name}, "
            f"{age_hours:.1f}h old, which exceeds the {max_age_hours:.0f}h "
            "threshold. Backups have stopped - check the scoratis-backup and "
            "scoratis-backup-offsite containers on the VM."
        )

    print(
        f"\nOK: most recent backup is {age_hours:.1f}h old "
        f"(threshold {max_age_hours:.0f}h)."
    )


if __name__ == "__main__":
    main()
