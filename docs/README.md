# Docs index, and what is intentionally missing

> English edition (primary). Chinese original: [`README.zh-CN.md`](README.zh-CN.md).

This directory is the public version of the original working notes. It is organised as "follow these
steps for a different firmware", not as a tutorial.

Every long document exists twice: `NAME.md` is the **English** edition, `NAME.zh-CN.md` is the Chinese
record of what was actually measured. Section numbers, hashes, byte counts and commands are identical;
where the two disagree, **the Chinese file wins**.

| file | why read it |
|---|---|
| [`BUILD_RECORD.md`](BUILD_RECORD.md) · [中文](BUILD_RECORD.zh-CN.md) | the manufacturing record: toolchain versions, the nine patch files one by one, payload verification, seven verification commands with expected hashes, the six constants to change on a firmware change |
| [`REBOOT_TRIAGE.md`](REBOOT_TRIAGE.md) · [中文](REBOOT_TRIAGE.zh-CN.md) | triage: what the `/dev/df*` markers mean, how to pull and read Samsung's crash archives, the decision table |
| [`KP_CASE_STUDY.md`](KP_CASE_STUDY.md) · [中文](KP_CASE_STUDY.zh-CN.md) | one real kernel panic taken from symptom to closed diagnosis — the best "do not guess" teaching material here |
| [`DECISIONS.md`](DECISIONS.md) · [中文](DECISIONS.zh-CN.md) | assumption and decision log: the evidence grade of every conclusion, **the hypotheses that were disproved**, the limits of the original environment |
| [`BASELINE.md`](BASELINE.md) · [中文](BASELINE.zh-CN.md) | SHA-256 baselines for every input and output, plus the pure-Python LZ4 frame decoder |
| [`DELIVERY.md`](DELIVERY.md) · [中文](DELIVERY.zh-CN.md) | how to install the built APK, how to verify it, how to read a failure, which risks are known |

## Paths the documents mention but that are **not** in this repo

Some things from the original working directory were not published, for privacy, size or licensing
reasons:

| path in the docs | what it was | do this instead |
|---|---|---|
| `firmware/boot.img.lz4`, `firmware/AP_*.jpg` | the firmware and a screenshot of its file list | put your own firmware in `firmware/` (gitignored) |
| `evidence/…` | on-device evidence dumps (containing device identifiers and the installed-app list) | re-run `tools/evidence.sh` / `evidence.bat` on your own device; the analysis method is in `KP_CASE_STUDY.md` |
| `deliverables/managers/*.apk`, `*.ko` | third-party KernelSU managers and their kernel modules | download from upstream releases, see `NOTICE.md` §2 |
| `toolchain/`, `src/` | the toolchain and the upstream source tree | rebuild with `bash setup_toolchain.sh` |
| `TODO.md` | the original project's internal task list | not published; the open threads live in each document's "known pitfalls" and "limitations" |
| `tmp_bootcheck.py` | an early experiment that segfaults | deleted; `tools/lz4frame.py` does the same job |
| the conversation archive `.md` | a private chat log | not published, and will not be |

## One reminder

`DECISIONS.md` deliberately keeps several conclusions that were **later disproved** (for example "if a
symbol name is not found in the kernel image, the symbol does not exist"). They are kept because they
record *why* a particular verification method is unreliable. When you see "retracted", read the
correction that follows it.
