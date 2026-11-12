# 把你的固件文件放这里 / put your firmware files here

```
firmware/
├── boot.img.lz4        # 或 boot.img（未压缩）。来自三星固件包 AP_*.tar.md5
├── getprop.txt         # adb shell getprop > firmware/getprop.txt
└── README.md           # 本文件
```

## 从哪来 / where to get it

1. 官方固件（如 Odin 用的四件套 / five-file package）里的 `AP_*.tar.md5`。
2. 解开它，取出 `boot.img.lz4`。
3. 不要用 `BL_*`、`CP_*`、`CSC_*` —— 分析只需要 boot 镜像。

`tools/analyze_firmware.py` 会：

- 解 LZ4 frame（纯 Python，无需装工具）→ 打印 boot 载荷与内核的 SHA-256
- 读内核 banner → 内核版本 + KMI（例如 `android15-6.6`）
- 判断是否早于 CVE-2026-43284 的修复线 `6.6.138`
- 从镜像里的字符串指纹判断 SCS / KCFI / DEFEX / RKP-KDP / BTI
- 产出六个 DeviceLock 常量

## 隐私 / privacy

- `firmware/` 已被 `.gitignore` 排除，**不会被提交**。
- `getprop.txt` 里含有序列号、IMEI 等标识；`analyze_firmware.py` 只读取这六个属性：

```
ro.product.model
ro.build.id
ro.build.display.id
ro.build.fingerprint
ro.build.version.sdk
ro.build.version.release
ro.build.version.security_patch
```

其余（序列号、IMEI、运营商、账号相关属性等）一律丢弃，报告里不会出现。

## 注意 / caveats

- 分析结果是**筛查**，不是"一定能 root"。唯一真正的测试是设备本身。
- 固件升级（OTA）后要重新分析：构建号变了，`DeviceLock` 会拒绝运行，这是设计行为。
