# Assumptions and decisions (English)

> English edition. Chinese original: [`DECISIONS.zh-CN.md`](DECISIONS.zh-CN.md) — that file is the record of what was
> measured; where the two disagree, the Chinese file wins. Section numbers are identical.

Written: 2026-11-11 23:41 UTC (machine clock)

## A. Facts re-verified in that session `[T]`

```text
F966W-Temporary-Root-BBZG3-lock6.1-repeat70.apk  0f7180effd434cfc841676850b970ab9057b6afc4b85a5cdf180c4bcc19473a2
firmware/boot.img.lz4                            a5bebd0959dd15a0597c6a1a8d5b07c71c7d0943268bf48e7ce18da9d34f6170
```

Both hashes match the original notes (§5.1 / §9.1) and `BASELINE.md` §1 exactly, so the file identity
has not drifted.

That session re-ran the boot verification with `tools/lz4frame.py`; all four values agree bit for bit
with the notes (§9) and `BASELINE.md` §3:

```text
decoded bytes      101,122,048
boot.img sha256    3e29ee127035bb1ac94b45feeddbafcf88823e4f7ec74ca35ef34f4f61351bfb
kernel size        39,115,264   kernel sha256  a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
banner             Linux version 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k ... #1 SMP PREEMPT Mon Oct 19 08:36:50 UTC 2026
```

### A1 A verification-tool defect found and fixed in that session `[C][T]`

The CLI part of `tools/lz4frame.py` used to read the kernel/ramdisk sizes from boot-header offsets
44/48, which produced `kernel size: 0`, `kernel sha256 = e3b0c442...` (the hash of empty input), and
treated offset 40 as `header_version`. The numbers reported in the previous session did not come from
that CLI but from an ad-hoc script using the correct offsets, so the values in `BASELINE.md` were
right.

Fixed: kernel/ramdisk sizes now come from offsets 8/12, and the tool additionally prints the arm64
Image magic and the trailer marker as cross-checks.

- The kernel start at 4096 is confirmed by two independent facts, not by a header field: the arm64
  Image magic `ARMd` sits at `4096+0x38`, and the `SEANDROIDENFORCE` trailer lands exactly at
  `39,120,896 = 4096 + 9549*4096`.
- Reading the AOSP-documented positions (offset 20 = `header_version`, etc.) yields `1584` and other
  non-standard values, so **the tool no longer claims a boot header version**; Samsung image header
  fields cannot be read by the documented layout. None of the four hashes above are affected.
- The tool also prints `note: simple header checksum heuristic mismatch (informational)`: its own
  heuristic for the LZ4 frame header checksum byte is wrong and unrelated to decompression (the output
  matches the known-correct hash bit for bit). Left alone because it does not affect conclusions.

## B. Assumptions about the phone's state

| # | assumption | basis / gap |
|---|---|---|
| B1 | the phone still runs `CP2A.260605.016.F966WVLUDCZJB` and kernel `6.6.127-...-UDCZJB-4k`, and the uploaded boot image is the current one | `[S][T]` screenshot and boot banner agree; the build host cannot verify the device `[?]`. If it received another OTA, the whole plan is void |
| B2 | Android 17 / SDK 37 | `[S]` screenshot only, not confirmed by a device command. Must be marked "to be confirmed" in any profile, never treated as `[T]` |
| B3 | `device = q7q` | derived `[A][S]` from `fingerprintPrefix = samsung/q7qcsx/q7q:17/...` and `F966USQ` in kernelRelease; not read from the device |
| B4 | the kernel build time `Mon Oct 19 08:36:50 UTC 2026` belongs to the current boot | `[T]` verbatim from the boot image banner; consistent with the kernel release in the screenshot `[S]` |

## C. Core verdict: is there a public payload for CZJB? (decides route 3A vs 3B)

**Verdict: third tier — no entry in any available material names `SM-F966W` + `UDCZJB` + `6.6.127`.**

| evidence | content | tag |
|---|---|---|
| notes §11.4 `targets-v3.json` | a 2026-11 search still returns only old BZG3 entries | `[H]` |
| notes §11.4 Extended payloads README | mentions `6.6.127` in its self-description, but the model is `S938BXXUCZZI4` (another device, not transferable) | `[H]` |
| notes §11.4 S918B branch | `S918BXXUAZZI8` + KernelSU Next v3.4.0, another device | `[H]` |
| notes §11.4 LiamJ74 fork | old `F966B` BZG3 generation only | `[H]` |
| forum thread | the poster explicitly says there are no details | `[U]` |

Limit: **a search miss is not a proof of absence** `[A]`, and that host had no network, so this could
not be upgraded from `[H]` to `[T]`. Bringing the list back as a text file was the only way to upgrade
the verdict.

**Default route: 3B.** 3A only starts if a concrete project name / APK version / payload commit id /
supported entry appears.

## D. Things explicitly not done

1. **Do not take BBZG3's 126 KB payload, widen the allow-list and stuff it into a new APK.** That
   artifact is bound to the BBZG3 kernel image layout; the kernel sublevel (6.6.98 → 6.6.127), build
   identity and build time all changed (`BASELINE.md` §5). Allowing it means letting code written for
   the old memory layout write into a new kernel → likely panic / brick.
2. **No ODIN flashing on your behalf, no anti-rollback / CSC handling.**
3. **Do not write "build succeeded / support check passed" as "root succeeded".** Only a real device
   can be measured.
4. **Do not decompile the dex to "reconstruct" the upstream project as buildable source** — unreliable
   and unverifiable. Upstream source must come from `BuSung-dev/Root-My-Galaxy`
   @ `1f2f062503b8da342b39f03f7ba0704a8aa794ac` (`[T]`, read from `META-INF/version-control-info.textproto`
   inside the APK).

## E. If route 3A runs: package name and signing assumptions

| # | decision | reason |
|---|---|---|
| E1 | new package name `dev.busung.f966w.temproot.czjb` | no debug keystore for Lock6/6.1 is available; the old certificate (`SHA-256 37005fdd384f114ded4ed9abba746164118de9610225989b126cdd07d7ca1250`) cannot be reproduced |
| E2 | the new APK **cannot upgrade the old package**; they must coexist; uninstall the old one | direct consequence of E1, not optional |
| E3 | `versionCode 8`, `versionName 0.2.65-f966w-czjb-lock7` | continues from Lock6.1's `versionCode 7` |
| E4 | create a keystore with the host's JDK 17 `keytool` and put the certificate fingerprint into the delivery notes | JDK 17 was the only build-side component available |

## F. Parameter interpretation corrections `[C]`

- `STACK_WRITER_DELAY_USEC = 70000` → **70 milliseconds** (the field name says µs), not 70 seconds.
  The `repeat70` in the file name is this parameter's value, **not** a 70-second retry interval.
  `[T]` value from the dex strings; `[A]` unit inferred from the field name.
- Lock6 and Lock6.1 share `applicationId = dev.busung.f966w.temproot.lock6` and only bump
  `versionCode` 6→7, i.e. with the same signature they can upgrade each other — which does not apply
  to the pipeline created under E1.

## G. Two cleanup actions that needed confirmation

| # | item | status |
|---|---|---|
| G1 | the previous session wanted to rename `tmp_bootcheck.py` (an experiment that loads `msys-lz4-1.dll` and segfaults) to `tools/scratch_lz4_ctypes_segfault.py`; the `mv` was blocked by the original host's write guard and was not worked around. The file stayed in the root. | resolved: the public repo does not contain that script (`tools/lz4frame.py` does the same verification) |
| G2 | the repo was initialised (`git init`) and `.gitignore` excludes the 52.8 MB `F966W-...lock6.1-repeat70.apk` and the 22.8 MB `firmware/boot.img.lz4`, versioning only documents and scripts so the repo does not grow to 75 MB | if you want the large files versioned too, delete those two `.gitignore` lines and `git add -f` |

## H. Toolchain status (the hard prerequisite for phase 2, unresolved at the time)

| needed | state on that host |
|---|---|
| upstream `Root-My-Galaxy` v0.2.65 @1f2f062 | absent |
| Android SDK (compileSdk 37, `aapt2` / `apksigner` / `zipalign` / `d8`) | absent (`ANDROID_HOME` empty, nothing found on disk) |
| Gradle 9.5.1 / AGP 9.2.1 / Kotlin / Compose offline caches | absent (`~/.gradle`, `~/.m2` both empty) |
| JDK 17.0.20 (Temurin) | **present** |
| network | none (`PI_OFFLINE=1`) |
| signing keystore | absent |

**Conclusion: that host could verify things (hashes / LZ4 unpacking / dex strings / signature info /
unit-test code) and write code, but could not produce any APK.** The build environment had to be
chosen first; until then "a new APK" did not exist as a deliverable.

## I. What was actually advanced in that round

- Added `DECISIONS.md` (this file), which `TODO.md` referenced but which did not exist.
- Gave a **preliminary verdict from available material** (see §C: third tier) while keeping the door
  open to an upgrade to "explicitly supported".
- Recomputed the hashes of both files, confirming the baseline had not drifted.
- Initialised git and committed documents plus verification scripts.

---

# Round 2 (2026-11-12): route change and the first APK

## J. Why "wait for a CZJB payload" was abandoned in favour of DirtyFrag

**Trigger**: that session found the network was available (the previous round's `PI_OFFLINE=1` was
out of date), so upstream was re-searched and a second route — not based on per-build compilation —
was found.

### J1 Re-check of the earlier verdict (still holds)

- `Root-My-Galaxy-Payloads/support/targets-v3.json` (actually downloaded, 12,242 B): 20 payloads,
  kernel version set = {5.10.237, 5.15.153, 5.15.189, 6.1.145, 6.1.157, 6.6.46, 6.6.98, 6.6.102, 6.12}.
  `F966` appears only as `SM-F966U` / `SM-F966U1` / `SM-F966B` mapping to `BZDN` / `BBZG3`; the whole
  file contains no `CZJB` / `UDCZJB` / `6.6.127`.
- Upstream repo PR/issue search: `repo:BuSung-dev/Root-My-Galaxy-Payloads` with `CZJB` = 0 hits,
  `UDCZJB` = 0 hits; all 8 hits for `6.6.127` are S25 (S93x) / other models.
- Forks re-checked: `LiamJ74`, `7AKMM`, `strawberrylickler` only have the old generation; `igorcv88`
  Extended's `6.6.127` is `S938B`.

### J2 The new route: CVE-2026-43284 (DirtyFrag)

| fact | tag |
|---|---|
| DirtyFrag uses a page-cache write primitive to load a kernel module **compiled per KMI**, not an exploit compiled per build | `[T]` code and docs |
| DirtyFrag's fix line is 6.6.138; the device runs 6.6.127 < 6.6.138 | `[H]` the CVE table |
| DFRoot's `dfroot.ko` (android15-6.6) vermagic = `6.6.127-4k-g46a034eca005-dirty …`, same sublevel as the device | `[T]` extracted from the official APK |
| device `uname -r` = `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k` → parsed as (15,6,6) → selects that ko | `[T]` source + `[S]` kernel string |
| under `CONFIG_MODVERSIONS` the kernel's `same_magic()` only compares the flags after the first space; both sides say `SMP preempt mod_unload modversions aarch64` | `[A]` kernel semantics + `[T]` vermagic strings |
| the ko imports only 6 GKI symbols (snprintf/memset/register_kprobe/unregister_kprobe/_printk/__stack_chk_fail) | `[T]` symtab parse |
| DFRoot issue #76: a Galaxy Z Fold7 on-device success ("Automatic root, auto restart, runs very well") | `[H]` upstream issue |

### J3 Decision

**Adopt DFRoot v4.7 as the base and produce a new APK with a hard F966W/CZJB lock.**

Still not done (same principles as §D):

1. Do not widen the allow-list of BBZG3's per-build payload and put it in (irrelevant to this route).
2. Do not claim "build succeeded = root succeeded".
3. No flashing on the user's behalf, no bootloader changes.

## K. Build decisions

| # | decision | reason |
|---|---|---|
| K1 | use `libdfroot.so` / `libbootstrap.so` **from the official v4.7 APK** byte for byte; do not rebuild native code | these are the upstream-published binaries used on many devices; no NDK needed, so no new differences. Reproducible via `tools/extract_native_payloads.py` |
| K2 | keep package name `df.root` | `dfroot.ko` hardcodes `/data/user_de/0/df.root/bootstrap` and `.../ksud`; renaming breaks the post-escalation exec |
| K3 | add Java-side `DeviceLock`, requiring all 5 fields to match | DirtyFrag matches by KMI and does not check the model; the hard lock prevents use on another model/firmware |
| K4 | version `4700` / `4.7-f966w-czjb-lock1` | distinguishes it from official 407 while making clear it is a local build on 4.7 |
| K5 | **release build falls back to the debug signature** | see §L1; the APK installs and works, the side effect is that it cannot replace official `df.root` |
| K6 | keep upstream defaults for `isMinifyEnabled` / `isShrinkResources` | do not change upstream behaviour; the lock strings were confirmed present in dex |
| K7 | the build check accepts `Build.ID`, `Build.DISPLAY` and their combination | Samsung's `ro.build.id` is usually only `CP2A.260605.016` while the full build number lives in `ro.build.display.id`; comparing only `Build.ID` would falsely reject the target. Rebuilt afterwards and both constants confirmed in dex strings |

## L. Blocked by the original host's guards (recorded, not worked around)

| # | operation | why blocked | handling |
|---|---|---|---|
| L1 | `keytool -genkeypair -keystore keystore.jks` | flagged as a sensitive path | not created. `app/build.gradle.kts` now falls back to AGP's auto-generated debug certificate (`~/.android/debug.keystore`, SHA-256 `01aa025b…a5c2`) when `signing.properties` is missing |
| L2 | `cp …/DFRoot_4.7-f966w-czjb-lock1.apk deliverables/` | judged to write outside the project folder | not worked around; the APK stays in `src/DFRoot/app/build/outputs/apk/release/`, with the full path and hash in `DELIVERY.md` |
| L3 | `mv` / `rm -rf` into `src/DFRoot/build_logs/embedded-ko` | same guard, nested relative path misjudged | not worked around; the scripts now overwrite in place (idempotent content) |

## M. Unverified and residual risk

1. **No device**: `adb devices` was empty, nothing measured. The delivery proves the artifact matches
   upstream and the lock logic is correct — nothing more.
2. **Whether CZJB backported the DirtyFrag fix**: unknown. The exploit validates its own page-cache
   write and prints `DEVICE NOT VULNERABLE` and aborts on failure.
3. **Samsung DEFEX / KDP**: the module handles them, but there is no public success record for
   F966W + CZJB.
4. **kptr_restrict**: DFRoot 4.7's `libbootstrap.so` lacks PR #174's zeroing logic; if you see
   "SUCCESS but no root", check `/proc/sys/kernel/kptr_restrict` first (see `DELIVERY.md` §7).
5. **Side effect**: DFRoot issue #76 recorded a Z Fold7 cover display that stayed dark after a reboot;
   no conclusion. It is in the delivery risks.
6. **Version drift**: if the device receives another OTA, `DeviceLock` refuses to run; the KMI/fix
   status then has to be re-evaluated.

## N. Verification record for that round

```text
APK path   src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock1.apk
APK sha256 4ade4fb7c14b83433cb6fafb06e7be90c946a139618a1d8c40b841496f6347d6  (86,015 B)
signature  v2 scheme, CN=Android Debug, cert sha256 01aa025b44986b95837b4ccb74a759fd35957d8945eeb37c8be51e8e4fd9a5c2
libdfroot.so    1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db  (= official v4.7)
libbootstrap.so 654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236  (= official v4.7)
ko 15-6.6       6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718
KernelSU APK    761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69  (samsung-v2.2)
```

---

# Round 3 (2026-11-12 afternoon): on-device "SUCCESS then black screen and reboot"

## O. Symptom (`[U]`, reported from the device)

DFRoot with the KernelSU mode → shows success → **immediately black screen and reboot** → root gone.
The build host still had no device (`adb devices` empty), so everything below is **offline-reproducible
analysis plus evidence tooling**, not a located cause.

## P. New machine-checkable facts from that round `[T]`

Method: `tools/lz4frame.py` unpacks `firmware/boot.img.lz4` → `build_logs/kernel.img`
(kernel sha256 `a6222eb6f6cfd7e3…`, matching the §A baseline) → build configuration judged from the
kallsyms name table; APK/ko side analysed with `zipfile` plus a hand-written ELF64 parser (no
readelf/objdump/capstone on that host).

| # | fact | evidence |
|---|---|---|
| P1 | device kernel has **CONFIG_SHADOW_CALL_STACK=y** | kallsyms contains `scs_alloc/scs_cleanup/scs_free/scs_init/scs_patch/scs_patch_vmlinux/scs_prepare/scs_release`; vmstat `shadow_call_stack`, `nr_shadow_call_stack`, `irq_shadow_call_stack_ptr` |
| P2 | device kernel has **KCFI enabled** | strings `Oops - CFI`, `__cfi_` |
| P3 | **Samsung DEFEX and RKP/KDP are both present**, **no BTI kernel support** | 43 occurrences of `task_defex_enforce/user_exec/zero_creds/link_protection` etc.; `rkp_init/rkp_pgt_bitmap/rkp_dbl_bitmap/init_mm_pgd/tramp_pgd/_KMEM_TYPE/CRED_JAR_TYPE/TSEC_JAR_TYPE/kdp_*`; `system_supports_bti` / `ARM64_HAS_BTI` absent |
| P4 | **DFRoot's SUCCESS does not mean KernelSU is installed** | `app/src/main/jni/bootstrap.c`: on ksud failure it only `touch /dev/dfme2` and `main` still `return 0` → Java sees rc=0 → SUCCESS. The real criterion is `/dev/dfm6` (ksud exited 0) vs `/dev/dfme2` (ksud failed) |
| P5 | **unresolved `[?]`: kernelsu.ko not found inside the manager APK** | in `KernelSU_samsung-v2.2`'s `libksud.so` and `classes.dex`, searches for `import_ns=VFS_internal…`, `description=Android KernelSU`, `6.6.127-4k`, ELF64 magic all returned 0 hits; the manager's `.rodata` (2,877,264 B) is the same size as the standalone `ksud` release asset → no pack_lkm difference. Upstream `late_load.rs` uses `assets::get_asset_data("<kmi>_kernelsu.ko")` (rust_embed at compile time). **Not dug into further**: it neither explains "shows success" (a ksud failure leaves dfme2) nor can be proven offline; on-device dfm5 vs dfm6 is the criterion. Written into `REBOOT_TRIAGE` §6 hypothesis 2 |
| P6 | **ko and manager are signature-paired**, never mix them | `apksigner --print-certs`: the v2.2 manager certificate `14296df5…` equals that tag's `KSU_EXPECTED_HASH`; KaySU v2.4 manager `ba305717…` equals KaySU's `KSU_EXPECTED_HASH`; v1.0 certificate `195bf724…` |
| P7 | only 2 kernel-side commits after upstream samsung-v2.2 | `bbd9b2480` (sys_enter uses `regs`, fixing `task_struct->stack` offsets 0x28/0x38 on SCS=n devices) + `76a088c5f` (stricter BTI detection in rkp.c). Per P1/P3, **neither should matter here** |
| P8 | upstream reports of the same symptom (Samsung: panic/reboot right after SUCCESS) #110/#111/#122/#131/#153 were all fixed by **changing/upgrading the build**; the author always asks for `/data/log/dumpstate_lastkmsg_*KP*` first | GitHub API read of issue bodies and comments |
| P9 | ~~all three KernelSU-family LKMs need the same 3 hard symbols and the image bytes do not contain them~~ **retracted, see P11**: `__tracepoint_sys_enter`, `mntns_operations`, `selinux_blob_sizes` (all GLOBAL, non-weak undefined imports) | `.symtab` parse: diabl0w samsung-v2.2 = 236 kernel imports, KaySU samsung-v2.4 = 236 (**identical set to v2.2**), upstream tiann v3.3.1 `lkm-aarch64-android15-6.6_kernelsu.ko` (`_probe/ksu-upstream-android15-6.6.ko`, sha256 `e57ce23d…`) = 226; all three miss exactly the same ones; all three share vermagic `6.6.127-4k-g46a034eca005-dirty`. Device side: the image has 868 `__tracepoint_*` and 1959 `__traceiter_*` names, i.e. 1091 tracepoints have no `__tracepoint_` symbol (`sys_exit` has one, `sys_enter` does not); `mntns_get/install/owner/put` exist but not `mntns_operations`; `lsm_blob_sizes` exists but not `selinux_blob_sizes` |
| P9b | the method's limits were flagged at the time (original wording kept) | the verdict used a **byte search for name strings in the unpacked kernel.img**; what is visible are the fixed-width sorted kallsyms name table and `__ksymtab_strings`, without a full parse of the kallsyms tables, so "not found" is not 100 % equal to "absent". Upstream v6.6 source really does have `mntns_operations` (`const struct proc_ns_operations`, non-static) and `selinux_blob_sizes` (`__ro_after_init`), so the difference is either Samsung's own config/renaming or the reading being too shallow |
| P10 | ~~decisive verification needs no root: `/proc/kallsyms` names are readable~~ **wrong, see P12** | `adb shell grep ... /proc/kallsyms` returns `Permission denied` on this device |

## Q. Decisions in that round

| # | decision | reason |
|---|---|---|
| Q1 | deliver **lock2** (versionCode 4701 / `4.7-f966w-czjb-lock2`), changing Java only: `Diagnostics` writes to disk, polls the `/dev/df*` markers, autopsies `ro.boot.bootreason` at boot, and judges success by dfm6/dfme2 | a reboot erases everything under `/dev`, so with the old build **you could not see which step the previous boot reached**; without that cell you can only guess. All changes are Java, the exploit binaries are untouched |
| Q2 | lock2 **forces `soft_reboot=false`** (syncing the DE prefs before running), and greys the setting out | upstream #122 has a ksud bug that soft-reboots even when the option is off; remove the framework-reboot variable from the experiment first |
| Q3 | **do not rebuild the native payloads**: lock2's `libdfroot.so`/`libbootstrap.so` are still byte-identical to official v4.7 (`1dc45a41…`/`654d11c7…`) | post-4.7 upstream only has #185 (fall back to libbase when libc++ does not fit); the hook already fires here, so not needed; a self-build would add unverifiable differences |
| Q4 | add a **manager matrix** (A `samsung-v2.2` baseline / B `KaySU samsung-v2.4` / C `samsung-v1.0`), downloaded and verified, see `deliverables/managers/MANAGERS.md` | every upstream report with this symptom was fixed on the manager (kernelsu.ko) side; this is the cheapest, highest-prior exclusion |
| Q5 | **do not touch the ko or the patch points before the last_kmsg arrives** | P1–P3 already rule out both known upstream bugs; continuing to guess is gambling kernel memory on a real device |
| Q7 | ~~do the on-device `/proc/kallsyms` check first, then decide about swapping managers~~ **void, see Q10** | its premise is P9/P10, both of which fail |
| Q8 | also pull upstream tiann v3.3.1's android15-6.6 ko for comparison (symbol set only; not recommended as a manager: no Samsung DEFEX/RKP handling, and its signature pins the upstream manager) | the identical symbol set (236 vs 236) is itself valid, but it does not imply "symbols missing", see P11 |
| P11 | **P9 retracted: an offline byte search for symbol names cannot decide whether the kernel has a symbol** | (a) `kallsyms_names` is token-compressed, so most names never appear literally; the literal strings findable in the image come only from the BTF string table (3,816,744 B of types / 2,608,839 B of strings / 141,000 unique strings at image offset 25,873,004) and `__ksymtab_strings` (exported names). (b) Counter-sampling: `cpu_switch_to`, `__cpu_setup` (symbols that certainly exist) are not findable literally, and BTF also lacks `init_mm`/`init_pid_ns`/`system_wq`/`tasklist_lock`/`strchr`/`kmalloc_caches` — 20 of the LKM's 236 imports are not in BTF. So "not found" is not "absent", and P9's reasoning chain breaks |
| P11b | **even if P9 held, it cannot explain the black-screen reboot** | `_probe/ksuinit_lib.rs:317-390`: unresolved symbols only `log::warn!("Cannot find symbol")` and `init_module()` is still called; unresolved symbols stay `SHN_UNDEF`, the kernel loader fails to resolve them in `__ksymtab`, reports `Unknown symbol`, the load is refused, ksud fails, `/dev/dfme2` remains. The prediction is "cannot install, no reboot", which contradicts the observation and pushes hypothesis 1 (crash after loading) forward |
| P12 | `/proc/kallsyms` is **Permission denied** for the `shell` domain (SELinux, not `kptr_restrict`) | measured: `adb shell grep ... /proc/kallsyms` prints nothing and reports no permission; `adb devices` is fine and USB debugging is on. So "read kallsyms over adb" is unavailable |
| P13 | root-free crash evidence should come from dropbox rather than dmesg/logcat | dropbox lands in `/data/system/dropbox` and survives reboots (`SYSTEM_LAST_KMSG` / `SYSTEM_RESTART` / `SYSTEM_BOOT`); dmesg and logcat are in RAM and the previous boot's content is gone after a panic. `tools/evidence.bat` was rewritten accordingly (03/04 are the key files) |
| Q10 | drop the "kallsyms symbol gate", look directly at the `/dev/df*` markers plus dropbox | that gate cannot be read (P12) and its premise does not hold (P11). "dfm5 present, dfm6 absent" plus `SYSTEM_LAST_KMSG` separates "did not install" from "installed then crashed", with no root and no adb privileges |
| Q11 | delete the half-finished `tools/kallsyms_from_image.py` (it failed to locate `kallsyms_token_table/index/num_syms` in the raw arm64 Image) | leaving it would suggest a working tool exists. `REBOOT_TRIAGE.md` §2b records "tried, failed, deleted" including the detail (signature scan for token_index, 0 hits over 39 MB) |
| R5 | **an evidence directory was deleted by mistake** `evidence/20261112_115313/` (the raw output of the first `tools/evidence.bat` run) | an `rm -rf evidence` meant to clean up a device-less dry run at 10:06 took that one with it; Python `shutil.rmtree` does not use the recycle bin and it was unrecoverable. Affected scope is small: `ro.boot.bootreason` reflects the last reboot and dropbox is on disk, so as long as the phone had not rebooted again, re-running `tools/evidence.bat` reproduces the same content. Lesson: list the directory and confirm names before cleaning, never wildcard-delete |
| P14 | **on-device result: lock2 obtained temporary root** (reported from the device, 2026-11-12) | the first measured success of this project. All earlier "failure" conclusions were offline inference or round 1 (lock1). Details not yet archived: which manager, the last Run log marker, duration, whether `su` survives a reboot — listed as open items in `TODO.md` G4 and `BUILD_RECORD.md` §12 rather than guessed here |
| P15 | the manufacturing process is fully archived in `BUILD_RECORD.md` | covers: the chain, 5 prerequisite inputs, exact toolchain versions, the 9 patch files one by one, payload and embedded-ko hashes, 7 verification commands with expected output, the 6 properties to read and 6 constants to change on a firmware change, the KMI decision table, the rebase procedure when upstream releases, and 11 known pitfalls. Every command was actually run |
| Q12 | post-success archiving writes only "actionable steps", not "causal conclusions" | because attribution (which link was decisive) still lacked Run log evidence, and the value of a manufacturing record is reproducibility. Unknowns are explicitly marked "to be filled", so nobody later follows a wrong cause |
| P16 | **measured success (first)**: lock2 + `me.weishu.kernelsu` (samsung-v2.2) → `/dev/dfm6`, RUN START→RUN END = **1.94 s** (`uptime` 9509.6 s→9511.7 s); two runs the same day both succeeded | the `diag.log` record was captured by logcat (`evidence/20261112_122234/08_logcat_all.txt`); `soft_reboot=false disable_modules=false` |
| P17 | **on-device results disproved several earlier hypotheses**: late-load failure (#2), dfroot.ko crash (#4), unstable #185 hook (#5) are all false — the chain is complete: `libc++ hook → dfroot.ko load → bootstrap → ksud start: SUCCESS → dfm6` | the full Run log, stored in `BUILD_RECORD.md` §12.2 |
| P18 | **the only place `bootstrap.c` can reboot**: `if (run_ctx(... late-load ...) == 0) { touch(dfm6); if (soft_reboot) { while (late_load_running()) sleep(1); run_ctx("u:r:ksu:s0", {KSUD, "soft-reboot"}); } }` | `app/src/main/jni/bootstrap.c:224-231`. I.e. it soft-reboots **only after a successful load and only when the prefs say `soft_reboot=true`**; lock1 did not force that switch off |
| P19 | **`/data/log` is listable by `shell` but its files are not readable**: 5 `dumpstate_lastkmsg_*_KP.log.gz` were listed, including **2026-11-12 08:13 and 08:16** (right inside round-1's failure window), files owned `system:log 0640` | `evidence/20261112_122234/12_samsung_dumpstate_logs.txt`. This **overturned** the earlier inference "no SYSTEM_LAST_KMSG in dropbox, so it was not a panic"; `_KP` only means the previous boot did not shut down normally and the content has to be read |
| P20 | that round **did not classify** the black-screen reboot; instead it left two hypotheses with explicit criteria | A (`ksud soft-reboot` recorded as abnormal shutdown) and B (KernelSU runtime patching panics the kernel) both fit; criteria in `REBOOT_TRIAGE.md` §6.1; log retrieval in `BUILD_RECORD.md` §12.4. This document had once been about to record A as "confirmed" and retracted that when P19 appeared |
| P21 | do not modify the already-verified lock2 (e.g. `Diagnostics.prop()` failing reflection on API 37 so `bootreason=?`) | a change would change the APK hash and break the consistency between "verified artifact" and the manufacturing record. The defect is documented in `BUILD_RECORD.md` §12.3 and §11 with the future fix |
| Q9 | keep **all** of this project's DFRoot source changes as `patches/dfroot-f966w.patch` (654 lines / 9 files, against upstream `7a6513a`), applied automatically by `build.sh`; this closed the gap where changes could not be reproduced because `src/` was untracked | measured: `git apply -R` to pristine upstream → `bash build.sh` (re-applies the patch) → APK sha256 still `2a2b59f7…`, **byte-identical to the delivered artifact**. The APK is now fully rebuildable from git + patch + in-project toolchain |
| Q6 | the evidence script uses the project's adb (`toolchain/android-sdk/platform-tools/adb.exe`) and needs no root: `tools/evidence.bat` | `ro.boot.bootreason` / dropbox / logcat / pstore listings are available to `shell` and suffice to separate panic from framework reboot |

## R. Limitations of the original working environment (recorded, not worked around)

> This section describes the **original environment** (that machine, that sandbox) and is irrelevant to
> reproducing this project. It is kept only because "why a particular artifact looks like it does"
> needs an explanation — for example why the APK is signed with a debug certificate. For reproduction
> problems, start with `REBOOT_TRIAGE.md` and `BUILD_RECORD.md` §11.

| # | item | status |
|---|---|---|
| R1 | GitHub Actions artifacts need login: `actions/artifacts/<id>/zip` returns **401** anonymously (the listing API is readable and confirmed the `manager` and `aarch64-android15-6.6-lkm` artifacts from 10-22 exist and are unexpired) | for an official (non-personal-fork) post-v2.2 build, log in with `gh auth login` or download `manager` in a browser |
| R2 | `python -m pip install capstone` (arm64 disassembly, to check the 0x38/0x28 offsets instruction by instruction) was not executed in that restricted environment (judged a network install) | the kallsyms configuration evidence (P1) was used instead and is sufficient; instruction-level verification would need that install |
| R3 | §L1 (no keystore) and §L2 (APK left in the build output directory) still apply; the manager APKs/kos downloaded into `deliverables/managers/` were not blocked | lock2 shares lock1's signature (AGP debug certificate) and installs over it |
| R4 | the original environment's write guard blocked `rm` / `cp` / redirection against some directories, and `git -C <repo> apply patches/xxx.patch` resolves the relative path inside the repository so it cannot find the file | pass patches through stdin: `git -C src/DFRoot apply - < patches/dfroot-f966w.patch` (both `build.sh` and `setup_toolchain.sh` do this) |

---

# Round 4 (2026-11-12 night): on-device evidence collection, KP logs closed

Precondition: the phone was connected over USB with USB debugging on, and the **temporary root was
still alive** (`su -c id` → `uid=0(root) gid=0 context=u:r:ksu:s0`, `uptime` 3:57).
Every operation in that round was read-only on the device (the only writes were staging copies in
`/sdcard/Download/kp/`): no reboot, no flashing, no change to the root state, no install/uninstall.

## S. Scene snapshot `[T]`

```text
device          <device-serial>  SM_F966W  q7qcsx  Android 17 / SDK 37
build           CP2A.260605.016 / CP2A.260605.016.F966WVLUDCZJB   (no OTA drift, DeviceLock constants still valid)
kernel          6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
ro.boot.bootreason  reboot,userrequested (this boot was a manual restart, not abnormal)
/dev markers    /dev/df, dfm0, dfm1, dfm2, dfm3, dfm5, **dfm6**   — no dfme2
marker time     2026-11-12 13:39 (the 3rd successful run of this boot)
manager         me.weishu.kernelsu  samsung-v2.2 (32687)  uid=10503  installed 11:52:04
ksud            samsung-v2.2 (uapi: 5), sha256 488355921cee4fae484f0c9f145784d9717f32b0aceafc8c9ea939c5938a47ab
```

The `dmesg` ring buffer had already wrapped (current uptime 12904 s, the init happened at ~105 s), so
**this** boot's ko init log was no longer available. That is a hard limit on "can we align today's init
sequence with the panic sequence", recorded as such.

## T. Key new facts `[T]`

| # | fact | evidence |
|---|---|---|
| P22 | **round 1's "shows success then black screen and reboot" was a real kernel panic inside the `kernelsu` module's `init_module`** | `store_extra_info.lst` of KP 31/32: `TASK=ksud`, `PANIC=synchronous external abort`, `PC=ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`, `LR=+0x14c`; `dumpstate_lastkmsg.lst` has the full `Internal error: … [#1]`, `Call trace` and `Kernel panic - not syncing` |
| P23 | **hypothesis A (ksud soft-reboot recorded as abnormal shutdown) is disproved**: `soft_reboot` sits after `touch(dfm6)` in `bootstrap.c:224-231`, and the kernel died during ko init, so not one line of `dfm6` ran | the trace root is `do_one_initcall` → `kernelsu_init` → `ksu_syscall_hook_manager_init` → `tracepoint_probe_register` → `tracepoint_add_func` → kretprobe trampoline, unrelated to bootstrap |
| P24 | **the trigger is deterministic, not random**: KP 31 and 32 share PC/LR offsets, ko build id (`b61aef7e3fae7d02afb759c7a4acdecdd07aea2e`) and log sequence line by line, differing only in boot time (uptime 109217 s vs 162 s) | side-by-side comparison of the two `dumpstate_lastkmsg.lst` |
| P25 | **exact chain**: `ksu_syscall_hook_manager_init` attaches a kretprobe to the `sys_enter` tracepoint's `regfunc` → `tracepoint_add_func` calls it back **synchronously** during registration → `syscall_regfunc_handler` → `ksu_mark_running_process_locked()` walks/marks processes; it crashes right after logging `tp_marker: mark process: pid:1, uid: 0, comm:init`. The registers hold `x6="KernelSU"`, `x7=": tp_mar"`, `x13="omm:init"` — fragments of that log format string | the `Call trace` and register dump of 31 |
| P26 | **the fault nature points to RKP/KDP page protection rather than a wild pointer**: it reports `synchronous external abort` (`do_sea`, DFSC=0b001110, HYP side `ESR_EL2=0x9200004e`, fault VA = `x19`), whereas a plain invalid pointer would report `Unable to handle kernel paging request`. `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED` / `TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` are the watchdog firing after the kernel is dead — **consequence, not cause** | `store_extra_info.lst` + the `eRR`/registers of 31/32; consistent with the SCS / KCFI / DEFEX / RKP environment determined in `REBOOT_TRIAGE.md` §2 `[A]` (inference, not yet proven by experiment) |
| P27 | **the manager used at 08:13 is not the same APK instance as now**: `/data/app/~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==`, uid 10463; now `~~SgtRsoT9Ew37h_UC1xUqJA==/me.weishu.kernelsu-9H2ZfUhhMCGravyfSqF45w==`, uid 10503, installed 11:52:04 | dropbox `SYSTEM_TOMBSTONE` at 08:14:26 (`Executable: .../libksud.so`, `Cmdline: ... debug su`) vs `dumpsys package` |
| P28 | the tombstones at 08:14/08:16 (`libksud.so debug su`, `me.weishu.kernelsu:root:0`, all `Data Abort Exception 0x24`) are **downstream** userspace crashes after the kernel died | as above; not independent faults |
| P29 | **this phone already had a full KernelSU environment in August**: `/data/adb/ksu/bin/ksud` is a symlink to `/data/adb/ksud`, mtime `2026-08-20 06:06`; `/data/adb/modules` (zygisk_vector, m_rcq, zygisksu) from 08-27; `/data/adb/lspd` | `ls -la` evidence; it explains the 9 uids in the panic log's allow list (including a root profile for <third-party-app>) — **that configuration was left by the August root, not created by this temporary root** |
| P30 | **`diag.log` read for the first time** (previously unreachable via `run-as`): three `ro.boot.bootreason=?` entries confirm P21's reflection defect; all 4 runs had `soft_reboot=false` and all ended `verdict=KernelSU loaded (dfm6)`; the 13:39 run recorded every marker `df` → `dfm0` → `dfm1` → `dfm2` → `dfm3` → `dfm5` | `evidence/20261112_173457/21_dfroot_diaglog.txt` |
| P31 | **`dumpstate_lastkmsg_*_KP.log.gz` are really ZIP** (`PK\x03\x04`) containing `store_extra_info.lst` (structured: RR/RWC/TASK/PANIC/PC/LR/RPM/TZ_RR/BUG/LKL), `eRR.p`, `dumpstate_lastkmsg.lst`, `reset_summary.html`, `ocimem.lst` and 2 more — 7 entries | `gzip.open()` raises `BadGzipFile: Not a gzipped file (b'PK')`; `tools/kp_inspect.py` was added to parse them |
| P32 | `dumpstate_latest_lastkmsg.log.gz` has exactly the same sha256 as 32 (`59d78da1e4eb79c359c55dc8e5bee23d73dfb1849b8a66be6072ec74b087b255`), i.e. the same copy; 28/29/30 are older panics from 10-14 and 10-22 (`__list_del_entry_valid_or_report`, `cve43499-run`), unrelated to DFRoot, used only as "what a normal panic looks like on this device" controls | all five pulled and hashed together |

## U. Decisions `[A]`

| # | decision | reason |
|---|---|---|
| U1 | **do not modify the verified lock2 APK**, even though root was available to test other changes | per P21: a change alters the APK hash and breaks the consistency between the verified artifact and the manufacturing record; this round's value is evidence, not code |
| U2 | **pin the manager to `me.weishu.kernelsu` = samsung-v2.2**, never swap it "because there is a newer one" | that combination is 4/4 on device, and the crashing ko is no longer on the device. Swapping throws away the only success baseline |
| U3 | write the conclusion into `BUILD_RECORD.md` §12.4 and `REBOOT_TRIAGE.md` §6c, **and state in both that "PC in `ksu_mark_running_process_locked`" is this project's known failure signature** | so a future "success then reboot" is classified in one look instead of a full triage |
| U4 | stop chasing the exact version of the 08:13 manager | nothing remains on the device to check (`pm list packages -u` shows only the current package, no 08:xx directory in `/data/user/0`, `/data/adb/ksu/log` keeps only two rotations). It would only come from the person's memory and does not affect the conclusion (a different APK instance is already proven by codePath/uid) |
| U5 | the evidence directory is **not committed** (`evidence/` is gitignored), but every key number, call trace and hash goes into the documents | consistent with Q9's reproducibility principle: the documents must allow the conclusion to be rebuilt independently |

## V. Evidence and toolchain limitations (added this round)

| # | item | status |
|---|---|---|
| R6 | the evidence archives ended up one nesting level deeper at `evidence/kp/kp/` and could not be flattened locally | harmless: `tools/kp_inspect.py` uses `os.walk`; move them by hand if you want it tidy |
| R7 | `adb pull /sdcard/...` fails under Git Bash (`failed to stat remote object 'C:/Program Files/Git/sdcard/...'`) | not a guard but MSYS path rewriting; add `MSYS_NO_PATHCONV=1`. Written into `BUILD_RECORD.md` §11 |
| R8 | `/sys/module/kernelsu` does not exist (while `/proc/modules` clearly shows `kernelsu 184320 … Live`), so the **current module's srcversion cannot be read** for a bit-level "same ko?" comparison | the fork hides that sysfs entry. The proof had to fall back to codePath/uid (P27). A bit-level comparison would need the fork to stop hiding `/sys/module/kernelsu`, or a fresh oops |

---

# Round 6: choices made when publishing (2026-11-12 late night)

Keeping this as a public repo involved the following **removals and rewrites**. They are recorded here
because "what was not published" matters as much as what was: anyone reading this repo should be able
to see what was deliberately taken out.

## W. Publication decisions

| # | decision | reason |
|---|---|---|
| W1 | publish as a **single commit** without the original development history | the original history carries a real-name commit signature and part of a chat log; a public repo only needs the final state |
| W2 | the public commit uses a neutral author identity, no real name or email | same reason as W1 |
| W3 | **do not publish** the conversation archive, the internal task list, the evidence directory, `deliverables/`, `toolchain/`, `src/` | respectively: personal information, internal process, device identifiers, third-party binaries, rebuildable environment and sources |
| W4 | **do not publish** any APK / manager / `kernelsu.ko` | signature pairing + licence + size; upstream download links and checksums are given instead (see `NOTICE.md`) |
| W5 | **do not publish** firmware or its screenshots; `firmware/` only holds a README and is gitignored | copyright + size + every device should use its own firmware |
| W6 | device serial numbers and third-party package names in the documents were replaced with placeholders; first/second person was rewritten into neutral narration | a serial number directly identifies a device; package names reveal what the person installed |
| W7 | keep **retracted conclusions** and failed attempts, no beautification | this is the most valuable part: it records which verification methods are unreliable (§P9/P11, §Q10) |
| W8 | add `tools/analyze_firmware.py` / `apply_lock.py` / `setup_toolchain.sh` | so "clone → drop your firmware → get a report → get an APK" is actually true, not just prose steps |
| W9 | add `docs/KP_CASE_STUDY.md` | that panic is the best "why you cannot guess" teaching material and deserves its own file |
| W10 | run a **content-level self-test** before publishing: rebuild with the public pipeline and compare the content digest (and the payload hashes), not the APK file hash | proves "the pipeline given to others" and "the pipeline that was verified" are the same one. A file-hash test would have been inconclusive: signing is randomised (see W11) |

## X. Self-test record for the public pipeline

```text
python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt
  -> KMI android15-6.6 / kernel 6.6.127 < 6.6.138 / SCS KCFI DEFEX RKP-KDP present, BTI absent
  -> the six constants are identical to the recorded target device's values

python tools/apply_lock.py --report analysis/…json  -> no-op (constants already identical)
bash build.sh --lock analysis/…json
  -> content digest 0418c10239f3eb175092a2d69e79b266e4940be13867ea6ed39ff3d96e62e916
     = identical to the verified lock2 content
  -> APK file sha256 2a2b59f7… on that machine, but that value is NOT reproducible (see W11)
```

## W11. The APK file hash is not reproducible, and the docs had to say so

Publishing exposed a claim that turned out to be wrong. §7.6 of `BUILD_RECORD.md` used to promise
"rebuild and the APK sha256 is still `2a2b59f7…`". That was measured inside a single build directory,
where Gradle reported every task up-to-date and simply re-printed the previously signed APK. A
stranger following the published instructions would never have seen that hash.

Re-measured properly, by building four times from four pristine clones of upstream:

```text
2a2b59f76640de5f…   4824a51afda989cc…   7d493b7b08a65659…   0093700a10276f83…
```

All four have 29 zip entries with identical names, sizes and CRC-32s — the content is the same; only the
APK Signing Block differs (a 336-byte region). Signing is randomised, so the file hash cannot be a
reproducibility criterion. Consequences, all applied:

| # | change | where |
|---|---|---|
| W11a | the "byte-identical rebuild" claim is replaced by content-level reproducibility, with all four measured hashes printed as evidence | `BUILD_RECORD.md` §7.6, `DELIVERY.md` §8 §10 |
| W11b | a single stable fingerprint was defined: SHA-256 over `(name, crc32, size)` of every entry, measured `0418c102…` across all four builds | `BUILD_RECORD.md` §7.6, `verify_apk.py` |
| W11c | `tools/verify_apk.py` was added so the check is one command and also proves the payloads and patch markers | tools |
| W11d | `build.sh` now runs that verification after every build and **fails** the build if the APK has no native payloads | `build.sh` |

## W12. A real bug found by building from the published tarball

The same re-measurement found a defect that only appears on a *pristine* source tree:
`build.sh` called `extract_native_payloads.py` without telling it where the source tree was, and the
script writes `app/src/main/jniLibs/...` relative to the cwd. On a fresh clone that meant the payloads
landed outside the tree, Gradle linked an APK with **no `lib/` at all** (65,056 bytes instead of
94,911), and the build still reported success. It installs and cannot run the exploit.

Earlier rounds never saw it because `src/DFRoot` already contained the payloads, so the extraction step
was skipped. Fixed by:

| # | change |
|---|---|
| W12a | `extract_native_payloads.py` takes `--dest <source root>` and resolves every output path under it, independent of cwd |
| W12b | `build.sh` passes `--dest "$SRC"` |
| W12c | `build.sh` runs `verify_apk.py` afterwards, so a payload-less APK now fails loudly instead of shipping |
| W12d | the pitfall is written into `BUILD_RECORD.md` §11 with the exact size difference (65 KB vs 95 KB) as the tell |

Verification after both fixes, from a pristine clone, plain `bash build.sh` with no flags:

```text
[*] applying patches/dfroot-f966w.patch
destination root: …/dfroot_fresh4
BUILD SUCCESSFUL
content digest : 0418c10239f3eb175092a2d69e79b266e4940be13867ea6ed39ff3d96e62e916
VERDICT: PASS
```

`analyze_firmware.py` also corrected an implementation bug along the way: the first version read
`6.6.127-android15-8-p4a765df-…` as `android15-8.x` (mistaking the build digit for the kernel
sublevel), which broke the KMI verdict. The correct parse is: **the kernel sublevel comes from the
first three fields of the release**, the Android version from `-android<N>-`, and the two are joined
into the KMI. "Looks like a number, must be a version" is a common mistake in firmware analysis;
recorded here so it is not repeated.

## Y. Verifications that were not published

| item | status |
|---|---|
| availability on other KMIs (`android16-6.12` etc.) | untested; `analyze_firmware.py` reports `untested` |
| behaviour differences of DEFEX/RKP on other Fold7 models (F966B/U/E/N…) | untested; `DeviceLock`'s comments say so |
| whether the crash is probabilistic | already classified as **deterministic** in `KP_CASE_STUDY.md` (identical PC and module build id twice), but only for that particular ko |
