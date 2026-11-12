# 当前基准（BASELINE）

> 🌐 **English full text: [`BASELINE.en.md`](BASELINE.en.md)** — same sections, same numbers, same commands.
> 中文正文在下方；两份以中文为记录正本（数值冲突时以中文为准）。

## Abstract (English)

The baseline: SHA-256 of every input and output that the rest of the documentation refers to, plus
the pure-Python LZ4-frame decoder used to unpack `boot.img.lz4` without any Samsung tooling. Hashes
are how you prove you are looking at the same kernel image as this record — check them first when
something does not reproduce.

核对时间：2026-11-11 20:23 UTC（本机 UTC）
核对机器：Windows 11 + Git Bash，Python 3.11.9，JDK 17.0.20（Temurin），`PI_OFFLINE=1`（无网络）
核对人：pi agent（本次会话全部数值由本机命令重新计算，不是引用旧档案）

## 1. 文件夹清单

| 路径 | bytes | SHA-256 |
|---|---:|---|
| `F966W-Temporary-Root-BBZG3-lock6.1-repeat70.apk` | 52,801,629 | `0f7180effd434cfc841676850b970ab9057b6afc4b85a5cdf180c4bcc19473a2` |
| `对话归档（未随仓库提供）` | 63,803 | 1,683 行 |
| `firmware/boot.img.lz4` | 22,797,350 | `a5bebd0959dd15a0597c6a1a8d5b07c71c7d0943268bf48e7ce18da9d34f6170` |
| `firmware/AP_F966WVLUDCZJB_..._OS17内包含的文件清单截图.jpg` | 338,482 | — |

两个哈希与档案第 5.1 / 9.1 节记录的完全一致 → 本地文件就是档案所指的那两份成品/上传件，不是同名副本。

## 2. 已交付 APK（Lock6.1）内部实况

APK 共 134 个条目。关键载荷（本次从 APK 内解出后重新计算）：

| 条目 | bytes | SHA-256 | 与档案一致 |
|---|---:|---|---|
| `assets/locked_payloads/cve-2026-43499-app.so` | 126,264 | `d809061172eb825a43571eaeb10d8a898d32db6f28a1f2fb90bae6b318a8068f` | 是 |
| `assets/locked_payloads/ksud-s25u-kdp` | 6,407,096 | `fa3edcc7d168637394877b30cb1f909d762dda788ec14051f4ae79edd6562d63` | 是 |
| `lib/arm64-v8a/libcve43499root.so` | 26,024 | `c6b0612b6bdbd60ded964694284f7e8d81cfff2079abeaf3b8854952c2b49eec` | 档案未记录 |
| `lib/arm64-v8a/libs25u_native.so` | 11,192 | `3104f3c15288a9a285f779c99d6768db7ed71d20c9606b1783fd344fd947fa26` | 档案未记录 |

从 `classes3.dex` 提取到的、成品 APK 里真正生效的锁定配置（比旧档案的"残留源码"可信）：

```text
applicationId            dev.busung.f966w.temproot.lock6
versionName              0.2.65-f966w-bzg3-lock6.1-repeat70
profile                  q7q-F966W-VLSBBZG3-locked
model                    SM-F966W
buildId                  BP4A.251205.006.F966WVLSBBZG3
csc/build marker         F966WVLSBBZG3
kernelRelease            6.6.98-android15-8-pd6ff1cd-abogkiF966USQSBBZG3-4k
fingerprintPrefix        samsung/q7qcsx/q7q:16/BP4A.251205.006/
STACK_WRITER_DELAY_USEC  70000        (= 70 毫秒，不是 70 秒)
PAYLOAD_COMMIT           536a0968077cbc213188ae7895bb688ea21ee779
内置下载 URL             raw.githubusercontent.com/BuSung-dev/Root-My-Galaxy-Payloads/536a0968.../artifacts/q7q-F966USQSBBZG3/cve-2026-43499-app.so
                         raw.githubusercontent.com/BuSung-dev/Root-My-Galaxy-Payloads/536a0968.../kernelsu/ksud-s25u-kdp
上游源码 revision        1f2f062503b8da342b39f03f7ba0704a8aa794ac（META-INF/version-control-info.textproto）
AGP                      9.2.1
界面文案                 "Canadian Galaxy Z Fold7 (SM-F966W / BBZG3 locked)"
```

APK 内 `META-INF/` 没有 `.RSA/.SF/.MF` → 与档案记录的"仅 v2 签名"一致。

**结论：这个 APK 按设计就会拒绝当前手机（One UI 9 / CZJB / 6.6.127）。它的 payload 是针对 BBZG3 内核镜像编译的产物。**

## 3. 新固件 boot 镜像（本次独立重算）

用自己写的纯 Python LZ4 frame 解码器（`tools/lz4frame.py`，不依赖任何安装包）重新解压：

```text
压缩文件 SHA-256      a5bebd0959dd15a0597c6a1a8d5b07c71c7d0943268bf48e7ce18da9d34f6170
解压后字节            101,122,048
magic                 ANDROID!
kernel size           39,115,264（header offset 8）
ramdisk size          0
boot.img SHA-256      3e29ee127035bb1ac94b45feeddbafcf88823e4f7ec74ca35ef34f4f61351bfb
kernel 字节 SHA-256   a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
banner                Linux version 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
                      (Android 11368308 +pgo +bolt +lto +mlgo, clang 18.0.0, LLD 18.0.0)
                      #1 SMP PREEMPT Mon Oct 19 08:36:50 UTC 2026
```

四项数值（解压长度、boot 哈希、kernel 哈希、banner）与档案第 9 章全部逐位一致。
2026-11-11 23:45 UTC 重跑：`python -u tools/lz4frame.py "firmware/boot.img.lz4"` 输出同上四项。
kernel 位置另两处交叉确认：`4096+0x38` 处是 arm64 Image 魔数 `ARMd`；`SEANDROIDENFORCE` 尾部在偏移 `39,120,896`。
本镜像头字段不套 AOSP 文档的 `header_version` 位置（详见 `DECISIONS.md` §A1）。
仍然只证明"镜像身份"，不证明官方签名有效、不证明存在可用 payload。

## 4. 工具链与源码现状（关键限制）

| 需要 | 本机状态 |
|---|---|
| 上游源码 `Root-My-Galaxy` v0.2.65 @1f2f062 | 不存在。全盘搜索 `root-my-galaxy` / `build.gradle.kts` / `settings.gradle` 无结果（只有历史 md 文档和本次会话记录） |
| Android SDK（compileSdk 37、build-tools: aapt2 / apksigner / zipalign / d8） | 不存在。`ANDROID_HOME` 为空，无 `AppData\Local\Android\Sdk`，全盘找不到 aapt2/apksigner/d8.jar |
| Gradle（历史用 9.5.1）/ AGP 9.2.1 / Kotlin / Compose 依赖 | 不存在，`~/.gradle`、`~/.m2` 均无缓存 |
| JDK 17 | 有（`Eclipse Adoptium\jdk-17.0.20.101`） |
| 网络 | 无（`PI_OFFLINE=1`） |
| 签名密钥库（Lock6/6.1 用的 debug keystore） | 不存在 |

**硬性结论：在这台机器上目前无法构建任何 APK（包括不含漏洞的只读诊断 APK）。构建前置条件必须先解决。**

## 5. 新旧固件差异（为什么旧 payload 不能"照搬白名单"）

| 字段 | BBZG3（APK 已锁定） | CZJB（手机现状） |
|---|---|---|
| kernel release | 6.6.98-...-p**d6ff1cd**-abogkiF966USQS**BBZG3**-4k | 6.6.127-...-p**4a765df**-abogkiF966USQ**UDCZJB**-4k |
| 内核编译时间 | Thu Jul 2 01:36:45 UTC 2026 | Mon Oct 19 08:36:50 UTC 2026 |
| Build | BP4A.251205.006.F966WVLSBBZG3 | CP2A.260605.016.F966WVLUDCZJB |
| Android / SDK | 16 / 36 | 17 / 37（截图；SDK 号未从设备命令复核） |
| kernel 字节哈希 | 未知（无旧镜像） | `a6222eb6f6cfd7e3...` |

内核次版本、构建标识、编译时间全变 → 与内核布局/偏移绑定的载荷不能跨构建使用。只改白名单放行 = 让按旧内核内存布局写的代码在新内核上乱写内存，这是明确的坏做法，本计划不包含。

---

# 6. 第二轮新增基准（2026-11-12）

本轮网络可用，按 DirtyFrag / DFRoot 路线产出了新 APK。以下是新增的可核验项。

## 6.1 新交付产物

| 路径 | bytes | SHA-256 |
|---|---:|---|
| `src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock1.apk` | 86,015 | `4ade4fb7c14b83433cb6fafb06e7be90c946a139618a1d8c40b841496f6347d6` |
| `deliverables/KernelSU_samsung-v2.2_32687-release.apk` | 7,607,475 | `761dffad54ae080a4977971db7b04e2fc65c2d9b5e2336accca4a85661290a69` |
| 上游官方 DFRoot v4.7 APK（比对基准） | 84,071 | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |

APK 内部（本次从产物重新计算）：

| 条目 | bytes | SHA-256 | 说明 |
|---|---:|---|---|
| `lib/arm64-v8a/libdfroot.so` | 123,384 | `1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db` | 与官方 v4.7 逐字节一致 |
| `lib/arm64-v8a/libbootstrap.so` | 10,048 | `654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236` | 与官方 v4.7 逐字节一致 |
| 内嵌 `dfroot-android15-6.6.ko` | 10,432 | `6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718` | vermagic `6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64` |
| KernelSU `lkm-aarch64-android15-6.6_kernelsu.ko` | 343,952 | `07127a9f635665cd3fb48e8f32ad36ca512656ea5b3d375e74164aab73cedc7f` | 同 KMI vermagic |

APK 元数据：package `df.root`、versionCode 4700、versionName `4.7-f966w-czjb-lock1`、
minSdk 32、targetSdk 37、label `DFRoot F966W`、`extractNativeLibs=true`、v2 签名
（CN=Android Debug，证书 SHA-256 `01aa025b…a5c2`）。

## 6.2 本机工具链（全部位于项目 `toolchain/`）

| 组件 | 版本 / 来源 |
|---|---|
| JDK | Temurin 21.0.13+9 |
| Android cmdline-tools | 16111833（sdkmanager 显示 23.0.0） |
| SDK platform | `android-37.0`（repo 包名 `platforms/android-37.0`） |
| build-tools | 37.0.0（aapt2 / apksigner / zipalign / d8） |
| platform-tools | 37.0.1（adb） |
| Gradle | 9.7.1（wrapper，`GRADLE_USER_HOME` 指向项目内） |
| AGP | 9.4.0 |
| 源码 | `diabl0w/DFRoot` master `7a6513a69ce4c1a90b68d857c26347bf166ffe10`（= v4.7 + #185） |

## 6.3 本轮复核过的上游事实

- `targets-v3.json` 12,242 B，20 个 payload，无 `CZJB`/`6.6.127`/`SM-F966W`（与上一轮判定一致）。
- DFRoot 设备选择逻辑：`uname -r` → (android, major, minor) = (15, 6, 6) → `dfroot-android15-6.6.ko`。
- `dfroot.ko` 只 import 6 个 GKI 符号，`__versions` 为空；上游实机日志（issue #60）显示该 ko
  可在 Samsung 6.6.x 上完成加载（随后失败发生在 ksud 阶段）。
- `apksigner verify`、`zipalign -c 4`、`aapt2 dump` 均通过；`PT_LOAD` 全部 `0x4000`。

## 6.4 仍未证明的事

- 没有真机连接（`adb devices` 为空），所以**没有实测 Root 成功**。
- CZJB 是否已 backport DirtyFrag 修复、One UI 9 的 DEFEX/KDP 行为，均未知。
- 本文件的“已验证”仅指构建产物与静态一致性，不等于漏洞利用成功。
