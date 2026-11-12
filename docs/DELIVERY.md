# 交付说明 — SM-F966W / CZJB 临时 Root APK

## Abstract (English)

Hand-off notes for the built APK: what it does and does not prove, install order (SU manager first,
then the exploit app), which `settings` must stay off, how to tell a real success from a fake one,
how to diagnose a failure, and the known risks and side effects. If you only read one file before
running anything, read this one after `README.md`.

生成时间：2026-11-12（本机 UTC）；2026-11-12 下午第二轮更新（黑屏重启分诊）
目标设备：Samsung Galaxy Z Fold7 (Canada) **SM-F966W**
固件：`CP2A.260605.016.F966WVLUDCZJB`（One UI 9 / Android 17 / SDK 37）
内核：`6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k`（KMI `android15-6.6`，4 KB 页）

第一轮真机结果：**选 KernelSU 模式后显示成功，立即黑屏重启，重启后 root 失效**。
因此本轮交付物改为带运行取证的 **lock2**，并新增分诊文档 `REBOOT_TRIAGE.md`。

---

## 0. 第二轮：黑屏重启（先看这一节）

**新 APK（与 lock1 同签名，可直接覆盖安装）：**

```text
src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk
94,911 bytes   versionCode 4701   versionName 4.7-f966w-czjb-lock2
sha256 2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
```

与 lock1 的差别（只改 Java；`libdfroot.so` / `libbootstrap.so` 仍与官方 v4.7 逐字节一致）：

1. 运行过程与 `/dev/df*` 进度标记落盘到 `df.root` 的设备加密存储 `files/diag.log`，
   **重启后仍在**；菜单 `Run log` 直接显示尾巴 120 行，`Markers now` 显示当前存在的标记。
2. 成功判定改到底：等到 `/dev/dfm6`（ksud late-load 退出码 0）才报成功；
   看到 `/dev/dfme2` 直接报"exploit 成功但 ksud 失败 = 没有 root"；
   90 s 内两个都没看到则列出当前标记（旧版里 ksud 失败也会打 SUCCESS）。
3. 每次启动 / 开机广播都会回显上一 kernel boot 的最后 14 行与
   `ro.boot.bootreason` / `sys.boot.reason` → 不用 adb 就能区分
   内核 panic 重启 与 Android 框架软重启。
4. `Auto Soft Reboot` 在本构建里强制 OFF（Settings 里置灰并注明）。

相关文档与工具：

| 位置 | 内容 |
|---|---|
| `REBOOT_TRIAGE.md` | 实测内核事实、假设排序、实验步骤（步骤 0–3）、判定表 |
| `deliverables/managers/MANAGERS.md` | 三组 manager（v2.2 基线 / KaySU v2.4 / v1.0）的哈希、包名、签名配对核验 |
| `tools/evidence.bat` | 免 root 取证：bootreason / pstore / last_kmsg / dropbox / logcat 一次性抓齐 |

---

---

## 1. 交付物

| 文件 | 路径 | 大小 | SHA-256 |
|---|---|---:|---|
| **新的 Root APK（lock2，本轮）** | `src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk` | 94,911 | `2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7` |
| DFRoot APK（lock1，第一轮） | 已从构建目录被 Gradle 清除（`assembleRelease` 只保留最新输出）。手机上已装的那个就是它；需要重新得到：`git checkout bc4f0e9 && bash build.sh` | 7,800,186 | `42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3` |
| **KernelSU 管理器（必须一起装）** | `deliverables/KernelSU_samsung-v2.2_32687-release.apk` | 7,607,475 | `761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69` |
| manager 候选（B/C 组） | `deliverables/managers/`（KaySU v2.4 APK+ko、KernelSU v1.0 APK） | — | 见 `deliverables/managers/MANAGERS.md` |
| 上游官方 DFRoot 4.7（仅作比对基准） | `_probe/apk/DFRoot_4.7.apk` | 84,071 | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |

> 说明：把 APK 复制到 `deliverables/` 这一步被本机"过夜护栏"权限钩子拦截（见 `DECISIONS.md` §L2）。
> 按规则没有绕过，APK 保留在 Gradle 的构建输出目录。上面路径是相对项目根目录的完整路径。

签名证书（新 APK，v2 签名）：

```
DN                  C=US, O=Android, CN=Android Debug
SHA-256             01aa025b44986b95837b4ccb74a759fd35957d8945eeb37c8be51e8e4fd9a5c2
SHA-1               ea819f569d023dba092cdaca693c901179ea1ca6
```

这是 AGP 自动生成的 **debug 证书**，原因：本机安全钩子禁止创建 `.jks`
（`DECISIONS.md` §L1）。APK 可正常侧载安装，但**不能覆盖官方 DFRoot**（同包名 `df.root`、
不同签名），安装前必须先卸载官方版。若之后自己生成 release keystore，
把 `signing.properties` 放回 `src/DFRoot/` 再跑一次 `build.sh` 即可换成正式签名。

---

## 2. 路线为什么换了

上一轮的结论（`DECISIONS.md` §C）是：Root My Galaxy 的公开 payload 清单里没有
`SM-F966W / UDCZJB / 6.6.127`，所以按原路线做不出能 root 的 APK。本次联网复核仍然成立：

- `Root-My-Galaxy-Payloads/support/targets-v3.json`：20 个 payload，内核版本只有
  5.10 / 5.15 / 6.1 / 6.6.46 / 6.6.98 / 6.6.102 / 6.12，F966 只有 `SM-F966U/U1/B`
  的 6.6.98 旧构建；没有任何 `CZJB` / `6.6.127` / `SM-F966W` 条目。
- 上游 fork（LiamJ74、7AKMM、strawberrylickler 等）同样只有旧 BZG3/BZDN 世代。
- `igorcv88` 的 Extended 清单有 6.6.127，但机型是 `S938B`（S25 Ultra），不能套用。

但存在另一条与"构建号"无关的链路：**CVE-2026-43284 / DirtyFrag**。

- 它是一个**按 KMI 匹配**的通用内核模块（不是按每个构建重编译的 exploit payload）。
  本项目设备 KMI 是 `android15-6.6`，DFRoot 的 `dfroot.ko` 内置了这个 KMI 的模块。
- DirtyFrag 的官方修复线是 **6.6.138**；CZJB 的 **6.6.127** 在其下方，属于受影响版本。
- DFRoot 项目的 issue #76（2026-10-07）有 **Galaxy Z Fold7 实机成功记录**：
  "Automatic root, auto restart, runs very well."（同时报告了重启后外屏不亮的副作用，见 §7）。
- 内核模块的 vermagic 为 `6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64`，
  与设备内核同为 **6.6.127**；在 `CONFIG_MODVERSIONS` 下内核只比较第一个空格之后的 flags，
  两边都是 `SMP preempt mod_unload modversions aarch64`，这是本方案能成立的关键。
- 模块只 import 6 个 GKI 稳定符号：`snprintf`、`memset`、`register_kprobe`、
  `unregister_kprobe`、`_printk`、`__stack_chk_fail`，跨 6.6.127 构建的 CRC 冲突风险低。

---

## 3. 这个 APK 具体做了什么

基于上游 **DFRoot v4.7** 源码（本次 clone 的 master = v4.7 + #185 一个提交）：

| 项 | 内容 |
|---|---|
| 原生 payload | 直接使用**官方 v4.7 发布 APK 里的** `libdfroot.so` / `libbootstrap.so`，与官方字节一致（sha256 见 §8），没有重新编译 |
| 内核模块 | `libdfroot.so` 内嵌 8 个 KMI 的 `dfroot-*.ko`；设备会选中 `android15-6.6`（ko sha256 `6d6f7472…767718`） |
| 新增 `DeviceLock.java` | 运行前校验 5 个字段：model / build / SDK_INT / fingerprint 前缀 / kernel release 前缀；任一不符返回码 3 并打印实际值，**不触碰内核**。build 同时接受 `Build.ID`（Samsung 通常只有 `CP2A.260605.016`）、`Build.DISPLAY`（完整构建号）或两者组合，避免误判 |
| 应用 ID | 保持 `df.root`。`dfroot.ko` 内硬编码 `/data/user_de/0/df.root/bootstrap`，改包名会导致提权后找不到 bootstrap |
| 版本 | `versionCode 4700`、`versionName 4.7-f966w-czjb-lock1`（官方为 407 / 4.7） |
| 界面 | 标题 `DFRoot F966W`，副标题 `@diabl0w github/xda · F966W/CZJB lock` |
| 权限 | 与上游一致（INTERNET / BOOT_COMPLETED / WAKE_LOCK / QUERY_ALL_PACKAGES），未新增 |

`DeviceLock` 的期望值就是 §1 的固件与内核。它只是**安全锁**，不是 exploit 的匹配条件：
DirtyFrag 本身按 KMI 匹配，锁用来保证这个 APK 只会在这台目标机上动手。

---

## 4. 已在本机验证（机器可复现）

| 检查 | 结果 |
|---|---|
| `aapt2 dump badging` | package `df.root`，versionCode 4700，versionName `4.7-f966w-czjb-lock1`，minSdk 32，targetSdk 37，label `DFRoot F966W` |
| `aapt2 dump xmltree` | `extractNativeLibs=true`（原生 payload 可从 `nativeLibraryDir` 执行）；无 `debuggable` |
| `apksigner verify` | v2 签名通过（v1 未启用，与官方一致） |
| `zipalign -c -v 4` | 通过 |
| `libdfroot.so` / `libbootstrap.so` | 与官方 v4.7 APK 内文件**逐字节相同** |
| 内嵌 android15-6.6 ko | 与从官方 APK 独立提取的 ko sha256 一致 |
| `PT_LOAD` 对齐 | 全部 `0x4000`（16 KB 页兼容） |
| DEX | 含 `SM-F966W`、`CP2A.260605.016.F966WVLUDCZJB`、内核前缀、fingerprint 前缀、`PROFILE LOCK` |
| KernelSU LKM | `lkm-aarch64-android15-6.6_kernelsu.ko` vermagic 与 `dfroot.ko` 同 KMI（`6.6.127-4k-…-dirty`） |

## 5. 未验证（必须由真机确认）

- **没有设备连接本机**（`adb devices` 为空），所以"能成功 root"**未实测**。本交付证明的是
  "构建产物正确、锁定逻辑正确、payload 与上游一致"，不是"Root 成功"。
- CZJB 是否被 Samsung 单独 backport 了 DirtyFrag 修复：未知。DirtyFrag 的 exploit 会先做
  页缓存写入校验，失败会打印 `DEVICE NOT VULNERABLE` 并中止，不会继续写内核。
- Samsung One UI 9 的 DEFEX / KDP 行为是否与上游测试机一致：模块里有对应处理，
  但 CZJB 本身没有公开成功记录。
- `ksud late-load` 在 Samsung `kptr_restrict` 设置下的行为：上游 DFRoot 4.7 的
  bootstrap **没有** `kptr_restrict` 归零逻辑（PR #174 未合入）。若出现
  "SUCCESS 但没有 root"，优先查这里（见 §7）。

---

## 6. 安装与运行

前置：手机解锁屏幕、能安装未知来源应用、**先备份数据**。

1. **核对固件**：`设置 → 关于手机 → 软件信息`
   - Build number 必须是 `CP2A.260605.016.F966WVLUDCZJB`
   - 内核版本必须是 `6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k`
   - 只要有一项不同，**不要安装**（或装好后它也会拒绝运行）。
2. **卸载官方 DFRoot（如果装过）**：包名同为 `df.root`，签名不同，无法覆盖升级。
3. 安装 `KernelSU_samsung-v2.2_32687-release.apk`（diabl0w 的 Samsung 适配版管理器）。
4. 安装 `DFRoot_4.7-f966w-czjb-lock1.apk`。
5. 打开 DFRoot → 顶部下拉框选 **KernelSU** → 点 **Launch Root**。
6. 等待日志结束。成功标志：
   - 日志出现 `* locked profile: SM-F966W / CP2A.260605.016.F966WVLUDCZJB / KMI android15-6.6`
   - 出现 `***SUCCESS***`
   - `adb shell su -c id` 返回 `uid=0(root)`，或在 KernelSU 管理器里看到已工作。
7. Root **只到本次重启**；重启后重新打开 DFRoot 再点一次即可。

注意事项：

- `开发者选项 → 日志缓冲区大小` 不能设为 **Off**，否则 DFRoot 会直接报错退出。
- 不要打开 DFRoot 的 "Start at Boot" 之前先在手动模式下验证成功，避免 bootloop。
- 不要在 DFRoot 里点 KernelSU 管理器的"安装 / 刷入 boot"类操作（锁 BL 的硬砖路径）。

## 7. 失败怎么读日志

| 日志 | 含义 | 处理 |
|---|---|---|
| `PROFILE LOCK: … Refusing to run` | 设备字段与锁定值不符 | 核对固件/内核；不要强改 APK |
| `DEVICE NOT VULNERABLE` | 页缓存写入校验失败，DirtyFrag 在 CZJB 上已被修 | 停止，等上游适配；不要重试 |
| `***FAILED***: ksud exited with error` / `SUCCESS` 但无 root | exploit 已进入内核阶段，问题在 KernelSU 侧 | 查 `adb shell grep kernelsu /proc/modules`；查 `/proc/sys/kernel/kptr_restrict`；参考 DFRoot discussions #69 |
| 手机重启 / 内核 panic | 竞态或布局不匹配 | 正常风险；重启后重试，不要连续硬重启。**若是"显示成功后立即黑屏重启"，按 `REBOOT_TRIAGE.md` §5 取证，不要盲重试** |
| `SUCCESS` 但马上重启、没 root | 旧版（lock1）的 SUCCESS 不代表 ksud 成功 | lock2 会给出真判据：`/dev/dfm6` 还是 `/dev/dfme2` |
| `already hooked, skipping` | 本次开机已经跑过 | 直接验证 `su`，或重启后再跑 |

抓日志：

```bash
adb logcat -s dfroot                       # DFRoot 的 logcat TAG（MainActivity/BootReceiver）
adb shell dmesg | tail -100                  # 通常因 kptr_restrict/dmesg_restrict 而不可用
adb shell getprop ro.boot.bootreason         # 区分内核 panic 还是框架软重启
```

推荐直接双击 `tools/evidence.bat`（用项目内 adb，一次把 bootreason / pstore / dropbox /
logcat / `/dev/df*` 列到 `evidence/<时间戳>/`）。lock2 还有自带取证：
DFRoot 菜单 → `Run log`（重启后仍能看到上一 boot 走到哪一格）与 `Markers now`。

## 8. 关键哈希（供复核）

```
lock2 APK（本轮）      2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
lock1 APK（第一轮）    42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3
KernelSU 管理器 APK    761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69
KaySU v2.4 管理器 APK  937eac92de8ab6fff8e26ddb63a4d2a50e7c1e1759a3f09ac614ec52e57f7792
KernelSU v1.0 管理器   c92f56c6569bfede6a37fdfa209e248c6a8f73b77214e51a3658ac2fec5dcf1e
上游 DFRoot 4.7 APK    9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1
libdfroot.so           1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db
libbootstrap.so        654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236
dfroot-android15-6.6.ko 6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718
kernelsu android15-6.6 (v2.2)  07127a9f635665cd3fb48e8f32ad36ca512656ea5b3d375e74164aab73cedc7f
kernelsu android15-6.6 (KaySU v2.4) c2d11f5e10f551c729e50a8bf7ec89a9bfa5f932e847cb73c0868383b2968d9a
设备 kernel（boot.img 解出） a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
```

## 9. 风险交底

- 这是**内核提权漏洞利用**。失败可能导致内核 panic、自动重启，极端情况下数据损坏。
  先备份重要数据，心里接受"可能需要救援/重刷"的最坏情况。
- 临时 root 不改变 BL 锁、不刷分区、重启即消失；但 exploit 运行期间对内核内存有写操作。
- **已知副作用记录**：DFRoot issue #76 的 Z Fold7 用户报告"重启后外屏不亮"。
  该 issue 被关闭并指向另一个项目的问题，但没有定论。若遇到，先记录再排查。
- 不承诺 Knox 熔断状态、保修、Play Integrity、银行类应用可用性。
- 不要把这个 APK 给其他型号/固件使用；`DeviceLock` 会拒绝，但请勿尝试改锁。

## 10. 复现构建

```bash
bash build.sh
```

工具链全部在项目内（`toolchain/`）：JDK 21.0.13、Android SDK platform `android-37.0`、
build-tools `37.0.0`、Gradle 9.7.1（wrapper）、AGP 9.4.0。
原生 payload 用 `python tools/extract_native_payloads.py` 从官方 v4.7 APK 重新提取并校验。
构建日志：`src/DFRoot/build_logs/gradle_release.log`。

本仓库对 DFRoot 源码的改动以补丁形式跟踪（`src/` 本身不入 git）：

```text
patches/dfroot-f966w.patch   654 行 / 9 个文件，基于上游 diabl0w/DFRoot 7a6513a
                            （DeviceLock、Diagnostics、真成功判定、soft reboot 钉死、菜单）
```

`build.sh` 会在 `src/DFRoot/app/src/main/java/df/root/DeviceLock.java` 不存在时自动
`git apply` 这个补丁，并警告上游基线不是 `7a6513a`。

**已验证到位级可复现**（本轮实测）：先 `git apply -R` 把 `src/DFRoot` 回到上游原状，
再跑 `bash build.sh`（自动重新应用补丁），产出的 APK sha256 仍是
`2a2b59f76640de5f…`，与上面交付的 lock2 **逐字节相同**。
重建前会先 `git -C src/DFRoot apply -R --check -` 确认能干净回退。
