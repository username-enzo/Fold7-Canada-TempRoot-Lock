#!/usr/bin/env bash
# Build the firmware-locked DFRoot APK with the toolchain kept inside this project.
#
#   bash build.sh                          # build with the constants already in DeviceLock.java
#   bash build.sh --lock analysis/x.json   # apply a lock report first, then build
#
# Prerequisites (run once):  bash setup_toolchain.sh
#
# What it does:
#   1. checks the local JDK / Android SDK / upstream source tree
#   2. applies patches/dfroot-f966w.patch to the upstream tree (idempotent)
#   3. extracts the native payloads from the official DFRoot release if they are missing
#   4. optionally rewrites the six DeviceLock constants from an analysis report
#   5. runs the Gradle wrapper and prints the APK path + SHA-256
#
# Overrides: TOOLCHAIN_DIR=... (where JDK/SDK live)  DFROOT_SRC=... (existing checkout)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$ROOT/toolchain}"
JDK="$TOOLCHAIN_DIR/jdk-21.0.13+9"
SDK="$TOOLCHAIN_DIR/android-sdk"
GRADLE_HOME="$TOOLCHAIN_DIR/gradle-home"
SRC="${DFROOT_SRC:-$ROOT/src/DFRoot}"
PATCH="$ROOT/patches/dfroot-f966w.patch"
LOCK=""

while [ $# -gt 0 ]; do
    case "$1" in
        --lock) LOCK="${2:-}"; [ -n "$LOCK" ] || { echo "--lock needs a path" >&2; exit 2; }; shift 2 ;;
        -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

pick_python() {
    # `python3` can be the Microsoft Store stub on Windows/Git Bash: verify it runs.
    for cand in python3 python; do
        if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys' >/dev/null 2>&1; then
            echo "$cand"
            return 0
        fi
    done
    return 1
}

PY="$(pick_python || true)"

die() { printf '[x] %s\n' "$*" >&2; exit 1; }

[ -x "$JDK/bin/java" ] || [ -f "$JDK/bin/java.exe" ] || die \
    "missing JDK: $JDK
    run: bash setup_toolchain.sh"
[ -d "$SDK/platforms/android-37.0" ] || die \
    "missing Android SDK platform: $SDK/platforms/android-37.0
    run: bash setup_toolchain.sh"
[ -d "$SRC" ] || die \
    "missing source tree: $SRC
    run: bash setup_toolchain.sh
    (it clones https://github.com/diabl0w/DFRoot at 7a6513a)"

# Our changes on top of upstream: firmware lock, on-disk diagnostics, a verdict based
# on /dev/dfm6, soft-reboot pinned off, extra menu entries. Without the patch the build
# would not be reproducible, because `src/` is not tracked here.
BASE="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo unknown)"
[ "$BASE" = "7a6513a" ] || echo "[!] src/DFRoot is at $BASE; the patch was made against 7a6513a" >&2
if [ ! -f "$SRC/app/src/main/java/df/root/DeviceLock.java" ]; then
    [ -f "$PATCH" ] || die "missing $PATCH"
    echo "[*] applying patches/dfroot-f966w.patch"
    # stdin, because `git -C <repo>` resolves a relative patch path inside <repo>
    git -C "$SRC" apply - < "$PATCH"
fi

# Native payloads, byte-identical to the official DFRoot v4.7 release
# (downloaded from upstream, never recompiled here).
# --dest is required: a relative default would write into the caller's cwd and the APK
# would end up with no lib/ directory at all (docs/BUILD_RECORD.md §11).
if [ ! -f "$SRC/app/src/main/jniLibs/arm64-v8a/libdfroot.so" ]; then
    [ -n "$PY" ] || die "python is required to extract the payloads"
    "$PY" "$ROOT/tools/extract_native_payloads.py" --dest "$SRC"
fi

if [ -n "$LOCK" ]; then
    [ -f "$LOCK" ] || die "no such report: $LOCK"
    "$PY" "$ROOT/tools/apply_lock.py" --report "$LOCK" --file \
        "$SRC/app/src/main/java/df/root/DeviceLock.java"
fi

echo
echo "[*] lock in effect:"
grep -E 'static final (String|int) (MODEL|BUILD_ID|BUILD_ID_SHORT|KERNEL_PREFIX|FINGERPRINT_PREFIX|SDK_INT) =' \
    "$SRC/app/src/main/java/df/root/DeviceLock.java" | sed 's/^ *//' | sed 's/^/    /'
echo

export JAVA_HOME="$JDK"
export ANDROID_HOME="$SDK"
export ANDROID_SDK_ROOT="$SDK"
export GRADLE_USER_HOME="$GRADLE_HOME"

cd "$SRC"
./gradlew --no-daemon :app:assembleRelease

APK="$(ls -1 app/build/outputs/apk/release/DFRoot_*.apk | head -n 1)"
echo
echo "APK: $APK"
sha256sum "$APK" 2>/dev/null || shasum -a 256 "$APK"

# A build can succeed and still be useless: without the native payloads the APK installs
# but cannot run the exploit. verify_apk.py fails loudly instead of handing over a dud,
# and also prints the content digest (the stable fingerprint - the file hash is not).
[ -n "$PY" ] || die "python is required for the post-build check"
"$PY" "$ROOT/tools/verify_apk.py" "$APK"
