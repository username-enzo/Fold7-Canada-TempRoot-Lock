#!/usr/bin/env python3
"""Write the six DeviceLock constants into the app source before building.

    python tools/apply_lock.py --report analysis/SM-F966W_CP2A.260605.016.F966WVLUDCZJB.json

The upstream DFRoot source is generic; this project adds a hard firmware lock so the
exploit refuses to touch a kernel it was not reviewed for. The lock lives in
`app/src/main/java/df/root/DeviceLock.java`, which arrives through
`patches/dfroot-f966w.patch` with the reference device's values baked in.

This script rewrites those six literals to whatever `tools/analyze_firmware.py`
derived from *your* firmware. Run it after the patch is applied and before `build.sh`.

Note: an APK built with different constants is a different artifact — the SHA-256 in
docs/BUILD_RECORD.md only matches the reference device's values.
"""

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(ROOT, "src", "DFRoot",
                           "app", "src", "main", "java", "df", "root", "DeviceLock.java")

# constant name -> (Java type, regex that replaces its initialiser)
PATTERNS = {
    "MODEL": r'(static final String MODEL = )"[^"]*"(;)',
    "BUILD_ID": r'(static final String BUILD_ID = )"[^"]*"(;)',
    "BUILD_ID_SHORT": r'(static final String BUILD_ID_SHORT = )"[^"]*"(;)',
    "KERNEL_PREFIX": r'(static final String KERNEL_PREFIX =\s*)"[^"]*"(;)',
    "FINGERPRINT_PREFIX": r'(static final String FINGERPRINT_PREFIX =\s*)"[^"]*"(;)',
    "SDK_INT": r'(static final int SDK_INT = )\d+(;)',
}


def load_report(path):
    data = json.loads(io.open(path, encoding="utf-8").read())
    consts = data.get("constants")
    if not isinstance(consts, dict):
        raise SystemExit(f"{path}: no 'constants' object - run tools/analyze_firmware.py first")
    return data, consts


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", required=True, help="analysis/*.json from analyze_firmware.py")
    ap.add_argument("--file", default=DEFAULT_SRC, help=f"DeviceLock.java (default: {DEFAULT_SRC})")
    ap.add_argument("--check", action="store_true", help="only report differences, write nothing")
    args = ap.parse_args(argv[1:])

    if not os.path.isfile(args.file):
        raise SystemExit(
            f"missing {args.file}\n"
            "Apply the patch first:  git -C src/DFRoot apply - < patches/dfroot-f966w.patch")

    data, consts = load_report(args.report)
    src = io.open(args.file, encoding="utf-8").read()
    out = src
    changes = []

    for name, pattern in PATTERNS.items():
        value = consts.get(name)
        if value in (None, ""):
            print(f"warning: {name} is empty in the report; leaving it alone", file=sys.stderr)
            continue
        literal = str(int(value)) if name == "SDK_INT" else '"%s"' % value
        rx = re.compile(pattern)
        hits = rx.findall(out)
        if len(hits) != 1:
            raise SystemExit(f"{name}: expected exactly one initialiser, found {len(hits)}")
        before = rx.search(out).group(0)
        out = rx.sub(lambda mm: mm.group(1) + literal + mm.group(2), out, count=1)
        after = rx.search(out).group(0)
        if before != after:
            changes.append((name, before, after))

    print(f"report : {args.report}")
    print(f"verdict: {data.get('verdict_cn', '?')} / {data.get('verdict_en', '?')}")
    print(f"target : {args.file}")
    if not changes:
        print("constants: already identical (no-op)")
        return 0
    for name, before, after in changes:
        print(f"  {name}:\n    - {before.strip()}\n    + {after.strip()}")
    if args.check:
        print("--check: nothing written")
        return 1
    io.open(args.file, "w", encoding="utf-8", newline="\n").write(out)
    print("written. now run: bash build.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
