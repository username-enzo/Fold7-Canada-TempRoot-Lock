# 文档索引，以及刻意缺失的内容

> 🌐 **English edition (primary): [`README.md`](README.md)**
> 本文件是中文版。

这个目录是原项目工作笔记的公开版本。内容按"换个固件照着做"来组织，不是教程式的科普。

每份长文档都有两个版本：`NAME.md` 是**英文版（主）**，`NAME.zh-CN.md` 是中文正本 ——
实测数值、哈希、字节数、命令两边完全一致；若两者冲突，**以中文文件为准**。

| 文件 | 读它的目的 |
|---|---|
| [`BUILD_RECORD.zh-CN.md`](BUILD_RECORD.zh-CN.md) · [English](BUILD_RECORD.md) | 制造记录：工具链版本、9 个补丁逐个说明、payload 校验、7 项验证命令与期望哈希、换固件要改的常量 |
| [`REBOOT_TRIAGE.zh-CN.md`](REBOOT_TRIAGE.zh-CN.md) · [English](REBOOT_TRIAGE.md) | 分诊：`/dev/df*` 标记含义、怎么取并读三星崩溃归档、判定表 |
| [`KP_CASE_STUDY.zh-CN.md`](KP_CASE_STUDY.zh-CN.md) · [English](KP_CASE_STUDY.md) | 一次真实内核 panic 的完整定案过程（含走错的路），可当教材 |
| [`DECISIONS.zh-CN.md`](DECISIONS.zh-CN.md) · [English](DECISIONS.md) | 假设与决策日志：每条结论的证据等级、**被推翻的假设**、原环境受限项 |
| [`BASELINE.zh-CN.md`](BASELINE.zh-CN.md) · [English](BASELINE.md) | 所有输入/输出的 SHA-256 基线，以及纯 Python 的 LZ4 解帧方法 |
| [`DELIVERY.zh-CN.md`](DELIVERY.zh-CN.md) · [English](DELIVERY.md) | 构建产物怎么装、怎么验证、怎么判失败、有哪些已知风险 |

## 文中提到但**不在**本仓库的路径

原工作目录里还有一些东西，出于隐私、体积与许可原因没有发布。对照表：

| 文中路径 | 是什么 | 公开仓库里的替代做法 |
|---|---|---|
| `firmware/boot.img.lz4`、`firmware/AP_*.jpg` | 自己的固件与其文件清单截图 | 把自己的固件放到 `firmware/`（已在 `.gitignore` 里） |
| `evidence/…` | 真机取证输出（含设备标识与已安装应用列表） | 用 `tools/evidence.sh` / `evidence.bat` 在自己设备上重跑；分析方法见 `KP_CASE_STUDY.zh-CN.md` |
| `deliverables/managers/*.apk`、`*.ko` | 第三方 KernelSU 管理器与其内核模块 | 从各自上游发布页下载，见 `NOTICE.md` §2 |
| `toolchain/`、`src/` | 本机工具链与上游源码树 | `bash setup_toolchain.sh` 重建 |
| `TODO.md` | 原项目的内部任务清单 | 未发布；待办思路散见各文档的"已知坑"与"限制" |
| `tmp_bootcheck.py` | 早期会段错误的试验脚本 | 已删除；`tools/lz4frame.py` 提供同样能力 |
| 对话归档 `.md` | 私人对话记录 | 未发布，也不会发布 |

## 一个提醒

`DECISIONS.zh-CN.md` 里保留了几条**后来被推翻的结论**（例如"内核镜像里搜不到某个符号名，就说明
内核没有这个符号"）。它们被故意留下，因为记录了"哪种验证方法为什么不可靠"。
读到"已撤回 / retracted"时，请连着后面那条更正一起看。
