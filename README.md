# Fold7 (Canada) TempRoot Lock — 固件锁定的 DFRoot 构建方法

**Fold7 (Canada) TempRoot Lock — a reproducible, firmware-locked DFRoot build**

> 用公开漏洞与公开项目，为 **Samsung Galaxy Z Fold7 (Canada) SM-F966W** 定制一个"只在自己这台固件上
> 才会动手"的临时 root APK；并且把**怎么判断另一台机器能不能用**、**怎么复现构建**、**怎么判读崩溃日志**
> 全部写成可执行的东西。
>
> Using only public vulnerabilities and public projects, this repo builds a temporary-root APK for
> **Samsung Galaxy Z Fold7 (Canada) SM-F966W** that refuses to run on any other firmware, and
> documents — as runnable tools, not prose — how to screen another device, how to reproduce the build,
> and how to read the crash logs when it goes wrong.

---

## ⚠️ 高风险警告 / High-risk warning

| 中文 | English |
|---|---|
| 本仓库描述的操作会**直接改写内核内存**，并加载一个未经三星签名的内核模块。 | Everything described here **writes to kernel memory** and loads a kernel module that is not signed by Samsung. |
| 可能的后果：黑屏、反复重启、数据丢失、无法开机而必须重新刷机、保修失效、Knox 与部分三星安全功能**不可逆失效**。 | Possible outcomes: black screen, boot loops, data loss, a device that only recovers by reflashing, voided warranty, and **irreversible** breakage of Knox and some Samsung security features. |
| 请只在**你自己拥有、且已经备份**的设备上尝试。第一次尝试前请确认你能回到可用状态（Odin + 官方固件）。 | Only on a device **you own and have backed up**. Before the first attempt, make sure you can get back to a working state (Odin + official firmware). |
| 一切后果由使用者自行承担。 / You are on your own. | |

---

## 法律与立场 / Legal position

| 中文 | English |
|---|---|
| **1. 全部技术信息均来自公开来源**：公开的漏洞公告与 PoC（见 CVE-2026-43284 "DirtyFrag"）、公开项目 `diabl0w/DFRoot`、公开的 `Root-My-Galaxy` payload 清单、公开的 `KernelSU`。本仓库不含任何未公开信息，也不含任何原创漏洞研究。 | **1. Everything here comes from public sources**: the public advisory/PoC for CVE-2026-43284 ("DirtyFrag"), the public `diabl0w/DFRoot` project, the public `Root-My-Galaxy` payload list, and public `KernelSU`. This repo contains no non-public information and no original vulnerability research. |
| **2. 不分发固件与专有文件**：不含三星固件、OTA 包、官方签名材料或任何专有二进制。固件请自行从正规渠道获取，并只在本机分析。 | **2. No firmware, no proprietary files**: no Samsung firmware, OTA packages, signing material, or proprietary binaries. Get firmware from official channels and analyse it locally. |
| **3. 不赚取任何商业利益**：无付费版本、无广告、无捐赠链接、无售卖、无收费代刷；不收集、不上传任何个人信息或设备标识。 | **3. No commercial interest**: no paid tier, no ads, no donation links, nothing for sale, no paid flashing service; no personal data or device identifiers are collected or uploaded. |
| **4. 仅用于教育与研究**：了解 Android/Linux 内核安全、内核模块加载与临时 root 的工程流程。使用者须自行确认是否符合当地法律与厂商服务条款。**禁止**用于规避 DRM、绕过支付/反作弊、未授权访问他人设备或任何违法用途。 | **4. Education and research only**: understanding Android/Linux kernel security, module loading, and temporary-root engineering. You must check whether it is legal and allowed by the vendor's terms where you live. **Do not** use it to circumvent DRM, to bypass payment or anti-cheat, to access devices you do not own, or for anything unlawful. |
| **5. 无担保**：作者不对设备损坏、数据丢失、保修失效、账号封禁或任何法律后果负责。 | **5. No warranty**: the authors are not liable for broken devices, lost data, voided warranties, banned accounts, or any legal consequence. |
| **6. 无关联**：本项目与 Samsung、Google、KernelSU 上游均无关联，未获其认可或授权。若你认为本仓库内容侵犯了你的权益，请开 Issue 说明，我们会处理。 | **6. No affiliation**: not affiliated with, endorsed by, or authorised by Samsung, Google, or the KernelSU upstream. If you believe something here infringes your rights, open an issue and it will be handled. |

---

## 目录 / Contents

1. [这是什么，不是什么](#1-这是什么不是什么--what-this-is-and-what-it-is-not)
2. [为什么需要"固件锁"](#2-为什么需要固件锁--why-a-firmware-lock)
3. [你需要准备什么](#3-你需要准备什么--what-you-need)
4. [快速开始（六步）](#4-快速开始六步--quick-start-six-steps)
5. [怎么读懂分析报告](#5-怎么读懂分析报告--how-to-read-the-report)
6. [换机型 / 换固件](#6-换机型--换固件--other-models-and-other-firmware)
7. [已知的坑](#7-已知的坑--known-pitfalls)
8. [仓库结构](#8-仓库结构--layout)
9. [许可与第三方](#9-许可与第三方--license-and-third-parties)
10. [参考资料](#10-参考资料--references)
11. [这个仓库最大的一个教训](#11-这个仓库最大的一个教训--the-one-lesson-worth-remembering)

---

## 1. 这是什么，不是什么 / What this is and what it is not

| 是 / Is | 不是 / Is not |
|---|---|
| 一套**方法 + 工具 + 制造记录**，说明如何在 SM-F966W 的一份**特定固件**上获得**重启即失效**的临时 root。 | A method + tools + build log for getting **temporary** (lost on reboot) root on **one specific firmware** of SM-F966W. |
| 一个**固件锁**：APK 会逐项比对型号、构建号、SDK、fingerprint、内核版本，任一不符就拒绝运行。 | A **firmware lock**: the APK compares model, build id, SDK, fingerprint, kernel release and refuses to run on a mismatch. |
| 一套**筛查工具**，用来判断某份 `boot.img` 是否落在这条路线的适用范围内。 | A **screening tool** that tells you whether a given `boot.img` falls inside this route's applicability. |
| 一份**失败案例研究**，包含那次"显示成功却重启"的完整内核 panic 定位。 | A **failure case study** with the full kernel panic analysis of a "says SUCCESS, then reboots" event. |
| 一个**可复现构建**：给定工具链与上游源码，产出逐字节相同的 APK（见 `docs/BUILD_RECORD.md` §7）。 | A **reproducible build**: given the toolchain and upstream sources it produces a byte-identical APK. |

| 不提供 / Not provided |
|---|
| 没有预编译 APK（见 §9）。需要就自己构建。 / No prebuilt APK (see §9) — build it yourself. |
| 没有固件、没有 manager APK、没有内核模块二进制。 / No firmware, no SU-manager APK, no kernel module binaries. |
| 没有"一键 root 任何 Fold7"。这条路线按 KMI 匹配、按固件加锁，本身就不是通用的。 / No "one-click root for any Fold7". The route is KMI-matched and firmware-locked by design. |
| 没有内核侧的绕过研究。内核模块（`kernelsu.ko`）由上游提供，本项目不修改它。 / No kernel-side bypass research. The kernel module comes from upstream unmodified. |

**一句话原理 / In one paragraph.** DFRoot 用一个公开的页缓存写原语（CVE-2026-43284）把
`init` 的某个文件替换成自己的 helper，从而在 `init` 里获得一次性代码执行；由它 `insmod` 一个
**按 KMI 编译**的 `dfroot.ko`，把 `ksud` 拉起来；`ksud late-load` 再加载 KernelSU 的内核模块。
整个过程按 **KMI**（这里是 `android15-6.6`）匹配，而不是按构建号匹配，所以"能不能用"主要由内核
次版本是否早于修复线决定。模块加载成功与否的判据是 `/dev/dfm6`（成功）与 `/dev/dfme2`（失败）——
**不是**应用里的 `***SUCCESS***`。
DFRoot uses a public page-cache write primitive (CVE-2026-43284) to replace one of `init`'s files with
its own helper, getting one-shot code execution inside `init`; that helper `insmod`s a
**KMI-matched** `dfroot.ko`, which spawns `ksud`; `ksud late-load` then loads KernelSU's kernel
module. The match is by **KMI** (`android15-6.6` here), not by build number, so applicability is
mostly decided by whether the kernel sublevel is below the fix line. Success is `/dev/dfm6`; failure
is `/dev/dfme2` — never the app's `***SUCCESS***` toast.

---

## 2. 为什么需要"固件锁" / Why a firmware lock

| 中文 | English |
|---|---|
| 这条路线按 KMI 匹配，意味着它**在别的固件上也可能跑起来**。同一份内核模块在未经审查的固件上加载，可能因为页表保护、CFI、DEFEX 策略不同而直接 panic —— 本仓库里就有一次真实案例（`docs/KP_CASE_STUDY.md`）。 | Because the route is KMI-matched, it **may also run on other firmware**. Loading the same module on an unreviewed build can panic outright — this repo documents exactly that happening (`docs/KP_CASE_STUDY.md`). |
| 所以 `patches/dfroot-f966w.patch` 加了一层 Java 侧硬锁：型号、构建号（`ro.build.id` 与 `ro.build.display.id` 都接受）、SDK、fingerprint 前缀、内核版本前缀，五项全中才允许动手。 | So `patches/dfroot-f966w.patch` adds a Java-side hard lock: model, build id (both `ro.build.id` and `ro.build.display.id` accepted), SDK, fingerprint prefix, kernel prefix — all five must match. |
| 给别人用时，`tools/analyze_firmware.py` 会把**你自己那台**的六个值算出来，`tools/apply_lock.py` 把它们写进源码，再构建。 | For your own device, `tools/analyze_firmware.py` derives the six values and `tools/apply_lock.py` writes them into the source before building. |
| 锁不是安全边界，只是"防止手滑"：它挡住了"拿别人的 APK 乱试"，挡不住"你明知不同还硬改常量"。 | The lock is not a security boundary, only a guard against accidents: it stops you from running someone else's APK, not from deliberately editing constants. |

---

## 3. 你需要准备什么 / What you need

| 必需 / Required | 说明 / Notes |
|---|---|
| 一台 Fold7 (Canada) `SM-F966W`，能开 USB 调试 | 其他机型的适配见 §6 / other models: see §6 |
| 该机**当前固件**的 `boot.img`（三星固件包里 `AP_*.tar.md5` 中的 `boot.img.lz4`） | 只用于**离线分析**，不上传 / offline analysis only |
| `adb shell getprop > firmware/getprop.txt` | 只读其中 6 个属性，序列号/IMEI 会被丢弃 / only 6 whitelisted keys are read |
| 与该内核 **KMI 相同**的 KernelSU 管理器（本项目验证过 `me.weishu.kernelsu` = `samsung-v2.2`） | 自行从上游发布页下载 / download from upstream releases |
| PC + `python3` + `bash`（Windows 用 Git Bash）+ `git` | 脚本只用标准库 / stdlib only |
| 网络（**仅第一次**：下载 JDK、SDK、Gradle 依赖） | 之后可离线 / offline afterwards |

| 不需要 / Not required | 说明 |
|---|---|
| Android Studio | 全部装在 `toolchain/` 内 |
| 解锁 bootloader | 这条路线不解 BL、不刷分区 |
| 三星账号 / 任何在线服务 | 全程本地 |

---

## 4. 快速开始（六步）/ Quick start (six steps)

```bash
git clone <this repo> && cd <repo>

# 1) 一次性环境：JDK 21 + Android SDK 37 + 上游 DFRoot 源码（唯一需要联网的步骤）
bash setup_toolchain.sh

# 2) 放入你自己的固件文件
mkdir -p firmware
cp /path/to/boot.img.lz4 firmware/
adb shell getprop > firmware/getprop.txt      # 只要这 6 个属性会被读取

# 3) 分析：能不能试、六个常量是什么
python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt

# 4) 把你的六个常量写进源码
python tools/apply_lock.py --report analysis/<你的报告>.json

# 5) 构建
bash build.sh

# 6) 装机、运行、看判据
adb install -r app/build/outputs/apk/release/DFRoot_*.apk
```

装机顺序与设置（**顺序错了会看不到 KernelSU**）：

| 步骤 | 做什么 | 为什么 |
|---|---|---|
| 1 | 先装 SU 管理器（KernelSU APK） | DFRoot 的 manager 下拉框只列出含 `libksud.so` 的应用 |
| 2 | 再装本仓库构建出的 DFRoot APK | 与官方 `df.root` 同包名但**不同签名**，不能覆盖安装，需要先卸载官方版 |
| 3 | Settings：`Start at Boot` 关、`Auto Soft Reboot` 保持关、`Disable KSU Modules` 关 | 避免开机自动重复触发与框架软重启干扰判读 |
| 4 | 下拉框选中管理器的包名，点 `LAUNCH ROOT` | — |
| 5 | 看菜单 `Run log` / `Markers now`，或 `adb shell ls -l /dev/df*` | `dfm6` = 成功，`dfme2` = 失败 |

> **`***SUCCESS***` 不代表成功。** 上游 `bootstrap.c` 两个分支都 `return 0`，所以 ksud 失败也会显示
> SUCCESS。唯一判据是 `/dev/dfm6`（KernelSU 已加载）与 `/dev/dfme2`（ksud 失败）。
> **`***SUCCESS***` does not mean success.** Both branches of upstream `bootstrap.c` return 0, so a
> failed ksud still shows SUCCESS. The verdict is `/dev/dfm6` vs `/dev/dfme2`.

> 重启后 root 消失是**预期行为**，不是缺陷：这是 late-load 的临时 root。
> Losing root after a reboot is **expected**, not a bug: this is a late-load temporary root.

---

## 5. 怎么读懂分析报告 / How to read the report

`tools/analyze_firmware.py` 输出 `analysis/<型号>_<构建号>.md` 与 `.json`，内容分三块：

**① 结论（会给出三种之一）**

| verdict | 含义 | 该做什么 |
|---|---|---|
| `maybe` / 可以尝试 | 内核早于修复线 `6.6.138`，KMI 是验证过的 `android15-6.6` | 可以试，但请先看 ② 的加固指纹 |
| `untested` / 未验证的 KMI | 内核不是 `android15-6.6` | 先确认上游是否有该 KMI 的内核模块（vermagic 必须匹配），否则不要试 |
| `patched` / 大概率已修复 | 内核版本 ≥ `6.6.138` | 停下，先找别的路线 |

**② 加固指纹**（`yes` 是强证据，`no` 是弱证据）

`shadow_call_stack` / `kcfi` / `samsung_defex` / `samsung_rkp_kdp` / `bti`。
`yes` 表示该加固在镜像里确实存在：它们不会阻止加载，但会让**崩溃**更容易发生且更难定位
（见 `docs/KP_CASE_STUDY.md`）。`no` 不能当作"没有编译进去"——`kallsyms` 的名字可能被 token
压缩，明文搜不到。

**③ DeviceLock 六个常量**，直接喂给 `apply_lock.py`。

> 报告是**筛查**，不是证明。离线无法证明某个内核一定可利用；真正的测试只有设备本身，
> 且要在"能救回来"的前提下进行。
> The report screens; it does not prove. Nothing offline can prove exploitability — the only real test
> is the device, with a recovery path ready.

---

## 6. 换机型 / 换固件 / Other models and other firmware

同一台机器换了固件（OTA 之后）也要重跑：`DeviceLock` 会拒绝运行，这是设计行为。

| 变化 | 需要确认 |
|---|---|
| 只有构建号变了，内核版本不变 | 重跑 `analyze_firmware.py`，`apply_lock.py`，重构建即可 |
| 内核**次版本**变了（如 `6.6.127` → `6.6.140`） | 若 ≥ `6.6.138`，这条路线基本结束 |
| **KMI** 变了（如 `android15-6.6` → `android16-6.12`） | 需要该 KMI 的内核模块；上游是否提供决定一切 |
| 换成别的机型（F966B / F966U / F966E …） | 解锁与否、DEFEX/RKP 策略、KMI 都可能不同；`DeviceLock` 的型号与 fingerprint 前缀必须改，且**本项目没有在该机型上验证过** |

改常量的最小步骤：

```bash
python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt
python tools/apply_lock.py --report analysis/<report>.json   # 会打印逐项 before/after
bash build.sh
```

没有 `getprop.txt` 时可以显式传值：`--model --build --build-short --kernel --fingerprint --sdk`。

---

## 7. 已知的坑 / Known pitfalls

| 坑 / pitfall | 现象 / symptom | 处理 / fix |
|---|---|---|
| 把 `***SUCCESS***` 当成功 | 显示成功其实没装上 | 看 `/dev/dfm6` vs `/dev/dfme2` |
| 下拉框里没有 KernelSU | 先装 DFRoot 后装管理器 | 先装管理器，再装/重启 DFRoot |
| `boot.img.lz4` 解不开 | 各家 LZ4 工具行为不一 | 用 `tools/lz4frame.py`（纯 Python，无依赖） |
| `.log.gz` 打不开 | 这些三星崩溃归档其实是 **ZIP** | 用 `tools/kp_inspect.py`，不要用 `gzip` |
| `adb pull /sdcard/...` 在 Git Bash 失败 | 路径被改写成 `C:/Program Files/Git/sdcard/...` | 加 `MSYS_NO_PATHCONV=1` |
| 崩溃后 `dmesg`/`logcat` 是空的 | 内核 panic 会清掉内存里的日志 | 看 dropbox 与厂商 KP 归档 |
| `apksigner` 不存在 | 只有 `apksigner.bat` | Windows 下用 `cmd //c "...apksigner.bat ..."` |
| release 构建报签名错误 | 没有 `signing.properties` | 脚本会自动回退到 debug 证书；要正式签名见 `signing.properties.example` |
| 装不上 | 与官方 `df.root` 同包名不同签名 | 先卸载官方版；或自己签名后覆盖 |

完整清单（含 20 多条实测踩坑）在 `docs/BUILD_RECORD.md` §11。

---

## 8. 仓库结构 / Layout

```
README.md                     this file (bilingual)
LICENSE                       GPL-2.0 — inherited from upstream DFRoot
NOTICE.md                     third-party components, licences, where to download them
docs/
  BUILD_RECORD.md/.en.md      step-level build recipe (toolchain, patches, hashes, verification)
  REBOOT_TRIAGE.md/.en.md     how to triage "rebooted / root gone" and read the crash logs
  KP_CASE_STUDY.md            a full, solved kernel-panic case (bilingual in one file)
  DECISIONS.md/.en.md         assumption/decision log, incl. retracted leads and local limits
  BASELINE.md/.en.md          hashes of every input and output this repo talks about
  DELIVERY.md/.en.md          install / verify / diagnose / risks for the built APK
  README.md                   index, plus which paths in the docs are intentionally absent
patches/
  dfroot-f966w.patch          9 files on top of upstream DFRoot 7a6513a (the lock + diagnostics)
tools/
  analyze_firmware.py         boot.img(.lz4) + getprop -> screening report + 6 constants
  apply_lock.py               report -> DeviceLock.java constants
  lz4frame.py                 pure-python LZ4 frame decoder (no deps)
  kp_inspect.py               read Samsung dumpstate_lastkmsg ZIP archives
  extract_native_payloads.py  pull the official DFRoot payloads out of the upstream APK
  evidence.sh / evidence.bat  collect post-crash evidence over adb
build.sh                      build the APK (optionally apply a lock report first)
setup_toolchain.sh            one-time environment setup (JDK + SDK + upstream clone)
signing.properties.example    copy to signing.properties for a real release key
firmware/                     YOUR firmware files go here (gitignored)
analysis/                     generated reports (gitignored)
```

`docs/` 里提到的 `evidence/`、`deliverables/`、`TODO.md` 属于原工作目录，**未随仓库发布**，
其作用与替代做法见 `docs/README.md`。

**每个长文档都有完整英文版**：`NAME.md` 是中文正本，`NAME.en.md` 是逐节对应的英文全文
（同编号、同哈希、同命令）。两者冲突时以中文为准。
**Every long document has a full English twin**: `NAME.md` is the Chinese record of what was
measured, `NAME.en.md` is a section-by-section English translation (same numbering, hashes and
commands). Where they disagree, the Chinese file wins.

---

## 9. 许可与第三方 / License and third parties

- 本仓库为 **GPL-2.0**（与上游 `diabl0w/DFRoot` 一致），见 `LICENSE`。
- `patches/dfroot-f966w.patch` 是相对上游 `7a6513a` 的派生修改，因此同样以 GPL-2.0 发布。
- 原生 payload（`libdfroot.so` / `libbootstrap.so`）**不随仓库分发**：
  `tools/extract_native_payloads.py` 从上游官方 release 下载后按 SHA-256 校验。
- KernelSU / 其衍生版管理器与内核模块**不随仓库分发**：请从各自的上游发布页下载。
- 三星固件**不随仓库分发**：请自行从正规渠道获取。
- 具体清单、许可与下载地址见 `NOTICE.md`。
- **不提供预编译 APK**：构建产物用 debug 证书签名、体积大，且分发给他人属于"代替其承担风险"，
  本项目不这么做。哈希记录在 `docs/BUILD_RECORD.md`，供你自行重建后核对。

---

## 10. 参考资料 / References

本项目只依赖以下**公开**来源（均可自行检索验证）：

| 来源 | 用途 |
|---|---|
| `https://github.com/diabl0w/DFRoot` | exploit 与 bootstrap 的源码；原生 payload 的官方发布 |
| `https://github.com/BuSung-dev/Root-My-Galaxy-Payloads` | 另一条按构建匹配的 payload 路线的清单（本项目用它的 `targets-v3.json` 证明"该固件没有现成 payload"） |
| `https://github.com/tiann/KernelSU` | late-load 内核模块与 `ksud` 的上游实现、KMI 矩阵 |
| **CVE-2026-43284 "DirtyFrag"** | 本路线使用的页缓存写原语（公开公告与 PoC；检索该编号即可） |
| Android boot image 格式、LZ4 frame 格式规范 | `tools/lz4frame.py` 的实现依据 |
| Adoptium Temurin 21 / Android SDK cmdline-tools | `setup_toolchain.sh` 下载的东西 |

---

## 11. 这个仓库最大的一个教训 / The one lesson worth remembering

| 中文 | English |
|---|---|
| 我们曾经也遇到过"应用显示成功、手机立刻黑屏重启"。当时最自然的解释是"框架软重启"，**是错的**。 | We hit "app says SUCCESS, phone reboots immediately". The obvious explanation — a framework soft reboot — was **wrong**. |
| 真正的死因是：内核模块 `kernelsu.ko` 在 `init_module` 里、`ksu_mark_running_process_locked+0x154` 处触发 `synchronous external abort`，两次记录 PC 与模块 build id 完全相同（确定性），看门狗咬只是后果。 | The real cause: `kernelsu.ko` faulted inside `init_module` at `ksu_mark_running_process_locked+0x154` with a synchronous external abort; two records had identical PC and module build id (deterministic). The watchdog bite was a consequence. |
| 完整判读过程（含我们走错的路）写在 `docs/KP_CASE_STUDY.md`，可直接当教学材料。 | The full analysis, including the wrong turns, is in `docs/KP_CASE_STUDY.md`. |
| 结论：**先看崩溃日志，再动手改东西**。没有日志时的每一次"试试换个版本"，都是在拿设备赌。 | Conclusion: **read the crash log before changing anything.** Swapping versions without a log is gambling with the device. |

---

## 贡献 / Contributing

- 欢迎针对**其他 Fold7 机型/固件**提交分析报告（`analysis/*.md`，注意先删掉任何设备标识）。
- 欢迎修正文档与工具；请保持"只有公开来源"这条底线。
- **请勿**在 Issue/PR 中粘贴序列号、IMEI、手机号或他人设备信息。
- 本仓库不接受"帮你 root 我的手机"这类请求。

- Reports for **other Fold7 models/firmware** are welcome (`analysis/*.md`, with identifiers removed).
- Fixes to docs and tools are welcome; keep the "public sources only" rule.
- **Do not** paste serial numbers, IMEIs, phone numbers, or other people's device data.
- "Please root my phone for me" requests are out of scope.
