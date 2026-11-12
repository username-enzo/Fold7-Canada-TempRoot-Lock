# 第三方组件与来源 / Third-party components and provenance

本仓库自身只有 **方法、补丁、脚本与文档**。下面这些组件由第三方维护，本项目不重新分发，
只在自己的构建/分析流程里使用，并记录版本与校验值，方便你自行获取后确认拿到的是同一份东西。

This repo ships **method, patches, scripts and documentation**. The components below are
maintained by third parties. They are *not* redistributed here; the build and the analysis only use
them, and their versions/checksums are recorded so you can confirm you fetched the same thing.

---

## 1. DFRoot（exploit 与 bootstrap） / the exploit and its bootstrap

| | |
|---|---|
| 出处 / source | `https://github.com/diabl0w/DFRoot` |
| 许可 / licence | **GPL-2.0**（见 `LICENSE`，与本仓库一致 / same as this repo） |
| 本项目使用 / used as | 源码基线（`setup_toolchain.sh` 克隆并检出 `7a6513a69ce4c1a90b68d857c26347bf166ffe10`），加上 `patches/dfroot-f966w.patch` |
| 原生 payload / native payloads | 由 `tools/extract_native_payloads.py` 从**上游官方 release**（v4.7）下载后提取，校验值见 `docs/BASELINE.md`；本项目**不重编译**它们 |
| 归属 / attribution | exploit 逻辑、`bootstrap`、`dfroot.ko` 的原始作者均为上游项目；本仓库只做固件锁与诊断的包装 |

> GPL-2.0 要求派生作品同样以 GPL-2.0 发布，这正是本仓库的许可。
> GPL-2.0 requires derivatives to stay GPL-2.0 — that is this repo's licence.

---

## 2. KernelSU 及衍生管理器 / KernelSU and derivative managers

| | |
|---|---|
| 上游 / upstream | `https://github.com/tiann/KernelSU`（GPL-2.0 / GPL-3.0 双许可，以外围仓库说明为准） |
| 本项目使用 / used as | **用户自行下载安装**到手机上；提供与内核 KMI 匹配的内核模块与 `ksud` |
| 是否分发 / redistributed | **否**。仓库里没有 manager APK，也没有 `kernelsu.ko` |
| 实测组合 / verified combo | `me.weishu.kernelsu` = `samsung-v2.2`（`ksud samsung-v2.2 (uapi: 5)`）。其他版本可能可用，但本项目未验证 |

为什么不分发：管理器与内核模块是**签名配对**的（模块里钉着期望的 APK 证书），分发二进制
既涉及许可，也容易让使用者混搭出无法诊断的组合。请只从上游发布页获取。

Why not redistributed: manager APKs and kernel modules are **signature-paired** (the module pins the
expected APK certificate). Redistributing binaries is both a licensing and a support problem —
mixing mismatched pairs is undiagnosable. Fetch them from upstream releases only.

---

## 3. Root-My-Galaxy payload 清单 / the Root-My-Galaxy payload list

| | |
|---|---|
| 出处 / source | `https://github.com/BuSung-dev/Root-My-Galaxy-Payloads` |
| 本项目使用 / used as | **只读参考**：`support/targets-v3.json` 用来证明目标固件**没有**现成的按构建匹配的 payload（`docs/DECISIONS.md` §C / §J1） |
| 是否分发 / redistributed | 否，也没有使用它的任何 payload |

---

## 4. 漏洞本身 / the vulnerability itself

| | |
|---|---|
| 编号 / id | **CVE-2026-43284**，公开名称 "DirtyFrag" |
| 性质 / kind | 页缓存写原语（page-cache write primitive），按 **KMI** 匹配内核模块，不需要按构建号编译 |
| 修复线 / fix line | 内核 `6.6.138`（`tools/analyze_firmware.py` 的判定依据） |
| 来源 / source | 公开公告与公开 PoC；检索该 CVE 编号即可自行核验。本项目不复制 PoC 代码，只使用上游 DFRoot 的实现 |

---

## 5. 构建与分析工具链 / build & analysis toolchain

| 组件 / component | 版本 / version | 获取 / from |
|---|---|---|
| Eclipse Temurin JDK | 21.0.13+9 | `https://api.adoptium.net` |
| Android SDK cmdline-tools | 16111833 | `https://dl.google.com/android/repository/` |
| SDK platform | android-37.0 | `sdkmanager` |
| build-tools | 37.0.0 | `sdkmanager` |
| platform-tools (`adb`) | 37.0.1 | `sdkmanager` |
| Gradle（wrapper） | 9.7.1 | `services.gradle.org` |
| AGP | 9.4.0 | Google Maven |
| Python | 3.9+（只用标准库 / stdlib only） | 系统自带 |

版本不是随便写的：不同 JDK/AGP 会改变 APK 字节，`docs/BUILD_RECORD.md` §7 记录的哈希就是在这套版本下产生的。

The versions matter: a different JDK/AGP changes the APK bytes. The hashes in
`docs/BUILD_RECORD.md` §7 were produced with exactly these.

---

## 6. 不在本仓库里的东西 / deliberately absent

| 项目 / item | 原因 / why |
|---|---|
| 三星固件、OTA 包、`AP_*.tar.md5` | 版权与体积；请从正规渠道获取 |
| 预编译 APK | debug 签名 + 体积 + 不分发"替你承担风险"的产物 |
| manager APK、`kernelsu.ko` | 见 §2 |
| 设备标识、崩溃日志原文、取证目录 | 隐私。日志分析方法在 `docs/KP_CASE_STUDY.md`，你可以在自己设备上复现 |
| 任何个人身份信息 | 本仓库刻意不含作者姓名、邮箱、设备序列号 |
