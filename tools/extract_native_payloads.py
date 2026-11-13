#!/usr/bin/env python3
"""Extract the native exploit payloads used by the F966W/CZJB lock build.

Source: official DFRoot v4.7 APK (upstream release, signed by diabl0w).

  https://github.com/diabl0w/DFRoot/releases/download/v4.7/DFRoot_4.7.apk
  sha256 9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1

Both the source APK and the two extracted .so files are hash-checked against the
values recorded in docs/DELIVERY.md, so a silently re-uploaded upstream release
cannot slip into the build unnoticed.

Outputs:
  app/src/main/jniLibs/arm64-v8a/libdfroot.so
  app/src/main/jniLibs/arm64-v8a/libbootstrap.so
  build_logs/embedded-ko/dfroot-<kmi>.ko   (for hash auditing only; not used by the build)

The APK is repackaged from DFRoot source with a Java-side firmware lock; the
native exploit code and the KMI kernel modules are shipped byte-identical to
the upstream v4.7 release. This script exists so that claim is reproducible.
"""
import hashlib
import os
import struct
import sys
import urllib.request
import zipfile

APK_URL = "https://github.com/diabl0w/DFRoot/releases/download/v4.7/DFRoot_4.7.apk"
APK_SHA256 = "9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1"

# Measured from the official v4.7 release; see docs/DELIVERY.md §8.
LIB_SHA256 = {
    "libdfroot.so": "1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db",
    "libbootstrap.so": "654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236",
}

KMIS = [
    "android12-5.10", "android13-5.10", "android13-5.15", "android14-5.15",
    "android14-6.1", "android15-6.6", "android16-6.12", "android17-6.18",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_kos(blob: bytes):
    """The KOs are .incbin'd back to back into libdfroot.so's .rodata."""
    out, pos, index = [], 0, 0
    while index < len(KMIS):
        off = blob.find(b"\x7fELF\x02\x01\x01", pos)
        if off < 0:
            break
        e_type = struct.unpack_from("<H", blob, off + 16)[0]
        if e_type != 1:  # ET_REL only; offset 0 is the .so itself (ET_DYN)
            pos = off + 4
            continue
        e_shoff = struct.unpack_from("<Q", blob, off + 0x28)[0]
        e_shentsize = struct.unpack_from("<H", blob, off + 0x3A)[0]
        e_shnum = struct.unpack_from("<H", blob, off + 0x3C)[0]
        end = off + e_shoff + e_shentsize * e_shnum
        if e_shoff and e_shnum and end <= len(blob):
            out.append((KMIS[index], blob[off:end]))
            index += 1
            pos = end
        else:
            pos = off + 4
    return out


def main(argv=None) -> int:
    # Everything is written *under* --dest (the DFRoot source root), never relative to
    # the caller's cwd. Getting this wrong produces an APK with no lib/ directory at
    # all, which installs and then cannot run the exploit - see docs/BUILD_RECORD.md §11.
    argv = sys.argv[1:] if argv is None else argv
    dest_root = "."
    if "--dest" in argv:
        dest_root = argv[argv.index("--dest") + 1]
    dest_root = os.path.abspath(dest_root)
    dest_lib = os.path.join(dest_root, "app/src/main/jniLibs/arm64-v8a")
    dest_ko = os.path.join(dest_root, "build_logs/embedded-ko")
    os.makedirs(dest_lib, exist_ok=True)
    os.makedirs(dest_ko, exist_ok=True)
    print("destination root:", dest_root)

    apk = os.path.join(dest_root, "build_logs/DFRoot_4.7.apk")
    if not os.path.exists(apk):
        print("downloading", APK_URL)
        urllib.request.urlretrieve(APK_URL, apk)
    data = open(apk, "rb").read()
    digest = sha256(data)
    print("source apk", apk, len(data), digest)
    if APK_SHA256 and digest != APK_SHA256:
        print("WARNING: source APK hash differs from the value recorded in this script")

    zf = zipfile.ZipFile(apk)
    for name in ("lib/arm64-v8a/libdfroot.so", "lib/arm64-v8a/libbootstrap.so"):
        blob = zf.read(name)
        out = os.path.join(dest_lib, os.path.basename(name))
        open(out, "wb").write(blob)
        got = sha256(blob)
        print(f"{out}  {len(blob)}  {got}")
        want = LIB_SHA256.get(os.path.basename(name))
        if want and got != want:
            print(f"ERROR: {name} is not the reviewed binary "
                  f"(expected {want})", file=sys.stderr)
            return 1

    libdfroot = zf.read("lib/arm64-v8a/libdfroot.so")
    for kmi, ko in find_kos(libdfroot):
        out = os.path.join(dest_ko, f"dfroot-{kmi}.ko")
        open(out, "wb").write(ko)
        print(f"{out}  {len(ko)}  {sha256(ko)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
