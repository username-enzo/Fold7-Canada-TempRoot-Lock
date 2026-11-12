# Put your firmware files here

> English (this file) · 中文说明见同一文件下半部分.

```
firmware/
├── boot.img.lz4        # or a plain boot.img. Comes from the Samsung firmware package AP_*.tar.md5
├── getprop.txt         # adb shell getprop > firmware/getprop.txt
└── README.md           # this file
```

## Where to get it

1. The official firmware package (the four/five-file set used by Odin), specifically `AP_*.tar.md5`.
2. Unpack it and take `boot.img.lz4`.
3. You do not need `BL_*`, `CP_*` or `CSC_*` — the analysis only needs the boot image.

`tools/analyze_firmware.py` will:

- unpack the LZ4 frame (pure Python, no extra tools) and print the SHA-256 of the boot payload and the kernel
- read the kernel banner → kernel version and KMI (e.g. `android15-6.6`)
- decide whether the kernel is older than the CVE-2026-43284 fix line `6.6.138`
- fingerprint SCS / KCFI / DEFEX / RKP-KDP / BTI from strings present in the image
- emit the six DeviceLock constants

## Privacy

- `firmware/` is gitignored and **will never be committed**.
- `getprop.txt` contains identifiers such as the serial number and IMEI. `analyze_firmware.py` only
  reads these six properties:

```
ro.product.model
ro.build.id
ro.build.display.id
ro.build.fingerprint
ro.build.version.sdk
ro.build.version.release
ro.build.version.security_patch
```

Everything else (serial, IMEI, carrier, account-related properties) is dropped and never appears in a
report.

## Caveats

- The analysis is **screening**, not "it will definitely root". The only real test is the device.
- After a firmware upgrade (OTA) you must re-analyse: the build id changes and `DeviceLock` will refuse
  to run, by design.

---

# 把你的固件文件放这里（中文）

```
firmware/
├── boot.img.lz4        # 或未压缩的 boot.img，来自三星固件包 AP_*.tar.md5
├── getprop.txt         # adb shell getprop > firmware/getprop.txt
└── README.md           # 本文件
```

**从哪来**：官方固件（Odin 用的四件套/五件套）里的 `AP_*.tar.md5` → 解开取出 `boot.img.lz4`。
不需要 `BL_*`、`CP_*`、`CSC_*`，分析只用 boot 镜像。

**`analyze_firmware.py` 会做什么**：解 LZ4 frame（纯 Python，无需装工具）→ 打印 boot 载荷与内核的
SHA-256；读内核 banner → 内核版本 + KMI（例如 `android15-6.6`）；判断是否早于 CVE-2026-43284 的修复线
`6.6.138`；从镜像里的字符串指纹判断 SCS / KCFI / DEFEX / RKP-KDP / BTI；产出六个 DeviceLock 常量。

**隐私**：`firmware/` 已被 `.gitignore` 排除，**不会被提交**。`getprop.txt` 里有序列号、IMEI 等标识，
脚本只读取上面列出的 7 个属性，其余一律丢弃，报告里不会出现。

**注意**：分析结果是**筛查**，不是"一定能 root"；唯一真正的测试是设备本身。固件升级（OTA）后要重新
分析：构建号变了，`DeviceLock` 会拒绝运行，这是设计行为。
