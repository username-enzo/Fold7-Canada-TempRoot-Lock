#!/usr/bin/env bash
# One-time setup: JDK 21 + Android SDK + upstream DFRoot source, all inside this
# project folder. Nothing is installed system-wide.
#
#   bash setup_toolchain.sh            # do it (idempotent; safe to re-run)
#   bash setup_toolchain.sh --check    # only report what is present / missing
#   bash setup_toolchain.sh --dry-run  # print what would be downloaded
#
# Everything lands in:
#   toolchain/jdk-21.0.13+9/     JDK (Temurin)
#   toolchain/android-sdk/       platform 37.0, build-tools 37.0.0, platform-tools, adb
#   toolchain/gradle-home/       Gradle user home (the wrapper fills it on first build)
#   src/DFRoot/                  upstream DFRoot at the commit the patch is based on
#
# Overrides (for people who already have these elsewhere):
#   TOOLCHAIN_DIR=...  DFROOT_SRC=...  CMDLINE_TOOLS_ZIP=...
#
# This is the only step that needs network access. Versions are pinned because the
# documentation quotes hashes produced with exactly these versions; a different JDK
# or AGP can change the APK bytes (see docs/BUILD_RECORD.md §7).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$ROOT/toolchain}"
JDK_VERSION="21.0.13+9"
JDK_DIR="$TOOLCHAIN_DIR/jdk-$JDK_VERSION"
SDK="$TOOLCHAIN_DIR/android-sdk"
find_sdkmanager() {
    # accept both the canonical layout and an extra `cmdline-tools/` nesting level
    # (some archives and some people's existing SDKs end up either way)
    ls "$SDK"/cmdline-tools/latest/bin/sdkmanager*        "$SDK"/cmdline-tools/*/cmdline-tools/bin/sdkmanager* 2>/dev/null | head -n1
}
CMDLINE_TOOLS_BUILD="16111833"
SDK_PACKAGES=("platforms;android-37.0" "build-tools;37.0.0" "platform-tools")
SRC="${DFROOT_SRC:-$ROOT/src/DFRoot}"
DFROOT_REPO="https://github.com/diabl0w/DFRoot.git"
DFROOT_COMMIT="7a6513a69ce4c1a90b68d857c26347bf166ffe10"
PATCH="$ROOT/patches/dfroot-f966w.patch"

MODE=setup
for arg in "$@"; do
    case "$arg" in
        --check)   MODE=check ;;
        --dry-run) MODE=dry ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

say()  { printf '[*] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }
die()  { printf '[x] %s\n' "$*" >&2; exit 1; }

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
[ -n "$PY" ] || die "python3 is required (used for unzipping and by the build scripts)"

case "$(uname -s)" in
    Linux*)                     HOST=linux ;;
    Darwin*)                    HOST=mac ;;
    MINGW*|MSYS*|CYGWIN*)       HOST=windows ;;
    *)                          die "unsupported host: $(uname -s)" ;;
esac

case "$(uname -m)" in
    x86_64|amd64)   ARCH=x64 ;;
    aarch64|arm64)  ARCH=aarch64 ;;
    *)              die "unsupported arch: $(uname -m)" ;;
esac

JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-${JDK_VERSION/+/%2B}/${HOST}/${ARCH}/jdk/hotspot/normal/eclipse"
JDK_URL_FALLBACK="https://api.adoptium.net/v3/binary/latest/21/ga/${HOST}/${ARCH}/jdk/hotspot/normal/eclipse"
CMDLINE_TOOLS_OS=linux
[ "$HOST" = mac ] && CMDLINE_TOOLS_OS=mac
[ "$HOST" = windows ] && CMDLINE_TOOLS_OS=win
CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-${CMDLINE_TOOLS_OS}-${CMDLINE_TOOLS_BUILD}_latest.zip"

have_jdk()  { [ -x "$JDK_DIR/bin/java" ] || [ -x "$JDK_DIR/bin/java.exe" ]; }
have_sdk()  { [ -n "$(find_sdkmanager)" ]; }
have_plat() { [ -d "$SDK/platforms/android-37.0" ] && [ -d "$SDK/build-tools/37.0.0" ]; }
have_src()  { [ -d "$SRC/.git" ]; }

report() {
    printf '\n%-28s %s\n' "JDK ($JDK_VERSION)"   "$(have_jdk  && echo present || echo MISSING)"
    printf '%-28s %s\n' "cmdline-tools"          "$(have_sdk  && echo present || echo MISSING)"
    printf '%-28s %s\n' "platform 37.0 / bt 37"  "$(have_plat && echo present || echo MISSING)"
    printf '%-28s %s\n' "src/DFRoot"             "$(have_src  && echo present || echo MISSING)"
    printf '%-28s %s\n' "patched source"         "$([ -f "$SRC/app/src/main/java/df/root/DeviceLock.java" ] && echo yes || echo no)"
    printf '\n'
}

fetch() { # fetch <url> <destfile>
    if command -v curl >/dev/null 2>&1; then
        curl -fL --retry 3 --connect-timeout 20 -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$2" "$1"
    else
        die "need curl or wget"
    fi
}

unpack() { # unpack <archive> <destdir>
    case "$1" in
        *.zip) "$PY" - "$1" "$2" <<'PYEOF'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
PYEOF
        ;;
        *.tar.gz|*.tgz) tar -xzf "$1" -C "$2" ;;
        *) die "unsupported archive: $1" ;;
    esac
}

if [ "$MODE" != setup ]; then report; [ "$MODE" = check ] && exit 0; fi

if [ "$MODE" != dry ]; then
    mkdir -p "$TOOLCHAIN_DIR/dl" "$SDK" "$TOOLCHAIN_DIR/gradle-home"
fi

if ! have_jdk; then
    ext=tar.gz; [ "$HOST" = windows ] && ext=zip
    out="$TOOLCHAIN_DIR/dl/jdk-$JDK_VERSION.$ext"
    say "downloading JDK $JDK_VERSION"
    if [ "$MODE" = dry ]; then
        echo "    $JDK_URL  ->  $JDK_DIR"
    else
        fetch "$JDK_URL" "$out" || { warn "pinned JDK not available, falling back to latest 21 GA"; fetch "$JDK_URL_FALLBACK" "$out"; }
        unpack "$out" "$TOOLCHAIN_DIR"
        if ! have_jdk; then
            found="$(cd "$TOOLCHAIN_DIR" && ls -d jdk-21* 2>/dev/null | head -n1 || true)"
            [ -n "$found" ] && [ "$TOOLCHAIN_DIR/$found" != "$JDK_DIR" ] && mv "$TOOLCHAIN_DIR/$found" "$JDK_DIR"
        fi
        have_jdk || die "JDK unpacked but $JDK_DIR/bin/java is missing"
    fi
fi

if ! have_sdk && ! have_plat; then
    out="$TOOLCHAIN_DIR/dl/cmdline-tools-$CMDLINE_TOOLS_BUILD.zip"
    say "downloading Android cmdline-tools $CMDLINE_TOOLS_BUILD"
    if [ "$MODE" = dry ]; then
        echo "    $CMDLINE_TOOLS_URL  ->  $SDK/cmdline-tools/latest"
        echo "    (if that URL 404s, download 'Command line tools only' from"
        echo "     https://developer.android.com/studio and point CMDLINE_TOOLS_ZIP at it)"
    else
        fetch "${CMDLINE_TOOLS_ZIP:-$CMDLINE_TOOLS_URL}" "$out"
        mkdir -p "$SDK/cmdline-tools/tmp"
        unpack "$out" "$SDK/cmdline-tools/tmp"
        rm -rf "$SDK/cmdline-tools/latest"
        mv "$SDK/cmdline-tools/tmp/cmdline-tools" "$SDK/cmdline-tools/latest"
        rm -rf "$SDK/cmdline-tools/tmp"
        have_sdk || die "sdkmanager not found after unpacking"
    fi
fi

if ! have_plat; then
    say "installing SDK packages: ${SDK_PACKAGES[*]}"
    if [ "$MODE" = dry ]; then
        echo "    sdkmanager --sdk_root=$SDK ${SDK_PACKAGES[*]}"
    else
        SM="$(find_sdkmanager)"
        [ -n "$SM" ] || die "sdkmanager not found"
        yes 2>/dev/null | "$SM" --sdk_root="$SDK" --licenses >/dev/null || true
        "$SM" --sdk_root="$SDK" "${SDK_PACKAGES[@]}"
        have_plat || die "SDK packages did not install"
    fi
fi

if ! have_src; then
    say "cloning upstream DFRoot"
    if [ "$MODE" = dry ]; then
        echo "    git clone $DFROOT_REPO $SRC && git checkout $DFROOT_COMMIT"
    else
        git clone "$DFROOT_REPO" "$SRC"
        git -C "$SRC" checkout --quiet "$DFROOT_COMMIT"
    fi
fi

if [ "$MODE" != dry ] && [ -d "$SRC/.git" ]; then
    base="$(git -C "$SRC" rev-parse --short HEAD)"
    [ "$base" = "7a6513a" ] || warn "src/DFRoot is at $base, the patch was made against 7a6513a"
    if [ ! -f "$SRC/app/src/main/java/df/root/DeviceLock.java" ]; then
        # stdin, because `git -C <repo>` resolves a relative patch path inside <repo>
        say "applying patches/dfroot-f966w.patch"
        git -C "$SRC" apply - < "$PATCH"
    fi
fi

report
cat <<'EOS'
next steps:
  1) put your own firmware files in firmware/   (boot.img.lz4 and `adb shell getprop > firmware/getprop.txt`)
  2) python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt
  3) python tools/apply_lock.py --report analysis/<your report>.json
  4) bash build.sh

Reminder: the build needs network once (Gradle 9.7.1 + AGP 9.4.0), after that it works offline.
EOS
