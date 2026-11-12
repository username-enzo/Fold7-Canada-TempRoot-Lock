# `analysis/` output directory

> 🌐 **English (this file) · [中文](README.zh-CN.md)**

`python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt` writes
here:

```
analysis/<model>_<build>.md     human-readable screening report
analysis/<model>_<build>.json   the six constants, for tools/apply_lock.py
```

The whole directory is gitignored: the file names carry the model and build, and you may add
device-specific notes. Review and strip identifiers before sharing a report.
