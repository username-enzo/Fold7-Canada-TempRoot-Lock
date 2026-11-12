# 案例研究：一次"显示成功后黑屏重启"的内核 panic 定案

# Case study: diagnosing a "SUCCESS then black screen reboot" kernel panic

> 这一篇是**教学材料**：把一次真实的临时 root 失败从"猜"做到"定案"的全过程摊开，
> 包括走错的路、以及哪一步才是决定性的。
> This is teaching material: a real temporary-root failure taken from guesswork to a closed
> diagnosis, including the wrong turns and the one step that actually decided it.

---

## 1. 现象 / Symptom

| 中文 | English |
|---|---|
| 手机上点 LAUNCH ROOT，应用显示 `***SUCCESS***`，随后**立刻黑屏并重启**；重启后 `su` 失效。 | Tap LAUNCH ROOT, the app prints `***SUCCESS***`, then the screen goes black and the phone reboots; `su` is gone afterwards. |
| 设备：Galaxy Z Fold7 (Canada) `SM-F966W`，`CP2A.260605.016.F966WVLUDCZJB`，内核 `6.6.127-android15-8-p4a765df-…-4k`（KMI `android15-6.6`）。 | Device: Z Fold7 (Canada) `SM-F966W`, build `CP2A.260605.016.F966WVLUDCZJB`, kernel `6.6.127-android15-…-4k` (KMI `android15-6.6`). |
| 第一版 APK（lock1）没有强制关闭 `Auto Soft Reboot`，所以最初的自然猜测是"`ksud soft-reboot` 被当成异常关机"。 | The first APK (lock1) did not force `Auto Soft Reboot` off, so the obvious first guess was "`ksud soft-reboot` got recorded as an abnormal shutdown". |

---

## 2. 为什么"显示 SUCCESS"什么也证明不了 / Why SUCCESS proves nothing

`app/src/main/jni/bootstrap.c` 里两个分支都返回 0：

```c
if (run_ctx(NULL, {KSUD, "late-load", "--package-name", su_manager, NULL}) == 0) {
    touch("/dev/dfm6");   // ksud exit code 0
    if (soft_reboot) { ... run_ctx("u:r:ksu:s0", {KSUD, "soft-reboot"}); }
} else {
    touch("/dev/dfme2");  // ksud failed
}
return 0;                 // ← both paths
```

Both branches return 0, so the Java side always sees `rc=0` and prints SUCCESS. The real verdict is
the `/dev/df*` marker: `dfm6` = KernelSU loaded, `dfme2` = it did not. A reboot wipes `/dev`, which is
exactly why the first step of any post-mortem is to make the app persist those markers to disk.

---

## 3. 日志在哪里，以及一个必须知道的坑 / Where the logs are, and one gotcha

| 中文 | English |
|---|---|
| `dmesg` / `logcat` 在内存里，内核 panic 后上一次开机的内容**全部丢失**。 | `dmesg` and `logcat` live in RAM; after a kernel panic the previous boot's content is gone. |
| 真正跨重启保留的是 **dropbox**（`/data/system/dropbox`）和 **Samsung 的 `/data/log/dumpstate_lastkmsg_*_KP.log.gz`**。后者目录可列、文件不可读（`system:log 0640`），必须借临时 root 才能拷出来。 | What survives is **dropbox** and Samsung's **`/data/log/dumpstate_lastkmsg_*_KP.log.gz`**. The directory is listable but the files are `system:log 0640`, so you need the temporary root to copy them. |
| **坑**：这些文件名叫 `.log.gz`，实际是 **ZIP**（`PK\x03\x04`）。`gzip.open()` 会报 `BadGzipFile: Not a gzipped file (b'PK')`。 | **Gotcha**: despite the `.log.gz` name they are **ZIP** archives. `gzip.open()` fails with `BadGzipFile: Not a gzipped file (b'PK')`. |
| 包内最有用的不是 2 MB 的内核日志，而是一行结构化记录的 `store_extra_info.lst`。 | The useful entry is not the 2 MB kernel log but `store_extra_info.lst`, a single line of structured fields. |

`store_extra_info.lst` 里的字段 / fields:

```
RR      reset reason class ("KP" = the previous boot died)
RWC     rolling record number
TASK    the task that faulted
PANIC   panic class
PC, LR  program counter / link register, with module name and offset
RPM     RPM/hypervisor side reason
TZ_RR   secure world reset reason
BUG     source file:line for a BUG() hit
LKL     last kernel log, truncated
```

---

## 4. 五条历史记录的判读结果 / The five archives, side by side

| # | 时间 / date | TASK | PANIC | PC |
|---|---|---|---|---|
| 28 | 10-14 13:46 | RenderThread | Oops - BUG (`lib/list_debug.c:67`) | `__list_del_entry_valid_or_report+0xec` |
| 29 | 10-14 16:39 | `cve43499-run` | Oops | `_raw_spin_trylock+0x1c` |
| 30 | 10-22 14:21 | Jit thread pool | Oops - BUG (`lib/list_debug.c:64`) | `__list_del_entry_valid_or_report+0xdc` |
| **31** | **11-12 08:13** | **ksud** | **synchronous external abort** | **`ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`** |
| **32** | **11-12 08:16** | **ksud** | same | same function, **same offset** |

28/29/30 与本次路线无关（10 月那次是别的实验），正好当对照组：**三星记录 panic 的格式是稳定的**，
所以 31/32 的一致性是信号，不是巧合。
28/29/30 predate this route and serve as controls: the record format is stable, so the agreement
between 31 and 32 is signal, not coincidence.

---

## 5. 决定性证据 / The decisive evidence

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

前一刻的内核日志 / the lines immediately before it:

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

读法 / how to read it:

1. **PC 落在 `[kernelsu]` 模块里**，并且 `do_init_module` 在栈上 → 崩溃发生在**内核模块加载过程中**，
   不是 DFRoot 的 exploit、不是 `dfroot.ko`、更不是用户态的 `ksud soft-reboot`。
   The PC is inside the `[kernelsu]` module and `do_init_module` is on the stack → the crash happened
   **while loading that module**, not in the exploit, not in `dfroot.ko`, not in a userspace soft-reboot.
2. 同一条栈上的 `tracepoint_add_func` 说明触发者是"注册 tracepoint 时同步回调的 kretprobe"，
   也就是 KernelSU 的 `sys_enter` 钩子初始化路径。
   `tracepoint_add_func` on the same stack means the trigger is the kretprobe that fires synchronously
   while the `sys_enter` tracepoint is being registered — KernelSU's syscall-hook init path.
3. `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED`、`TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` 是**内核已经死了之后**
   看门狗咬出来的，是结果不是原因。把这两个字段当原因会一路查错方向。
   The AOP/TZ watchdog entries are produced **after** the kernel is already dead: consequence, not cause.
4. `synchronous external abort`（`do_sea`，DFSC = `0b001110`）不同于 `Unable to handle kernel paging request`：
   前者通常意味着这一页被更底层的保护拒绝（本机存在 Samsung RKP/KDP 与 KCFI），
   后者才是普通野指针。此处的读数（`x19` 与 hypervisor 报的 fault VA 相同）支持前者。
   An external abort is not a plain bad pointer; it usually means the page access was refused by a
   lower layer (this device has Samsung RKP/KDP plus KCFI). The registers support that reading.
5. 两次 panic 的 **ko build id 相同**（`b61aef7e…`）、PC 偏移相同、日志序列逐行相同
   → 这是那个二进制里**确定性的**一条代码路径，不是随机故障。
   Same module build id, same offset, same log sequence → a **deterministic** code path in that
   binary, not a flaky one.

---

## 6. 排除了什么 / What got ruled out

| 假设 / hypothesis | 判定 / verdict | 依据 / why |
|---|---|---|
| `ksud soft-reboot` 被当成异常关机 / soft-reboot seen as abnormal shutdown | **否 / ruled out** | `soft_reboot` 排在 `touch(dfm6)` 之后，而内核死在 ko 的 `init_module` 里，`dfm6` 根本没写出来。`soft_reboot` runs after `touch(dfm6)`; the kernel died inside `init_module`, so `dfm6` was never written. |
| late-load 失败（ksud 起不来）/ late-load failure | 否 / ruled out | 同一台机器后续四次都走到 `/dev/dfm6`。Four later runs on the same device all reached `/dev/dfm6`. |
| `dfroot.ko` 自己的补丁动作 / the exploit module itself | 否 / ruled out | 栈上没有 `dfroot`，崩溃在 `[kernelsu]`。`dfroot` is not on the stack. |
| 上游 4.7 缺 #185 / missing upstream fix #185 | 否 / ruled out | hook 命中并成功 patch；后续四次成功。The hook lands and later runs succeed. |
| ko 随机崩 / random module crash | 否 / no | 两次完全一致；且后续四次同样的代码没崩 —— 说明"当时那份 ko"与"现在这份"不是同一二进制。Identical twice, and the later binary does not crash: the two are not the same build. |

那份"当时的 ko"与"现在的 ko"不是同一个 APK 实例，证据来自 dropbox 的 crash tombstone：

```
SYSTEM_TOMBSTONE  2026-11-12 08:14:26
Executable: /data/app/~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==/lib/arm64/libksud.so
Cmdline:    .../libksud.so debug su
uid: 10463
```

而事后成功那台机器上的同一包名是另一个 `/data/app` 实例、另一个 uid。
The later, working install has a different `/data/app` instance hash and a different uid.

---

## 7. 复现这套取证 / Reproducing this evidence collection

```bash
# 1) 先拿到临时 root（只在本次开机有效），然后立刻拷出归档
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell "su -c 'mkdir -p /sdcard/Download/kp && \
  cp -f /data/log/dumpstate_lastkmsg_*_KP.log.gz /sdcard/Download/kp/ && \
  chmod 644 /sdcard/Download/kp/*'"
MSYS_NO_PATHCONV=1 $ADB pull /sdcard/Download/kp/ evidence/kp/

# 2) 判读（.gz 实际是 ZIP，用专门工具，别用 gzip）
python tools/kp_inspect.py evidence/kp --extract evidence/kp/extracted
```

`MSYS_NO_PATHCONV=1` 只对 Git Bash 需要：否则 `/sdcard/...` 会被改写成
`C:/Program Files/Git/sdcard/...`。
Only needed on Git Bash, otherwise `/sdcard/...` is rewritten to a Windows path.

---

## 8. 五条可复用的教训 / Five reusable lessons

1. **`SUCCESS` 只是"exploit 打通了"**，不等于内核模块装上了。判据永远是 `/dev/dfm6` / `/dev/dfme2`。
   `SUCCESS` only means the exploit worked; the verdict is always `dfm6` vs `dfme2`.
2. **崩溃后 `dmesg`/`logcat` 先别指望**，直接看 dropbox 和厂商的 KP 归档。
   Do not count on `dmesg`/`logcat` after a crash; go to dropbox and the vendor KP archive.
3. **看门狗/复位原因的字段是结果不是原因**，先找 PC 落在哪。
   Watchdog and reset-reason fields are consequences; find where the PC landed first.
4. **PC 落在某模块里时，先读出该模块的 build id**（oops 行里就有），再决定要不要换版本 ——
   否则换了一次还是同一个二进制，等于没换。
   When the PC is in a module, read that module's build id from the oops before swapping versions.
5. **临时 root 有时间窗**：日志必须在"拿到 root"和"下次重启"之间取。把这一步写进检查清单。
   The root window is finite: collect within it, and put it in your checklist.
