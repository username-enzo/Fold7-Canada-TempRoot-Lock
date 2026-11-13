# Build record — DFRoot_4.7-f966w-czjb-lock2.apk (English)

> English edition. Chinese original: [`BUILD_RECORD.zh-CN.md`](BUILD_RECORD.zh-CN.md) — that file is the record of what was
> measured; where the two disagree, the Chinese file wins. Section numbers are identical.

This is an **operating manual**, not a summary. The goal: after a firmware change, following it end to
end produces a new locked APK. All commands are run from the project root and all paths are relative
(Git Bash on Windows).

---

## 0. Artifact fingerprint (confirm that this is the thing you are building)

```text
file name     DFRoot_4.7-f966w-czjb-lock2.apk
path          src/DFRoot/app/build/outputs/apk/release/
size          94,911 bytes
sha256        2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
package       df.root (same as upstream, so it installs over older versions)
versionCode   4701
versionName   4.7-f966w-czjb-lock2
label         DFRoot F966W
minSdk 32 / targetSdk 37 / arm64-v8a only
signature     v2, CN=Android Debug, certificate SHA-256 01aa025b44986b95837b4ccb74a759fd35957d8945eeb37c8be51e8e4fd9a5c2
```

`src/` is not in git, so **every source change is recorded in `patches/dfroot-f966w.patch`
(654 lines / 9 files)**. "git + patch + in-project toolchain" alone rebuilds this APK with identical
content — but **not an identical file hash**, because signing is randomised; §7.6 explains how to
compare instead.

---

## 1. How it works: what this APK actually does

Understand the chain and you will know which link breaks when the firmware changes.

```text
APK (Java)                         kernel / user space
────────────────────────────────────────────────────────────────────
tap LAUNCH ROOT
  └─ DeviceLock.check()      five checks: model / build / sdk / fingerprint / kernel
  └─ ExploitRunner.run()
       ├─ pick the manager package ────┐
       ├─ build IPsec tunnel + shm ────┤
       └─ exec libdfroot.so ───────────┘
                          │
                          ├─ CVE-2026-43284 "DirtyFrag": writes into the
                          │  page cache behind init's executable mapping; the
                          │  patched shellcode runs inside init
                          │  → touch /dev/df, insmod dfroot.ko
                          │                        (dfroot-android15-6.6.ko)
                          ├─ dfroot.ko: SELinux permissive + patch DEFEX
                          │  → call_usermodehelper starts sh → /dev/dfm0
                          └─ bootstrap (main() from libbootstrap.so):
                             /dev/dfm1  started
                             /dev/dfm2  read prefs, got su_manager
                             /dev/dfm3  adopted the zygote environment
                             /dev/dfm4  (optional) disable KSU modules
                             /dev/dfm5  about to exec `ksud late-load`
                                      │
                                      └─ ksud: relocates kernelsu.ko by hand
                                         from /proc/kallsyms → init_module(2)
                                         → /dev/dfm6 (exit 0)
                                         → /dev/dfme2 (failure)
```

**Key point**: `libdfroot.so` and `libbootstrap.so` are **binaries compiled upstream**; this record
does not rebuild them. The locked build does only three things:

1. add a lock that only lets it run on the specified firmware (Java);
2. persist how far execution got and judge success with the real criterion (dfm6/dfme2) (Java);
3. turn off one option that is known to self-reboot (Java).

The kernel-side exploit capability comes 100 % from upstream, so **recompiling it is pointless and
would destroy verifiability**.

---

## 2. Prerequisites: five inputs

| # | input | used for | value used here |
|---|---|---|---|
| 1 | official DFRoot v4.7 APK | contains the native payloads and the ko for 8 KMIs | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |
| 2 | upstream DFRoot source | base for the Java-side changes | `diabl0w/DFRoot` `7a6513a` (v4.7 + #185) |
| 3 | KernelSU manager APK | ksud is the late-load payload; its signature must pair with kernelsu.ko | `KernelSU_samsung-v2.2_32687-release.apk` `761dffad…` |
| 4 | the firmware's `boot.img.lz4` | **offline check of kernel version / KMI / build config**, no flashing needed | `firmware/boot.img.lz4` |
| 5 | the target device's runtime properties | fill in DeviceLock's five constants | see §9.1 |

Item 4 is easy to skip and decides everything: **pick the wrong KMI and the ko will never load**.
Getting the kernel version out of `boot.img.lz4` (`tools/lz4frame.py` is read-only and prints directly):

```bash
python -u tools/lz4frame.py "firmware/boot.img.lz4"
```

It prints both the kernel version string and the kernel hash (measured output here):

```text
kernel size: 39115264
arm64 Image magic @4096+0x38: b'ARMd'
banner: Linux version 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k (kleaf@build-host) ... #1 SMP PREEMPT Mon Oct 19 08:36:50 UTC 2026
kernel  sha256: a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
```

To also write it to a file (needed later for the config check), add three lines:

```bash
python - <<'PY'
import sys, struct
sys.path.insert(0, 'tools')
from lz4frame import decode_frame
boot = decode_frame(open('firmware/boot.img.lz4', 'rb').read())
ksize = struct.unpack_from('<I', boot, 8)[0]        # boot header offset 8 = kernel_size
open('build_logs/kernel.img', 'wb').write(boot[4096:4096 + ksize])
PY
sha256sum build_logs/kernel.img     # must equal the kernel sha256 printed above
```

(`4096` is the boot header page size; get it wrong and the file will not start with `ARM\x64`, which
is immediately obvious.)

---

## 3. Build the toolchain (all inside the project, nothing system-wide)

Versions must match, otherwise the artifact hash changes.

| component | version | location |
|---|---|---|
| JDK | Temurin **21.0.13+9** | `toolchain/jdk-21.0.13+9/` |
| Android cmdline-tools | 16111833 (sdkmanager 23.0.0) | `toolchain/android-sdk/cmdline-tools/latest/` |
| SDK platform | **android-37.0** | `toolchain/android-sdk/platforms/android-37.0` |
| build-tools | **37.0.0** | `toolchain/android-sdk/build-tools/37.0.0` |
| platform-tools | 37.0.1 (adb) | `toolchain/android-sdk/platform-tools` |
| Gradle | **9.7.1** (wrapper) | `toolchain/gradle-home/` |
| AGP | **9.4.0** | pulled from Maven |

```bash
mkdir -p toolchain/dl toolchain/android-sdk toolchain/gradle-home
# JDK: Adoptium Temurin 21.0.13+9, unpack into toolchain/jdk-21.0.13+9/
# cmdline-tools: commandlinetools-win-16111833_latest.zip, unpack into toolchain/android-sdk/cmdline-tools/latest/
export JAVA_HOME="$PWD/toolchain/jdk-21.0.13+9"
export ANDROID_HOME="$PWD/toolchain/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export GRADLE_USER_HOME="$PWD/toolchain/gradle-home"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager.bat" --sdk_root="$ANDROID_HOME" \
    "platforms;android-37.0" "build-tools;37.0.0" "platform-tools"
```

`build.sh` uses the project's JDK/SDK and ignores the system environment, so it does not matter whether
Android Studio is installed. (`setup_toolchain.sh` in the repo root automates all of this.)

---

## 4. Get the source (pin the exact commit)

```bash
git clone https://github.com/diabl0w/DFRoot src/DFRoot
git -C src/DFRoot checkout 7a6513a69ce4c1a90b68d857c26347bf166ffe10
git -C src/DFRoot rev-parse --short HEAD     # must print 7a6513a
```

`7a6513a` = v4.7 + `Fall back to libbase when libc++ hook selection fails (#185)`. The patch is made
against exactly this commit.

---

## 5. Apply the local patch (9 files, one by one)

```bash
git -C src/DFRoot apply patches/dfroot-f966w.patch
```

`build.sh` does this automatically (only when `DeviceLock.java` is absent), so running it by hand is
optional. **Backup / revert**:

```bash
git -C src/DFRoot apply -R --check - < patches/dfroot-f966w.patch   # confirm a clean revert first
git -C src/DFRoot apply -R -         < patches/dfroot-f966w.patch   # revert to pristine upstream
```

> Note: `git -C <dir> apply` resolves a relative patch path **inside the repository**, so feeding it
> through stdin is the reliable form.

| file | change | why |
|---|---|---|
| `app/build.gradle.kts` | versionCode 407→**4701**, versionName→`4.7-f966w-czjb-lock2`; signing config becomes "build a release config only when a keystore exists, otherwise fall back to debug"; removes `externalNativeBuild/cmake` | distinguish the version from upstream so a wrong upgrade cannot overwrite; no keystore is generated here; **no native build**, the prebuilt payloads are used |
| `app/src/main/AndroidManifest.xml` | label `DFRoot` → `DFRoot F966W` | you can tell which build is installed at a glance |
| `DeviceLock.java` (new) | five checks: `MODEL` / `BUILD_ID(+SHORT)` / `SDK_INT` / `FINGERPRINT_PREFIX` / `KERNEL_PREFIX` | DirtyFrag matches by KMI, so other models on the same KMI could run it too. This lock is a seatbelt: refuse to touch the kernel on a mismatch |
| `Diagnostics.java` (new) | run log into `files/diag.log` (device-encrypted storage, survives reboot); poll `/dev/df*` every 150 ms; on boot print `ro.boot.bootreason` plus the tail of the previous boot | `/dev/*` markers vanish on reboot, so with the old build **you could not see how far it got** |
| `ExploitRunner.java` | DeviceLock check at the entry point (covers the BootReceiver path); force `soft_reboot=false` (`commit()` synchronously, because `bootstrap.c` reads the prefs XML directly); after the exploit exits keep waiting up to 90 s for `/dev/dfm6` or `/dev/dfme2`, and judge by **markers**, not exit code | upstream `bootstrap.c` still **returns 0 from main when ksud fails** → the old build printed SUCCESS anyway. That is the biggest source of confusion |
| `MainActivity.java` | disable Launch when the lock fails; new menus `Run log` / `Markers now`; toasts distinguish 6 outcomes; subtitle marks the locked build | evidence collection without adb |
| `BootReceiver.java` | also writes the banner / log from the boot broadcast | same path as boot-time autostart |
| `SettingsFragment.java` | `Auto Soft Reboot` greyed out with a note that it is forced off | upstream #122 has a ksud bug that soft-reboots even when the option is off |
| `res/menu/main_menu.xml` | adds `action_log` / `action_markers` | as above |

---

## 6. Native payloads (no rebuild, but verify them)

```bash
python tools/extract_native_payloads.py --dest src/DFRoot
```

It pulls the two `.so` files out of the official v4.7 APK and, for hash auditing, cuts out the **8 ko
files `.incbin`'d into `libdfroot.so`'s `.rodata`** (written under `src/DFRoot/build_logs/embedded-ko/`).

`--dest` is not optional in practice: without it the files are written relative to your shell's cwd, and
`build.sh` will then link an APK that has no `lib/` directory at all — it installs and cannot run
the exploit. `build.sh` passes `--dest` for you. Expected values:

```text
libdfroot.so      1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db
libbootstrap.so   654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236
```

Full list and hashes of the embedded kos (`src/DFRoot/build_logs/embedded-ko/`):

| KMI file | sha256 |
|---|---|
| `dfroot-android12-5.10.ko` | `294564a3ee6d7d5fb0a5d7e4e5be408d2b479d98c3dd27ebebc220446014934a` |
| `dfroot-android13-5.10.ko` | `3a3c0e74230e960fea802bbc0f6a784934e41d853b64ed94b1fac679bf2aa3f0` |
| `dfroot-android13-5.15.ko` | `9dfb8b71b306f5a38fd8b35b283d4dab8b4eb25a08ad97ca0f4ef705b6151c68` |
| `dfroot-android14-5.15.ko` | `8b4d0a88ac07302415fb5483c2017412e7b67106a3b46b45aa9868d86fb5a3a5` |
| `dfroot-android14-6.1.ko` | `5b6107a885b9df54cad7c0f766c87195adda996a1b21814398493a41fc71a0d7` |
| **`dfroot-android15-6.6.ko`** | `6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718` |
| `dfroot-android16-6.12.ko` | `236b82afee477091542a6334ac79a635a1f46374ec447b763f6648998370ed1c` |
| `dfroot-android17-6.18.ko` | `5d1b0ccbe96b1df5b690545a167d61cf6616304a18a1366af8ca681690cd9a5e` |

The target device uses `android15-6.6`, vermagic:
`6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64`.

**How the KMI is derived**: DFRoot itself reads `uname -r` and takes `(android, major, minor)`.
`6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k` → `android15-6.6`.
So the **sublevel (127) does not influence ko selection**; only `androidNN-X.Y` does. That determines
whether the ko has to change on a firmware upgrade.

---

## 7. Build and verify

### 7.1 Build

```bash
bash build.sh
```

Internal order: check JDK/SDK/source → `git apply` the patch if needed → extract payloads if needed →
`./gradlew --no-daemon :app:assembleRelease` → print the APK path and sha256.

### 7.2 Metadata

```bash
BT=toolchain/android-sdk/build-tools/37.0.0
$BT/aapt2.exe dump badging src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk \
  | grep -E "^package|application-label:|native-code"
```

Expected:

```text
package: name='df.root' versionCode='4701' versionName='4.7-f966w-czjb-lock2' ... compileSdkVersion='37'
application-label:'DFRoot F966W'
native-code: 'arm64-v8a'
```

### 7.3 The payloads are untouched (the most important check)

```bash
python - <<'PY'
import zipfile,hashlib
z=zipfile.ZipFile('src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk')
for n in ['lib/arm64-v8a/libdfroot.so','lib/arm64-v8a/libbootstrap.so']:
    print(n, hashlib.sha256(z.read(n)).hexdigest())
PY
```

Must equal the two hashes in §6. If not, someone touched the native code and the artifact is not
trustworthy.

### 7.4 The patch is really in effect (search strings in dex)

```bash
python - <<'PY'
import zipfile
d=zipfile.ZipFile('src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk').read('classes.dex')
for s in [b'Markers now',b'Run log',b'diag.log',b'ksud late-load EXITED',b'bootreason',b'Auto Soft Reboot',b'SM-F966W']:
    print(s, d.count(s))
PY
```

Expected: each ≥1 (`diag.log` and `ksud late-load EXITED` are 2 each).

### 7.5 Signature and alignment

```bash
cmd //c "toolchain\android-sdk\build-tools\37.0.0\apksigner.bat verify --print-certs \
  src\DFRoot\app\build\outputs\apk\release\DFRoot_4.7-f966w-czjb-lock2.apk"
$BT/zipalign.exe -c -v 4 src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk
```

Expected signature `CN=Android Debug`, certificate SHA-256 `01aa025b…`; zipalign passes when it prints
no error. (On Windows `apksigner` only exists as a `.bat`, not an `.exe`.)

### 7.6 Reproducibility: content yes, file hash no

```bash
git -C src/DFRoot apply -R - < patches/dfroot-f966w.patch      # back to pristine upstream
bash build.sh                                                  # re-applies the patch, verifies the APK
python tools/verify_apk.py src/DFRoot/app/build/outputs/apk/release/DFRoot_*.apk
```

**The APK file's own SHA-256 is not reproducible, and this is expected.** Every zip entry is
byte-identical between builds, but the APK Signing Block carries a randomised signature, so signing the
same content twice produces a different file. Measured on four independent builds of identical content:

```text
2a2b59f76640de5f…   4824a51afda989cc…   7d493b7b08a65659…   0093700a10276f83…
                  ^ four different files, identical content
```

What *is* stable is the content: the set of zip entries with their sizes and CRC-32s. `verify_apk.py`
folds that into one value:

```text
content digest   0418c10239f3eb175092a2d69e79b266e4940be13867ea6ed39ff3d96e62e916
```

That digest is what "did I build the same thing?" should mean. The tool also asserts that both native
payloads are present and byte-identical to official v4.7, and that the patch markers are really in
`classes.dex` — so it catches a *silently broken* build (for example an APK built without `lib/`) that
a hash comparison would only report as "different".

If the content digest ever differs, then the toolchain or upstream drifted — do not flash it.

---

## 8. Install and first run

1. Install the KernelSU manager APK first (`deliverables/KernelSU_samsung-v2.2_32687-release.apk`).
   DFRoot's dropdown only lists apps that **ship `libksud.so`**, so the order cannot be reversed.
2. Install DFRoot (`df.root`, installs over older versions, same debug signature).
3. Open it → Settings: `Start at Boot` off, `Disable KSU Modules` off, `Auto Soft Reboot` already
   greyed out.
4. Pick KernelSU in the main dropdown.
5. Tap `LAUNCH ROOT` and read the last line:
   - `SUCCESS (KernelSU loaded)` = `/dev/dfm6` was seen
   - `exploit OK but ksud late-load FAILED` = `/dev/dfme2` was seen
   - `chain never finished` = neither within 90 s; use the `Markers now` menu to see where it stopped

When `/dev/df` exists the button is disabled (already run during this boot); reboot to run again.

---

## 9. Rebuilding after a firmware upgrade (the core chapter)

### 9.1 Step one: take six values from the device (no root, adb is enough)

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell getprop ro.product.model          # → DeviceLock.MODEL
$ADB shell getprop ro.build.display.id       # → DeviceLock.BUILD_ID (Samsung's full build id)
$ADB shell getprop ro.build.id               # → source of BUILD_ID_SHORT
$ADB shell getprop ro.build.version.sdk      # → DeviceLock.SDK_INT
$ADB shell getprop ro.build.fingerprint      # → DeviceLock.FINGERPRINT_PREFIX
$ADB shell uname -r                          # → DeviceLock.KERNEL_PREFIX, also decides the KMI
```

Values for this device (CZJB):

```text
ro.product.model        SM-F966W
ro.build.display.id     CP2A.260605.016.F966WVLUDCZJB
ro.build.id             CP2A.260605.016
ro.build.version.sdk    37
ro.build.fingerprint    samsung/q7qcsx/q7q:17/CP2A.260605.016/...
uname -r                6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
```

> `q7q` / `q7qcsx` is the Fold7 codename. On another model these two segments will differ — do not
> copy them blindly.

### 9.2 Step two: change the six constants in `DeviceLock.java`

Re-export the patch afterwards, otherwise the change is lost the next time, because `src/` is not in git:

```bash
# 1) edit src/DFRoot/app/src/main/java/df/root/DeviceLock.java directly
# 2) re-export the patch (src/ is not committed, the patch must follow)
git -C src/DFRoot add -N app/src/main/java/df/root/DeviceLock.java \
                        app/src/main/java/df/root/Diagnostics.java
git -C src/DFRoot diff -- app/build.gradle.kts app/src/main/AndroidManifest.xml \
                          app/src/main/java app/src/main/res/menu > patches/dfroot-f966w.patch
git -C src/DFRoot reset -q
```

`MODEL` / `BUILD_ID` / `BUILD_ID_SHORT` / `SDK_INT` / `FINGERPRINT_PREFIX` / `KERNEL_PREFIX`.
Also bump `build.gradle.kts`'s `versionCode` by one (4701 → 4702 …) and change the versionName suffix
(`-lock3`), so the new package definitely installs over the old one.

### 9.3 Step three: decide whether the KMI changed (does the ko have to change?)

Take `androidNN` and `X.Y` from the new `uname -r` and join them into `androidNN-X.Y`:

| new `uname -r` | KMI | verdict |
|---|---|---|
| `6.6.xxx-android15-…` | `android15-6.6` | **no ko change**, just update the lock and rebuild |
| `6.12.xxx-android16-…` | `android16-6.12` | upstream v4.7 already embeds a ko for this KMI, usable as is |
| `6.18.xxx-android17-…` | `android17-6.18` | same as above |
| anything else (e.g. `android15-6.12`) | not upstream | **stop**: wait for a new DFRoot release, or this route is closed for now |

The second half is checking that upstream has a ko for that KMI (no network needed — just list them):

```bash
ls src/DFRoot/build_logs/embedded-ko/     # 8 KMIs, see the table in §6
```

At the same time **KernelSU needs a `kernelsu.ko` for the same KMI**. DFRoot's ko only takes kernel
control; the thing that actually provides root is KernelSU's LKM, and both KMIs must match. To check:

```bash
curl -sL "https://api.github.com/repos/diabl0w/KernelSU/releases/latest" \
 | python -c "import json,sys;[print(a['name']) for a in json.load(sys.stdin)['assets'] if 'lkm' in a['name']]"
```

When no public release covers the new KMI, the manager's late-load fails (`/dev/dfme2`, no reboot).
That is not the APK's fault — do not start editing Java.

### 9.4 Step four: the new firmware may have fixed or broken the exploit (decide this first)

Look at these three lines first: things that are **allowed to change but must still be present** in the
official run log (§12.2 holds the CZJB baseline):

| line in the run log | CZJB baseline | how it can change after an upgrade |
|---|---|---|
| `found ko_target: …` | `/vendor/lib64/libbinderdebug.so` | renamed/moved/removed → the exploit fails at step one |
| `Found: hook=… shellcode=… len=…` | `hook=0xb4ae8 shellcode=0x10faa8 len=464` | changes whenever libc++ changes, which is normal; not finding it errors out |
| `BTI/PAC preamble at hook site, advancing +4` | present | if it disappears the external calling convention changed — be suspicious |

Then the vulnerability itself. DirtyFrag (CVE-2026-43284) is fixed at **6.6.138**. Therefore:

| new kernel sublevel | risk |
|---|---|
| still `< 6.6.138`, and `uname -r` only changed the build string | most likely still usable; just build |
| `>= 6.6.138` | **the vulnerability may have been backported**; check DFRoot's issues for a success report first, do not try blindly |

How to judge (no device needed): unpack `kernel.img` from the new `boot.img.lz4`, read the kernel
version and check whether `system_supports_bti`, `scs_*`, `rkp_*`, `task_defex_*` are present, and
compare against your recorded baseline (method in §2). This only tells you whether the conditions
changed; it cannot prove the vulnerability is still there.

On the device there is exactly one test: run it once and watch whether `/dev/df` appears.
If `DEVICE NOT VULNERABLE` shows up, the page-cache write validation failed, i.e. the bug is fixed —
**stop retrying immediately**.

### 9.5 Step five: rebuild + verify + install

Walk through §7 entirely; only three items **must** be re-confirmed: §7.2 (version changed), §7.6
(rebuild hash), and §8 item 5 (the on-device result). The payload hashes in §7.3 should stay the same
as long as the DFRoot release did not change.

### 9.6 When upstream DFRoot publishes a new version

The patch is based on `7a6513a`. Any upstream movement makes `git apply` fail. Order of handling:

```bash
git -C src/DFRoot fetch && git -C src/DFRoot checkout <new tag>
git -C src/DFRoot apply --3way patches/dfroot-f966w.patch   # try a three-way merge first
```

- If it merges: manually check that `ExploitRunner.java` (the real-verdict part) and the marker names
  in `bootstrap.c` still agree — **the marker names are hardcoded in `lkm/dfroot.c` and
  `jni/bootstrap.c`**; if upstream renames them, `Diagnostics.MARKERS` must change too, otherwise it
  will "always time out".
- If it does not merge: redo the 9 changes from §5 by hand, then re-export the patch per §9.2.

Also update the baseline commit string (`7a6513a`) in `build.sh`.

---

## 10. Version ledger

| version | versionCode | sha256 | purpose |
|---|---|---|---|
| lock1 | 4700 | `42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3` | first installable version, firmware lock only. **Round-1's "shows success then black screen and reboot" was this one** |
| **lock2** | **4701** | **`2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7`** | adds run diagnostics + the real success criterion + forced-off soft reboot. **Temporary root measured on device (twice, ~2 s each)** |

lock1 and lock2 have byte-identical native payloads; the difference is Java only. So behavioural
differences between them can only come from: the real criterion, the diagnostics to disk, and the
forced-off `soft_reboot`. If those two KPs from 08:13 / 08:16 (see §12.4) really were
`ksud soft-reboot` recorded as an abnormal shutdown, then "soft reboot turned off" is the key
difference — **that could only be settled by the KP log contents**, and it was (see §12.4.1).

Related git commits (project root repository):

```text
ee886a2  feat: build F966W/CZJB-locked DFRoot APK (DirtyFrag KMI route)
a114f4e  fix(lock): accept Build.DISPLAY for Samsung build id; final APK hash
eeada33  repro: track DFRoot source changes as patches/dfroot-f966w.patch
ffa78d1  chore: .gitattributes so patches/build.sh keep LF
```

---

## 11. Known pitfalls (all of these were actually hit)

| pitfall | symptom | fix |
|---|---|---|
| treating `***SUCCESS***` as root success | it says success, ksud actually failed | upstream `bootstrap.c` returns 0 from both branches. Look at `/dev/dfm6` vs `/dev/dfme2`, use lock2's Run log |
| `git apply patches/...` says file not found | `git -C src/DFRoot` resolves the relative path inside the repo | use stdin: `git -C src/DFRoot apply - < patches/dfroot-f966w.patch` |
| the patch fails to apply on Windows | CRLF contamination | the repo's `.gitattributes` forces LF for `*.patch` / `*.sh`; do not delete it |
| `apksigner.exe` does not exist | only `apksigner.bat` | use `cmd //c "...apksigner.bat ..."` |
| KernelSU is missing from the dropdown | DFRoot was installed before the manager | install the manager first; DFRoot only lists apps with `libksud.so` |
| KaySU installed but nothing seems to happen | the class ksud restarts via `am start` is hardcoded to `me.weishu.kernelsu.ui.MainActivity` | open KaySU manually to read the status |
| `adb shell grep /proc/kallsyms` prints nothing | `Permission denied` (SELinux) | this path is closed; do not use it as a criterion — use `/dev/df*` + dropbox |
| `ls /data/log` lists files but cannot read them | `dumpstate_lastkmsg_*_KP.log.gz` is `system:log 0640` | the directory is readable, the files are not. You need the temporary root first (see §12.4) |
| `gzip` cannot open `dumpstate_lastkmsg_*_KP.log.gz` | despite the name it is a ZIP (`PK\x03\x04`); `gzip.open()` raises `BadGzipFile: Not a gzipped file (b'PK')` | use `python tools/kp_inspect.py <dir>`; the truth is in `store_extra_info.lst` (one line of structured fields: RR/TASK/PANIC/PC/LR) — do not start with the 2 MB `dumpstate_lastkmsg.lst` |
| `adb pull /sdcard/...` fails with `failed to stat remote object 'C:/Program Files/Git/sdcard/...'` | Git Bash rewrites a leading `/` into a Windows path | add `MSYS_NO_PATHCONV=1` (paths inside `adb shell` are unaffected) |
| Run log shows `ro.boot.bootreason=?` | `Diagnostics.prop()`'s reflection is blocked by API 37's hidden-API restriction | harmless (not fixed, to avoid touching a verified artifact); read the real value with `adb shell getprop ro.boot.bootreason` |
| `dmesg` / `logcat` are empty after a crash | they live in RAM and are lost on a kernel panic | look at dropbox (`SYSTEM_LAST_KMSG` / `SYSTEM_RESTART`); `tools/evidence.bat` is ordered accordingly |
| `src/` is not in git | you spend an hour editing, then a clone loses it | put every change into `patches/`, see §9.2 |
| compiling the native code from `src/` yourself | the artifact hash no longer matches and the behaviour is unverifiable | do not. Use the official v4.7 binaries only |
| running `extract_native_payloads.py` from the wrong directory | it writes `app/src/main/jniLibs` relative to the cwd; the build then links an APK with **no `lib/`** (65 KB instead of 95 KB) that installs and cannot work | pass `--dest <source root>`; `build.sh` does. `verify_apk.py` fails such an APK loudly |
| comparing only the APK's SHA-256 between rebuilds | two identical builds report different hashes and it looks like a broken pipeline | compare the **content digest** (`tools/verify_apk.py`) and the payload hashes, not the file hash (see §7.6) |

---

## 12. Success record (2026-11-12, measured)

### 12.1 Measured result

| item | measured value |
|---|---|
| result | **success**, `/dev/dfm6` appeared (`ksud late-load finished cleanly - KernelSU is loaded`) |
| SU manager | `me.weishu.kernelsu` = `KernelSU_samsung-v2.2_32687-release.apk` (group A) |
| duration | **1.94 s** (RUN START 12:03:26.755 → RUN END 12:03:28.791, `uptime` 9509.6 s → 9511.7 s) |
| repeatability | two runs on the same day both succeeded (12:03 and 12:19), the second also within 2 s |
| after reboot | `su` is gone (expected for temporary root, not a defect) |
| evidence archive | `evidence/20261112_122234/` (not committed; git-ignored) |

### 12.2 Full run log (this is what "success" looks like — compare against it next time)

```text
* locked profile: SM-F966W / CP2A.260605.016.F966WVLUDCZJB / KMI android15-6.6 (DirtyFrag)
* app version: 4.7-f966w-czjb-lock2
* manufacturer: samsung
* model: SM-F966W
* android version: 17
* security patch: 2026-10-05
* kernel version: 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k

=== setup ===
found ko_target: /vendor/lib64/libbinderdebug.so
encap port: 59588
spi: 0x19ee75a5

=== exploit (patching files) ===
patch: crash_dump64 <- splicehelper (1408 bytes)
patched 1408 bytes to /apex/com.android.runtime/bin/crash_dump64+0x0
Using KMI: android15-6.6
patch: /vendor/lib64/libbinderdebug.so <- dfroot.ko (10432 bytes)
patched 10432 bytes to /vendor/lib64/libbinderdebug.so+0x0
Finding symbol offsets for /system/lib64/libc++.so:
BTI/PAC preamble at hook site, advancing +4
Found: hook=0xb4ae8 shellcode=0x10faa8 len=464
patch: /system/lib64/libc++.so <- shellcode (464 bytes)
patched 464 bytes to /system/lib64/libc++.so+0x10faa8
patch: /system/lib64/libc++.so <- trampoline (16 bytes)
patched 16 bytes to /system/lib64/libc++.so+0xb4ae0

=== init  ===
Triggering hook...
libc++: loading custom module
kernel module: launching bootstrap
bootstrap: loading app preferences file
bootstrap: cloning zygote env
bootstrap: setting partitions ro
bootstrap: starting SU daemon
ksud start: SUCCESS

=== cleanup ===
restoring trampoline in /system/lib64/libc++.so
patched 16 bytes to /system/lib64/libc++.so+0xb4ae0
restoring shellcode in /system/lib64/libc++.so
patched 464 bytes to /system/lib64/libc++.so+0x10faa8
* exploit binary exited rc=0; waiting for the init hook to fire...
* ksud late-load finished cleanly (/dev/dfm6) - KernelSU is loaded
```

The matching records in `diag.log` (retained across reboots — this is lock2's value):

```text
11-12 12:03:26.725 up=9509.6s --- DFRoot 4.7-f966w-czjb-lock2 (build 4701) ---
11-12 12:03:26.755 up=9509.6s === RUN START (manual) manager=me.weishu.kernelsu soft_reboot=false disable_modules=false /dev/df=false
11-12 12:03:28.712 up=9511.6s * marker /dev/df appeared - shellcode ran in init (ko written, insmod path taken)
11-12 12:03:28.791 up=9511.7s === RUN END exploit rc=0, verdict=KernelSU loaded (dfm6) ===
```

### 12.3 What this success confirmed and disproved

**Confirmed**:
- `/dev/dfm6` is a reliable success criterion, and `bootstrap.c`'s `***SUCCESS***` really does not
  mean root (the old build's misleading behaviour is real).
- lock2's 90 s wait logic is correct: dfm6 was seen within 0.08 s (`RUN END` right after the `/dev/df`
  marker).
- the `soft_reboot=false` path works.

**New facts (added to the firmware-upgrade checklist)**:
1. **`ko_target` is `/vendor/lib64/libbinderdebug.so`**. If an upgrade changes that vendor library
   (renamed, different size, no longer at that path), the exploit's first step
   `patch: ... <- dfroot.ko` fails. This is the line to watch after an upgrade.
2. **The hook site is `/system/lib64/libc++.so+0xb4ae8` and it is preceded by a BTI/PAC preamble,
   which DFRoot skips by advancing +4** (log: `BTI/PAC preamble at hook site, advancing +4`). After a
   libc++ update the offset moves; DFRoot searches for it again, but **a failed search means an error
   or a crash** — that is upstream adaptation work, not something the APK can fix.
3. `/data/log` is **readable** by `shell` (`ls` succeeds), but the
   `dumpstate_lastkmsg_*_KP.log.gz` files inside are `system:log 0640` and **their content cannot be
   read** without root (see §12.4).

**Known defect (harmless, not fixed, to avoid touching a verified artifact)**:
- `Diagnostics.prop()` calls `android.os.SystemProperties.get` via reflection, which API 37's
  hidden-API restriction blocks, so the Run log shows `ro.boot.bootreason=? | sys.boot.reason=?`.
  Read the real bootreason with `adb shell getprop ro.boot.bootreason` (measured here:
  `reboot,userrequested`, i.e. a manual reboot). If it is ever fixed: use
  `Runtime.getRuntime().exec("getprop ...")` instead.

### 12.4 Closed: round-1's "black screen and reboot" was a real kernel panic inside the kernelsu module

`evidence/20261112_122234/12_samsung_dumpstate_logs.txt` lists these (`ls /data/log` needs no root):

```text
-rw-r----- system log  666385 2026-10-14 13:46 dumpstate_lastkmsg_28_20261014_134615_KP.log.gz
-rw-r----- system log  698594 2026-10-14 16:39 dumpstate_lastkmsg_29_20261014_163921_KP.log.gz
-rw-r----- system log  703939 2026-10-22 14:21 dumpstate_lastkmsg_30_20261022_142106_KP.log.gz
-rw-r----- system log  693845 2026-11-12 08:14 dumpstate_lastkmsg_31_20261112_081336_KP.log.gz
-rw-r----- system log  725097 2026-11-12 08:16 dumpstate_lastkmsg_32_20261112_081607_KP.log.gz
```

**11-12 08:13 and 08:16 fall inside the window of round-1's failure ("shows success then black screen
and reboot")**, so that reboot was very probably kernel-side rather than a software reboot. Note that
`_KP` only means "the previous boot did not shut down normally"; the content may be a real panic
(Oops/BUG) or just a normal log truncated by a hard reset — **you must read it to classify it**.

How to grab them while holding the temporary root (root only lasts until the next reboot, and takes
about 2 s to get):

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
# 1) tap LAUNCH ROOT on the phone (~2 s)
# 2) pull the KP logs
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_31_*_KP.log.gz /sdcard/Download/"
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_32_*_KP.log.gz /sdcard/Download/"
$ADB pull /sdcard/Download/ evidence/kp/
```

### 12.4.1 2026-11-12 night: pulled and classified (verdict: real panic, hypothesis B holds)

The device still had root at that point (`su -c id` → `uid=0(root) context=u:r:ksu:s0`), so all five
KP archives were pulled in one pass:

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell "su -c 'mkdir -p /sdcard/Download/kp && cp -f /data/log/dumpstate_lastkmsg_*_KP.log.gz /data/log/dumpstate_latest_lastkmsg.log.gz /sdcard/Download/kp/ && chmod 644 /sdcard/Download/kp/*'"
MSYS_NO_PATHCONV=1 $ADB pull /sdcard/Download/kp/ evidence/kp/   # Git Bash rewrites /sdcard to C:/Program Files/Git/sdcard
```

**Gotcha: these `.log.gz` files are not gzip, they are ZIP (`PK\x03\x04`).** `gzip.open()` raises
`BadGzipFile: Not a gzipped file (b'PK')`. Parse them with `tools/kp_inspect.py` (runs without an
unzip binary): each archive holds `store_extra_info.lst` (one line of structured fields, the most
useful part), `eRR.p`, `dumpstate_lastkmsg.lst` (2 MB of kernel log), `reset_summary.html`,
`ocimem.lst` and 3 more entries.

For classification: `python tools/kp_inspect.py evidence/kp --extract evidence/kp/extracted`

| KP | time | TASK | PANIC | PC |
|---|---|---|---|---|
| 28 | 10-14 13:46 | RenderThread | Oops - BUG (`lib/list_debug.c:67`) | `__list_del_entry_valid_or_report+0xec` |
| 29 | 10-14 16:39 | `cve43499-run` | Oops | `_raw_spin_trylock+0x1c` |
| 30 | 10-22 14:21 | Jit thread pool | Oops - BUG (`lib/list_debug.c:64`) | `__list_del_entry_valid_or_report+0xdc` |
| **31** | **11-12 08:13** | **ksud** | **synchronous external abort** | **`ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`** |
| **32** | **11-12 08:16** | **ksud** | **synchronous external abort** | **same PC, same module build id** |

(`dumpstate_latest_lastkmsg.log.gz` has exactly the same sha256 as 32: `59d78da1e4eb79c3…`, i.e. the
same copy.)

The call traces of 31 and 32 are identical line by line (after `Internal error:` in
`dumpstate_lastkmsg.lst`):

```text
ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu b61aef7e3fae7d02afb759c7a4acdecdd07aea2e]
 syscall_regfunc_handler+0x4c/0x88        [kernelsu b61aef7e…]
 __kretprobe_trampoline_handler+0xcc/0x140
 trampoline_probe_handler+0x28/0x48
 __kretprobe_trampoline+0x74/0xcc
 tracepoint_add_func+0x64/0x404
 tracepoint_probe_register+0x60/0xa4
 ksu_syscall_hook_manager_init+0xa8/0xe4  [kernelsu b61aef7e…]
 kernelsu_init+0xec/0x130                 [kernelsu b61aef7e…]
 do_one_initcall+0xdc/0x360 -> do_init_module -> load_module -> __arm64_sys_init_module
```

The trigger is **inside `init_module`**: `ksu_syscall_hook_manager_init` attaches a kretprobe to the
`sys_enter` tracepoint's `regfunc`, `tracepoint_add_func` calls it back synchronously, and inside that
callback the log line `tp_marker: mark process: pid:1, uid: 0, comm:init` has just been emitted
(the registers `x6`/`x7`/`x13` still hold format-string fragments `KernelSU` / `: tp_mar` /
`omm:init`), when the very next data access at `ksu_mark_running_process_locked+0x154` raises a
`synchronous external abort` (`do_sea`, ESR low bits `0x96000010` / HYP-side `ESR_EL2=0x9200004e`,
DFSC=0b001110), immediately followed by
`Kernel panic - not syncing: synchronous external abort: Fatal exception`.
The `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED` / `TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` in
`store_extra_info.lst` are the watchdog firing after the kernel is already dead — **not the cause**.

### 12.4.2 What this panic tells us

1. **Hypothesis A (ksud soft-reboot recorded as an abnormal shutdown) is void**: `soft_reboot` in
   `bootstrap.c` sits after `dfm6`, and this kernel died inside `kernelsu.ko`'s `init_module` — not a
   single line of `dfm6` was reached. lock2 forcing `soft_reboot=false` could not have been the cure
   for these two events (it is still a correct hardening, just not the cause).
2. The symptom chain matches exactly: ko init crashes → kernel dies → watchdog fires → hard reboot →
   root disappears.
3. The crash is **a linear-map read** while `ksu_mark_running_process_locked` walks/marks processes
   (`x19` equals the fault VA reported by the hypervisor: `0xffffff8032f29d00` /
   `0xffffff8032e9c300`, the two boots differing only by the KASLR offset). A plain wild pointer would
   report `Unable to handle kernel paging request`; a `synchronous external abort` means that page was
   **refused by the secure world / hypervisor** — consistent with the **RKP/KDP page protection + KCFI**
   environment determined in `REBOOT_TRIAGE.md` §2 `[A]` (inference, not yet proven by experiment).
4. **Both panics share the same ko build id** (`b61aef7e…`), the same PC offset and the same log
   sequence → a **deterministic** code path in that binary, not flakiness.

### 12.4.3 The manager in use back then was not the current one (verifiable)

Two independent pieces of evidence show that the install at 08:13 was **a different APK instance**,
not the current `samsung-v2.2`:

| evidence | 08:13 | now (the 13:39 success) |
|---|---|---|
| `/data/app` instance directory (derived from APK content/signature) | `~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==` | `~~SgtRsoT9Ew37h_UC1xUqJA==/me.weishu.kernelsu-9H2ZfUhhMCGravyfSqF45w==` |
| app uid | `10463` | `10503` (`u0_a503`) |
| install time | — (same package name; the version cannot be recovered from the device) | `firstInstallTime=2026-11-12 11:52:04` |

Sources: dropbox `SYSTEM_TOMBSTONE` (08:14:26, `Executable: .../libksud.so`,
`Cmdline: ... debug su`, `uid: 10463`); the current values come from
`dumpsys package me.weishu.kernelsu`. Current `ksud --version` = `ksud samsung-v2.2 (uapi: 5)`.

The same tombstone shows the crashing processes were `libksud.so debug su` and
`me.weishu.kernelsu:root:0`, both with `Data Abort Exception 0x24` — **downstream** userspace crashes
caused by the dead kernel, not separate faults.

> Still undetermined: the exact version of that 08:13 APK (nothing is left on the device:
> `pm list packages -u` shows only the current package, `/data/user/0` has no 08:xx directory, and
> `/data/adb/ksu/log` keeps only the last two rotations). Filling that cell in would require the
> installation record of what was `adb install`ed around 08:0x. **It does not affect the conclusion**:
> the crash point and the manager used by the 4 successes are not the same instance.
