#!/usr/bin/env python3
"""Self-consistency guard for hash-pinned IAASO standards documents.

A ballot pins a document by `doc_url@commit` plus a plain SHA-256 over the raw
bytes at that commit. Any byte that moves after the pin de-synchronises the
document from the register record that ratified it. Two failure modes have
already cost IAASO-0002 a re-cut each:

  * a machine-readable field asserting something the document's own prose
    denies (`version: "1.0"` under a v1.1 header; `date: 2026-07-06` under a
    change note dated 2026-08-25), and
  * a trailing newline lost in transport, so that any later editor or hook
    re-appending it changes `content_hash` with zero semantic change.

This script asserts, and never writes. It makes no git calls and derives no
value from repository history: a guard that rewrites metadata would itself be
a new way to move a `content_hash`, which is the defect it exists to prevent.
Run it locally before pushing:

    python3 .github/scripts/check_standards_metadata.py

Scope, per the intrinsic/extrinsic split adopted on IAASO-0002:

  INTRINSIC (code, title, version, date, header, footer) must be self-consistent
  with the bytes — this script checks that.

  EXTRINSIC (stage, doc_url) is governed by the IAASO register, not by the
  document. `stage` is therefore NOT checked against anything; `doc_url` is
  checked only to confirm the document does not attempt to hold it (A5).
"""

import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# A5: `doc_url` names a blob URL at a commit SHA, so writing the SHA into the
# file changes the file, the commit and the SHA. It cannot be made true from
# inside the artifact. The register is the binding record of `doc_url`; §11 is
# not. The placeholder is a fixpoint and stays a placeholder after ratification.
DOC_URL_PLACEHOLDER = "TBD — to be assigned upon ratification (placeholder)"

META_BLOCK = re.compile(
    r"^## 11\. Document Metadata\s*\n+```yaml\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)
YAML_SCALAR = re.compile(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$", re.MULTILINE)
HEADER_VERSION = re.compile(r"^\*\*Version ([0-9]+(?:\.[0-9]+)*)\*\*\s*$", re.MULTILINE)
TABLE_VERSION = re.compile(r"^\|\s*Version\s*\|\s*([0-9]+(?:\.[0-9]+)*)\s*\|\s*$", re.MULTILINE)
FOOTER_VERSION = re.compile(r"End of (IAASO-[0-9]+) v([0-9]+(?:\.[0-9]+)*)")
CHANGE_NOTE = re.compile(r"Change in v([0-9]+(?:\.[0-9]+)*)\s*\((\d{4}-\d{2}-\d{2})\)")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

failures = []


def fail(path, assertion, message):
    failures.append((path, assertion, message))


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def check_bytes(rel, data):
    """A2 — the byte sequence a content_hash is taken over must be stable."""
    if b"\r" in data:
        fail(rel, "A2", "contains a CR byte (CRLF or lone CR); a line-ending "
                        "rewrite changes content_hash with no semantic change")
    if not data.endswith(b"\n"):
        fail(rel, "A2", "does not end with a terminal newline (0a); any editor "
                        "or hook that re-appends it changes content_hash")
    elif data.endswith(b"\n\n"):
        fail(rel, "A2", "ends with more than one newline; trailing blank lines "
                        "are silently normalised by common tooling")


def check_metadata(rel, text):
    block = META_BLOCK.search(text)
    if not block:
        return  # no §11 Document Metadata block: A1/A3/A4/A5 do not apply

    meta = {k: unquote(v) for k, v in YAML_SCALAR.findall(block.group(1))}

    # --- A1: every version site in the document agrees ---------------------
    yaml_version = meta.get("version")
    if not yaml_version:
        fail(rel, "A1", "§11 Document Metadata has no `version:` field")
    sites = {}
    if yaml_version:
        sites["§11 yaml `version:`"] = yaml_version
    header = HEADER_VERSION.search(text)
    if header:
        sites["header `**Version N**`"] = header.group(1)
    else:
        fail(rel, "A1", "no `**Version N**` header line; a §11 block without a "
                        "stated header version cannot be cross-checked")
    table = TABLE_VERSION.search(text)
    if table:
        sites["header table `| Version | N |`"] = table.group(1)
    footer = FOOTER_VERSION.search(text)
    if footer:
        sites["footer `End of <code> vN`"] = footer.group(2)
        code = meta.get("code")
        if code and footer.group(1) != code:
            fail(rel, "A1", "footer names %s but §11 `code:` is %s"
                 % (footer.group(1), code))
    else:
        fail(rel, "A1", "no `End of <code> vN` footer; a §11 block without a "
                        "stated footer version cannot be cross-checked")
    distinct = set(sites.values())
    if len(distinct) > 1:
        fail(rel, "A1", "version sites disagree: "
             + "; ".join("%s = %s" % (k, v) for k, v in sorted(sites.items())))

    # --- A3: `date` is present and a real ISO-8601 calendar date -----------
    doc_date = meta.get("date")
    if not doc_date:
        fail(rel, "A3", "§11 Document Metadata has no `date:` field")
    elif not ISO_DATE.match(doc_date):
        fail(rel, "A3", "§11 `date: %s` is not ISO-8601 YYYY-MM-DD" % doc_date)
    else:
        try:
            date(*(int(p) for p in doc_date.split("-")))
        except ValueError:
            fail(rel, "A3", "§11 `date: %s` is not a real calendar date" % doc_date)

    # --- A4: `date` is the date this version's change note declares --------
    # `date` is the publication date of THIS version (SGM §8.1); stage-entry
    # dating is the §5.3 transition record's "decision date" and lives on the
    # governance chain, not here. So the in-file witness is the change note.
    notes = dict(CHANGE_NOTE.findall(text))
    if notes and yaml_version:
        if yaml_version not in notes:
            fail(rel, "A4", "declares version %s and carries change notes for "
                            "%s, but none for %s"
                 % (yaml_version, ", ".join(sorted(notes)), yaml_version))
        elif doc_date and notes[yaml_version] != doc_date:
            fail(rel, "A4", "§11 `date: %s` disagrees with the v%s change note "
                            "dated %s" % (doc_date, yaml_version, notes[yaml_version]))

    # --- A5: `doc_url` stays the literal placeholder ------------------------
    if "doc_url" in meta and meta["doc_url"] != DOC_URL_PLACEHOLDER:
        fail(rel, "A5", "§11 `doc_url` is %r; it must stay the literal "
                        "placeholder %r. doc_url is a blob URL at a commit SHA, "
                        "so writing it into the file changes the file, the "
                        "commit and the SHA. The register holds doc_url; §11 "
                        "does not." % (meta["doc_url"], DOC_URL_PLACEHOLDER))


def main():
    checked = 0
    for path in sorted(REPO.glob("**/*.md")):
        if ".github" in path.parts:
            continue
        rel = path.relative_to(REPO).as_posix()
        data = path.read_bytes()
        check_bytes(rel, data)
        check_metadata(rel, data.decode("utf-8"))
        checked += 1

    if failures:
        print("standards metadata guard: %d failure(s) across %d file(s)\n"
              % (len(failures), checked))
        for rel, assertion, message in failures:
            print("  %s [%s] %s" % (rel, assertion, message))
        print("\nA1 version sites agree · A2 byte sequence stable · A3 date "
              "present and ISO-8601 · A4 date matches the change note · A5 "
              "doc_url stays the placeholder")
        return 1

    print("standards metadata guard: %d file(s) checked, all assertions hold "
          "(A1 version sites · A2 bytes · A3 date · A4 change note · A5 doc_url)"
          % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
