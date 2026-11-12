# Third-party components and provenance

> 🌐 **English (this file) · [中文](NOTICE.zh-CN.md)**

This repo ships **method, patches, scripts and documentation**. The components below are maintained by
third parties. They are *not* redistributed here; the build and the analysis only use them, and their
versions/checksums are recorded so you can confirm you fetched the same thing.

---

## 1. DFRoot (the exploit and its bootstrap)

| | |
|---|---|
| source | `https://github.com/diabl0w/DFRoot` |
| licence | **GPL-2.0** (see `LICENSE`, same as this repo) |
| used as | source baseline (`setup_toolchain.sh` clones it and checks out `7a6513a69ce4c1a90b68d857c26347bf166ffe10`), plus `patches/dfroot-f966w.patch` |
| native payloads | extracted by `tools/extract_native_payloads.py` from the **official upstream release** (v4.7); checksums in `docs/BASELINE.md`. **Not recompiled here** |
| attribution | the exploit logic, the bootstrap and `dfroot.ko` are the upstream project's work; this repo only adds a firmware lock and diagnostics around them |

> GPL-2.0 requires derivatives to stay GPL-2.0 — that is this repo's licence.

---

## 2. KernelSU and derivative managers

| | |
|---|---|
| upstream | `https://github.com/tiann/KernelSU` (GPL-2.0 / GPL-3.0 dual-licensed; see the per-repo notes) |
| used as | **installed by you** on the phone; supplies a KMI-matched kernel module and `ksud` |
| redistributed | **no**. There is no manager APK and no `kernelsu.ko` in this repo |
| verified combination | `me.weishu.kernelsu` = `samsung-v2.2` (`ksud samsung-v2.2 (uapi: 5)`). Other versions may work but are unverified here |

Why not redistributed: manager APKs and kernel modules are **signature-paired** (the module pins the
expected APK certificate). Redistributing binaries is both a licensing and a support problem — mixing
mismatched pairs is undiagnosable. Fetch them from upstream releases only.

---

## 3. The Root-My-Galaxy payload list

| | |
|---|---|
| source | `https://github.com/BuSung-dev/Root-My-Galaxy-Payloads` |
| used as | **read-only reference**: `support/targets-v3.json` is what proves the target firmware has **no** ready-made per-build payload (`docs/DECISIONS.md` §C / §J1) |
| redistributed | no, and none of its payloads are used |

---

## 4. The vulnerability itself

| | |
|---|---|
| id | **CVE-2026-43284**, public name "DirtyFrag" |
| kind | page-cache write primitive that loads a **KMI-matched** kernel module; no per-build compilation |
| fix line | kernel `6.6.138` (the criterion `tools/analyze_firmware.py` uses) |
| source | public advisory and public PoC; search the CVE id to verify it yourself. This repo does not copy PoC code, it uses upstream DFRoot's implementation |

---

## 5. Build and analysis toolchain

| component | version | from |
|---|---|---|
| Eclipse Temurin JDK | 21.0.13+9 | `https://api.adoptium.net` |
| Android SDK cmdline-tools | 16111833 | `https://dl.google.com/android/repository/` |
| SDK platform | android-37.0 | `sdkmanager` |
| build-tools | 37.0.0 | `sdkmanager` |
| platform-tools (`adb`) | 37.0.1 | `sdkmanager` |
| Gradle (wrapper) | 9.7.1 | `services.gradle.org` |
| AGP | 9.4.0 | Google Maven |
| Python | 3.9+ (standard library only) | system |

The versions matter: a different JDK/AGP changes the APK bytes. The hashes in
`docs/BUILD_RECORD.md` §7 were produced with exactly these.

---

## 6. Deliberately absent

| item | why |
|---|---|
| Samsung firmware, OTA packages, `AP_*.tar.md5` | copyright and size; get them from official channels |
| prebuilt APK | debug signature + size + not handing someone else a risk-bearing artifact |
| manager APK, `kernelsu.ko` | see §2 |
| device identifiers, raw crash logs, evidence dumps | privacy. The analysis method is in `docs/KP_CASE_STUDY.md`; reproduce it on your own device |
| any personal identity data | this repo deliberately contains no author name, email, or device serial |
