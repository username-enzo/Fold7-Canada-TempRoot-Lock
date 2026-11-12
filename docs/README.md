# 文档索引与"缺失内容"说明 / Docs index and what is intentionally missing

这个目录是原项目工作笔记的公开版本。内容按"换个固件照着做"来组织，不是教程式的科普。

This directory is the public version of the original working notes. It is organised as
"follow these steps for a different firmware", not as a tutorial.

| 文件 / file | 读它的目的 / why read it |
|---|---|
| `BUILD_RECORD.md` | 制造记录：工具链版本、9 个补丁逐个说明、payload 校验、7 项验证命令与期望哈希、换固件要改的常量 |
| `REBOOT_TRIAGE.md` | 分诊：`/dev/df*` 标记含义、怎么取并读三星崩溃归档、判定表 |
| `KP_CASE_STUDY.md` | 一次真实内核 panic 的完整定案过程（中英双语，可当教材） |
| `DECISIONS.md` | 假设与决策日志：每条结论的证据等级、**被推翻的假设**、本机受限项 |
| `BASELINE.md` | 所有输入/输出的 SHA-256 基线，以及纯 Python 的 LZ4 解帧方法 |
| `DELIVERY.md` | 构建产物怎么装、怎么验证、怎么判失败、有哪些已知风险 |

## 文中提到但**不在**本仓库的路径 / paths referenced but not shipped

原工作目录里还有一些东西，出于隐私、体积与许可原因没有发布。对照表：

| 文中路径 / path in docs | 是什么 / what it was | 公开仓库里的替代 / instead, do this |
|---|---|---|
| `firmware/boot.img.lz4`、`firmware/AP_*.jpg` | 自己的固件与其文件清单截图 | 放自己的固件到 `firmware/`（已在 `.gitignore`） |
| `evidence/…` | 真机取证输出（含设备标识与已安装应用列表） | 用 `tools/evidence.sh` / `evidence.bat` 在自己设备上重跑；分析方法见 `KP_CASE_STUDY.md` |
| `deliverables/managers/*.apk`、`*.ko` | 第三方 KernelSU 管理器与其内核模块 | 从上游发布页下载，见 `NOTICE.md` §2 |
| `toolchain/`、`src/` | 本机工具链与上游源码树 | `bash setup_toolchain.sh` 重建 |
| `TODO.md` | 原项目的内部任务清单 | 未发布；待办思路散见各文档的"已知坑"与"受限项" |
| `tmp_bootcheck.py` | 早期会段错误的试验脚本 | 已删除；`tools/lz4frame.py` 提供同样能力 |
| 对话归档 `.md` | 私人对话记录 | 未发布，也不会发布 |

## 一个提醒 / one reminder

`docs/DECISIONS.md` 里保留了几条**后来被推翻的结论**（例如"内核里搜不到某符号就说明没有"）。
它们被故意留下，因为它们记录了"哪种验证方法为什么不可靠"。读到"已撤回 / retracted"时，
请连着后面那条更正一起看。

`docs/DECISIONS.md` deliberately keeps several conclusions that were later disproved. They are kept
because they document *why* a particular verification method is unreliable. When you see
"retracted", read the correction that follows it.
