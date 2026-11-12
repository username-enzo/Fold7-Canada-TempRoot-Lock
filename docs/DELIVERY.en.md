# Delivery notes — SM-F966W / CZJB temporary-root APK (English)

> Full English translation of `DELIVERY.md`. Hashes, sizes, paths and commands are copied verbatim.
> The Chinese file is the record of what was measured; this translation tracks it section by section.

Built: 2026-11-12 (machine clock); updated in the second round that afternoon (black-screen reboot triage)
Target device: Samsung Galaxy Z Fold7 (Canada) **SM-F966W**
Firmware: `CP2A.260605.016.F966WVLUDCZJB` (One UI 9 / Android 17 / SDK 37)
Kernel: `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k` (KMI `android15-6.6`, 4 KB pages)

Round-1 on-device result: **selecting the KernelSU mode showed success, the screen went black and the
phone rebooted, and root was gone afterwards**. That is why this round delivers **lock2**, which
persists run diagnostics, plus the new triage document `REBOOT_TRIAGE.md`.

---

## 0. Round 2: the black-screen reboot (read this section first)

**The new APK (same signing certificate as lock1, so it installs over it):**

```text
src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk
94,911 bytes   versionCode 4701   versionName 4.7-f966w-czjb-lock2
sha256 2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
```

Differences from lock1 (Java only; `libdfroot.so` / `libbootstrap.so` are still byte-identical to
official v4.7):

1. The run log and the `/dev/df*` progress markers are written to `df.root`'s device-encrypted
   storage `files/diag.log` and **survive a reboot**. Menu `Run log` shows the last 120 lines,
   `Markers now` shows the markers that currently exist.
2. The success verdict now reaches the real end: success is reported only after `/dev/dfm6`
   (ksud late-load exit code 0). Seeing `/dev/dfme2` reports "exploit worked but ksud failed =
   no root". If neither appears within 90 s the current markers are listed (the old version printed
   SUCCESS even when ksud failed).
3. Every launch / boot broadcast echoes the last 14 lines of the previous kernel boot plus
   `ro.boot.bootreason` / `sys.boot.reason`, so a kernel-panic reboot can be distinguished from an
   Android framework soft reboot without adb.
4. `Auto Soft Reboot` is forced OFF in this build (greyed out in Settings with a note).

Related documents and tools:

| Location | Content |
|---|---|
| `REBOOT_TRIAGE.md` | measured kernel facts, ranked hypotheses, experiment steps (0–3), decision table |
| `deliverables/managers/MANAGERS.md` | hashes, package names and signature pairing of three managers (v2.2 baseline / KaySU v2.4 / v1.0) |
| `tools/evidence.bat` | root-free evidence collection: bootreason / pstore / last_kmsg / dropbox / logcat in one go |

---

## 1. Deliverables

| File | Path | Size | SHA-256 |
|---|---|---:|---|
| **new root APK (lock2, this round)** | `src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk` | 94,911 | `2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7` |
| DFRoot APK (lock1, round 1) | Gradle wiped it from the build directory (`assembleRelease` keeps only the newest output). The one on the phone *is* it; to get it again: `git checkout bc4f0e9 && bash build.sh` | 7,800,186 | `42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3` |
| **KernelSU manager (must be installed too)** | `deliverables/KernelSU_samsung-v2.2_32687-release.apk` | 7,607,475 | `761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69` |
| candidate managers (groups B/C) | `deliverables/managers/` (KaySU v2.4 APK + ko, KernelSU v1.0 APK) | — | see `deliverables/managers/MANAGERS.md` |
| upstream official DFRoot 4.7 (comparison baseline only) | `_probe/apk/DFRoot_4.7.apk` | 84,071 | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |

> Note: copying the APK into `deliverables/` was blocked by the original host's write guard (see
> `DECISIONS.md` §L2). It was not worked around, so the APK stays in Gradle's output directory;
> the paths above are complete paths relative to the project root.

Signing certificate (new APK, v2 scheme):

```
DN                  C=US, O=Android, CN=Android Debug
SHA-256             01aa025b44986b95837b4ccb74a759fd35957d8945eeb37c8be51e8e4fd9a5c2
SHA-1               ea819f569d023dba092cdaca693c901179ea1ca6
```

That is AGP's auto-generated **debug certificate**, because the original host forbade creating a
`.jks` (`DECISIONS.md` §L1). The APK sideloads fine but **cannot replace official DFRoot** (same
package name `df.root`, different signature) — uninstall the official one first. To switch to a real
release signature later, generate a keystore, put `signing.properties` back into `src/DFRoot/` and run
`build.sh` again.

---

## 2. Why the route changed

The previous round's conclusion (`DECISIONS.md` §C) was that the public Root My Galaxy payload list
has nothing for `SM-F966W / UDCZJB / 6.6.127`, so the original route could not produce a rootable APK.
A networked re-check in this round confirmed it:

- `Root-My-Galaxy-Payloads/support/targets-v3.json`: 20 payloads, kernel versions only
  5.10 / 5.15 / 6.1 / 6.6.46 / 6.6.98 / 6.6.102 / 6.12; for F966 only the 6.6.98 build of
  `SM-F966U/U1/B`; no `CZJB` / `6.6.127` / `SM-F966W` entry at all.
- Upstream forks (LiamJ74, 7AKMM, strawberrylickler, …) are likewise stuck in the older BZG3/BZDN era.
- `igorcv88`'s Extended list does have 6.6.127, but for `S938B` (S25 Ultra) — not transferable.

But there is another route that is independent of the build number: **CVE-2026-43284 / DirtyFrag**.

- It loads a **KMI-matched** generic kernel module, not a per-build exploit payload. This device's KMI
  is `android15-6.6`, and DFRoot's `dfroot.ko` ships a module for exactly that KMI.
- DirtyFrag's official fix line is **6.6.138**; CZJB's **6.6.127** is below it, i.e. affected.
- DFRoot issue #76 (2026-10-07) contains a **successful on-device report for a Galaxy Z Fold7**:
  "Automatic root, auto restart, runs very well." (the same report mentions the cover display not
  lighting up after a reboot — see §7).
- The module's vermagic is `6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64`,
  the same **6.6.127** as the device kernel. Under `CONFIG_MODVERSIONS` the kernel only compares the
  flags after the first space, and both sides say `SMP preempt mod_unload modversions aarch64` — this
  is exactly why the approach works.
- The module imports only 6 GKI stable symbols: `snprintf`, `memset`, `register_kprobe`,
  `unregister_kprobe`, `_printk`, `__stack_chk_fail`, so the CRC-mismatch risk across 6.6.127 builds
  is low.

---

## 3. What this APK actually does

Built on upstream **DFRoot v4.7** source (master at clone time = v4.7 + one commit, #185):

| Item | Content |
|---|---|
| native payloads | taken straight out of the **official v4.7 release APK** (`libdfroot.so` / `libbootstrap.so`), byte-identical to official (sha256 in §8), never recompiled |
| kernel module | `libdfroot.so` embeds `dfroot-*.ko` for 8 KMIs; the device selects `android15-6.6` (ko sha256 `6d6f7472…767718`) |
| new `DeviceLock.java` | checks 5 fields before doing anything: model / build / SDK_INT / fingerprint prefix / kernel release prefix; any mismatch returns code 3 with the actual values and **never touches the kernel**. The build check accepts `Build.ID` (Samsung usually reports only `CP2A.260605.016`), `Build.DISPLAY` (full build id) or the combination, to avoid false rejections |
| application id | kept as `df.root`. `dfroot.ko` hardcodes `/data/user_de/0/df.root/bootstrap`; renaming the package would break the post-escalation bootstrap |
| version | `versionCode 4700`, `versionName 4.7-f966w-czjb-lock1` (official is 407 / 4.7) |
| UI | title `DFRoot F966W`, subtitle `@diabl0w github/xda · F966W/CZJB lock` |
| permissions | unchanged from upstream (INTERNET / BOOT_COMPLETED / WAKE_LOCK / QUERY_ALL_PACKAGES), nothing added |

`DeviceLock`'s expected values are the firmware and kernel from §1. It is a **safety lock only**, not
the exploit's matching condition: DirtyFrag itself matches on KMI, and the lock guarantees this APK
only acts on this one target.

---

## 4. Verified on the build host (machine-reproducible)

| Check | Result |
|---|---|
| `aapt2 dump badging` | package `df.root`, versionCode 4700, versionName `4.7-f966w-czjb-lock1`, minSdk 32, targetSdk 37, label `DFRoot F966W` |
| `aapt2 dump xmltree` | `extractNativeLibs=true` (native payloads can run from `nativeLibraryDir`); no `debuggable` |
| `apksigner verify` | v2 signature valid (v1 not enabled, same as official) |
| `zipalign -c -v 4` | pass |
| `libdfroot.so` / `libbootstrap.so` | **byte-identical** to the files inside official v4.7 |
| embedded android15-6.6 ko | sha256 matches the ko extracted independently from the official APK |
| `PT_LOAD` alignment | all `0x4000` (16 KB page compatible) |
| DEX | contains `SM-F966W`, `CP2A.260605.016.F966WVLUDCZJB`, the kernel prefix, the fingerprint prefix, `PROFILE LOCK` |
| KernelSU LKM | `lkm-aarch64-android15-6.6_kernelsu.ko` vermagic matches `dfroot.ko`'s KMI (`6.6.127-4k-…-dirty`) |

## 5. Not verified (device confirmation required)

- **No device was ever attached to the build host** (`adb devices` empty), so "it can root" is
  **not measured**. What this delivery proves is "the artifact is correct, the lock logic is correct,
  the payloads match upstream" — not "root succeeded".
- Whether Samsung backported the DirtyFrag fix into CZJB alone: unknown. DirtyFrag's exploit first
  validates the page-cache write; on failure it prints `DEVICE NOT VULNERABLE` and aborts instead of
  writing further into the kernel.
- Whether One UI 9's DEFEX / KDP behaves like the upstream test devices: the module handles them, but
  there is no public success report for CZJB specifically.
- How `ksud late-load` behaves under Samsung's `kptr_restrict`: upstream DFRoot 4.7's bootstrap does
  **not** have the `kptr_restrict` zeroing logic (PR #174 was never merged). If you get
  "SUCCESS but no root", look there first (see §7).

---

## 6. Install and run

Preconditions: screen unlocked, installing from unknown sources allowed, **back up your data first**.

1. **Check the firmware**: `Settings → About phone → Software information`
   - Build number must be `CP2A.260605.016.F966WVLUDCZJB`
   - Kernel version must be `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k`
   - If either differs, **do not install** (or it will refuse to run anyway).
2. **Uninstall official DFRoot (if present)**: same package name `df.root`, different signature, so it
   cannot be upgraded over.
3. Install `KernelSU_samsung-v2.2_32687-release.apk` (diabl0w's Samsung-adapted manager).
4. Install `DFRoot_4.7-f966w-czjb-lock1.apk`.
5. Open DFRoot → pick **KernelSU** in the top dropdown → tap **Launch Root**.
6. Wait for the log to finish. Signs of success:
   - the log shows `* locked profile: SM-F966W / CP2A.260605.016.F966WVLUDCZJB / KMI android15-6.6`
   - `***SUCCESS***` appears
   - `adb shell su -c id` returns `uid=0(root)`, or the KernelSU manager shows it working.
7. Root **lasts until the next reboot**; open DFRoot and tap again after rebooting.

Caveats:

- `Developer options → Logger buffer sizes` must not be **Off**, or DFRoot errors out immediately.
- Do not enable DFRoot's "Start at Boot" before you have verified manual mode, otherwise you risk a
  boot loop.
- Do not use any "install / flash boot" action of the KernelSU manager from inside DFRoot (that is the
  hard-brick path with a locked bootloader).

## 7. Reading the logs when it fails

| Log | Meaning | Action |
|---|---|---|
| `PROFILE LOCK: … Refusing to run` | device fields do not match the locked values | verify firmware/kernel; do not force-edit the APK |
| `DEVICE NOT VULNERABLE` | page-cache write validation failed, DirtyFrag is patched on CZJB | stop and wait for an upstream adaptation; do not retry |
| `***FAILED***: ksud exited with error` / `SUCCESS` but no root | the exploit reached the kernel stage, the problem is on the KernelSU side | check `adb shell grep kernelsu /proc/modules`; check `/proc/sys/kernel/kptr_restrict`; see DFRoot discussions #69 |
| phone reboots / kernel panic | race or layout mismatch | a normal risk; retry after the reboot, do not hard-reboot repeatedly. **If it is "shows success then immediately goes black and reboots", collect evidence per `REBOOT_TRIAGE.md` §5 instead of guessing** |
| `SUCCESS` then immediate reboot, no root | in the old build (lock1) SUCCESS did not mean ksud succeeded | lock2 gives the real verdict: `/dev/dfm6` vs `/dev/dfme2` |
| `already hooked, skipping` | already ran during this boot | just verify `su`, or reboot and run again |

Collecting logs:

```bash
adb logcat -s dfroot                       # DFRoot's logcat TAG (MainActivity/BootReceiver)
adb shell dmesg | tail -100                # usually blocked by kptr_restrict/dmesg_restrict
adb shell getprop ro.boot.bootreason        # kernel panic vs framework soft reboot
```

Better: run `tools/evidence.bat` (uses the project's adb) which dumps bootreason / pstore / dropbox /
logcat / `/dev/df*` into `evidence/<timestamp>/` in one shot. lock2 also self-documents: DFRoot menu →
`Run log` (still shows which step the previous boot reached) and `Markers now`.

## 8. Key hashes (for verification)

```
lock2 APK (this round)   2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
lock1 APK (round 1)      42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3
KernelSU manager APK     761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69
KaySU v2.4 manager APK   937eac92de8ab6fff8e26ddb63a4d2a50e7c1e1759a3f09ac614ec52e57f7792
KernelSU v1.0 manager    c92f56c6569bfede6a37fdfa209e248c6a8f73b77214e51a3658ac2fec5dcf1e
upstream DFRoot 4.7 APK  9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1
libdfroot.so             1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db
libbootstrap.so          654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236
dfroot-android15-6.6.ko  6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718
kernelsu android15-6.6 (v2.2)      07127a9f635665cd3fb48e8f32ad36ca512656ea5b3d375e74164aab73cedc7f
kernelsu android15-6.6 (KaySU v2.4) c2d11f5e10f551c729e50a8bf7ec89a9bfa5f932e847cb73c0868383b2968d9a
device kernel (from boot.img)      a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
```

## 9. Stated risks

- This is a **kernel privilege-escalation exploit**. Failure can panic the kernel, reboot the phone,
  and in the worst case corrupt data. Back up first and accept that recovery/reflashing may be needed.
- Temporary root does not change the bootloader lock and does not flash partitions; it disappears on
  reboot. But the exploit does write to kernel memory while it runs.
- **Recorded side effect**: the Z Fold7 user in DFRoot issue #76 reported "the cover display does not
  light up after a reboot". The issue was closed pointing at another project's bug, with no conclusion.
  If you hit it, record it before debugging.
- No promises about Knox fuse state, warranty, Play Integrity, or banking apps.
- Do not use this APK on another model/firmware; `DeviceLock` will refuse, and do not try to edit the
  lock out.

## 10. Reproducing the build

```bash
bash build.sh
```

The whole toolchain lives inside the project (`toolchain/`): JDK 21.0.13, Android SDK platform
`android-37.0`, build-tools `37.0.0`, Gradle 9.7.1 (wrapper), AGP 9.4.0.
Native payloads are re-extracted and verified from the official v4.7 APK by
`python tools/extract_native_payloads.py`. Build log: `src/DFRoot/build_logs/gradle_release.log`.

This project's changes to DFRoot are tracked as a patch (`src/` itself is not committed):

```text
patches/dfroot-f966w.patch   654 lines / 9 files, against upstream diabl0w/DFRoot 7a6513a
                             (DeviceLock, Diagnostics, real success verdict, soft reboot pinned off, menu)
```

`build.sh` applies that patch automatically when
`src/DFRoot/app/src/main/java/df/root/DeviceLock.java` is missing, and warns when the upstream baseline
is not `7a6513a`.

**Bit-level reproducibility was measured** in that round: first `git apply -R` to return `src/DFRoot`
to pristine upstream, then run `bash build.sh` (which re-applies the patch). The produced APK sha256 is
still `2a2b59f76640de5f…`, **byte-identical** to the lock2 delivered above. Before rebuilding,
`git -C src/DFRoot apply -R --check -` confirms the patch can be reverted cleanly.
