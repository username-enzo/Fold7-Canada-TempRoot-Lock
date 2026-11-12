# Baseline (English)

> Full English translation of `BASELINE.md`. Section numbers, hashes, byte counts and commands are
> copied verbatim; if the two ever disagree, the Chinese file is the record of what was measured.

Verification time: 2026-11-11 20:23 UTC (machine clock)
Verification host: Windows 11 + Git Bash, Python 3.11.9, JDK 17.0.20 (Temurin), `PI_OFFLINE=1` (no network)
Verified by: `pi agent` — every number in this file was recomputed with local commands, not quoted from older notes.

## 1. Folder inventory

| Path | bytes | SHA-256 |
|---|---:|---|
| `F966W-Temporary-Root-BBZG3-lock6.1-repeat70.apk` | 52,801,629 | `0f7180effd434cfc841676850b970ab9057b6afc4b85a5cdf180c4bcc19473a2` |
| `conversation archive (not shipped)` | 63,803 | 1,683 lines |
| `firmware/boot.img.lz4` | 22,797,350 | `a5bebd0959dd15a0597c6a1a8d5b07c71c7d0943268bf48e7ce18da9d34f6170` |
| `firmware/AP_F966WVLUDCZJB_..._OS17 file list screenshot.jpg` | 338,482 | — |

Both hashes match §5.1 / §9.1 of the original notes exactly, so the local files are the very
artifacts those notes refer to, not similarly named copies.

## 2. What the delivered APK (Lock6.1) actually contains

The APK has 134 entries. Key payloads, recomputed from the APK during this pass:

| Entry | bytes | SHA-256 | matches notes |
|---|---:|---|---|
| `assets/locked_payloads/cve-2026-43499-app.so` | 126,264 | `d809061172eb825a43571eaeb10d8a898d32db6f28a1f2fb90bae6b318a8068f` | yes |
| `assets/locked_payloads/ksud-s25u-kdp` | 6,407,096 | `fa3edcc7d168637394877b30cb1f909d762dda788ec14051f4ae79edd6562d63` | yes |
| `lib/arm64-v8a/libcve43499root.so` | 26,024 | `c6b0612b6bdbd60ded964694284f7e8d81cfff2079abeaf3b8854952c2b49eec` | not recorded |
| `lib/arm64-v8a/libs25u_native.so` | 11,192 | `3104f3c15288a9a285f779c99d6768db7ed71d20c9606b1783fd344fd947fa26` | not recorded |

The lock configuration that is actually in effect in the built APK, extracted from `classes3.dex`
(more trustworthy than "leftover sources" in the older notes):

```text
applicationId            dev.busung.f966w.temproot.lock6
versionName              0.2.65-f966w-bzg3-lock6.1-repeat70
profile                  q7q-F966W-VLSBBZG3-locked
model                    SM-F966W
buildId                  BP4A.251205.006.F966WVLSBBZG3
csc/build marker         F966WVLSBBZG3
kernelRelease            6.6.98-android15-8-pd6ff1cd-abogkiF966USQSBBZG3-4k
fingerprintPrefix        samsung/q7qcsx/q7q:16/BP4A.251205.006/
STACK_WRITER_DELAY_USEC  70000        (= 70 milliseconds, not 70 seconds)
PAYLOAD_COMMIT           536a0968077cbc213188ae7895bb688ea21ee779
built-in download URLs   raw.githubusercontent.com/BuSung-dev/Root-My-Galaxy-Payloads/536a0968.../artifacts/q7q-F966USQSBBZG3/cve-2026-43499-app.so
                         raw.githubusercontent.com/BuSung-dev/Root-My-Galaxy-Payloads/536a0968.../kernelsu/ksud-s25u-kdp
upstream source revision 1f2f062503b8da342b39f03f7ba0704a8aa794ac (META-INF/version-control-info.textproto)
AGP                      9.2.1
UI string                "Canadian Galaxy Z Fold7 (SM-F966W / BBZG3 locked)"
```

`META-INF/` contains no `.RSA/.SF/.MF`, i.e. v2-only signing, consistent with the older notes.

**Conclusion: by design this APK refuses the current phone (One UI 9 / CZJB / 6.6.127). Its payload
was compiled against the BBZG3 kernel image.**

## 3. The new firmware's boot image (independently recomputed here)

Unpacked again with our own pure-Python LZ4 frame decoder (`tools/lz4frame.py`, no installed packages):

```text
compressed file SHA-256   a5bebd0959dd15a0597c6a1a8d5b07c71c7d0943268bf48e7ce18da9d34f6170
decoded bytes             101,122,048
magic                     ANDROID!
kernel size               39,115,264  (header offset 8)
ramdisk size              0
boot.img SHA-256          3e29ee127035bb1ac94b45feeddbafcf88823e4f7ec74ca35ef34f4f61351bfb
kernel bytes SHA-256      a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
banner                    Linux version 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
                          (Android 11368308 +pgo +bolt +lto +mlgo, clang 18.0.0, LLD 18.0.0)
                          #1 SMP PREEMPT Mon Oct 19 08:36:50 UTC 2026
```

All four values (decoded length, boot hash, kernel hash, banner) match chapter 9 of the original notes
bit for bit. Re-run on 2026-11-11 23:45 UTC: `python -u tools/lz4frame.py "firmware/boot.img.lz4"`
prints the same four values.

Two independent cross-checks for the kernel offset: the arm64 Image magic `ARMd` sits at `4096+0x38`,
and the `SEANDROIDENFORCE` trailer ends at offset `39,120,896`. This image does **not** follow the
AOSP-documented `header_version` field positions (see `DECISIONS.md` §A1).

This still only proves image identity: not that the official signature is valid, and not that a
working payload exists.

## 4. Toolchain and source status (the hard limitation)

| Needed | State on that host |
|---|---|
| upstream source `Root-My-Galaxy` v0.2.65 @1f2f062 | absent. A full-disk search for `root-my-galaxy` / `build.gradle.kts` / `settings.gradle` found nothing (only the historical markdown notes and this session's records) |
| Android SDK (compileSdk 37, build-tools: aapt2 / apksigner / zipalign / d8) | absent. `ANDROID_HOME` empty, no `AppData\Local\Android\Sdk`, no aapt2/apksigner/d8.jar anywhere |
| Gradle (9.5.1 historically) / AGP 9.2.1 / Kotlin / Compose dependencies | absent, no cache in `~/.gradle` or `~/.m2` |
| JDK 17 | present (`Eclipse Adoptium\jdk-17.0.20.101`) |
| network | none (`PI_OFFLINE=1`) |
| signing keystore (the debug keystore used for Lock6/6.1) | absent |

**Hard conclusion: on that host no APK could be built at all (not even a read-only diagnostic APK
without an exploit). The build prerequisites had to be solved first.**

## 5. Old vs new firmware (why the old payload cannot be "allow-listed as is")

| Field | BBZG3 (what the APK is locked to) | CZJB (what the phone runs) |
|---|---|---|
| kernel release | 6.6.98-...-p**d6ff1cd**-abogkiF966USQS**BBZG3**-4k | 6.6.127-...-p**4a765df**-abogkiF966USQ**UDCZJB**-4k |
| kernel build time | Thu Jul 2 01:36:45 UTC 2026 | Mon Oct 19 08:36:50 UTC 2026 |
| Build | BP4A.251205.006.F966WVLSBBZG3 | CP2A.260605.016.F966WVLUDCZJB |
| Android / SDK | 16 / 36 | 17 / 37 (from a screenshot; SDK not confirmed by a device command) |
| kernel bytes hash | unknown (no old image) | `a6222eb6f6cfd7e3...` |

Kernel sublevel, build identity and build time all changed, so a payload bound to kernel layout/offsets
cannot be carried across builds. Only changing the allow-list would mean letting code written for the
old kernel layout write to memory under a new kernel — clearly wrong, and not part of this project.

---

# 6. Baseline added in round 2 (2026-11-12)

Network was available in that round, so a new APK was produced along the DirtyFrag / DFRoot route.
The new verifiable values follow.

## 6.1 New artifacts

| Path | bytes | SHA-256 |
|---|---:|---|
| `src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock1.apk` | 86,015 | `4ade4fb7c14b83433cb6fafb06e7be90c946a139618a1d8c40b841496f6347d6` |
| `deliverables/KernelSU_samsung-v2.2_32687-release.apk` | 7,607,475 | `761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69` |
| upstream official DFRoot v4.7 APK (comparison baseline) | 84,071 | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |

Inside the APK (recomputed from the produced artifact):

| Entry | bytes | SHA-256 | note |
|---|---:|---|---|
| `lib/arm64-v8a/libdfroot.so` | 123,384 | `1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db` | byte-identical to official v4.7 |
| `lib/arm64-v8a/libbootstrap.so` | 10,048 | `654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236` | byte-identical to official v4.7 |
| embedded `dfroot-android15-6.6.ko` | 10,432 | `6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718` | vermagic `6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64` |
| KernelSU `lkm-aarch64-android15-6.6_kernelsu.ko` | 343,952 | `07127a9f635665cd3fb48e8f32ad36ca512656ea5b3d375e74164aab73cedc7f` | same-KMI vermagic |

APK metadata: package `df.root`, versionCode 4700, versionName `4.7-f966w-czjb-lock1`,
minSdk 32, targetSdk 37, label `DFRoot F966W`, `extractNativeLibs=true`, v2 signature
(CN=Android Debug, certificate SHA-256 `01aa025b…a5c2`).

## 6.2 Toolchain on that host (all inside the project's `toolchain/`)

| Component | Version / source |
|---|---|
| JDK | Temurin 21.0.13+9 |
| Android cmdline-tools | 16111833 (sdkmanager reports 23.0.0) |
| SDK platform | `android-37.0` (repo package `platforms/android-37.0`) |
| build-tools | 37.0.0 (aapt2 / apksigner / zipalign / d8) |
| platform-tools | 37.0.1 (adb) |
| Gradle | 9.7.1 (wrapper, `GRADLE_USER_HOME` pointing inside the project) |
| AGP | 9.4.0 |
| source | `diabl0w/DFRoot` master `7a6513a69ce4c1a90b68d857c26347bf166ffe10` (= v4.7 + #185) |

## 6.3 Upstream facts re-checked in that round

- `targets-v3.json`, 12,242 B, 20 payloads, no `CZJB` / `6.6.127` / `SM-F966W` (same verdict as the
  previous round).
- DFRoot's device selection: `uname -r` → (android, major, minor) = (15, 6, 6) → `dfroot-android15-6.6.ko`.
- `dfroot.ko` imports only 6 GKI symbols and its `__versions` is empty. An upstream on-device log
  (issue #60) shows that this ko does load on Samsung 6.6.x; the later failure happens at the ksud stage.
- `apksigner verify`, `zipalign -c 4` and `aapt2 dump` all pass; every `PT_LOAD` is `0x4000`-aligned.

## 6.4 Still unproven

- No device was attached (`adb devices` was empty), so **root success was never measured there**.
- Whether CZJB backports the DirtyFrag fix, and how DEFEX/KDP behave on One UI 9, are both unknown.
- "Verified" in this file means the artifact and its static consistency only — it does not mean the
  exploit succeeded.
