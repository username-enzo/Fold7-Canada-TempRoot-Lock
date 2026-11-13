#!/usr/bin/env python3
"""Verify a DFRoot lock APK, the way a rebuild actually can be verified.

    python tools/verify_apk.py src/DFRoot/app/build/outputs/apk/release/DFRoot_*.apk

Why this tool exists: **the APK file's own SHA-256 is not reproducible.** The zip entries
are byte-identical between rebuilds, but the APK Signing Block contains a randomised
signature, so signing the same content twice yields two different files. Measured on
three independent builds (see docs/BUILD_RECORD.md §7.6):

    2a2b59f7…  4824a51a…  7d493b7b…     <- same content, three file hashes

What *is* stable is the content: the set of zip entries with their sizes and CRC-32s.
`--digest` prints that as a single value, and `--expect-digest` compares it. Together
with the payload SHA-256s below, that is what "did I build the same thing?" should mean.

Checks performed:
  1. both native payloads are present and byte-identical to official DFRoot v4.7
  2. the firmware-lock strings really are in classes.dex (the patch took effect)
  3. a content digest over (name, crc32, size) of every zip entry, comparable to a record
  4. the file's own SHA-256, printed with a reminder that it varies per build
"""

import argparse
import hashlib
import sys
import zipfile

# Measured from the official DFRoot v4.7 release; see docs/DELIVERY.md §8.
PAYLOADS = {
    "lib/arm64-v8a/libdfroot.so": "1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db",
    "lib/arm64-v8a/libbootstrap.so": "654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236",
}

# Strings the patch adds; any of them missing means the patch was not applied.
PATCH_MARKERS = [b"PROFILE LOCK", b"Markers now", b"Run log", b"diag.log",
                 b"ksud late-load EXITED", b"Auto Soft Reboot", b"SM-F966W"]


def entry_digest(zf):
    lines = "".join(f"{i.filename}\t{i.CRC:08x}\t{i.file_size}\n" for i in zf.infolist())
    return hashlib.sha256(lines.encode()).hexdigest()


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("apk")
    ap.add_argument("--expect-digest", help="content digest recorded in docs/BUILD_RECORD.md §7.6")
    args = ap.parse_args(argv[1:])

    zf = zipfile.ZipFile(args.apk)
    names = set(zf.namelist())
    ok = True

    print(f"apk            : {args.apk}")
    print(f"entries        : {len(names)}")
    print(f"content digest : {entry_digest(zf)}")

    print("\nnative payloads (must be byte-identical to official DFRoot v4.7):")
    for name, want in PAYLOADS.items():
        if name not in names:
            print(f"  {name}\n    MISSING  <-- the APK cannot run the exploit")
            ok = False
            continue
        got = hashlib.sha256(zf.read(name)).hexdigest()
        status = "ok" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  {name}\n    {got}  {status}")

    print("\npatch markers in classes.dex:")
    dex = zf.read("classes.dex") if "classes.dex" in names else b""
    for marker in PATCH_MARKERS:
        n = dex.count(marker)
        print(f"  {marker.decode(errors='replace'):16s} {n}")
        if n == 0:
            ok = False

    print("\nfile sha256    :", hashlib.sha256(open(args.apk, "rb").read()).hexdigest())
    print("  note: this value differs between rebuilds even with identical content,")
    print("        because the signing block carries a randomised signature.")

    if args.expect_digest:
        got = entry_digest(zf)
        match = got == args.expect_digest
        print(f"\nexpected digest: {args.expect_digest}  {'MATCH' if match else 'DIFFERENT'}")
        if not match:
            ok = False

    print("\nVERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
