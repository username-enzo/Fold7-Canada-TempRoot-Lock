# 案例研究：一次"显示成功后黑屏重启"的内核 panic 定案

> 🌐 **English edition (primary): [`KP_CASE_STUDY.md`](KP_CASE_STUDY.md)**
> 本文件是中文正本。逐节对应的英文版见上面链接。

> 这一篇是**教学材料**：把一次真实的临时 root 失败从"猜"做到"定案"的全过程摊开，
> 包括走错的路、以及哪一步才是决定性的。

---

## 1. 现象

| 项 | 内容 |
|---|---|
| 症状 | 手机上点 LAUNCH ROOT，应用显示 `***SUCCESS***`，随后**立刻黑屏并重启**；重启后 `su` 失效 |
| 设备 | Galaxy Z Fold7 (Canada) `SM-F966W` |
| 固件 | `CP2A.260605.016.F966WVLUDCZJB` |
| 内核 | `6.6.127-android15-8-p4a765df-…-4k`（KMI `android15-6.6`） |
| 最初的猜测 | 第一版 APK（lock1）没有强制关闭 `Auto Soft Reboot`，所以最自然的解释是"`ksud soft-reboot` 被当成异常关机" |

---

## 2. 为什么"显示 SUCCESS"什么也证明不了

`app/src/main/jni/bootstrap.c` 里两个分支都返回 0：

```c
if (run_ctx(NULL, {KSUD, "late-load", "--package-name", su_manager, NULL}) == 0) {
    touch("/dev/dfm6");   // ksud exit code 0
    if (soft_reboot) { ... run_ctx("u:r:ksu:s0", {KSUD, "soft-reboot"}); }
} else {
    touch("/dev/dfme2");  // ksud failed
}
return 0;                 // ← 两个分支都走到这里
```

因为两个分支都 `return 0`，Java 侧永远拿到 `rc=0` 并打印 SUCCESS。真正的判据是 `/dev/df*` 标记：
`dfm6` = KernelSU 装上了，`dfme2` = 没装上。重启会清空 `/dev`，所以任何事后分析的**第一步**都是
让应用把这些标记落盘。

---

## 3. 日志在哪里，以及一个必须知道的坑

| 项 | 内容 |
|---|---|
| 会丢的 | `dmesg` / `logcat` 在内存里，内核 panic 后上一次开机的内容**全部丢失** |
| 会留的 | **dropbox**（`/data/system/dropbox`）与 **三星的 `/data/log/dumpstate_lastkmsg_*_KP.log.gz`**。后者目录可列、文件不可读（`system:log 0640`），必须借临时 root 才能拷出来 |
| 坑 | 这些文件名叫 `.log.gz`，实际是 **ZIP**（`PK\x03\x04`）。`gzip.open()` 会报 `BadGzipFile: Not a gzipped file (b'PK')` |
| 最有用的条目 | 不是 2 MB 的内核日志，而是一行结构化记录的 `store_extra_info.lst` |

`store_extra_info.lst` 里的字段：

```
RR      reset reason class（"KP" = 上次开机异常结束）
RWC     滚动记录编号
TASK    出错的任务名
PANIC   panic 分类
PC, LR  程序计数器 / 链接寄存器，带模块名与偏移
RPM     RPM / hypervisor 侧的原因
TZ_RR   安全世界复位原因
BUG     BUG() 命中的源码 file:line
LKL     截断的内核日志
```

---

## 4. 五条历史记录的判读结果

| # | 时间 | TASK | PANIC | PC |
|---|---|---|---|---|
| 28 | 10-14 13:46 | RenderThread | Oops - BUG（`lib/list_debug.c:67`） | `__list_del_entry_valid_or_report+0xec` |
| 29 | 10-14 16:39 | `cve43499-run` | Oops | `_raw_spin_trylock+0x1c` |
| 30 | 10-22 14:21 | Jit thread pool | Oops - BUG（`lib/list_debug.c:64`） | `__list_del_entry_valid_or_report+0xdc` |
| **31** | **11-12 08:13** | **ksud** | **synchronous external abort** | **`ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`** |
| **32** | **11-12 08:16** | **ksud** | 同上 | 同一函数、**同一偏移** |

28/29/30 早于本次路线（10 月那次是别的实验），正好当对照组：**三星记录 panic 的格式是稳定的**，
所以 31/32 的一致性是信号，不是巧合。

---

## 5. 决定性证据

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

前一刻的内核日志：

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

读法：

1. **PC 落在 `[kernelsu]` 模块里**，并且 `do_init_module` 在栈上 → 崩溃发生在**内核模块加载过程中**，
   不是 DFRoot 的 exploit、不是 `dfroot.ko`、更不是用户态的 `ksud soft-reboot`。
2. 同一条栈上的 `tracepoint_add_func` 说明触发者是"注册 tracepoint 时同步回调的 kretprobe"，
   也就是 KernelSU 的 `sys_enter` 钩子初始化路径。
3. `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED`、`TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` 是**内核已经死了之后**
   看门狗咬出来的，是结果不是原因。把这两个字段当原因会一路查错方向。
4. `synchronous external abort`（`do_sea`，DFSC = `0b001110`）不同于 `Unable to handle kernel paging request`：
   前者通常意味着这一页被更底层的保护拒绝（本机存在 Samsung RKP/KDP 与 KCFI），
   后者才是普通野指针。此处的读数（`x19` 与 hypervisor 报的 fault VA 相同）支持前者。
5. 两次 panic 的 **ko build id 相同**（`b61aef7e…`）、PC 偏移相同、日志序列逐行相同
   → 这是那个二进制里**确定性的**一条代码路径，不是随机故障。

---

## 6. 排除了什么

| 假设 | 判定 | 依据 |
|---|---|---|
| `ksud soft-reboot` 被当成异常关机 | **否** | `soft_reboot` 排在 `touch(dfm6)` 之后，而内核死在 ko 的 `init_module` 里，`dfm6` 根本没写出来 |
| late-load 失败（ksud 起不来） | 否 | 同一台机器后续四次都走到 `/dev/dfm6` |
| `dfroot.ko` 自己的补丁动作 | 否 | 栈上没有 `dfroot`，崩溃在 `[kernelsu]` |
| 上游 4.7 缺 #185 | 否 | hook 命中并成功 patch；后续四次成功 |
| ko 随机崩 | 否 | 两次完全一致；且后续四次同样的代码没崩 —— 说明"当时那份 ko"与"现在这份"不是同一二进制 |

那份"当时的 ko"与"现在的 ko"不是同一个 APK 实例，证据来自 dropbox 的 crash tombstone：

```
SYSTEM_TOMBSTONE  2026-11-12 08:14:26
Executable: /data/app/~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==/lib/arm64/libksud.so
Cmdline:    .../libksud.so debug su
uid: 10463
```

而事后成功那台机器上的同一包名是另一个 `/data/app` 实例、另一个 uid。

---

## 7. 复现这套取证

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

---

## 8. 五条可复用的教训

1. **`SUCCESS` 只是"exploit 打通了"**，不等于内核模块装上了。判据永远是 `/dev/dfm6` / `/dev/dfme2`。
2. **崩溃后 `dmesg`/`logcat` 先别指望**，直接看 dropbox 和厂商的 KP 归档。
3. **看门狗/复位原因的字段是结果不是原因**，先找 PC 落在哪。
4. **PC 落在某模块里时，先读出该模块的 build id**（oops 行里就有），再决定要不要换版本 ——
   否则换了一次还是同一个二进制，等于没换。
5. **临时 root 有时间窗**：日志必须在"拿到 root"和"下次重启"之间取。把这一步写进检查清单。
