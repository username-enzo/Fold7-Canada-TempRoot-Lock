# `analysis/` output directory

`python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt` writes
here:

```
analysis/<model>_<build>.md     human-readable screening report
analysis/<model>_<build>.json   the six constants, for tools/apply_lock.py
```

The whole directory is gitignored: the file names carry the model and build, and you may add
device-specific notes. Review and strip identifiers before sharing a report.

---

# `analysis/` 输出目录（中文）

`python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt` 把报告写到
这里：`analysis/<model>_<build>.md`（人读的筛查报告）与 `.json`（给 `tools/apply_lock.py` 用的六个
常量）。

整个目录被 `.gitignore` 排除：文件名里带机型与构建号，而且你可能会在自己那份里补充设备信息。
要分享报告请先自行检查并删除标识信息。
