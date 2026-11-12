# Black screen / root gone — triage and handling (English)

> English edition. Chinese original: [`REBOOT_TRIAGE.zh-CN.md`](REBOOT_TRIAGE.zh-CN.md) — that file is the record of what was
> measured; where the two disagree, the Chinese file wins. Section numbers are identical.

Observed symptom (on-device report): DFRoot with the KernelSU mode selected, log/toast says success,
**the screen immediately goes black and the phone reboots**, and root is gone afterwards.
This document gives: (1) the device kernel facts measured here from the boot image; (2) why "it says
success" does not mean KernelSU got installed; (3) what the newly delivered APK (lock2) changes;
(4) the experiments that rule out whole classes of causes, in order.

---

## 1. First, a key misreading to correct: `***SUCCESS***` does not mean KernelSU is installed

`main()` in `app/src/main/jni/bootstrap.c`:

```c
if (run_ctx(NULL, { KSUD_STAGE, "late-load", "--package-name", su_manager, NULL }) == 0) {
    touch("/dev/dfm6");            // ksud exit code 0
    ...
} else {
    touch("/dev/dfme2");           // ksud exit code non-zero
}
return 0;                          // ← both branches land here
```

So **bootstrap returns 0 even when ksud fails**, and the Java-side `ExploitRunner` takes that 0 and
prints SUCCESS / a toast. What actually distinguishes success is the marker files in `/dev`:

| Marker | Meaning (from `lkm/dfroot.c` + `jni/bootstrap.c`) |
|---|---|
| `/dev/df` | the shellcode in `init` ran (ko dropped and `insmod` succeeded) |
| `/dev/dfm0` | dfroot.ko → usermodehelper started a shell |
| `/dev/dfm1/2/3` | bootstrap started / read prefs / adopted the zygote environment |
| `/dev/dfm5` | about to `exec ksud late-load` |
| **`/dev/dfm6`** | **ksud late-load exited 0 — KernelSU is actually loaded** |
| **`/dev/dfme2`** | **ksud late-load exited non-zero — KernelSU is not installed** |

So "it shows success" proves only this much: the exploit worked, `dfroot.ko` entered the kernel,
SELinux was set permissive, and bootstrap ran. It **does not prove** the KernelSU module loaded. A
reboot wipes everything under `/dev`, and which step the previous boot reached becomes unknowable —
which is exactly what the lock2 build addresses (see §4).

---

## 2. Device kernel facts measured here from `boot.img.lz4` (reproducible, no phone needed)

Kernel `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k`,
kernel sha256 `a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51`
(`build_logs/kernel.img`, unpacked by `tools/lz4frame.py`). Configuration judged from the kallsyms
name table:

| Fact | Evidence (kallsyms / strings) | What it means for this failure |
|---|---|---|
| **CONFIG_SHADOW_CALL_STACK = y** | `scs_alloc`, `scs_cleanup`, `scs_free`, `scs_init`, `scs_patch`, `scs_patch_vmlinux`, `scs_prepare`, `scs_release`; vmstat `shadow_call_stack`; `irq_shadow_call_stack_ptr` | The KernelSU upstream fix from 10-22 ("`task_pt_regs(current)` computed a wrong offset → EL1 translation fault → immediate reboot", commit `bbd9b2480`, for A065/MTK SCS=n devices) **does not apply here**: this project is SCS=y with `task_struct->stack` at 0x38 |
| **KCFI enabled** | `Oops - CFI`, `__cfi_` (kprobe blacklist prefix) | Any patched function entry / mismatched function pointer type → **immediate panic**. DFRoot and KSU both patch kernel functions, so this amplifies every "patch the kernel and it dies" risk |
| **Samsung DEFEX present** | `task_defex_enforce`, `task_defex_user_exec`, `task_defex_zero_creds`, `task_defex_link_protection` and 43 `*_defex_*` occurrences in total | DFRoot's ko patches two of them; the Samsung KernelSU additionally disables DEFEX at runtime through a jump label (fork commit `69f6f2571`) — **that path is the most suspicious panic source** |
| **Samsung RKP + KDP present** | `rkp_init`, `rkp_pgt_bitmap`, `rkp_dbl_bitmap`, `init_mm_pgd`, `id_map_pgd`, `tramp_pgd`, `_KMEM_TYPE`, `CRED_JAR_TYPE`, `TSEC_JAR_TYPE`, `selinux_enforcing_va`, `kdp_*` | Kernel text/rodata/page tables are hardware-protected; the KSU fork's `kernel/compat/rkp.c` has to deal with it. Upstream only fixed "Fix RKP to do bulk write" on 10-15 (already in v2.2) |
| **No BTI kernel support** | `system_supports_bti` / `ARM64_HAS_BTI` absent entirely | The other upstream change from 10-22 (`76a088c5f`, stricter BTI landing-pad detection) **most likely does not matter here** (no BTI enforcement) |
| Symbols DFRoot's ko depends on are all present | `kallsyms_lookup_name`, `aarch64_insn_patch_text`, `module_kallsyms_lookup_name`, `call_usermodehelper_setup/exec`, `invalidate_inode_pages2`, `kern_path`, `path_put`, `selinux_state`, `avc_has_perm_noaudit` | Consistent with the observation that the exploit worked and the ko loaded |

**Conclusion**: on this device neither of the two post-v2.2 upstream fixes looks like the cure; the
most likely panic point is **KernelSU's Samsung-side runtime patching (DEFEX jump label / RKP / KCFI
interaction)** — but that has to be proven with logs, not guessed.

---

## 2b. One retracted lead (kept here so it is not re-walked)

This document once concluded, from "search the kernel image bytes for symbol names", that all three
KernelSU LKMs hard-depend on `__tracepoint_sys_enter` / `mntns_operations` / `selinux_blob_sizes`
and that the device lacked them, and treated that as the primary lead. **That conclusion is wrong and
is retracted.** Two mistakes:

**Mistake 1: the method is invalid.** One sampling is enough to show it:

| Symbol | literal string in kernel.img | reality |
|---|---|---|
| `do_exit`, `init_task`, `init_mm`, `selinux_state`, `strchr` | present | genuinely exists |
| `cpu_switch_to`, `__cpu_setup` | absent | **genuinely exists** (assembly symbols, no BTF) |
| `mntns_operations`, `selinux_blob_sizes` | absent | undetermined |

Literal names findable in the image come from only two stores: the **BTF string table** (present here:
3,816,744 B of types / 2,608,839 B of strings / 141,000 unique strings at image offset 25,873,004)
and **`__ksymtab_strings` (exported symbol names)**. Every name in `kallsyms_names` is **token
compressed**, so most names never appear literally. BTF is incomplete too: it lacks even `init_mm`,
`init_pid_ns`, `system_wq`, `tasklist_lock`, `strchr`, `kmalloc_caches` (20 of the LKM's 236 imports
are not in BTF). So "not found" cannot prove "does not exist".

A proper kallsyms decode was attempted (`kallsyms_token_table` / `kallsyms_token_index` /
`kallsyms_num_syms` signature scanning) and failed to locate them in this image. That script was
deleted rather than left in the repo pretending to be a working tool.

**Mistake 2: even if true, it cannot explain the symptom.** Reading `load_module()` in
`userspace/ksuinit/src/lib.rs` (local copy `_probe/ksuinit_lib.rs:317-390`):

```rust
for name in unresolved_symbols.keys() {
    log::warn!("Cannot find symbol: {}", name);   // warn only
}
...
match init_module(&buffer, params) { ... }        // loads anyway
```

Unresolved symbols stay `SHN_UNDEF`, so the module loader looks them up by name in `__ksymtab`; a miss
means `Unknown symbol` → `init_module` returns an error → `ksud` fails → `/dev/dfme2` is left behind.
**The prediction of that path is "clean failure, no root, no reboot", which contradicts "black screen
and reboot".**

Put differently: **a missing symbol can at worst prevent the module from loading; it cannot cause a
reboot.** The symptom requires "the ko got loaded, and then it crashed". That reasoning actually
pushes hypothesis 1 (KernelSU runtime patching) further forward.

**One more important fact**: `/proc/kallsyms` is **Permission denied** for the `shell` domain on this
device (SELinux, not `kptr_restrict`). So "grep kallsyms over adb" is a dead end and should not appear
in any procedure again. The workable substitute is the `/dev/df*` markers plus dropbox (see §5 step 0).

## 3. Upstream history with the same symptom (why swap the manager first)

Every "panic/reboot right after SUCCESS" Samsung report on `diabl0w/DFRoot` was resolved by **changing
or upgrading the build**:

| issue | device | outcome |
|---|---|---|
| [#111](https://github.com/diabl0w/DFRoot/issues/111) | Galaxy A53 | samsung-v1.0 fine; **v1.1 froze and auto-rebooted after SUCCESS**; after reading `dumpstate_lastkmsg_*_KP.log` the author called it an "easy fix" and shipped it after two CI runs |
| [#110](https://github.com/diabl0w/DFRoot/issues/110) | Galaxy A53 | same symptom, v1.1 was pulled by the author |
| [#122](https://github.com/diabl0w/DFRoot/issues/122) | Galaxy M55 | v1.0 works, v2.0 panics; fixed in CI. Also clarified a ksud bug where it soft-reboots even with the option off |
| [#131](https://github.com/diabl0w/DFRoot/issues/131) | Galaxy A53 | DFRoot v4.5 regression, gone after switching to a newer DFRoot CI build |
| [#153](https://github.com/diabl0w/DFRoot/issues/153) | Samsung | "v1.0 is the only manager that does not panic" |

In other words: **same exploit binary, different manager (= different `kernelsu.ko`) turns a panic
into a working root.** The manager pinned by this project is `KernelSU samsung-v2.2` (2026-10-15,
build 32687), and diabl0w/KernelSU main has two more kernel-side commits after it (10-22). But there is
**no** public release newer than v2.2 upstream; fixed builds only exist as Actions artifacts (login
required). A verified public alternative: `DaniTheSillyFem/KaySU samsung-v2.4` (2026-11-07) — diffed
against upstream main `76a088c5f`, the only differences are 6 files (3 workflows, README, the manager
package name/cert fingerprint in `kernel/Kbuild`, the manager's AndroidManifest theme) plus localized
strings; **the kernel C code is identical to upstream main**. Details and hashes in
`deliverables/managers/MANAGERS.md`.

---

## 4. What this round changed (new APK: lock2)

`src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk`
versionCode 4701 / versionName `4.7-f966w-czjb-lock2`,
sha256 `2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7`.
Same signature as lock1 (AGP debug certificate), so **it installs over lock1 without uninstalling**.
The native payloads (`libdfroot.so` / `libbootstrap.so`) are byte-identical to official v4.7.

All changes are on the Java side (the exploit binaries are untouched):

1. **New `Diagnostics.java`**: writes the run into `df.root`'s device-encrypted storage
   `files/diag.log` (survives reboot, no unlock needed), polling the `/dev/df*` markers every 150 ms
   and persisting each one as it appears.
   → After a reboot you can still see **which step the previous boot reached**.
2. **Success verdict reaches the end**: after the exploit process exits it keeps waiting up to 90 s;
   `/dev/dfm6` reports "KernelSU loaded", `/dev/dfme2` reports "exploit OK but ksud failed = no root",
   and a timeout lists the markers that do exist with the hint
   "dfm5 present, dfm6 absent = died inside ksud late-load".
3. **Post-boot autopsy**: every launch/boot broadcast writes a line
   `=== BOOT id=… ro.boot.bootreason=… sys.boot.reason=… ===` and echoes the last 14 lines of the
   previous kernel boot (different `boot_id`) to the UI.
   → Without adb and without root you can tell "kernel panic reboot" from "framework soft reboot".
4. **`Auto Soft Reboot` forced OFF**: the DE prefs are written back to false before running
   (`bootstrap.c` reads the XML directly, so a synchronous commit is used). The Settings entry is
   greyed out with a note. Reason: in #122 a ksud bug soft-rebooted even with the option off, so this
   variable is removed from the experiment.
5. New menu entries **Run log** (shows the last 120 lines of diag.log — a screenshot is enough) and
   **Markers now** (current /dev markers).

---

## 5. Experiment steps (step 0 done; only step 2's KP logs remain)

> **2026-11-12 evening update**: step 0 is done and succeeded, and step 1 (manager matrix) no longer
> needs to be run. Only step 2 (pulling the `dumpstate_lastkmsg_*_KP` logs) is left. The original
> steps are kept below as a record.

### Step 0 · one clean reproduction + evidence 【done】

1. Install lock2 on the phone (it installs over lock1). Open DFRoot:
   - Settings: `Start at Boot` **off**; `Auto Soft Reboot` should now be greyed out (OFF);
     `Disable KSU Modules` **off** (no modules were installed).
   - Choose the manager (start with group A in §5.2).
2. Tap **LAUNCH ROOT** and **start timing** (watch the phone clock's second hand). Note:
   - how many seconds from the tap to the black screen (<3 s / 5–10 s / 30 s+);
   - after the reboot, reopen DFRoot → menu **Run log** → **screenshot**; menu **Markers now** →
     **screenshot**. These two screenshots usually pin down which link in the chain broke.
3. Connect the phone to a PC and double-click `tools/evidence.bat` (it uses the project's
   `toolchain/.../adb.exe`), then hand over the whole generated `evidence/<timestamp>/` directory.
   Look at these files first:

   | file | what to look for | verdict |
   |---|---|---|
   | `02_bootreason.txt` | `ro.boot.bootreason` containing `panic` / `wdt` / `watchdog` | **the kernel restarted itself** |
   | `02_bootreason.txt` | containing `reboot,userspace` / `reboot,shell` / `soft` | **Android framework soft reboot** |
   | `03_dropbox_last_kmsg.txt` | any content = the kernel log of the crash | most valuable, can localise directly |
   | `04_dropbox_restart.txt` | who requested this restart | separates panic from a userspace reboot |

   dropbox lives in `/data/system/dropbox`, is **unrelated to the reboot and is retained**; `dmesg`
   and `logcat` live in RAM, so after a panic the previous boot's content is gone. That is why
   `03` / `04` matter more than `08` / `09`.

   Note: `/proc/kallsyms`, `/data/log`, `pstore` and `/proc/last_kmsg` are all denied to the `shell`
   domain (SELinux); those files are usually empty or `Permission denied`, which is expected.

### Step 1 · decide whether it is a manager (`kernelsu.ko`) problem

Same device, same lock2 APK, only the manager changes; two runs per group, with Run log screenshots:

| group | manager | what it would rule out |
|---|---|---|
| **A** (the one in use) | `KernelSU samsung-v2.2` (build 32687, 10-15) | baseline |
| **B** | `KaySU samsung-v2.4` (build 32702, 11-07, includes both upstream 10-22 kernel fixes) | if B works → it is a v2.2 ko problem; settle on B |
| **C** | `KernelSU samsung-v1.0` (build 32664, 10-05, before the Samsung jump-label/DEFEX rework) | if C does not panic but has no root → the panic comes from the Samsung runtime-patching path (the old #111/#153 pattern) |

> Managers use different package names (`me.weishu.kernelsu` / `me.ella.kaysu`) and can coexist; but
> **KaySU's ko only accepts KaySU's own manager signature**, so group B must install KaySU's APK and
> select it in DFRoot. Re-select the manager in DFRoot's dropdown after switching.
>
> Also: after a successful late-load, ksud runs `am force-stop` + `am start` on the manager
> (late_load.rs step 14). So "the screen blinks and the manager closes and reopens" is normal, not a
> reboot; and that `am start` line hardcodes the class `me.weishu.kernelsu.ui.MainActivity`, so it
> fails with KaySU → **you must open KaySU manually to see the status** (see MANAGERS.md group B).

### Step 2 · as soon as any run succeeds, pull the panic logs (the only path to a cure)

> **This is the only remaining to-do.** Root is temporary and lives only in the current boot, so
> pulling the logs has to happen between "getting root" and "rebooting". Exact commands in
> `BUILD_RECORD.md` §12.4.

Samsung generates the previous crash's last_kmsg **after the next boot**, in `/data/log/`, with `KP`
(kernel panic) in the name:

```sh
su
ls -l /data/log | grep -i dumpstate
cp /data/log/dumpstate_lastkmsg_*KP*.gz /sdcard/Download/
exit
```
then `adb pull /sdcard/Download/`. With a panic backtrace (pc/lr/call trace/addresses written) you can
decide whether it is DEFEX jump-label, RKP write permission or KCFI type checking, and therefore
whether to modify the ko, swap the manager, or abandon the route. (That is how the upstream author
localises every issue.)

### Step 3 · if BootReceiver causes a boot loop

Do not enable `Start at Boot`. If it was enabled and you are boot looping: hold **Volume Down** during
boot to enter safe mode (AOSP/Samsung common), then disable DFRoot's Start at Boot or uninstall DFRoot
(the official remedy in DFRoot's README).

---

## 6. Status (2026-11-12 night: case closed, see §6c)

> **In one line**: round 1's "shows success then black screen and reboot" was a real kernel panic
> inside the `kernelsu` module's `init_module` (`ksu_mark_running_process_locked+0x154`), not a
> soft-reboot. Conclusion and evidence: **§6c**; full call trace and scene: `BUILD_RECORD.md` §12.4.

**lock2 succeeded on device**: four times (12:03 / 12:19 / 12:36 / 13:39), about 2–3 s each,
`/dev/dfm6` present, manager `me.weishu.kernelsu` (samsung-v2.2). Full run log and timestamps in
`BUILD_RECORD.md` §12.

So the triage above is no longer the main task, and the **manager matrix (original step 1) no longer
needs to be run**: group A succeeds directly.

But one thing did **not** get closed: `ls /data/log` (no root needed) exposed the KP logs on this device:

```text
dumpstate_lastkmsg_28_20261014_134615_KP.log.gz
dumpstate_lastkmsg_29_20261014_163921_KP.log.gz
dumpstate_lastkmsg_30_20261022_142106_KP.log.gz
dumpstate_lastkmsg_31_20261112_081336_KP.log.gz   ← the day of round-1's failures
dumpstate_lastkmsg_32_20261112_081607_KP.log.gz   ← the day of round-1's failures
```

`_KP` means "the previous boot did not shut down normally"; the content may be a real panic, or just a
normal log truncated by a hard reset. **08:13 / 08:16 fall exactly inside the "shows success then black
screen" window**, so that reboot was probably kernel-side rather than the software reboot previously
suspected.

### 6.1 The two remaining possibilities and what each predicts

| # | hypothesis | relation to known evidence | how the KP log decides it |
|---|---|---|---|
| A | **`ksud soft-reboot` recorded as an abnormal shutdown** (`bootstrap.c` only calls `ksud soft-reboot` after `dfm6` when `soft_reboot==true`; lock1 did not force that switch off) | fits "reboot right after success, root gone"; also fits lock2 succeeding (lock2 forces it off) | the log **stops dead with no exception stack**, ending in ordinary kernel messages |
| B | **KernelSU crashing the kernel while patching at runtime after loading** (DEFEX jump label / RKP / KCFI) | also fits the symptom, but contradicts lock2 succeeding twice (unless it is probabilistic; upstream #152 did report random panics) | ends with `Unable to handle kernel` / `Oops` / `BUG:` / `Internal error`, and the `Call trace` PC lands in the `kernelsu` segment |

Both can be decided without changing code — **just run the two commands in §12.4** (temporary root
takes about 2 seconds).

### 6.2 Pulling the KP logs 【done, 2026-11-12 evening】

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
# tap LAUNCH ROOT on the phone, wait ~2 s
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_3*_KP.log.gz /sdcard/Download/"
$ADB pull /sdcard/Download/ evidence/kp/
```

When this was actually run the phone still held the temporary root, so all five were pulled in one go.
Note that these `.log.gz` files are really ZIP: read them with
`python tools/kp_inspect.py evidence/kp`. The full verdict table, call trace and evidence sources are
in **`BUILD_RECORD.md` §12.4**.

---

## 6c. Case closed (measured 2026-11-12 at night)

**Verdict: hypothesis B holds, hypothesis A is void.**

| question | answer | evidence |
|---|---|---|
| what was round 1's "shows success then black screen and reboot" | **a real kernel panic**, inside the `kernelsu` module's `init_module` | `store_extra_info.lst` of KP 31/32: `TASK=ksud`, `PANIC=synchronous external abort`, `PC/LR=ksu_mark_running_process_locked+0x154/0x14c` |
| exact location | `ksu_syscall_hook_manager_init` attaches a kretprobe to the `sys_enter` tracepoint's `regfunc`; `tracepoint_add_func` calls it back synchronously, and inside that callback the crash happens right after `tp_marker: mark process` logs | full call trace in `BUILD_RECORD.md` §12.4.1 |
| random or deterministic | **deterministic**: same PC offset, same ko build id (`b61aef7e…`), same log sequence line by line | comparing 31 and 32 |
| was it a soft-reboot | **no**. `soft_reboot` sits after `dfm6` in `bootstrap.c`; this kernel died during ko init, so `dfm6` was never reached | `bootstrap.c:224-231` + the panic call trace |
| why do 4 runs succeed now | the manager at 08:13 was not the same APK instance as today's (different `/data/app` instance hash and uid); today's `samsung-v2.2` is 4/4 | `dumpsys package` vs the 08:14 `SYSTEM_TOMBSTONE` |
| is the watchdog bite the cause | no, it is the result | `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED`, `TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` appear after the panic |
| what risk remains | only 4 successful samples of the current combination; the ko that crashed is no longer on the device, and **its exact version number cannot be recovered from the device** | see `BUILD_RECORD.md` §12.4.3 |

**Operational conclusion**: pin the manager to `me.weishu.kernelsu` = `samsung-v2.2` (the combination
that is 4/4), and do not swap the manager "just to update it". If "success then black screen and
reboot" ever returns, pull the KP logs per §6.2 first — and compare against the PC
`ksu_mark_running_process_locked`.

---

## 6b. Historical hypotheses (kept, no longer the main line)

| # | hypothesis | result |
|---|---|---|
| 1 | KernelSU's ko crashes the kernel by patching DEFEX/jump labels at runtime | **holds, but at an earlier stage**: not runtime patching; it crashes inside the ko's `init_module` while `/tp_marker` is marking processes, see §6c |
| 2 | late-load failed and something else caused the reboot | ruled out: `/dev/dfm6` was observed, ksud succeeded |
| 3 | `ksud soft-reboot` perceived as a reboot | **disproved**: the panic happens during ko init, the `dfm6`/soft-reboot code never ran, see §6c |
| 4 | dfroot.ko's own patching crashed | ruled out: the chain reached bootstrap and the ko loaded |
| 5 | upstream 4.7 lacking #185 makes the hook position unstable | ruled out: the hook landed and patched successfully |

---

## 7. Known side effect noted along the way

The Z Fold7 has a separate "cover display does not light up after a reboot" issue in the
DFRoot / Root-My-Galaxy community (`diabl0w/DFRoot` #76 → `BuSung-dev/Root-My-Galaxy` #235, needs one
extra root command to fix). If root ever becomes stable and you then hit a black cover display, that is
a different problem and unrelated to this panic.
