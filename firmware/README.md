# Put your firmware files here

> 🌐 **English (this file) · [中文](README.zh-CN.md)**

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

## What `tools/analyze_firmware.py` does with it

- unpacks the LZ4 frame (pure Python, no extra tools) and prints the SHA-256 of the boot payload and the
  kernel
- reads the kernel banner → kernel version and KMI (e.g. `android15-6.6`)
- decides whether the kernel is older than the CVE-2026-43284 fix line `6.6.138`
- fingerprints SCS / KCFI / DEFEX / RKP-KDP / BTI from strings present in the image
- emits the six DeviceLock constants

## Privacy

`firmware/` is gitignored and **will never be committed**. `getprop.txt` contains identifiers such as
the serial number and IMEI; the tool only reads these seven properties:

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
