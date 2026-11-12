# Case study: diagnosing a "SUCCESS then black screen reboot" kernel panic

> English edition. Chinese original: [`KP_CASE_STUDY.zh-CN.md`](KP_CASE_STUDY.zh-CN.md) — that file is
> the record of what was measured; where the two disagree, the Chinese file wins.

> This is teaching material: a real temporary-root failure taken from guesswork to a closed diagnosis,
> including the wrong turns and the one step that actually decided it.

---

## 1. Symptom

| item | content |
|---|---|
| symptom | tap LAUNCH ROOT, the app prints `***SUCCESS***`, then the screen goes **black immediately and the phone reboots**; `su` is gone afterwards |
| device | Galaxy Z Fold7 (Canada) `SM-F966W` |
| firmware | `CP2A.260605.016.F966WVLUDCZJB` |
| kernel | `6.6.127-android15-8-p4a765df-…-4k` (KMI `android15-6.6`) |
| first guess | the first APK (lock1) did not force `Auto Soft Reboot` off, so the obvious explanation was "`ksud soft-reboot` got recorded as an abnormal shutdown" |

---

## 2. Why "it says SUCCESS" proves nothing

Both branches of `main()` in `app/src/main/jni/bootstrap.c` return 0:

```c
if (run_ctx(NULL, {KSUD, "late-load", "--package-name", su_manager, NULL}) == 0) {
    touch("/dev/dfm6");   // ksud exit code 0
    if (soft_reboot) { ... run_ctx("u:r:ksu:s0", {KSUD, "soft-reboot"}); }
} else {
    touch("/dev/dfme2");  // ksud failed
}
return 0;                 // ← both branches land here
```

Because both branches `return 0`, the Java side always sees `rc=0` and prints SUCCESS. The real
criterion is the `/dev/df*` marker: `dfm6` = KernelSU installed, `dfme2` = not installed. A reboot
wipes `/dev`, so the **first step** of any post-mortem is to make the app persist those markers.

---

## 3. Where the logs are, and one gotcha you must know

| item | content |
|---|---|
| what is lost | `dmesg` / `logcat` live in RAM; after a kernel panic the previous boot's content is **gone** |
| what survives | **dropbox** (`/data/system/dropbox`) and Samsung's **`/data/log/dumpstate_lastkmsg_*_KP.log.gz`**. The latter: the directory is listable but the files are `system:log 0640`, so you need the temporary root to copy them out |
| gotcha | despite the `.log.gz` name they are **ZIP** (`PK\x03\x04`); `gzip.open()` raises `BadGzipFile: Not a gzipped file (b'PK')` |
| the useful entry | not the 2 MB kernel log but `store_extra_info.lst`, a single line of structured fields |

Fields inside `store_extra_info.lst`:

```
RR      reset reason class ("KP" = the previous boot ended abnormally)
RWC     rolling record number
TASK    the task that faulted
PANIC   panic class
PC, LR  program counter / link register, with module name and offset
RPM     RPM / hypervisor side reason
TZ_RR   secure world reset reason
BUG     source file:line for a BUG() hit
LKL     truncated kernel log
```

---

## 4. The five archives, side by side

| # | date | TASK | PANIC | PC |
|---|---|---|---|---|
| 28 | 10-14 13:46 | RenderThread | Oops - BUG (`lib/list_debug.c:67`) | `__list_del_entry_valid_or_report+0xec` |
| 29 | 10-14 16:39 | `cve43499-run` | Oops | `_raw_spin_trylock+0x1c` |
| 30 | 10-22 14:21 | Jit thread pool | Oops - BUG (`lib/list_debug.c:64`) | `__list_del_entry_valid_or_report+0xdc` |
| **31** | **11-12 08:13** | **ksud** | **synchronous external abort** | **`ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`** |
| **32** | **11-12 08:16** | **ksud** | same | same function, **same offset** |

28/29/30 predate this route (the October experiment was something else) and serve as controls: the
record format is stable, so the agreement between 31 and 32 is signal, not coincidence.

---

## 5. The decisive evidence

```
ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu b61aef7e3fae7d02afb759c7a4acdecdd07aea2e]
 syscall_regfunc_handler+0x4c/0x88        [kernelsu b61aef7e…]
 __kretprobe_trampoline_handler+0xcc/0x140
 trampoline_probe_handler+0x28/0x48
 __kretprobe_trampoline+0x74/0xcc
 tracepoint_add_func+0x64/0x404
 tracepoint_probe_register+0x60/0xa4
 ksu_syscall_hook_manager_init+0xa8/0xe4  [kernelsu b61aef7e…]
 kernelsu_init+0xec/0x130                 [kernelsu b61aef7e…]
 do_one_initcall -> do_init_module -> load_module -> __arm64_sys_init_module
```

The kernel log immediately before it:

```
KernelSU: hook_manager: ksu_hook_manager_init called
KernelSU: hook_manager: register_syscall_regfunc kretprobe: 0
KernelSU: registered syscall hook for nr=147 / 221 / 79 / 48
KernelSU: tp_marker: mark process: pid:1, uid: 0, comm:init
Internal error: synchronous external abort: 0000000096000010 [#1] PREEMPT SMP
...
pc : ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]
Kernel panic - not syncing: synchronous external abort: Fatal exception
```

How to read it:

1. **The PC is inside the `[kernelsu]` module** and `do_init_module` is on the stack → the crash
   happened **while that kernel module was loading**, not in DFRoot's exploit, not in `dfroot.ko`, and
   certainly not in a userspace `ksud soft-reboot`.
2. `tracepoint_add_func` on the same stack means the trigger is the kretprobe that fires synchronously
   while the `sys_enter` tracepoint is being registered — KernelSU's syscall-hook init path.
3. `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED`, `TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` are the watchdog
   firing **after** the kernel is already dead: consequence, not cause. Treating those fields as the
   cause sends you in the wrong direction for hours.
4. A `synchronous external abort` (`do_sea`, DFSC = `0b001110`) is not the same as
   `Unable to handle kernel paging request`: the former usually means the page access was refused by a
   lower layer (this device has Samsung RKP/KDP plus KCFI), the latter is a plain wild pointer. The
   registers here (`x19` equals the hypervisor-reported fault VA) support the former.
5. Both panics share the **same ko build id** (`b61aef7e…`), the same PC offset and the same log
   sequence line by line → a **deterministic** code path in that binary, not flakiness.

---

## 6. What got ruled out

| hypothesis | verdict | why |
|---|---|---|
| `ksud soft-reboot` recorded as an abnormal shutdown | **no** | `soft_reboot` runs after `touch(dfm6)`, and the kernel died inside the ko's `init_module`, so `dfm6` was never written |
| late-load failure (ksud never started) | no | four later runs on the same device all reached `/dev/dfm6` |
| `dfroot.ko`'s own patching | no | `dfroot` is not on the stack; the crash is in `[kernelsu]` |
| upstream 4.7 missing #185 | no | the hook landed and patched successfully; four later runs succeeded |
| a random ko crash | no | identical twice, and the later binary does not crash — so "the ko back then" and "the ko now" are not the same binary |

That "ko back then" was a different APK instance from "the ko now"; the evidence comes from a dropbox
crash tombstone:

```
SYSTEM_TOMBSTONE  2026-11-12 08:14:26
Executable: /data/app/~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==/lib/arm64/libksud.so
Cmdline:    .../libksud.so debug su
uid: 10463
```

whereas the later, working install of the same package name is a different `/data/app` instance with a
different uid.

---

## 7. Reproducing this evidence collection

```bash
# 1) get the temporary root first (it only lives in this boot), then copy the archives out immediately
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell "su -c 'mkdir -p /sdcard/Download/kp && \
  cp -f /data/log/dumpstate_lastkmsg_*_KP.log.gz /sdcard/Download/kp/ && \
  chmod 644 /sdcard/Download/kp/*'"
MSYS_NO_PATHCONV=1 $ADB pull /sdcard/Download/kp/ evidence/kp/

# 2) read them (.gz is really ZIP — use the dedicated tool, not gzip)
python tools/kp_inspect.py evidence/kp --extract evidence/kp/extracted
```

`MSYS_NO_PATHCONV=1` is only needed on Git Bash, otherwise `/sdcard/...` is rewritten to
`C:/Program Files/Git/sdcard/...`.

---

## 8. Five reusable lessons

1. **`SUCCESS` only means "the exploit worked"**, not that the kernel module is installed. The verdict
   is always `/dev/dfm6` vs `/dev/dfme2`.
2. **Do not count on `dmesg`/`logcat` after a crash**; go to dropbox and the vendor's KP archive.
3. **Watchdog and reset-reason fields are consequences**; find where the PC landed first.
4. **When the PC is inside a module, read that module's build id** (it is right there in the oops line)
   before swapping versions — otherwise you swap and end up with the same binary.
5. **The temporary-root window is finite**: collect the logs between "got root" and "next reboot", and
   put that step in your checklist.
