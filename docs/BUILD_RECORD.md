# 制作记录 — DFRoot_4.7-f966w-czjb-lock2.apk

> 🌐 **English full text: [`BUILD_RECORD.en.md`](BUILD_RECORD.en.md)** — same sections, same numbers, same commands.
> 中文正文在下方；两份以中文为记录正本（数值冲突时以中文为准）。

## Abstract (English)

A step-level manufacturing log for the locked temporary-root APK on Samsung Galaxy Z Fold7 (Canada)
`SM-F966W` / `CP2A.260605.016.F966WVLUDCZJB` (Android 17, kernel `6.6.127-android15-6.6-4k`).
It records the exact toolchain versions, the nine source patches, the byte-identical native payloads
extracted from the official `diablo/DFRoot` v4.7 release, seven verification commands with expected
hashes, and the six constants that must be edited when targeting a different firmware. Follow it top
to bottom and you can rebuild the same APK from scratch. Everything here is derived from public
material: `diablo/DFRoot`, the public DirtyFrag (CVE-2026-43284) LKM-loading technique, and the
public KernelSU builds. No Samsung firmware or proprietary file is redistributed.

本文是**操作手册**，不是总结。目标：换一份新固件后，照着做完就能产出新的锁定版 APK。
所有命令都在项目根目录执行，路径一律相对（Git Bash on Windows）。
本记录只描述**实测跑通**的步骤；没跑过的会明确标注。

记录时间：2026-11-12（真机临时 root 成功后整理）

---

## 0. 产物指纹（先确认要造的的确实是这一个）

```text
文件名        DFRoot_4.7-f966w-czjb-lock2.apk
路径          src/DFRoot/app/build/outputs/apk/release/
大小          94,911 bytes
sha256        2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7
包名          df.root（与上游一致，可覆盖安装旧版）
versionCode   4701
versionName   4.7-f966w-czjb-lock2
label         DFRoot F966W
minSdk 32 / targetSdk 37 / 只有 arm64-v8a
签名          v2，CN=Android Debug，证书 SHA-256 01aa025b44986b95837b4ccb74a759fd35957d8945eeb37c8be51e8e4fd9a5c2
```

`src/` 不入 git，所以**源码改动全部记录在 `patches/dfroot-f966w.patch`（654 行 / 9 个文件）**。
只靠"git + 补丁 + 项目内工具链"就能逐字节重建这个 APK，已实测验证（见 §7.6）。

---

## 1. 原理：这个 APK 到底做了什么

理解链条才能知道换固件时哪一环会断。

```text
APK (Java)                         内核 / 用户态
────────────────────────────────────────────────────────────────────
点 LAUNCH ROOT
  └─ DeviceLock.check()      五项校验：model / build / sdk / fingerprint / kernel
  └─ ExploitRunner.run()
       ├─ 选 manager 包名 ─────────────┐
       ├─ 建 IPsec 隧道 + 共享内存 ─────┤
       └─ exec libdfroot.so ────────────┘
                          │
                          ├─ CVE-2026-43284 "DirtyFrag"：把页缓存写进
                          │  init 的可执行映射，改写出的 shellcode 在 init
                          │  里执行 → touch /dev/df，insmod dfroot.ko
                          │                              （dfroot-android15-6.6.ko）
                          ├─ dfroot.ko: SELinux permissive + patch DEFEX
                          │  → call_usermodehelper 起 sh → /dev/dfm0
                          └─ bootstrap（libbootstrap.so 里的 main）：
                             /dev/dfm1 起来了
                             /dev/dfm2 读到 prefs，拿到 su_manager
                             /dev/dfm3 继承 zygote 环境
                             /dev/dfm4 （可选）禁用 KSU 模块
                             /dev/dfm5 即将 exec `ksud late-load`
                                      │
                                      └─ ksud: 用 /proc/kallsyms 手工重定位
                                         kernelsu.ko → init_module(2)
                                         → /dev/dfm6（退出 0）
                                         → /dev/dfme2（失败）
```

**关键点**：`libdfroot.so` 和 `libbootstrap.so` 是**上游编译好的二进制**，本记录不重编译它们。
锁定版只做三件事：

1. 加一道"只在指定固件上运行"的锁（Java）；
2. 把执行到哪一步落盘 + 用真判据（dfm6/dfme2）判断成败（Java）；
3. 关掉一个已知会自己重启的选项（Java）。

内核侧的 exploit 能力 100% 来自上游，所以**自编译没有意义，反而破坏可核验性**。

---

## 2. 前置准备：需要准备五个输入

| # | 输入 | 用途 | 本机取值 |
|---|---|---|---|
| 1 | 官方 DFRoot v4.7 APK | 里面装着原生 payload 与 8 个 KMI 的 ko | `9e193ffdaada8577e14a04fb19403256b3fa4991fae1331c7956e083c098a7b1` |
| 2 | 上游 DFRoot 源码 | Java 侧改动的基础 | `diabl0w/DFRoot` `7a6513a`（v4.7 + #185） |
| 3 | KernelSU 管理器 APK | ksud 作为 late-load 的载荷，签名必须与 kernelsu.ko 配对 | `KernelSU_samsung-v2.2_32687-release.apk` `761dffad…` |
| 4 | 固件包的 `boot.img.lz4` | **离线核对内核版本 / KMI / 编译配置**，不必刷机 | `firmware/boot.img.lz4` |
| 5 | 目标机的运行时属性 | 填 DeviceLock 的五个常量 | 见 §9.1 |

第 4 项容易被跳过，但它决定一切：**KMI 选错，ko 必装不进**。
从 `boot.img.lz4` 取内核版本的做法（`tools/lz4frame.py` 只读不写，直接打印结果）：

```bash
python -u tools/lz4frame.py "firmware/boot.img.lz4"
```

它同时给出内核版本字符串和内核哈希（本机实测输出）：

```text
kernel size: 39115264
arm64 Image magic @4096+0x38: b'ARMd'
banner: Linux version 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k (kleaf@build-host) ... #1 SMP PREEMPT Mon Oct 19 08:36:50 UTC 2026
kernel  sha256: a6222eb6f6cfd7e32941e5f74feae5b2f371081c14298fe1633969cf4abe2e51
```

要把它落成文件（后续查编译配置用）就补三行：

```bash
python - <<'PY'
import sys, struct
sys.path.insert(0, 'tools')
from lz4frame import decode_frame
boot = decode_frame(open('firmware/boot.img.lz4', 'rb').read())
ksize = struct.unpack_from('<I', boot, 8)[0]        # boot 头 offset 8 = kernel_size
open('build_logs/kernel.img', 'wb').write(boot[4096:4096 + ksize])
PY
sha256sum build_logs/kernel.img     # 应等于上面打印的 kernel sha256
```

（`4096` 是 boot 头的页长度；写错会得到一个不以 `ARM\x64` 开头的文件，一看就知道。）

---

## 3. 搭工具链（全部装在项目内，不碰系统）

版本必须一致，否则产物哈希会变。

| 组件 | 版本 | 落在 |
|---|---|---|
| JDK | Temurin **21.0.13+9** | `toolchain/jdk-21.0.13+9/` |
| Android cmdline-tools | 16111833（sdkmanager 23.0.0） | `toolchain/android-sdk/cmdline-tools/latest/` |
| SDK platform | **android-37.0** | `toolchain/android-sdk/platforms/android-37.0` |
| build-tools | **37.0.0** | `toolchain/android-sdk/build-tools/37.0.0` |
| platform-tools | 37.0.1（adb） | `toolchain/android-sdk/platform-tools` |
| Gradle | **9.7.1**（wrapper） | `toolchain/gradle-home/` |
| AGP | **9.4.0** | Maven 拉取 |

```bash
mkdir -p toolchain/dl toolchain/android-sdk toolchain/gradle-home
# JDK：Adoptium Temurin 21.0.13+9，解到 toolchain/jdk-21.0.13+9/
# cmdline-tools：commandlinetools-win-16111833_latest.zip，解到 toolchain/android-sdk/cmdline-tools/latest/
export JAVA_HOME="$PWD/toolchain/jdk-21.0.13+9"
export ANDROID_HOME="$PWD/toolchain/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export GRADLE_USER_HOME="$PWD/toolchain/gradle-home"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager.bat" --sdk_root="$ANDROID_HOME" \
    "platforms;android-37.0" "build-tools;37.0.0" "platform-tools"
```

`build.sh` 用的是项目内 JDK/SDK，不读系统环境，所以系统上装不装 Android Studio 都无所谓。

---

## 4. 取源码（必须钉到具体 commit）

```bash
git clone https://github.com/diabl0w/DFRoot src/DFRoot
git -C src/DFRoot checkout 7a6513a69ce4c1a90b68d857c26347bf166ffe10
git -C src/DFRoot rev-parse --short HEAD     # 必须输出 7a6513a
```

`7a6513a` = v4.7 + `Fall back to libbase when libc++ hook selection fails (#185)`。
补丁就是相对这个 commit 做的。

---

## 5. 应用本地补丁（9 个文件，逐个说明）

```bash
git -C src/DFRoot apply patches/dfroot-f966w.patch
```

`build.sh` 会自动做这一步（检测 `DeviceLock.java` 不存在时才应用），所以手动跑也行、不跑也行。
**备份/回退**：

```bash
git -C src/DFRoot apply -R --check - < patches/dfroot-f966w.patch   # 先确认能干净回退
git -C src/DFRoot apply -R -         < patches/dfroot-f966w.patch   # 回退到上游原状
```

> 注意：`git -C <dir> apply` 会把相对补丁路径按**仓库目录**解析，所以用 stdin 喂进去最稳。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `app/build.gradle.kts` | versionCode 407→**4701**，versionName→`4.7-f966w-czjb-lock2`；签名配置改成"有 keystore 才建 release，否则回落 debug"；删掉 `externalNativeBuild/cmake` | 版本号与上游区分，避免误升级覆盖；本机不生成 keystore；**不编译 native**，用预编译 payload |
| `app/src/main/AndroidManifest.xml` | label `DFRoot` → `DFRoot F966W` | 手机上能一眼看出装的是哪个构建 |
| `DeviceLock.java`（新增） | 五项校验：`MODEL` / `BUILD_ID(+SHORT)` / `SDK_INT` / `FINGERPRINT_PREFIX` / `KERNEL_PREFIX` | DirtyFrag 是按 KMI 匹配的，同一 KMI 的别的机型也能跑。这把锁是安全带：不匹配就拒绝碰内核 |
| `Diagnostics.java`（新增） | 运行日志写 `files/diag.log`（设备加密存储，重启仍在）；每 150 ms 轮询 `/dev/df*` 标记；开机打印 `ro.boot.bootreason` + 上一次 boot 的尾部 | `/dev/*` 标记重启即消失，旧版崩了以后**查不到走到哪一步** |
| `ExploitRunner.java` | 入口加 DeviceLock 校验（覆盖 BootReceiver 通道）；强制 `soft_reboot=false`（`commit()` 同步写，因为 `bootstrap.c` 直接读 prefs XML）；exploit 退出后继续等 `/dev/dfm6` 或 `/dev/dfme2` 最多 90 s，用**标记**而不是退出码判成败 | 上游 `bootstrap.c` 在 ksud 失败时 **main 仍 return 0** → 旧版照打 SUCCESS。这是最大的误导源 |
| `MainActivity.java` | 锁失败时禁用 Launch；新增菜单 `Run log` / `Markers now`；toast 区分 6 种结果；副标题标注锁定版 | 没有 adb 也能取证 |
| `BootReceiver.java` | 开机广播里也写 banner / 日志 | 开机自启路径同源 |
| `SettingsFragment.java` | `Auto Soft Reboot` 置灰 + 写明被强制关闭 | 上游 #122 有"没勾也自己软重启"的 ksud bug |
| `res/menu/main_menu.xml` | 加 `action_log` / `action_markers` | 同上 |

---

## 6. 原生 payload（不重编译，但要核对）

```bash
python tools/extract_native_payloads.py
```

它从官方 v4.7 APK 里取两个 `.so`，并把 `libdfroot.so` 的 `.rodata` 里 **`.incbin` 进去的 8 个 ko**
切出来做哈希审计（写到 `src/DFRoot/build_logs/embedded-ko/`，只因脚本的 cwd 是源码根）。期望值：

```text
libdfroot.so      1dc45a41991c7db2e23e21d3ecd769640dfce3a9eeb2c9fd1b2248b1578ad3db
libbootstrap.so   654d11c78eaaa3469dd90072d038181961dc11a0ef4d3b7bdea4aa54cabab236
```

内嵌 ko 的完整清单与哈希（`src/DFRoot/build_logs/embedded-ko/`）：

| KMI 文件 | sha256 |
|---|---|
| `dfroot-android12-5.10.ko` | `294564a3ee6d7d5fb0a5d7e4e5be408d2b479d98c3dd27ebebc220446014934a` |
| `dfroot-android13-5.10.ko` | `3a3c0e74230e960fea802bbc0f6a784934e41d853b64ed94b1fac679bf2aa3f0` |
| `dfroot-android13-5.15.ko` | `9dfb8b71b306f5a38fd8b35b283d4dab8b4eb25a08ad97ca0f4ef705b6151c68` |
| `dfroot-android14-5.15.ko` | `8b4d0a88ac07302415fb5483c2017412e7b67106a3b46b45aa9868d86fb5a3a5` |
| `dfroot-android14-6.1.ko` | `5b6107a885b9df54cad7c0f766c87195adda996a1b21814398493a41fc71a0d7` |
| **`dfroot-android15-6.6.ko`** | `6d6f747234ad33c746e2dbb503336f2e82ff82a790b653e511feb0e02d767718` |
| `dfroot-android16-6.12.ko` | `236b82afee477091542a6334ac79a635a1f46374ec447b763f6648998370ed1c` |
| `dfroot-android17-6.18.ko` | `5d1b0ccbe96b1df5b690545a167d61cf6616304a18a1366af8ca681690cd9a5e` |

目标机用的是 `android15-6.6`，vermagic：
`6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64`。

**KMI 是怎么定的**：DFRoot 自己读 `uname -r`，取 `(android, major, minor)`。
`6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k` → `android15-6.6`。
所以**子版本号（127）不影响选 ko**，只有 `androidNN-X.Y` 影响。这条决定了换固件时 ko 要不要跟着换。

---

## 7. 构建与核验

### 7.1 构建

```bash
bash build.sh
```

内部顺序：检查 JDK/SDK/源码 → 必要时 `git apply` 补丁 → 必要时提取 payload →
`./gradlew --no-daemon :app:assembleRelease` → 打印 APK 路径与 sha256。

### 7.2 元数据

```bash
BT=toolchain/android-sdk/build-tools/37.0.0
$BT/aapt2.exe dump badging src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk \
  | grep -E "^package|application-label:|native-code"
```

期望：

```text
package: name='df.root' versionCode='4701' versionName='4.7-f966w-czjb-lock2' ... compileSdkVersion='37'
application-label:'DFRoot F966W'
native-code: 'arm64-v8a'
```

### 7.3 payload 没被动过（最重要的一项）

```bash
python - <<'PY'
import zipfile,hashlib
z=zipfile.ZipFile('src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk')
for n in ['lib/arm64-v8a/libdfroot.so','lib/arm64-v8a/libbootstrap.so']:
    print(n, hashlib.sha256(z.read(n)).hexdigest())
PY
```

必须等于 §6 的两个哈希。不等就说明有人动过 native 代码，产物不可信。

### 7.4 补丁确实生效（在 dex 里查字符串）

```bash
python - <<'PY'
import zipfile
d=zipfile.ZipFile('src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk').read('classes.dex')
for s in [b'Markers now',b'Run log',b'diag.log',b'ksud late-load EXITED',b'bootreason',b'Auto Soft Reboot',b'SM-F966W']:
    print(s, d.count(s))
PY
```

期望：每个都 ≥1（`diag.log` 与 `ksud late-load EXITED` 各 2）。

### 7.5 签名与对齐

```bash
cmd //c "toolchain\android-sdk\build-tools\37.0.0\apksigner.bat verify --print-certs \
  src\DFRoot\app\build\outputs\apk\release\DFRoot_4.7-f966w-czjb-lock2.apk"
$BT/zipalign.exe -c -v 4 src/DFRoot/app/build/outputs/apk/release/DFRoot_4.7-f966w-czjb-lock2.apk
```

期望签名 `CN=Android Debug`，证书 SHA-256 `01aa025b…`；zipalign 无输出错误即通过。
（`apksigner` 在 Windows 上只有 `.bat`，没有 `.exe`。）

### 7.6 位级可复现（重建一次，比哈希）

```bash
git -C src/DFRoot apply -R - < patches/dfroot-f966w.patch      # 回到上游原状
bash build.sh                                                   # 自动重新应用补丁
sha256sum src/DFRoot/app/build/outputs/apk/release/DFRoot_*.apk
```

期望仍是 `2a2b59f7…`。本机已实测通过。**这一步是这份记录可信的全部依据**：
如果哪天重建出来的哈希变了，说明工具链或上游漂移了，别急着装机。

---

## 8. 安装与首次运行

1. 先装 KernelSU 管理器 APK（`deliverables/KernelSU_samsung-v2.2_32687-release.apk`）。
   DFRoot 的下拉框只列出**装了 `libksud.so`** 的应用，所以顺序不能反。
2. 装 DFRoot（`df.root`，可覆盖旧版，同一 debug 签名）。
3. 打开 → Settings：`Start at Boot` 关、`Disable KSU Modules` 关、`Auto Soft Reboot` 已置灰。
4. 主界面下拉框选 KernelSU。
5. 点 `LAUNCH ROOT`，看输出最后一行：
   - `SUCCESS (KernelSU loaded)` = 看到 `/dev/dfm6`
   - `exploit OK but ksud late-load FAILED` = 看到 `/dev/dfme2`
   - `chain never finished` = 90 s 内既无 dfm6 也无 dfme2，菜单 `Markers now` 看停在哪一格

`/dev/df` 存在时按钮会禁用（本次开机已经跑过），重启后才能再跑。

---

## 9. 固件升级后怎么重建（核心章节）

### 9.1 第一步：从真机取六个值（不 root，adb 即可）

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell getprop ro.product.model          # → DeviceLock.MODEL
$ADB shell getprop ro.build.display.id       # → DeviceLock.BUILD_ID（三星完整版本号）
$ADB shell getprop ro.build.id               # → BUILD_ID_SHORT 的来源
$ADB shell getprop ro.build.version.sdk      # → DeviceLock.SDK_INT
$ADB shell getprop ro.build.fingerprint      # → DeviceLock.FINGERPRINT_PREFIX
$ADB shell uname -r                          # → DeviceLock.KERNEL_PREFIX，同时决定 KMI
```

本机这一次的值（CZJB）：

```text
ro.product.model        SM-F966W
ro.build.display.id     CP2A.260605.016.F966WVLUDCZJB
ro.build.id             CP2A.260605.016
ro.build.version.sdk    37
ro.build.fingerprint    samsung/q7qcsx/q7q:17/CP2A.260605.016/...
uname -r                6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
```

> `q7q` / `q7qcsx` 是 Fold7 的代号。换机型的话这两段一定不同，别照抄。

### 9.2 第二步：改 `DeviceLock.java` 六个常量

改完重新生成补丁，否则 `src/` 不在 git 里下次就丢了：

```bash
# 1) 直接改 src/DFRoot/app/src/main/java/df/root/DeviceLock.java
# 2) 重新导出补丁（src/ 不入库，补丁必须跟着更新）
git -C src/DFRoot add -N app/src/main/java/df/root/DeviceLock.java \
                        app/src/main/java/df/root/Diagnostics.java
git -C src/DFRoot diff -- app/build.gradle.kts app/src/main/AndroidManifest.xml \
                          app/src/main/java app/src/main/res/menu > patches/dfroot-f966w.patch
git -C src/DFRoot reset -q
```

`MODEL` / `BUILD_ID` / `BUILD_ID_SHORT` / `SDK_INT` / `FINGERPRINT_PREFIX` / `KERNEL_PREFIX`。
另外把 `build.gradle.kts` 的 `versionCode` 再 +1（4701 → 4702 …）、versionName 换后缀
（`-lock3`），这样新包一定能覆盖旧包。

### 9.3 第三步：判断 KMI 变了没有（决定要不要换 ko）

从新 `uname -r` 取 `androidNN` 和 `X.Y`，拼成 `androidNN-X.Y`：

| 新 `uname -r` | KMI | 结论 |
|---|---|---|
| `6.6.xxx-android15-…` | `android15-6.6` | **ko 不用换**，只改锁 + 重编 |
| `6.12.xxx-android16-…` | `android16-6.12` | 上游 v4.7 已内嵌这个 KMI 的 ko，能直接用 |
| `6.18.xxx-android17-…` | `android17-6.18` | 同上 |
| 其它（如 `android15-6.12`） | 上游没有 | **停手**：要么等 DFRoot 出新版，要么这条路暂时不通 |

第二步是查上游有没有对应 KMI（不用联网，看内嵌 ko 清单即可）：

```bash
ls src/DFRoot/build_logs/embedded-ko/     # 8 个 KMI，见 §6 表格
```

同时 **KernelSU 那一侧也要有同一个 KMI 的 `kernelsu.ko`**。DFRoot 的 ko 只负责拿内核控制权，
真正提供 root 的是 KernelSU 的 LKM，两边的 KMI 必须一致。查法：

```bash
curl -sL "https://api.github.com/repos/diabl0w/KernelSU/releases/latest" \
 | python -c "import json,sys;[print(a['name']) for a in json.load(sys.stdin)['assets'] if 'lkm' in a['name']]"
```

没有任何公开 release 覆盖新 KMI 时，管理器的 late-load 会失败（`/dev/dfme2`，不重启）。
这种情况不是 APK 的问题，别去改 Java。

### 9.4 第四步：新固件可能顺带修好/改坏了 exploit（必须先判断）

先看这三行：官方 Run log 里“允许变化、但必须存在”的东西（§12.2 是 CZJB 的基准值）：

| Run log 里的行 | CZJB 基准 | 固件升级后可能怎么变 |
|---|---|---|
| `found ko_target: …` | `/vendor/lib64/libbinderdebug.so` | 改名/移位/被删 → exploit 第一步就失败 |
| `Found: hook=… shellcode=… len=…` | `hook=0xb4ae8 shellcode=0x10faa8 len=464` | libc++ 一改就变，属正常；搜不到会直接报错 |
| `BTI/PAC preamble at hook site, advancing +4` | 有 | 消失说明外部调用约定变了，要警惕 |

然后是漏洞本身。DirtyFrag（CVE-2026-43284）的修复线在 **6.6.138**。所以：

| 新内核子版本 | 风险 |
|---|---|
| 仍 `< 6.6.138`，且 `uname -r` 只改了构建串 | 大概率还能用，直接构建 |
| `>= 6.6.138` | **漏洞可能已被 backport 修复**，先看 DFRoot issue 区有没有人成功，别盲试 |

判断方法（不用真机）：从新固件 `boot.img.lz4` 解出 `kernel.img`，看内核版本与是否含
`system_supports_bti`、`scs_*`、`rkp_*`、`task_defex_*` 这些符号是否存在，
和自己记录的基线对比（方法见 §2）。这只判断"条件变没变"，不能证明漏洞还在。

真机上的判定只有一个：跑一次，看 `/dev/df` 有没有出现。
`DEVICE NOT VULNERABLE` 出现就说明页缓存写入校验失败，即漏洞已被修，**立即停止重试**。

### 9.5 第五步：重建 + 核验 + 装机

按 §7 全部走一遍，其中**必须重新确认的只有三项**：
§7.2（版本号变了）、§7.6（重建哈希）、§8 第 5 条（真机结果）。
§7.3 的 payload 哈希在"没换 DFRoot 版本"时应保持不变。

### 9.6 上游 DFRoot 发新版时

补丁基于 `7a6513a`。上游一动，`git apply` 会失败。处理顺序：

```bash
git -C src/DFRoot fetch && git -C src/DFRoot checkout <新 tag>
git -C src/DFRoot apply --3way patches/dfroot-f966w.patch   # 先试三方合并
```

- 能合并：人工检查 `ExploitRunner.java`（真判据那段）与 `bootstrap.c` 的标记名是否还一致 ——
  **标记名是硬编码在 `lkm/dfroot.c` 与 `jni/bootstrap.c` 里的**，上游改了名字，
  `Diagnostics.MARKERS` 必须同步改，否则"永远超时"。
- 不能合并：手工重做 §5 的 9 处改动，然后按 §9.2 重新导出补丁。

同时把 `build.sh` 里的基线 commit 字符串（`7a6513a`）改成新的。

---

## 10. 版本台账

| 版本 | versionCode | sha256 | 用途 |
|---|---|---|---|
| lock1 | 4700 | `42368624c762785385f126501014205e94cd377b5392dc9792f72046a66f9af3` | 首个可装版本，只有固件锁。**第一轮“显示成功后黑屏重启”就是它** |
| **lock2** | **4701** | **`2a2b59f76640de5fbf144da99214506da80bbe0201ac175f75fe59260e2047a7`** | 加运行取证 + 真成功判据 + 强制关 soft reboot。**已实测临时 root 成功（两次，各 2 秒）** |

lock1 与 lock2 的原生 payload 逐字节相同，差在 Java 侧。所以两版之间行为差异只能来自：
真判据、诊断落盘、`soft_reboot` 强制关。若那两次 08:13 / 08:16 的 KP（见 §12.4）真的是
`ksud soft-reboot` 被当成异常关机，那“关掉 soft reboot”就是两版之间的关键差异；
**这条要等 KP 日志内容才能定论**。

相关 git commit（本项目根仓库）：

```text
ee886a2  feat: build F966W/CZJB-locked DFRoot APK (DirtyFrag KMI route)
a114f4e  fix(lock): accept Build.DISPLAY for Samsung build id; final APK hash
eeada33  repro: track DFRoot source changes as patches/dfroot-f966w.patch
ffa78d1  chore: .gitattributes so patches/build.sh keep LF
```

---

## 11. 已知坑（都是实际踩过的）

| 坑 | 现象 | 处理 |
|---|---|---|
| 把 `***SUCCESS***` 当成 root 成功 | 显示成功，其实 ksud 失败 | 上游 `bootstrap.c` 两个分支都 `return 0`。看 `/dev/dfm6` 与 `/dev/dfme2`，用 lock2 的 Run log |
| 直接 `git apply patches/...` 报找不到文件 | `git -C src/DFRoot` 把相对路径按仓库目录解析 | 用 stdin：`git -C src/DFRoot apply - < patches/dfroot-f966w.patch` |
| 补丁在 Windows 上应用失败 | CRLF 污染 | 仓库有 `.gitattributes` 强制 `*.patch` / `*.sh` 用 LF，别删 |
| `apksigner.exe` 不存在 | 只有 `apksigner.bat` | 用 `cmd //c "...apksigner.bat ..."` |
| 下拉框里没有 KernelSU | 先装了 DFRoot 后装管理器 | 先装管理器；DFRoot 只列出含 `libksud.so` 的应用 |
| 装了 KaySU 却看不到效果 | ksud 用 `am start` 重启的管理器类名写死成 `me.weishu.kernelsu.ui.MainActivity` | 手动开 KaySU 看状态 |
| `adb shell grep /proc/kallsyms` 无输出 | `Permission denied`（SELinux） | 这条路走不通，不要用它做判定；用 `/dev/df*` + dropbox |
| `ls /data/log` 能列但读不了文件 | `dumpstate_lastkmsg_*_KP.log.gz` 是 `system:log 0640` | 目录可读、文件不可读。要拿走内容必须先拿到临时 root（见 §12.4） |
| `gzip` 解不开 `dumpstate_lastkmsg_*_KP.log.gz` | 名字叫 `.gz`，实际是 ZIP（`PK\x03\x04`），`gzip.open()` 报 `BadGzipFile: Not a gzipped file (b'PK')` | 用 `python tools/kp_inspect.py <目录>`；真值在包内 `store_extra_info.lst`（一行结构化字段：RR/TASK/PANIC/PC/LR），不要先去读 2 MB 的 `dumpstate_lastkmsg.lst` |
| `adb pull /sdcard/...` 报 `failed to stat remote object 'C:/Program Files/Git/sdcard/...'` | Git Bash 把前导 `/` 改成 Windows 路径 | 加 `MSYS_NO_PATHCONV=1`（`adb shell` 里的路径不受影响） |
| Run log 里 `ro.boot.bootreason=?` | `Diagnostics.prop()` 的反射被 API 37 隐藏 API 限制拦下 | 不影响功能（不修，避免动已验证产物）；实际原因用 `adb shell getprop ro.boot.bootreason` 看 |
| 崩了以后 `dmesg` / `logcat` 是空的 | 它们在内存里，kernel panic 后全丢 | 看 dropbox（`SYSTEM_LAST_KMSG` / `SYSTEM_RESTART`），`tools/evidence.bat` 已按此排序 |
| `src/` 不在 git 里 | 改半天，一 clone 就没了 | 改动一律落进 `patches/`，见 §9.2 |
| 用 `src/` 的 native 代码自己编 | 产物哈希对不上，且行为不可验证 | 不要编。payload 只用官方 v4.7 的二进制 |

---

## 12. 成功记录（2026-11-12，实测）

### 12.1 实测结果

| 项目 | 实测值 |
|---|---|
| 结果 | **成功**，`/dev/dfm6` 出现（`ksud late-load finished cleanly - KernelSU is loaded`） |
| SU manager | `me.weishu.kernelsu` = `KernelSU_samsung-v2.2_32687-release.apk`（A 组） |
| 耗时 | **1.94 秒**（RUN START 12:03:26.755 → RUN END 12:03:28.791，`uptime` 9509.6s → 9511.7s） |
| 重复性 | 同一天连做两次都成功（12:03 与 12:19），第二次同样在 2 s 内 |
| 重启后 | `su` 失效（临时 root 的正常预期，不是缺陷） |
| 取证存档 | `evidence/20261112_122234/`（本次提交时不入库，git 忽略） |

### 12.2 完整 Run log（这是"成功"长什么样，下次拿来对照）

```text
* locked profile: SM-F966W / CP2A.260605.016.F966WVLUDCZJB / KMI android15-6.6 (DirtyFrag)
* app version: 4.7-f966w-czjb-lock2
* manufacturer: samsung
* model: SM-F966W
* android version: 17
* security patch: 2026-10-05
* kernel version: 6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k

=== setup ===
found ko_target: /vendor/lib64/libbinderdebug.so
encap port: 59588
spi: 0x19ee75a5

=== exploit (patching files) ===
patch: crash_dump64 <- splicehelper (1408 bytes)
patched 1408 bytes to /apex/com.android.runtime/bin/crash_dump64+0x0
Using KMI: android15-6.6
patch: /vendor/lib64/libbinderdebug.so <- dfroot.ko (10432 bytes)
patched 10432 bytes to /vendor/lib64/libbinderdebug.so+0x0
Finding symbol offsets for /system/lib64/libc++.so:
BTI/PAC preamble at hook site, advancing +4
Found: hook=0xb4ae8 shellcode=0x10faa8 len=464
patch: /system/lib64/libc++.so <- shellcode (464 bytes)
patched 464 bytes to /system/lib64/libc++.so+0x10faa8
patch: /system/lib64/libc++.so <- trampoline (16 bytes)
patched 16 bytes to /system/lib64/libc++.so+0xb4ae0

=== init  ===
Triggering hook...
libc++: loading custom module
kernel module: launching bootstrap
bootstrap: loading app preferences file
bootstrap: cloning zygote env
bootstrap: setting partitions ro
bootstrap: starting SU daemon
ksud start: SUCCESS

=== cleanup ===
restoring trampoline in /system/lib64/libc++.so
patched 16 bytes to /system/lib64/libc++.so+0xb4ae0
restoring shellcode in /system/lib64/libc++.so
patched 464 bytes to /system/lib64/libc++.so+0x10faa8
* exploit binary exited rc=0; waiting for the init hook to fire...
* ksud late-load finished cleanly (/dev/dfm6) - KernelSU is loaded
```

`diag.log` 里对应的落盘记录（跨重启保留，这是 lock2 的价值所在）：

```text
11-12 12:03:26.725 up=9509.6s --- DFRoot 4.7-f966w-czjb-lock2 (build 4701) ---
11-12 12:03:26.755 up=9509.6s === RUN START (manual) manager=me.weishu.kernelsu soft_reboot=false disable_modules=false /dev/df=false
11-12 12:03:28.712 up=9511.6s * marker /dev/df appeared - shellcode ran in init (ko written, insmod path taken)
11-12 12:03:28.791 up=9511.7s === RUN END exploit rc=0, verdict=KernelSU loaded (dfm6) ===
```

### 12.3 这次成功印证/否定的东西

**印证**：
- `/dev/dfm6` 是可靠的成功判据，`bootstrap.c` 的 `***SUCCESS***` 确实不代表 root（旧版的误导成立）。
- lock2 的 90 s 等待逻辑正确：实测 0.08 s 内就等到 dfm6（`RUN END` 紧跟 `/dev/df` marker）。
- `soft_reboot=false` 这一路正常。

**新事实（写进固件升级注意事项）**：
1. **`ko_target` 是 `/vendor/lib64/libbinderdebug.so`**。固件升级如果改动了这个 vendor 库
   （改名、改大小、不在原路径），exploit 的第一步 `patch: ... <- dfroot.ko` 就会失败。
   这是换固件后要重点看的一行。
2. **hook 点落在 `/system/lib64/libc++.so+0xb4ae8`，前面有 BTI/PAC 前导，DFRoot 会自动 +4 跳过**
   （日志：`BTI/PAC preamble at hook site, advancing +4`）。固件更新 libc++ 后偏移会变，
   DFRoot 会重新搜索，但**搜索失败就是直接报错或崩**，这属于"上游适配"范畴，不是 APK 能修的。
3. `/data/log` 目录对 `shell` **可读**（`ls` 成功），但里面的 `dumpstate_lastkmsg_*_KP.log.gz`
   是 `system:log 0640`，**读不了内容**。要读必须先拿到 root（见 §12.4）。

**已知缺陷（不影响使用，未修，避免动已验证的产物）**：
- `Diagnostics.prop()` 用反射调 `android.os.SystemProperties.get`，在 API 37 上被隐藏 API 限制拦下，
  所以 Run log 里显示 `ro.boot.bootreason=? | sys.boot.reason=?`。
  看真实的 bootreason 请用 `adb shell getprop ro.boot.bootreason`（本次实测 `reboot,userrequested`，
  即用户手动重启）。若以后要修：改用 `Runtime.getRuntime().exec("getprop ...")` 读。

### 12.4 已结案：第一轮"黑屏重启"是真 kernel panic，死在 kernelsu 模块里

`evidence/20261112_122234/12_samsung_dumpstate_logs.txt` 里列出（`ls /data/log` 无需 root）：

```text
-rw-r----- system log  666385 2026-10-14 13:46 dumpstate_lastkmsg_28_20261014_134615_KP.log.gz
-rw-r----- system log  698594 2026-10-14 16:39 dumpstate_lastkmsg_29_20261014_163921_KP.log.gz
-rw-r----- system log  703939 2026-10-22 14:21 dumpstate_lastkmsg_30_20261022_142106_KP.log.gz
-rw-r----- system log  693845 2026-11-12 08:14 dumpstate_lastkmsg_31_20261112_081336_KP.log.gz
-rw-r----- system log  725097 2026-11-12 08:16 dumpstate_lastkmsg_32_20261112_081607_KP.log.gz
```

**11-12 08:13 与 08:16 这两条，时间落在第一轮失败（"显示成功后黑屏重启"）的范围里。**
所以那次很可能真的是内核侧异常，而不是软件重启。注意 `_KP` 只代表"上次开机没有正常关机"，
里面可能是真 panic（Oops/BUG），也可能只是被硬复位截断的正常日志 —— **必须读内容才能定性**。

拿临时 root 顺手把它们取出来的方法（root 只活到下次重启，2 秒就有）：

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
# 1) 手机上点 LAUNCH ROOT（约 2 秒）
# 2) 取出 KP 日志
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_31_*_KP.log.gz /sdcard/Download/"
$ADB shell su -c "cp /data/log/dumpstate_lastkmsg_32_*_KP.log.gz /sdcard/Download/"
$ADB pull /sdcard/Download/ evidence/kp/
```

### 12.4.1 2026-11-12 夜里：已取出并判读（结论：真 panic，B 假设成立）

设备当时 root 仍在（`su -c id` → `uid=0(root) context=u:r:ksu:s0`），一次取齐 5 条 KP 日志：

```bash
ADB=toolchain/android-sdk/platform-tools/adb.exe
$ADB shell "su -c 'mkdir -p /sdcard/Download/kp && cp -f /data/log/dumpstate_lastkmsg_*_KP.log.gz /data/log/dumpstate_latest_lastkmsg.log.gz /sdcard/Download/kp/ && chmod 644 /sdcard/Download/kp/*'"
MSYS_NO_PATHCONV=1 $ADB pull /sdcard/Download/kp/ evidence/kp/   # Git Bash 会把 /sdcard 改写成 C:/Program Files/Git/sdcard
```

**坑：这些 `.log.gz` 不是 gzip，是 ZIP（`PK\x03\x04`）。** `gzip.open()` 会报
`BadGzipFile: Not a gzipped file (b'PK')`。用 `tools/kp_inspect.py` 解析（本机无 unzip 也能跑）：
每个包里有 `store_extra_info.lst`（一行结构化字段，最有用）、`eRR.p`、
`dumpstate_lastkmsg.lst`（2 MB 内核日志）、`reset_summary.html`、`ocimem.lst` 等 7 个条目。

判读用：`python tools/kp_inspect.py evidence/kp --extract evidence/kp/extracted`

| KP | 时间 | TASK | PANIC | PC |
|---|---|---|---|---|
| 28 | 10-14 13:46 | RenderThread | Oops - BUG (`lib/list_debug.c:67`) | `__list_del_entry_valid_or_report+0xec` |
| 29 | 10-14 16:39 | `cve43499-run` | Oops | `_raw_spin_trylock+0x1c` |
| 30 | 10-22 14:21 | Jit thread pool | Oops - BUG (`lib/list_debug.c:64`) | `__list_del_entry_valid_or_report+0xdc` |
| **31** | **11-12 08:13** | **ksud** | **synchronous external abort** | **`ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu]`** |
| **32** | **11-12 08:16** | **ksud** | **synchronous external abort** | **同一 PC、同一模块 build id** |

（`dumpstate_latest_lastkmsg.log.gz` 与 32 的 sha256 完全相同：`59d78da1e4eb79c3…`，是同一份拷贝。）

31 与 32 的调用栈逐行相同（`dumpstate_lastkmsg.lst` 里 `Internal error:` 之后）：

```text
ksu_mark_running_process_locked+0x154/0x1e8 [kernelsu b61aef7e3fae7d02afb759c7a4acdecdd07aea2e]
 syscall_regfunc_handler+0x4c/0x88        [kernelsu b61aef7e…]
 __kretprobe_trampoline_handler+0xcc/0x140
 trampoline_probe_handler+0x28/0x48
 __kretprobe_trampoline+0x74/0xcc
 tracepoint_add_func+0x64/0x404
 tracepoint_probe_register+0x60/0xa4
 ksu_syscall_hook_manager_init+0xa8/0xe4  [kernelsu b61aef7e…]
 kernelsu_init+0xec/0x130                 [kernelsu b61aef7e…]
 do_one_initcall+0xdc/0x360 -> do_init_module -> load_module -> __arm64_sys_init_module
```

触发点在 `init_module` **内部**：`ksu_syscall_hook_manager_init` 在 `sys_enter` tracepoint 的
`regfunc` 上挂 kretprobe，`tracepoint_add_func` 同步回调它，回调里 `tp_marker: mark process:
pid:1, uid: 0, comm:init` 这条日志刚打完（`x6/x7/x13` 还是 `KernelSU` / `: tp_mar` / `omm:init` 这些
格式串片段），紧接着在 `ksu_mark_running_process_locked+0x154` 取数时 `synchronous external abort`
（`do_sea`，ESR 低位 `0x96000010`/HYP 侧 `ESR_EL2=0x9200004e`，DFSC=0b001110），
随即 `Kernel panic - not syncing: synchronous external abort: Fatal exception`。
`store_extra_info.lst` 里的 `RPM=AOP_NON_SECURE_WD_BITE_INT_RECEIVED` / `TZ_RR=TZBSP_ERR_FATAL_NON_SECURE_WDT`
是内核已经死掉之后看门狗咬的结果，**不是原因**。

### 12.4.2 这次 panic 说明了什么

1. **A 假设（`ksud soft-reboot` 被当异常关机）作废**：`soft_reboot` 在 `bootstrap.c` 里位于
   `dfm6` 之后，而这次内核是在 `kernelsu.ko` 的 `init_module` 里死的 —— 一行 `dfm6` 都没走到。
   lock2 强制 `soft_reboot=false` 不可能是这两次的解药（它仍然是个正确的加固，只是不是原因）。
2. 症状链完全对上：ko init 崩 → 内核死 → watchdog 咬 → 硬重启 → root 消失。
3. 崩塌点是 `ksu_mark_running_process_locked` 遍历/标记进程时的**一次线性映射读**
   （`x19` 与 HYP 报的 fault VA 相同，`0xffffff8032f29d00` / `0xffffff8032e9c300`，两次只差 KASLR 偏移）。
   正常野指针会报 `Unable to handle kernel paging request`；`synchronous external abort` 意味着
   这一页由**非安全世界/管理程序**拒绝访问 —— 与 `REBOOT_TRIAGE.md` §2 判定的
   **RKP/KDP 页保护 + KCFI** 环境吻合 `[A]`（推断，未被进一步实验证实）。
4. **两次 panic 的 ko build id 相同**（`b61aef7e…`）、PC 偏移相同、日志序列相同 → 是那个
   二进制里**确定性的**代码路径问题，不是随机抽风。

### 12.4.3 当时用的 manager 不是现在这个（可核）

两个独立证据说明 08:13 装的是**另一个 APK 实例**，与当前 `samsung-v2.2` 不是同一份：

| 证据 | 08:13 | 现在（13:39 那次成功） |
|---|---|---|
| `/data/app` 实例目录（由 APK 内容/签名派生） | `~~akfkl_99vwnprRk2n8cDtA==/me.weishu.kernelsu-mvqige6ybGyuUO0HTeV6wA==` | `~~SgtRsoT9Ew37h_UC1xUqJA==/me.weishu.kernelsu-9H2ZfUhhMCGravyfSqF45w==` |
| 应用 uid | `10463` | `10503`（`u0_a503`） |
| 安装时间 | —（包名相同，版本号无法从设备恢复） | `firstInstallTime=2026-11-12 11:52:04` |

来源：dropbox `SYSTEM_TOMBSTONE`（08:14:26，`Executable: .../libksud.so`，`Cmdline: ... debug su`，
`uid: 10463`）；当前值来自 `dumpsys package me.weishu.kernelsu`。
当前 `ksud --version` = `ksud samsung-v2.2 (uapi: 5)`。

同一 tombstone 还显示崩的是 `libksud.so debug su` 与 `me.weishu.kernelsu:root:0`，
两者都是 `Data Abort Exception 0x24` —— 内核已死时的**下游**用户态崩溃，不是独立故障。

> 仍未确定：08:13 那个 APK 的确切版本号（设备上无残留：`pm list packages -u` 只剩当前包，
> `/data/user/0` 无 08:xx 目录，`/data/adb/ksu/log` 只保留最近两个旋转）。要补这一格只能靠当时的安装记录
> 08:0x 时 `adb install` 的是哪个文件。**不影响结论**：崩塌点与当前 4 次成功所用的 manager 不同一实例。

