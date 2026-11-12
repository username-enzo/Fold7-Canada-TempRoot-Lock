# Fold7 (Canada) TempRoot Lock — a reproducible, firmware-locked DFRoot build

> 🌐 **English (this file) · [中文](README.zh-CN.md)**
>
> Using only public vulnerabilities and public projects, this repo builds a temporary-root APK for
> **Samsung Galaxy Z Fold7 (Canada) SM-F966W** that refuses to run on any other firmware, and
> documents — as runnable tools, not prose — how to screen another device, how to reproduce the build,
> and how to read the crash logs when it goes wrong.

---

## ⚠️ High-risk warning

- Everything described here **writes to kernel memory** and loads a kernel module that is not signed by
  Samsung.
- Possible outcomes: black screen, boot loops, data loss, a device that only recovers by reflashing,
  voided warranty, and **irreversible** breakage of Knox and some Samsung security features.
- Only on a device **you own and have backed up**. Before the first attempt, make sure you can get back
  to a working state (Odin + official firmware).
- You are on your own.

---

## Legal position

1. **Everything here comes from public sources**: the public advisory/PoC for CVE-2026-43284
   ("DirtyFrag"), the public `diabl0w/DFRoot` project, the public `Root-My-Galaxy` payload list, and
   public `KernelSU`. This repo contains no non-public information and no original vulnerability
   research.
2. **No firmware, no proprietary files**: no Samsung firmware, OTA packages, signing material, or
   proprietary binaries. Get firmware from official channels and analyse it locally.
3. **No commercial interest**: no paid tier, no ads, no donation links, nothing for sale, no paid
   flashing service; no personal data or device identifiers are collected or uploaded.
4. **Education and research only**: understanding Android/Linux kernel security, module loading, and
   temporary-root engineering. You must check whether it is legal and allowed by the vendor's terms
   where you live. **Do not** use it to circumvent DRM, to bypass payment or anti-cheat, to access
   devices you do not own, or for anything unlawful.
5. **No warranty**: the authors are not liable for broken devices, lost data, voided warranties, banned
   accounts, or any legal consequence.
6. **No affiliation**: not affiliated with, endorsed by, or authorised by Samsung, Google, or the
   KernelSU upstream. If you believe something here infringes your rights, open an issue and it will be
   handled.

---

## Contents

1. [What this is and what it is not](#1-what-this-is-and-what-it-is-not)
2. [Why a firmware lock](#2-why-a-firmware-lock)
3. [What you need](#3-what-you-need)
4. [Quick start (six steps)](#4-quick-start-six-steps)
5. [How to read the report](#5-how-to-read-the-report)
6. [Other models and other firmware](#6-other-models-and-other-firmware)
7. [Known pitfalls](#7-known-pitfalls)
8. [Layout](#8-layout)
9. [License and third parties](#9-license-and-third-parties)
10. [References](#10-references)
11. [The one lesson worth remembering](#11-the-one-lesson-worth-remembering)

---

## 1. What this is and what it is not

| Is | Is not |
|---|---|
| A method + tools + build log for getting **temporary** (lost on reboot) root on **one specific firmware** of SM-F966W. | A universal root tool for every Fold7. |
| A **firmware lock**: the APK compares model, build id, SDK, fingerprint and kernel release against the five values it was built for, and refuses to run on a mismatch. | A security boundary. It stops accidents, not determination. |
| A **screening tool** that tells you whether a given `boot.img` falls inside this route's applicability. | A proof that an exploit will work — no offline check can do that. |
| A **failure case study** with the full kernel panic analysis of a "says SUCCESS, then reboots" event. | A guarantee that it will not happen to you. |
| A **reproducible build**: given the toolchain and upstream sources it produces a byte-identical APK (see [`docs/BUILD_RECORD.md`](docs/BUILD_RECORD.md) §7). | A prebuilt APK (see §9) — build it yourself. |

Not provided: no firmware, no SU-manager APK, no kernel-module binaries, no "one-click root for any
Fold7" (the route is KMI-matched and firmware-locked by design), and no kernel-side bypass research —
the kernel module comes from upstream unmodified.

**In one paragraph.** DFRoot uses a public page-cache write primitive (CVE-2026-43284) to replace one of
`init`'s files with its own helper, getting one-shot code execution inside `init`; that helper
`insmod`s a **KMI-matched** `dfroot.ko`, which spawns `ksud`; `ksud late-load` then loads KernelSU's
kernel module. The match is by **KMI** (`android15-6.6` here), not by build number, so applicability is
mostly decided by whether the kernel sublevel is below the fix line (6.6.138). Success is `/dev/dfm6`;
failure is `/dev/dfme2` — never the app's `***SUCCESS***` toast.

---

## 2. Why a firmware lock

- Because the route is KMI-matched, it **may also run on other firmware**. Loading the same module on an
  unreviewed build can panic outright — this repo documents exactly that happening
  ([`docs/KP_CASE_STUDY.md`](docs/KP_CASE_STUDY.md)).
- So `patches/dfroot-f966w.patch` adds a Java-side hard lock: model, build id (both `ro.build.id` and
  `ro.build.display.id` accepted), SDK, fingerprint prefix, kernel prefix — all five must match.
- For your own device, `tools/analyze_firmware.py` derives the six values and
  `tools/apply_lock.py` writes them into the source before building.
- The lock is not a security boundary, only a guard against accidents: it stops you from running
  someone else's APK, not from deliberately editing constants.

---

## 3. What you need

| Required | Notes |
|---|---|
| a Fold7 (Canada) `SM-F966W` with USB debugging | other models: see §6 |
| the `boot.img` of its **current** firmware (`boot.img.lz4` inside `AP_*.tar.md5`) | offline analysis only, never uploaded |
| `adb shell getprop > firmware/getprop.txt` | only 6 whitelisted properties are read; serial/IMEI are dropped |
| a KernelSU manager for the **same KMI** (verified here: `me.weishu.kernelsu` = `samsung-v2.2`) | download from upstream releases yourself |
| PC + `python3` + `bash` (Git Bash on Windows) + `git` | the scripts use the standard library only |
| network (**first run only**: JDK, SDK, Gradle dependencies) | offline afterwards |

Not required: Android Studio (everything installs into `toolchain/`), an unlocked bootloader (this
route does not touch partitions), any Samsung account or online service (everything is local).

---

## 4. Quick start (six steps)

```bash
git clone <this repo> && cd <repo>

# 1) one-time environment: JDK 21 + Android SDK 37 + upstream DFRoot source (the only network step)
bash setup_toolchain.sh

# 2) drop in your own firmware files
mkdir -p firmware
cp /path/to/boot.img.lz4 firmware/
adb shell getprop > firmware/getprop.txt      # only these 6 properties are read

# 3) screen it: can it be tried, and what are the six constants
python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt

# 4) write your six constants into the source
python tools/apply_lock.py --report analysis/<your report>.json

# 5) build
bash build.sh

# 6) install, run, read the verdict
adb install -r src/DFRoot/app/build/outputs/apk/release/DFRoot_*.apk
```

Install order and settings (**get this wrong and KernelSU will not appear in the dropdown**):

| step | do | why |
|---|---|---|
| 1 | install the SU manager (KernelSU APK) first | DFRoot's manager dropdown only lists apps that ship `libksud.so` |
| 2 | then install the DFRoot APK built here | same package name as official `df.root` but a **different signature**, so it cannot install over it — uninstall the official one first |
| 3 | Settings: `Start at Boot` off, `Auto Soft Reboot` stays off, `Disable KSU Modules` off | avoids boot-time re-triggering and framework soft reboots polluting the diagnosis |
| 4 | select the manager package in the dropdown, tap `LAUNCH ROOT` | — |
| 5 | read menu `Run log` / `Markers now`, or `adb shell ls -l /dev/df*` | `dfm6` = success, `dfme2` = failure |

> **`***SUCCESS***` does not mean success.** Both branches of upstream `bootstrap.c` return 0, so a
> failed ksud still shows SUCCESS. The verdict is `/dev/dfm6` (KernelSU loaded) vs `/dev/dfme2`
> (ksud failed).

> Losing root after a reboot is **expected**, not a bug: this is a late-load temporary root.

---

## 5. How to read the report

`tools/analyze_firmware.py` writes `analysis/<model>_<build>.md` and `.json` with three parts.

**① Verdict (one of three)**

| verdict | meaning | what to do |
|---|---|---|
| `maybe` | kernel is older than the fix line `6.6.138`, KMI is the verified `android15-6.6` | worth trying, but read the hardening fingerprint first |
| `untested` | the kernel is not `android15-6.6` | confirm upstream has a kernel module for that KMI (vermagic must match), otherwise do not try |
| `patched` | kernel version ≥ `6.6.138` | stop, look for another route |

**② Hardening fingerprint** (`yes` is strong evidence, `no` is weak)

`shadow_call_stack` / `kcfi` / `samsung_defex` / `samsung_rkp_kdp` / `bti`.
`yes` means the hardening really is in the image: it will not prevent loading, but it makes a **crash**
more likely and much harder to localise (see [`docs/KP_CASE_STUDY.md`](docs/KP_CASE_STUDY.md)). `no`
must not be read as "not compiled in" — `kallsyms` names can be token-compressed and are then not
findable as plain text.

**③ The six DeviceLock constants**, which go straight into `apply_lock.py`.

> The report screens; it does not prove. Nothing offline can prove exploitability — the only real test
> is the device, with a recovery path ready.

---

## 6. Other models and other firmware

The same device after a firmware upgrade (OTA) must be re-run too: `DeviceLock` will refuse to run, by
design.

| change | what to confirm |
|---|---|
| only the build id changed, kernel unchanged | re-run `analyze_firmware.py`, `apply_lock.py`, rebuild |
| the kernel **sublevel** changed (e.g. `6.6.127` → `6.6.140`) | if ≥ `6.6.138`, this route is basically over |
| the **KMI** changed (e.g. `android15-6.6` → `android16-6.12`) | you need a kernel module for that KMI; whether upstream provides one decides everything |
| a different model (F966B / F966U / F966E …) | unlockability, DEFEX/RKP policy and the KMI can all differ; the model and fingerprint prefix in `DeviceLock` must change, and **this project has not verified that model** |

Minimal steps to change the constants:

```bash
python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt
python tools/apply_lock.py --report analysis/<report>.json   # prints before/after per constant
bash build.sh
```

Without a `getprop.txt` you can pass values explicitly:
`--model --build --build-short --kernel --fingerprint --sdk`.

---

## 7. Known pitfalls

| pitfall | symptom | fix |
|---|---|---|
| treating `***SUCCESS***` as success | it says success but nothing is installed | look at `/dev/dfm6` vs `/dev/dfme2` |
| KernelSU missing from the dropdown | DFRoot installed before the manager | install the manager first, then install/restart DFRoot |
| `boot.img.lz4` will not unpack | LZ4 tools differ | use `tools/lz4frame.py` (pure Python, no dependencies) |
| `.log.gz` will not open | these Samsung crash archives are actually **ZIP** | use `tools/kp_inspect.py`, not `gzip` |
| `adb pull /sdcard/...` fails on Git Bash | the path is rewritten to `C:/Program Files/Git/sdcard/...` | add `MSYS_NO_PATHCONV=1` |
| `dmesg`/`logcat` are empty after a crash | a kernel panic wipes the in-RAM logs | look at dropbox and the vendor's KP archive |
| `apksigner` does not exist | only `apksigner.bat` is shipped | on Windows use `cmd //c "...apksigner.bat ..."` |
| the release build complains about signing | no `signing.properties` | it falls back to a debug certificate automatically; for a real signature see `signing.properties.example` |
| it will not install | same package name as official `df.root`, different signature | uninstall the official one, or sign with your own key |

The full list (20+ pitfalls actually hit) is in [`docs/BUILD_RECORD.md`](docs/BUILD_RECORD.md) §11.

---

## 8. Layout

```
README.md                     this file (English, primary)
README.zh-CN.md               中文版
LICENSE                       GPL-2.0 — inherited from upstream DFRoot
NOTICE.md                     third-party components, licences, where to download them
docs/
  BUILD_RECORD.md             step-level build recipe (toolchain, patches, hashes, verification)
  REBOOT_TRIAGE.md            how to triage "rebooted / root gone" and read the crash logs
  KP_CASE_STUDY.md            a full, solved kernel-panic case
  DECISIONS.md                assumption/decision log, incl. retracted leads and local limits
  BASELINE.md                 hashes of every input and output this repo talks about
  DELIVERY.md                 install / verify / diagnose / risks for the built APK
  README.md                   index, plus which paths in the docs are intentionally absent
  *.zh-CN.md                  the Chinese record of each of the above (same numbering)
patches/
  dfroot-f966w.patch          9 files on top of upstream DFRoot 7a6513a (the lock + diagnostics)
tools/
  analyze_firmware.py         boot.img(.lz4) + getprop -> screening report + 6 constants
  apply_lock.py               report -> DeviceLock.java constants
  lz4frame.py                 pure-python LZ4 frame decoder (no deps)
  kp_inspect.py               read Samsung dumpstate_lastkmsg ZIP archives
  extract_native_payloads.py  pull the official DFRoot payloads out of the upstream APK
  evidence.sh / evidence.bat  collect post-crash evidence over adb
build.sh                      build the APK (optionally apply a lock report first)
setup_toolchain.sh            one-time environment setup (JDK + SDK + upstream clone)
signing.properties.example    copy to signing.properties for a real release key
firmware/                     YOUR firmware files go here (gitignored)
analysis/                     generated reports (gitignored)
```

Paths the documents mention that are **not** in this repo (`evidence/`, `deliverables/`, `TODO.md`) are
explained in [`docs/README.md`](docs/README.md).

**Language convention**: `NAME.md` is the English edition, `NAME.zh-CN.md` is the Chinese record of
what was measured (identical section numbers, hashes and commands). Where they disagree, the Chinese
file wins.

---

## 9. License and third parties

- This repo is **GPL-2.0** (same as upstream `diabl0w/DFRoot`), see `LICENSE`.
- `patches/dfroot-f966w.patch` is a derivative of upstream `7a6513a`, so it is GPL-2.0 as well.
- The native payloads (`libdfroot.so` / `libbootstrap.so`) are **not redistributed**:
  `tools/extract_native_payloads.py` downloads them from the official upstream release and verifies
  their SHA-256.
- KernelSU / its forks' managers and kernel modules are **not redistributed**: download them from their
  own upstream releases.
- Samsung firmware is **not redistributed**: get it from official channels.
- The exact list, licences and download locations are in `NOTICE.md`.
- **No prebuilt APK**: the artifact is signed with a debug certificate, is large, and handing one to
  someone else means taking on their risk. The hash is recorded in
  [`docs/BUILD_RECORD.md`](docs/BUILD_RECORD.md) so you can rebuild and compare.

---

## 10. References

This project only depends on the following **public** sources (all independently verifiable):

| source | used for |
|---|---|
| `https://github.com/diabl0w/DFRoot` | the exploit and bootstrap source; the official release the native payloads come from |
| `https://github.com/BuSung-dev/Root-My-Galaxy-Payloads` | the per-build payload route's list (its `targets-v3.json` is what proves this firmware has no ready-made payload) |
| `https://github.com/tiann/KernelSU` | the upstream late-load kernel module and `ksud`, plus the KMI matrix |
| **CVE-2026-43284 "DirtyFrag"** | the page-cache write primitive used by this route (public advisory and PoC; search the id) |
| Android boot image format / LZ4 frame format specs | the basis for `tools/lz4frame.py` |
| Eclipse Temurin 21 / Android SDK cmdline-tools | what `setup_toolchain.sh` downloads |

---

## 11. The one lesson worth remembering

We hit "the app says SUCCESS, the phone immediately goes black and reboots". The obvious explanation —
a framework soft reboot — was **wrong**.

The real cause: `kernelsu.ko` faulted inside `init_module` at `ksu_mark_running_process_locked+0x154`
with a synchronous external abort; two records had identical PC and identical module build id
(deterministic). The watchdog bite was a consequence.

The full analysis, including the wrong turns, is in
[`docs/KP_CASE_STUDY.md`](docs/KP_CASE_STUDY.md).

**Conclusion: read the crash log before changing anything.** Swapping versions without a log is
gambling with the device.

---

## Contributing

- Reports for **other Fold7 models/firmware** are welcome (`analysis/*.md`, with identifiers removed).
- Fixes to docs and tools are welcome; keep the "public sources only" rule.
- **Do not** paste serial numbers, IMEIs, phone numbers, or other people's device data.
- "Please root my phone for me" requests are out of scope.
