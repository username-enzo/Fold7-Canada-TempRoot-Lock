# `analysis/` 输出目录

> 🌐 **[English](README.md) · 中文（本文件）**

`python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt` 把报告写到
这里：

```
analysis/<model>_<build>.md     人读的筛查报告
analysis/<model>_<build>.json   给 tools/apply_lock.py 用的六个常量
```

整个目录被 `.gitignore` 排除：文件名里带机型与构建号，而且你可能会在自己那份里补充设备信息。
要分享报告请先自行检查并删除标识信息。
