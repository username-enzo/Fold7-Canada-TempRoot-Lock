#!/usr/bin/env bash
# Collect post-crash evidence from the phone. Most of it needs no root.
# Run it right after the phone comes back up from a black-screen reboot.
#
#   bash tools/evidence.sh
#
# What it proves:
#   02  ro.boot.bootreason        panic / wdt  => the kernel restarted itself
#                                 reboot,user* => a userspace reboot request
#   03  dropbox SYSTEM_LAST_KMSG  the previous boot's kernel log, if it was captured
#   04  dropbox SYSTEM_RESTART    who asked for the reboot
#   07  /dev/df* markers          which step of the DFRoot chain this boot reached
#
# dmesg and logcat live in RAM: after a kernel panic the previous boot's content is gone.
# dropbox survives reboots. That is why 03/04 matter more than 08/09.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
ADB="${ADB:-$(command -v adb || true)}"
[ -n "$ADB" ] || ADB="$ROOT/toolchain/android-sdk/platform-tools/adb"
[ -x "$ADB" ] || ADB="$ADB.exe"
[ -x "$ADB" ] || { echo "adb not found; set ADB=/path/to/adb" >&2; exit 1; }

OUT="$ROOT/evidence/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
echo "writing to $OUT"

"$ADB" devices -l                                              > "$OUT/00_devices.txt"        2>&1

# ---- what we came for: why did the phone restart? ----
"$ADB" shell getprop                                           > "$OUT/01_getprop.txt"        2>&1
{
    "$ADB" shell getprop ro.boot.bootreason
    "$ADB" shell getprop sys.boot.reason
    "$ADB" shell getprop ro.boot.bootkeys
    "$ADB" shell uptime
}                                                              > "$OUT/02_bootreason.txt"     2>&1

# ---- dropbox survives reboots: panic / restart records ----
"$ADB" shell dumpsys dropbox --print SYSTEM_LAST_KMSG          > "$OUT/03_dropbox_last_kmsg.txt" 2>&1
"$ADB" shell dumpsys dropbox --print SYSTEM_RESTART            > "$OUT/04_dropbox_restart.txt"   2>&1
"$ADB" shell dumpsys dropbox --print SYSTEM_TOMBSTONE          > "$OUT/05_dropbox_tombstone.txt" 2>&1
"$ADB" shell dumpsys dropbox --print                           > "$OUT/06_dropbox_all.txt"       2>&1

# ---- DFRoot's own chain: which marker survived this boot ----
"$ADB" shell 'ls -l /dev/df /dev/dfm0 /dev/dfm1 /dev/dfm2 /dev/dfm3 /dev/dfm4 \
    /dev/dfm5 /dev/dfm6 /dev/dfme0 /dev/dfme1 /dev/dfme2 /dev/dfmw0 /dev/dfmw1' \
                                                               > "$OUT/07_dev_markers.txt"    2>&1

# ---- logs of the CURRENT boot ----
"$ADB" logcat -b all -d -v time                                > "$OUT/08_logcat_all.txt"     2>&1
"$ADB" shell dmesg                                             > "$OUT/09_dmesg.txt"          2>&1

# ---- sources that need root (they fail cleanly on a non-rooted phone) ----
"$ADB" shell ls -l /sys/fs/pstore                              > "$OUT/10_pstore_list.txt"    2>&1
"$ADB" shell cat /sys/fs/pstore/console-ramoops-0              > "$OUT/11_pstore_console.txt" 2>&1
"$ADB" shell 'ls -l /data/log | grep -i dumpstate'             > "$OUT/12_dumpstate_logs.txt" 2>&1

# Samsung's kernel-panic archives are system:log 0640 and cannot be read as `shell`.
# If you still hold the temporary root (it dies on reboot), pull them now:
#
#   "$ADB" shell "su -c 'mkdir -p /sdcard/Download/kp && cp -f /data/log/dumpstate_lastkmsg_*_KP.log.gz /sdcard/Download/kp/ && chmod 644 /sdcard/Download/kp/*'"
#   MSYS_NO_PATHCONV=1 "$ADB" pull /sdcard/Download/kp/ "$OUT/kp/"
#   python tools/kp_inspect.py "$OUT/kp" --extract "$OUT/kp/extracted"
#
# Then read 03 / 07 / the extracted store_extra_info.lst, in that order.

echo
echo "done. files:"
ls -1 "$OUT"
echo
echo "read 02 (bootreason), 07 (markers) and 03 (dropbox last kmsg) first."
