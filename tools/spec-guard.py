#!/usr/bin/env python3
"""Intrinsic-consistency guard for the IAASO specification documents.

Every document in this repository is hash-pinned: a ballot on the IAASO
register pins ``doc_url@<commit>`` together with the ``content_hash`` of the
bytes at that commit.  A pinned hash is only as good as the bytes it names, so
any edit to a published document is a governance event, not a typo fix.  This
guard checks the properties that a document must satisfy *against its own
bytes* -- the class of defect that cost IAASO-0002 four re-cuts in a single
day, each one a fresh content_hash.

Scope -- INTRINSIC fields only
------------------------------
An INTRINSIC field is one the document asserts about itself (code, title,
version, date, header, footer).  A mismatch between two of them is a
self-contradiction inside frozen bytes, and is BLOCKING.

An EXTRINSIC field is a snapshot of state that lives outside the document
(``stage``, ``supersedes``, and the register row generally).  Frozen,
hash-pinned bytes structurally cannot track external state, so a disagreement
there is NOT a defect and this guard deliberately does not test for it.
``stage: proposed`` inside a document whose register row later reads
``published`` is correct behaviour, not drift.

``doc_url`` is the one apparent exception, and it is not one: because
``doc_url`` is a blob URL containing the commit SHA of the very bytes that
carry it, writing a real URL into the field changes the SHA the field names.
It is a fixpoint, so it must stay a placeholder forever -- an intrinsic rule.

What this guard must never do
-----------------------------
It must never *rewrite* metadata, and in particular must never derive ``date``
from git history.  A guard that edits a document is a new way to move a
content_hash -- the exact defect it exists to prevent.  This script is
read-only and reports; it does not fix.

Run locally before committing:  python3 tools/spec-guard.py
"""

from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADER_VERSION = re.compile(r"^\*\*Version\s+(\S+)\*\*\s*$", re.M)
TABLE_VERSION = re.compile(r"^\|\s*Version\s*\|\s*(\S+?)\s*\|\s*$", re.M)
FOOTER = re.compile(
    r"^\*End of (IAASO-\d{4}) v([0-9]+(?:\.[0-9]+)*)(?:\s*\([^)]*\))?\.\*\s*$", re.M
)
META_HEADING = re.compile(r"^##\s+\d+\.\s+Document Metadata\s*$", re.M)
FENCE = re.compile(r"^```yaml\s*$(.*?)^```\s*$", re.M | re.S)

failures: list[str] = []
notes: list[str] = []


def fail(path: str, msg: str) -> None:
    failures.append(f"{path}: {msg}")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True, text=True
    ).stdout
    return [p for p in out.split("\0") if p]


def top_level_yaml(block: str) -> dict[str, str]:
    """Parse the top-level ``key: value`` pairs of a small YAML block.

    Deliberately not a YAML parser: only unindented scalar keys are read, which
    is all the metadata block asserts about itself.  Nested mappings are
    ignored rather than guessed at.
    """
    out: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0] in " \t#":
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def check_terminal_newline(path: str) -> None:
    with open(path, "rb") as fh:
        data = fh.read()
    if not data:
        fail(path, "file is empty")
        return
    if b"\0" in data[:8192]:
        notes.append(f"{path}: binary, terminal-newline check skipped")
        return
    if data[-1:] != b"\n":
        fail(
            path,
            "does not end with a newline (0a). A stripped trailing newline "
            "silently changes the content_hash of a pinned document.",
        )


def check_intrinsic_metadata(path: str) -> None:
    """A document carrying ANY intrinsic version marker must carry them all.

    Self-arming on purpose: this is what makes deleting a marker a failure
    rather than a silent pass.
    """
    text = open(path, encoding="utf-8").read()

    header = HEADER_VERSION.search(text)
    table = TABLE_VERSION.search(text)
    footer = FOOTER.search(text)
    heading = META_HEADING.search(text)

    if not any((header, table, footer, heading)):
        notes.append(f"{path}: no intrinsic version markers, not a metadata-bearing document")
        return

    present = {
        "header '**Version X**'": bool(header),
        "'| Version | X |' table row": bool(table),
        "'*End of ... vX.*' footer": bool(footer),
        "'## N. Document Metadata' block": bool(heading),
    }
    missing = [name for name, ok in present.items() if not ok]
    if missing:
        fail(path, "carries some intrinsic version markers but is missing: " + ", ".join(missing))
        return

    block = FENCE.search(text, heading.end())
    if not block:
        fail(path, "'## N. Document Metadata' is not followed by a ```yaml block")
        return
    meta = top_level_yaml(block.group(1))

    # -- version agreement: header == table == metadata == footer ------------
    versions = {
        "header": header.group(1),
        "table row": table.group(1),
        "metadata version": meta.get("version", "<absent>"),
        "footer": footer.group(2),
    }
    if len(set(versions.values())) != 1:
        fail(
            path,
            "version disagreement across intrinsic fields: "
            + ", ".join(f"{k}={v!r}" for k, v in versions.items()),
        )

    # -- code agreement: footer vs metadata ----------------------------------
    code = meta.get("code")
    if code and code != footer.group(1):
        fail(path, f"metadata code {code!r} does not match footer code {footer.group(1)!r}")

    # -- date: present, ISO-8601, real ---------------------------------------
    date = meta.get("date")
    if not date:
        fail(path, "metadata block has no 'date'")
    elif not ISO_DATE.match(date):
        fail(path, f"metadata date {date!r} is not ISO-8601 YYYY-MM-DD")
    else:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            fail(path, f"metadata date {date!r} is not a real calendar date")

    # -- doc_url: a fixpoint, so it must stay a placeholder ------------------
    doc_url = meta.get("doc_url")
    if doc_url is None:
        fail(path, "metadata block has no 'doc_url'")
    elif "://" in doc_url:
        fail(
            path,
            f"metadata doc_url {doc_url!r} is a real URL. doc_url names the "
            "commit that carries these bytes, so writing it in changes the "
            "SHA it names. It must remain a placeholder.",
        )
    elif "TBD" not in doc_url:
        fail(path, f"metadata doc_url {doc_url!r} is not the TBD placeholder")


def main() -> int:
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
    ).stdout.strip()
    os.chdir(root)

    files = tracked_files()
    for path in files:
        if not os.path.isfile(path):
            continue
        check_terminal_newline(path)

    for path in files:
        if path.endswith(".md") and os.path.isfile(path):
            check_intrinsic_metadata(path)

    for note in notes:
        print(f"note: {note}")
    print(f"checked {len(files)} tracked files")

    if failures:
        print()
        print(f"FAIL — {len(failures)} intrinsic-consistency problem(s):")
        for f in failures:
            print(f"  - {f}")
        print()
        print(
            "These documents are hash-pinned on the IAASO register. Fix the "
            "document, do not adjust the pin."
        )
        return 1

    print("OK — intrinsic metadata is self-consistent in every checked document")
    return 0


if __name__ == "__main__":
    sys.exit(main())
