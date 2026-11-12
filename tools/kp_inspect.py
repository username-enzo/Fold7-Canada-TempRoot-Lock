#!/usr/bin/env python3
"""Inspect Samsung `dumpstate_lastkmsg_*_KP.log.gz` archives.

Facts learned the hard way (2026-11-12, SM-F966W / CZJB):

  * The file named `*.log.gz` is **not** gzip. Its first bytes are `PK\x03\x04`,
    i.e. it is a ZIP container. `gzip.open()` fails with
    `BadGzipFile: Not a gzipped file (b'PK')`.
  * Entries inside:
        dumpstate_lastkmsg.lst      last kernel log (2 MB, tab prefixed)
        eRR.p                       Samsung's exception record (raw)
        store_extra_info.lst        ONE LINE of "KEY":"VALUE" pairs
                                    -> RR / PANIC / PC / LR / TASK / RPM / TZ_RR
        reset_summary.html          human readable reset summary
        history_of_auto_comment.txt
        ocimem.lst                  OCRAM dump
        dumpstate_auto_comment.lst
  * `store_extra_info.lst` is the useful bit: it is a structured panic record
    (RR type, panicking TASK, PANIC text, PC/LR with module+offset, and the RPM /
    TZ reset reason). Read that first, not the 2 MB kernel log.

Usage:
    python tools/kp_inspect.py evidence/kp          # summary table only
    python tools/kp_inspect.py evidence/kp --extract evidence/kp/extracted
                                                    # also unpack the entries

No third-party deps.
"""

import io
import json
import os
import re
import sys
import zipfile

# Keys worth surfacing in the summary table, in reading order.
FIELDS = ["RR", "RWC", "TASK", "PANIC", "PC", "LR", "RPM", "TZ_RR", "FAULT", "BUG"]

ENTRY_LASTKMSG = "dumpstate_lastkmsg.lst"
ENTRY_EXTRA = "store_extra_info.lst"
ENTRY_ERR = "eRR.p"
ENTRY_RESET = "reset_summary.html"

# Signature lines that mean "the kernel died here".
SIGS = [
    "Unable to handle kernel",
    "Internal error",
    "Kernel panic",
    "Oops",
    "BUG:",
    "Call trace",
    "Synchronous External Abort",
    "watchdog",
    "WDT",
]


def parse_extra(raw: bytes) -> dict:
    """`store_extra_info.lst` is a single JSON-ish line: {"K":"V","K2":"V2"}."""
    text = raw.decode("utf-8", "replace").strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    # fallback: flat regex, tolerant of unescaped quotes inside values
    out = {}
    for m in re.finditer(r'"([A-Z0-9_]+)":"(.*?)"(?=,|\})', text, re.S):
        out[m.group(1)] = m.group(2)
    return out


def analyze(path: str):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        extra = parse_extra(z.read(ENTRY_EXTRA)) if ENTRY_EXTRA in names else {}
        last = z.read(ENTRY_LASTKMSG).decode("utf-8", "replace") if ENTRY_LASTKMSG in names else ""
    return names, extra, last


def hits(last: str):
    lines = last.splitlines()
    found = []
    for i, line in enumerate(lines):
        if any(s in line for s in SIGS):
            found.append((i, line))
    return lines, found


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = argv[1]
    extract = None
    if "--extract" in argv:
        extract = argv[argv.index("--extract") + 1]

    paths = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for f in sorted(filenames):
            if f.endswith(".gz"):
                paths.append(os.path.join(dirpath, f))
    if not paths:
        print(f"no *.gz under {root}")
        return 1

    rows = []
    for p in paths:
        names, extra, last = analyze(p)
        rows.append((p, extra, last, names))

    width = max(len(os.path.basename(r[0])) for r in rows)
    print("=" * 100)
    print("summary from store_extra_info.lst  (RR=KP means the *previous* boot died)")
    print("=" * 100)
    for p, extra, _last, _names in rows:
        print(os.path.basename(p).ljust(width))
        for k in FIELDS:
            v = extra.get(k, "")
            if not v:
                continue
            if len(v) > 300:
                v = v[:300] + " ..."
            print(f"    {k:<6} {v}")
        lk = extra.get("LKL", "")
        if lk:
            print(f"    LKL    (last kernel log, {len(lk)} B) tail:")
            for line in lk[-600:].replace("\\n", "\n").splitlines()[-3:]:
                print(f"           {line.strip()[:200]}")
        print()

    print("=" * 100)
    print("panic signatures inside dumpstate_lastkmsg.lst")
    print("=" * 100)
    for p, _extra, last, _names in rows:
        lines, found = hits(last)
        print(f"\n### {os.path.basename(p)}  ({len(lines)} lines)")
        if not found:
            print("    no signature hit")
            continue
        for i, line in found[:12]:
            print(f"    [{i}] {line.strip()[:220]}")
        if len(found) > 12:
            print(f"    ... {len(found) - 12} more")

    if extract:
        for p, _extra, _last, names in rows:
            tag = re.search(r"lastkmsg_(\d+)_", os.path.basename(p))
            tag = tag.group(1) if tag else os.path.basename(p)[:20]
            outdir = os.path.join(extract, tag)
            os.makedirs(outdir, exist_ok=True)
            with zipfile.ZipFile(p) as z:
                for n in names:
                    with open(os.path.join(outdir, os.path.basename(n)), "wb") as fh:
                        fh.write(z.read(n))
            print(f"extracted -> {outdir}  ({len(names)} entries)")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv))
