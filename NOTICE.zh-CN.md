# 第三方组件与来源

> 🌐 **[English](NOTICE.md) · 中文（本文件）**

本仓库自身只有**方法、补丁、脚本与文档**。下面这些组件由第三方维护，本项目不重新分发，只在自己的
构建/分析流程里使用，并记录版本与校验值，方便你自行获取后确认拿到的是同一份东西。

## 1. DFRoot（exploit 与 bootstrap）

| | |
|---|---|
| 出处 | `https://github.com/diabl0w/DFRoot` |
| 许可 | **GPL-2.0**（见 `LICENSE`，与本仓库一致） |
| 本项目使用 | 源码基线（`setup_toolchain.sh` 克隆并检出 `7a6513a69ce4c1a90b68d857c26347bf166ffe10`），加上 `patches/dfroot-f966w.patch` |
| 原生 payload | 由 `tools/extract_native_payloads.py` 从**上游官方 release**（v4.7）下载后提取，校验值见 `docs/BASELINE.zh-CN.md`；本项目**不重编译**它们 |
| 归属 | exploit 逻辑、`bootstrap`、`dfroot.ko` 的原始作者均为上游项目；本仓库只做固件锁与诊断的包装 |

GPL-2.0 要求派生作品同样以 GPL-2.0 发布，这正是本仓库的许可。

## 2. KernelSU 及衍生管理器

| | |
|---|---|
| 上游 | `https://github.com/tiann/KernelSU`（GPL-2.0 / GPL-3.0 双许可，以各自仓库说明为准） |
| 本项目使用 | **由使用者自行下载安装**到手机上；提供与内核 KMI 匹配的内核模块与 `ksud` |
| 是否分发 | **否**。仓库里没有 manager APK，也没有 `kernelsu.ko` |
| 实测组合 | `me.weishu.kernelsu` = `samsung-v2.2`（`ksud samsung-v2.2 (uapi: 5)`）。其他版本可能可用，但本项目未验证 |

为什么不分发：管理器与内核模块是**签名配对**的（模块里钉着期望的 APK 证书），分发二进制既涉及许可，
也容易让使用者混搭出无法诊断的组合。请只从上游发布页获取。

## 3. Root-My-Galaxy payload 清单

| | |
|---|---|
| 出处 | `https://github.com/BuSung-dev/Root-My-Galaxy-Payloads` |
| 本项目使用 | **只读参考**：`support/targets-v3.json` 用来证明目标固件**没有**现成的按构建匹配的 payload（`docs/DECISIONS.zh-CN.md` §C / §J1） |
| 是否分发 | 否，也没有使用它的任何 payload |

## 4. 漏洞本身

| | |
|---|---|
| 编号 | **CVE-2026-43284**，公开名称 "DirtyFrag" |
| 性质 | 页缓存写原语（page-cache write primitive），按 **KMI** 匹配内核模块，不需要按构建号编译 |
| 修复线 | 内核 `6.6.138`（`tools/analyze_firmware.py` 的判定依据） |
| 来源 | 公开公告与公开 PoC；检索该 CVE 编号即可自行核验。本项目不复制 PoC 代码，只使用上游 DFRoot 的实现 |

## 5. 构建与分析工具链

| 组件 | 版本 | 获取 |
|---|---|---|
| Eclipse Temurin JDK | 21.0.13+9 | `https://api.adoptium.net` |
| Android SDK cmdline-tools | 16111833 | `https://dl.google.com/android/repository/` |
| SDK platform | android-37.0 | `sdkmanager` |
| build-tools | 37.0.0 | `sdkmanager` |
| platform-tools (`adb`) | 37.0.1 | `sdkmanager` |
| Gradle（wrapper） | 9.7.1 | `services.gradle.org` |
| AGP | 9.4.0 | Google Maven |
| Python | 3.9+（只用标准库） | 系统自带 |

版本不是随便写的：不同 JDK/AGP 会改变 APK 字节，`docs/BUILD_RECORD.zh-CN.md` §7 记录的哈希就是在这套
版本下产生的。

## 6. 不在本仓库里的东西

| 项目 | 原因 |
|---|---|
| 三星固件、OTA 包、`AP_*.tar.md5` | 版权与体积；请从正规渠道获取 |
| 预编译 APK | debug 签名 + 体积 + 不分发"替你承担风险"的产物 |
| manager APK、`kernelsu.ko` | 见 §2 |
| 设备标识、崩溃日志原文、取证目录 | 隐私。分析方法在 `docs/KP_CASE_STUDY.zh-CN.md`，可在自己设备上复现 |
| 任何个人身份信息 | 本仓库刻意不含作者姓名、邮箱、设备序列号 |
