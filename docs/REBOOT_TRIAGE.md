# 黑屏重启 / root 失效 — 分诊与处置（2026-11-12）

> 🌐 **English full text: [`REBOOT_TRIAGE.en.md`](REBOOT_TRIAGE.en.md)** — same sections, same numbers, same commands.
> 中文正文在下方；两份以中文为记录正本（数值冲突时以中文为准）。

## Abstract (English)

Triage handbook for the two failure modes of this route: "the app says SUCCESS but the phone reboots"
and "root is gone after a reboot". It documents how to read the `/dev/df*` markers produced by
DFRoot's bootstrap, which one is the real verdict (`dfm6` = KernelSU loaded, `dfme2` = ksud failed),
how to extract and read Samsung's `dumpstate_lastkmsg_*_KP` panic archives (`tools/kp_inspect.py`),
and one fully solved case: a deterministic kernel panic inside the `kernelsu` LKM at
`ksu_mark_running_process_locked+0x154`, complete with the call trace to compare against.
Useful for anyone debugging a temporary root, not only for this model.

现象（实测反馈）：DFRoot 选 KernelSU 模式，日志/toast 显示成功，**立刻黑屏并重启**，重启后 root 消失。
本文给出：① 本机从 boot 镜像实测到的设备内核事实；② 为什么"显示成功"不等于 root 成功；
③ 已交付的新 APK（lock2）做了什么；④ 下一步的判定实验（按顺序做，每步都能排除一整类原因）。

---

## 1. 先纠正一个关键误读：`***SUCCESS***` 不代表 KernelSU 装上了

`app/src/main/jni/bootstrap.c` 的 main()：

```c
if (run_ctx(NULL, { KSUD_STAGE, "late-load", "--package-name", su_manager, NULL }) == 0) {
    touch("/dev/dfm6");            // ksud 退出码 0
    ...
} else {
    touch("/dev/dfme2");           // ksud 退出码非 0
}
return 0;                          // ← 两个分支都走到这里
```

也就是：**ksud 失败时 bootstrap 仍然返回 0**，Java 侧 `ExploitRunner` 拿到 0 就打 SUCCESS / toast。
真正区分成败的是 `/dev` 里的标记文件：

| 标记 | 含义（来自 `lkm/dfroot.c` + `jni/bootstrap.c`） |
|---|---|
| `/dev/df` | init 里的 shellcode 跑了（ko 落地并 insmod 成功） |
| `/dev/dfm0` | dfroot.ko → usermodehelper 起来了 sh |
| `/dev/dfm1/2/3` | bootstrap 起来了 / 读到 prefs / 继承 zygote 环境 |
| `/dev/dfm5` | 即将 exec `ksud late-load` |
| **`/dev/dfm6`** | **ksud late-load 退出码 0 —— KernelSU 真的加载了** |
| **`/dev/dfme2`** | **ksud late-load 退出码非 0 —— KernelSU 没装上** |

所以"显示成功"只证明了：exploit 打通、dfroot.ko 进内核、SELinux 已置 permissive、
bootstrap 跑起来；**不证明** KernelSU 模块加载成功。重启后 `/dev/*` 全消失，
上一boot 走到哪一步就再也查不到 —— 这正是 lock2 版本要解决的（见 §4）。

---

## 2. 本机从 `boot.img.lz4` 实测的设备内核事实（可复现，无需手机）

内核 `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k`，
kernel sha256 `a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51`
（`build_logs/kernel.img`，由 `tools/lz4frame.py` 解出）。用 kallsyms 名字表判定配置：

| 事实 | 证据（kallsyms / 字符串） | 对本次故障的意义 |
|---|---|---|
| **CONFIG_SHADOW_CALL_STACK = y** | `scs_alloc`、`scs_cleanup`、`scs_free`、`scs_init`、`scs_patch`、`scs_patch_vmlinux`、`scs_prepare`、`scs_release`；vmstat `shadow_call_stack`；`irq_shadow_call_stack_ptr` | KernelSU 上游 10-22 修的那个"读 `task_pt_regs(current)` 算错偏移 → EL1 翻译错误 → 立刻重启"（commit `bbd9b2480`，A065/MTK SCS=n 机型）**对本机不适用**：本项目正是 SCS=y、`task_struct->stack` 在 0x38 的布局 |
| **KCFI 打开** | `Oops - CFI`、`__cfi_`（kprobes 黑名单前缀） | 任何被改写的函数入口/函数指针类型不匹配 → **直接 panic**。DFRoot/KSU 都要 patch 内核函数，这是"改内核函数就崩"这类风险的放大器 |
| **Samsung DEFEX 存在** | `task_defex_enforce`、`task_defex_user_exec`、`task_defex_zero_creds`、`task_defex_link_protection` 等 43 处 `*_defex_*` | DFRoot ko 会 patch 其中两个；samsung 版 KernelSU 还会在运行时用 jump label 关 DEFEX（fork commit `69f6f2571`）——**这条路径是最可疑的 panic 源** |
| **Samsung RKP + KDP 存在** | `rkp_init`、`rkp_pgt_bitmap`、`rkp_dbl_bitmap`、`init_mm_pgd`、`id_map_pgd`、`tramp_pgd`、`_KMEM_TYPE`、`CRED_JAR_TYPE`、`TSEC_JAR_TYPE`、`selinux_enforcing_va`、`kdp_*` | 内核 text/rodata/页表受硬件保护；KSU fork 的 `kernel/compat/rkp.c` 要处理它。上游 10-15 才修过 "Fix RKP to do bulk write"（v2.2 已含） |
| **无 BTI 内核支持** | `system_supports_bti` / `ARM64_HAS_BTI` 全不存在 | 上游 10-22 另一个改动（`76a088c5f` 把 BTI landing pad 判定写严）在本机**大概率不影响**（没有 BTI 强制） |
| DFRoot ko 依赖的符号都在 | `kallsyms_lookup_name`、`aarch64_insn_patch_text`、`module_kallsyms_lookup_name`、`call_usermodehelper_setup/exec`、`invalidate_inode_pages2`、`kern_path`、`path_put`、`selinux_state`、`avc_has_perm_noaudit` | 与"exploit 打通、ko 加载成功"这一观察一致 |

**结论**：这台机器上，上游那两个 post-v2.2 修复都不像是本项目的解药；
最可能的 panic 点是 **KernelSU 的 samsung 侧运行时打补丁（DEFEX jump label / RKP / KCFI 交互）**，
但这必须用日志证实，不能靠猜。

---

## 2b. 已撤回的一条线索（记录在此，避免以后重复踩）

本文一度根据"在 kernel.img 里按字节搜符号名"得出"三个 KernelSU LKM 都硬依赖
`__tracepoint_sys_enter` / `mntns_operations` / `selinux_blob_sizes`，而本机搜不到"，
并把它当成首要线索。**这个结论是错的，已撤回。** 两处错误：

**错误一：方法不成立。** 用一个采样就能看出来：

| 符号 | kernel.img 里有字面串 | 实际情况 |
|---|---|---|
| `do_exit`、`init_task`、`init_mm`、`selinux_state`、`strchr` | 有 | 真存在 |
| `cpu_switch_to`、`__cpu_setup` | 无 | **真存在**（汇编符号，无 BTF） |
| `mntns_operations`、`selinux_blob_sizes` | 无 | 未定 |

图像里能搜到的字面名只来自两类存储：**BTF 字符串表**（本机有，3,816,744 B 类型 /
2,608,839 B 字符串 / 141,000 个唯一串，镜像偏移 25,873,004）和
**`__ksymtab_strings`（导出符号名）**。而 `kallsyms_names` 里每个名字都是**按 token 压缩**的，
大多数名字根本不会以字面形式出现。BTF 也不全：它连 `init_mm`、`init_pid_ns`、`system_wq`、
`tasklist_lock`、`strchr`、`kmalloc_caches` 都不含（实测 LKM 的 236 个导入里有 20 个不在 BTF）。
所以"搜不到"证明不了"不存在"。

本文试过正经解 kallsyms（`kallsyms_token_table` / `kallsyms_token_index` / `kallsyms_num_syms`
签名定位），在这张图上定位失败 —— 该脚本已删除，没有留在仓库里冒充可用工具。

**错误二：就算它成立，也解释不了该现象。** 读 `userspace/ksuinit/src/lib.rs`
的 `load_module()`（本地副本 `_probe/ksuinit_lib.rs:317-390`）：

```rust
for name in unresolved_symbols.keys() {
    log::warn!("Cannot find symbol: {}", name);   // 只 warn
}
...
match init_module(&buffer, params) { ... }        // 照样加载
```

没解析到的符号保持 `SHN_UNDEF`，于是内核模块加载器按名字去 `__ksymtab` 找，
找不到就是 `Unknown symbol` → `init_module` 返回错误 → `ksud` 失败 → 留 `/dev/dfme2`。
**这条路的预测是"干净失败、没有 root、不重启"，与"黑屏重启"不符。**

换句话说：**符号缺失最多导致装不上，不会导致重启。** 该症状要求"ko 装进去了、然后崩"。
这个推理反而把假设 1（KernelSU 运行时打补丁）推得更前。

**顺带一个重要事实**：`/proc/kallsyms` 在本机对 `shell` 域是 **Permission denied**
（SELinux，不是 `kptr_restrict`）。所以"用 adb grep kallsyms"这条路根本走不通，
以后不要再写在步骤里。可行的替代是 `/dev/df*` 标记 + dropbox（见 §5 步骤 0）。

## 3. 上游同样症状的历史（为什么先换 manager）

`diabl0w/DFRoot` 上"SUCCESS 之后立刻 panic/重启"的 Samsung 报告，全部是靠**换/升 build** 解决的：

| issue | 机型 | 结论 |
|---|---|---|
| [#111](https://github.com/diabl0w/DFRoot/issues/111) | Galaxy A53 | samsung-v1.0 正常；**升到 v1.1 就 SUCCESS 后冻结并自动重启**；作者看了 `dumpstate_lastkmsg_*_KP.log` 后说"easy fix"，两次 CI 后修好 |
| [#110](https://github.com/diabl0w/DFRoot/issues/110) | Galaxy A53 | 同一现象，v1.1 被作者直接撤掉 |
| [#122](https://github.com/diabl0w/DFRoot/issues/122) | Galaxy M55 | v1.0 可用、v2.0 KP；CI 修好。还澄清了一个"没开 soft reboot 也自己软重启"的 ksud bug |
| [#131](https://github.com/diabl0w/DFRoot/issues/131) | Galaxy A53 | DFRoot v4.5 回归，换新的 DFRoot CI build 后消失 |
| [#153](https://github.com/diabl0w/DFRoot/issues/153) | Samsung | "v1.0 是唯一不 KP 的 manager" |

即：**同样的 exploit 二进制，换 manager（=换 kernelsu.ko）就能从 KP 变成可用。**
本项目目前钉死的 manager 是 `KernelSU samsung-v2.2`（2026-10-15, build 32687），
而 diabl0w/KernelSU 的 main 在它之后还有 2 个内核侧提交（10-22）。
但上游**没有**比 v2.2 更新的公开发布版；带修复的构建只存在于 Actions artifact（要登录才能下载）。
已验证可用的公开替代：`DaniTheSillyFem/KaySU samsung-v2.4`（2026-11-07）——
把它和上游 main `76a088c5f` 对比，代码差异只有 6 个文件（3 个 workflow、README、
`kernel/Kbuild` 里的 manager 包名/证书指纹、manager AndroidManifest 主题名）+ 各语言字符串，
**内核 C 代码与上游 main 完全一致**。细节与哈希见 `deliverables/managers/MANAGERS.md`。

---

## 4. 本轮已做的改动（新 APK：lock2）

`src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk`
versionCode 4701 / versionName `4.7-f966w-czjb-lock2`，
sha256 `2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7`。
签名与 lock1 相同（AGP debug 证书），**可直接覆盖安装 lock1，不用先卸载**。
原生 payload（`libdfroot.so` / `libbootstrap.so`）与官方 v4.7 逐字节不变。

改动全部在 Java 侧（不碰 exploit 二进制）：

1. **新增 `Diagnostics.java`**：把运行过程写进
   `df.root` 的设备加密存储 `files/diag.log`（重启仍在、不需要解锁），
   并每 150 ms 轮询 `/dev/df*` 标记，出现即落盘。
   → 手机重启后，**上一 boot 走到哪一格**仍然能看到。
2. **成功判定改到底**：exploit 进程退出后继续等最多 90 s，
   看到 `/dev/dfm6` 才报 "KernelSU loaded"，看到 `/dev/dfme2` 直接报
   "exploit OK 但 ksud 失败 = 没有 root"，超时则列出当前存在的标记并提示
   "dfm5 有、dfm6 没有 = 死在 ksud late-load 里"。
3. **开机后验尸**：每次启动/开机广播都写一行
   `=== BOOT id=… ro.boot.bootreason=… sys.boot.reason=… ===`
   并把上一 kernel boot（不同 boot_id）的最后 14 行回显到界面。
   → 不用 adb、不用 root，就能区分"内核 panic 重启"还是"框架软重启"。
4. **强制 `Auto Soft Reboot = OFF`**：运行前把 DE prefs 写回 false
   （bootstrap.c 直接读 XML，所以用同步 commit）。
   Settings 里该项已置灰并注明。理由：#122 里"没勾选也自己软重启"是 ksud 侧已知问题，
   先把它从变量里去掉。
5. 菜单新增 **Run log**（把 diag.log 尾部 120 行显示出来，截图即可）和
   **Markers now**（当前 /dev 标记）。

---

## 5. 实验步骤（步骤 0 已完成，只剩步骤 2 的 KP 日志）

> **2026-11-12 傍晚更新**：步骤 0 已完成且成功，步骤 1（manager 矩阵）不必再做。
> 现在只需做步骤 2（取 `dumpstate_lastkmsg_*_KP` 日志）。下文保留原始步骤作历史记录。

### 步骤 0 · 一次干净的复现 + 取证 【已完成】

1. 手机装 lock2（可直接覆盖 lock1）。打开 DFRoot：
   - Settings：`Start at Boot` **关**；`Auto Soft Reboot` 现在应该是灰的（OFF）；
     `Disable KSU Modules` **关**（本次未装模块）。
   - 选择 manager（先按 §5.2 的 A 组）。
2. 点 **LAUNCH ROOT**，**同时开始计时**（看手机时钟秒针）。记下：
   - 从点下去到黑屏大概几秒（<3 s / 5–10 s / 30 s+）；
   - 重启后重新打开 DFRoot → 菜单 **Run log** → **截图**；菜单 **Markers now** → **截图**。
   这两张图基本就能定位到链条的哪一格断掉。
3. 手机连 PC，双击 `tools/evidence.bat`（用的是项目内 `toolchain/.../adb.exe`），
   把生成的 `evidence/<时间戳>/` 整个目录发出来。先看这几个文件：

   | 文件 | 看什么 | 判定 |
   |---|---|---|
   | `02_bootreason.txt` | `ro.boot.bootreason` 含 `panic` / `wdt` / `watchdog` | **内核自己重启** |
   | `02_bootreason.txt` | 含 `reboot,userspace` / `reboot,shell` / `soft` | **Android 框架软重启** |
   | `03_dropbox_last_kmsg.txt` | 有内容 = 上次崩溃时的内核日志 | 最有价值，能直接定位 |
   | `04_dropbox_restart.txt` | 谁请求了这次重启 | 区分 panic 与用户态重启 |

   dropbox 存在 `/data/system/dropbox`，**跟重启无关，会保留**；`dmesg` 和 `logcat`
   存在内存里，panic 之后就没有上一次开机的了。所以 `03` / `04` 比 `08` / `09` 重要。

   注意：`/proc/kallsyms`、`/data/log`、`pstore`、`/proc/last_kmsg` 对 `shell` 域
   都是拒绝的（SELinux），这几个文件多半是空的或 `Permission denied`，属正常现象。

### 步骤 1 · 判断是不是 manager(kernelsu.ko) 的问题

同一台机器、同一个 lock2 APK，只换 manager，各测 2 次，并记录 Run log 截图：

| 组 | manager | 预期能排除什么 |
|---|---|---|
| **A**（现在用的） | `KernelSU samsung-v2.2`（build 32687，10-15） | 基线 |
| **B** | `KaySU samsung-v2.4`（build 32702，11-07，含上游 10-22 两个内核修复） | 若 B 成功 → 就是 v2.2 ko 的问题，按 B 收尾 |
| **C** | `KernelSU samsung-v1.0`（build 32664，10-05，早于 samsung jump-label/DEFEX 改造） | 若 C 不 KP 但没 root → 说明 KP 来自 samsung 运行时打补丁路径（#111/#153 的老规律） |

> manager 之间包名不同（`me.weishu.kernelsu` / `me.ella.kaysu`），可以并存安装；
> 但 **KaySU 的 ko 只认 KaySU 自己的 manager 签名**，所以 B 组必须装 KaySU 的 manager APK 并在 DFRoot 里选它。
> 换 manager 后要在 DFRoot 下拉框里重新选一次。
>
> 另：late-load 成功后 ksud 会 `am force-stop` + `am start` 管理器（late_load.rs 第 14 步）。
> 所以“屏幕闪一下黑 / 管理器自己关掉又开”是正常现象，不是重启；
> 而且那行 `am start` 的类名写死了 `me.weishu.kernelsu.ui.MainActivity`，
> 用 KaySU 时这一步会失败 → **必须手动开 KaySU 看状态**（详见 MANAGERS.md B 组）。

### 步骤 2 · 一旦任何一次 root 成功，立刻把 panic 日志捞出来（这是根治的唯一途径）

> **这条现在是唯一的待办。** root 是临时的，只在本次开机内有效，所以“取日志”必须夹在
> “拿到 root”与“重启”之间。准确命令见 `BUILD_RECORD.md` §12.4。

Samsung 会在**下一次开机后**自动生成上次崩溃的 last_kmsg，路径 `/data/log/`，文件名带 `KP`（kernel panic）：

```sh
su
ls -l /data/log | grep -i dumpstate
cp /data/log/dumpstate_lastkmsg_*KP*.gz /sdcard/Download/
exit
```
然后 `adb pull /sdcard/Download/` 发出来。有了 panic 回溯（pc/lr/调用栈/被写的地址）
才能判定是 DEFEX jump-label、RKP 写权限还是 KCFI 类型检查，也才能决定是改 ko、换 manager 还是放弃这条路。
（上游作者在各 issue 里都是这么定位的。）

### 步骤 3 · 若 BootReceiver 造成循环重启

不要开 `Start at Boot`。万一已经开了又 bootloop：开机时按住**音量下**进安全模式
（AOSP/Samsung 通用），进去后关掉 DFRoot 的 Start at Boot 或卸载 DFRoot
（DFRoot README 的官方处置办法）。

---

## 6. 现状（2026-11-12 夜里：已结案，见 §6c）

> **一句话**：第一轮的"显示成功后黑屏重启"是真 kernel panic，死在 `kernelsu` 模块的
> `init_module` 里（`ksu_mark_running_process_locked+0x154`），不是 soft-reboot。
> 结论与证据：**§6c**；完整调用栈与现场：`BUILD_RECORD.md` §12.4。

**lock2 实测成功**：四次（12:03 / 12:19 / 12:36 / 13:39），各约 2–3 秒，`/dev/dfm6` 出现，
manager 为 `me.weishu.kernelsu`（samsung-v2.2）。完整 Run log 与时间戳见 `BUILD_RECORD.md` §12。

所以本文前面那套"分诊"已经不是当前主要任务，**manager 矩阵（原步骤 1）不必再测了**：
A 组直接成功。

但有一件事**没有结案**：`ls /data/log`（不需要 root）露出了这台机器的 KP 日志：

```text
dumpstate_lastkmsg_28_20261014_134615_KP.log.gz
dumpstate_lastkmsg_29_20261014_163921_KP.log.gz
dumpstate_lastkmsg_30_20261022_142106_KP.log.gz
dumpstate_lastkmsg_31_20261112_081336_KP.log.gz   ← 第一轮失败那天
dumpstate_lastkmsg_32_20261112_081607_KP.log.gz   ← 第一轮失败那天
```

`_KP` 的含义是"上次开机没有正常关机"，内容可能是真 panic，也可能只是被硬复位截断的正常日志。
**08:13 / 08:16 正好落在"显示成功后黑屏重启"的时间窗里**，所以那次重启很可能是内核侧的，
而不是先前推测的软件重启。

### 6.1 剩下两种可能，以及各自的预测

| # | 假设 | 与已知证据的关系 | 用 KP 日志怎么判 |
|---|---|---|---|
| A | **`ksud soft-reboot` 被当成异常关机**（`bootstrap.c` 里只有 `soft_reboot==true` 才会在 `dfm6` 之后调 `ksud soft-reboot`；lock1 没强制关这个开关） | 与"成功后立刻重启、root 失效"完全吻合；与 lock2 成功也吻合（lock2 把它强制关掉） | 日志**戛然而止、无异常栈**，末尾是正常的内核 消息 |
| B | **KernelSU 加载后运行时打补丁把内核打崩**（DEFEX jump label / RKP / KCFI） | 也吻合症状，但与 lock2 两次都成功矛盾（除非是概率性的，上游 #152 确实报告过随机 panic） | 末尾有 `Unable to handle kernel` / `Oops` / `BUG:` / `Internal error`，`Call trace` 的 PC 落在 `kernelsu` 段 |

两条都不需要改代码就能判，**只要把 §12.4 的两条命令跑一遍**（先临时 root，2 秒就有了）。

### 6.2 取 KP 日志【已完成，2026-11-12 傍晚】

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
# 手机上点 LAUNCH ROOT，等约 2 秒
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_3*_KP.log.gz /sdcard/Download/"
$ADB pull /sdcard/Download/ evidence/kp/
```

实际执行时手机还带着临时 root，所以一次就把 5 条全取了；注意这些 `.log.gz` 实为 ZIP，
用 `python tools/kp_inspect.py evidence/kp` 读。完整判读表、调用栈与证据来源见
**`BUILD_RECORD.md` §12.4**。

---

## 6c. 结案（2026-11-12 夜里实测）

**结论：假设 B 成立，假设 A 作废。**

| 问题 | 回答 | 证据 |
|---|---|---|
| 第一轮"显示成功后黑屏重启"是什么 | **真 kernel panic**，死在 `kernelsu` 模块 `init_module` 里 | KP 31/32 的 `store_extra_info.lst`：`TASK=ksud`、`PANIC=synchronous external abort`、`PC/LR=ksu_mark_running_process_locked+0x154/0x14c` |
| 具体位置 | `ksu_syscall_hook_manager_init` 在 `sys_enter` tracepoint 的 `regfunc` 上挂 kretprobe，`tracepoint_add_func` 同步回调，回调里 `tp_marker: mark process` 打完日志后崩 | 完整调用栈见 `BUILD_RECORD.md` §12.4.1 |
| 是随机还是确定 | **确定性**：两次 panic 的 PC 偏移、ko build id（`b61aef7e…`）、日志序列逐行相同 | 31 与 32 对比 |
| 是不是 soft-reboot | **不是**。`soft_reboot` 在 `bootstrap.c` 里位于 `dfm6` 之后；这次内核在 ko init 阶段就死了，`dfm6` 根本没走到 | `bootstrap.c:224-231` + panic 调用栈 |
| 为什么现在 4 次都成功 | 08:13 用的 manager 与现在不是同一个 APK 实例（`/data/app` 实例哈希与 uid 都不同）；现在的 `samsung-v2.2` 已 4/4 成功 | `dumpsys package` vs 08:14 的 `SYSTEM_TOMBSTONE` |
| 看门狗咬是不是原因 | 不是，是结果 | `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED`、`TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT` 出现在 panic 之后 |
| 还剩什么风险 | 当前组合的成功样本只有 4 次；崩过一次的那个 ko 已不在机器上，但它的**具体版本号无法从设备恢复** | 见 `BUILD_RECORD.md` §12.4.3 |

**操作结论**：把 manager 钉在 `me.weishu.kernelsu` = `samsung-v2.2`（当前这套 4/4 成功的组合），
不要为了"更新"换 manager；若以后又出现"成功即黑屏重启"，先按 §6.2 取 KP，对照组直接看
`ksu_mark_running_process_locked` 这个 PC。

---

## 6b. 历史假设（保留，已不是主线）

| # | 假设 | 结果 |
|---|---|---|
| 1 | KernelSU ko 运行时打 DEFEX/jump label 把内核打崩 | **成立（但阶段更早）**：不是运行时打 patch，而是 ko 的 `init_module` 里 `/tp_marker` 标记进程时崩，见 §6c |
| 2 | late-load 失败，重启由别的组件引起 | 已排除：实测 `/dev/dfm6` 出现，ksud 成功 |
| 3 | ksud soft-reboot 被感知为重启 | **已否证**：panic 发生在 ko init，`dfm6`/soft-reboot 代码一行都没走到，见 §6c |
| 4 | dfroot.ko 自身的补丁动作崩 | 已排除：链条完整走到 bootstrap 且 ko 加载成功 |
| 5 | 上游 4.7 缺 #185 导致 hook 位置不稳 | 已排除：hook 命中并成功patch |

---

## 7. 顺手记下的已知副作用

Z Fold7 在 DFRoot/Root-My-Galaxy 社区里有"重启后外屏不亮"的单独问题
（`diabl0w/DFRoot` #76 → `BuSung-dev/Root-My-Galaxy` #235，需要额外一条 root 命令修复）。
如果哪天 root 稳定了又碰到外屏黑，那是另一件事，跟本次 panic 无关。
