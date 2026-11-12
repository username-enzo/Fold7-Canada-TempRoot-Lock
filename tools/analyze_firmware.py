#!/usr/bin/env python3
"""Screen a firmware image: can this temporary-root route plausibly work here?

    python tools/analyze_firmware.py --boot firmware/boot.img.lz4 --props firmware/getprop.txt

What it does, offline and read-only:

  1. unpacks `boot.img.lz4` (LZ4 frame) or a plain `boot.img` and locates the kernel
  2. reads the `Linux version ...` banner -> exact kernel release and KMI
     (e.g. `6.6.127-android15-8-...-4k` -> KMI `android15-6.6`)
  3. checks the CVE fix line: this route needs a kernel *older* than 6.6.138
  4. fingerprints the hardening this route has historically tripped over
     (SHADOW_CALL_STACK / KCFI / Samsung DEFEX / RKP+KDP / BTI) from strings
     that are present in the image
  5. turns a `getprop` dump into the six DeviceLock constants that `tools/apply_lock.py`
     writes into the app before building

Outputs `analysis/<model>_<build>.md` and `.json`. The JSON is what `apply_lock.py` eats.

IMPORTANT: this is a *screening* tool, not a proof. No offline test can tell you that an
exploit will succeed on a given kernel; the only real test is the device itself, with a
recovery plan. A green report means "worth trying", not "will work".

Privacy: only the whitelisted properties below are ever written into the report. `getprop`
also contains identifiers (serial number, IMEI); those are dropped. Never commit the
`firmware/` directory (it is gitignored).
"""

import argparse
import hashlib
import io
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz4frame import decode_frame  # noqa: E402

LZ4_MAGIC = 0x184D2204
ANDROID_MAGIC = b"ANDROID!"
ARM64_IMAGE_MAGIC = b"ARMd"

# This route (loading a KMI-matched kernel module through CVE-2026-43284 "DirtyFrag")
# is documented as fixed in 6.6.138. Kernels at or above that sublevel are expected
# to reject the primitive, so the whole route stops there.
FIXED_IN = (6, 6, 138)

# Safe, low-noise fingerprints. Each one is a string that only exists in the image
# when the corresponding feature is compiled in. A *negative* result is weak evidence
# (kallsyms names can be token-compressed and therefore unfindable by plain search);
# a *positive* result is strong.
PROBES = [
    ("shadow_call_stack", ["scs_patch_vmlinux", "scs_alloc", "shadow_call_stack"]),
    ("kcfi", ["Oops - CFI", "__cfi_"]),
    ("samsung_defex", ["task_defex_enforce", "task_defex_zero_creds"]),
    ("samsung_rkp_kdp", ["rkp_pgt_bitmap", "rkp_dbl_bitmap"]),
    ("bti", ["system_supports_bti", "ARM64_HAS_BTI"]),
]

# Only these ever leave the machine / land in the report.
PROP_KEYS = [
    "ro.product.model",
    "ro.build.id",
    "ro.build.display.id",
    "ro.build.fingerprint",
    "ro.build.version.sdk",
    "ro.build.version.release",
    "ro.build.version.security_patch",
]

PROPS_HINT = """\
需要一份 getprop 转储 / a getprop dump is required, e.g.

    adb shell getprop > firmware/getprop.txt

只有下面这些键会被读取，其余（序列号、IMEI 等）一律丢弃：
only these keys are read, everything else is dropped:
""" + "\n".join("    " + k for k in PROP_KEYS)


# --------------------------------------------------------------------------- input

def load_boot(path):
    raw = open(path, "rb").read()
    if len(raw) >= 4 and struct.unpack_from("<I", raw, 0)[0] == LZ4_MAGIC:
        return decode_frame(raw), "lz4-frame"
    if raw[:8] == ANDROID_MAGIC:
        return raw, "raw-boot-image"
    raise SystemExit(f"{path}: neither an LZ4 frame nor an Android boot image")


def split_kernel(boot):
    """Return (kernel_bytes, kernel_offset, header_kernel_size)."""
    hdr_size = struct.unpack_from("<I", boot, 8)[0]
    for off in range(0, min(len(boot), 128 * 1024), 4096):
        if boot[off + 0x38:off + 0x3C] == ARM64_IMAGE_MAGIC:
            size = hdr_size if 0 < hdr_size <= len(boot) - off else len(boot) - off
            return boot[off:off + size], off, hdr_size
    raise SystemExit("could not find the arm64 Image magic (ARMd) in the boot image")


def banner_of(kernel):
    i = kernel.find(b"Linux version ")
    if i < 0:
        return ""
    end = kernel.find(b"\x00", i)
    return kernel[i:end].decode("ascii", "replace").strip()


def parse_props(path):
    """Accept `adb shell getprop` output or key=value lines; keep the whitelist only."""
    out = {}
    text = io.open(path, encoding="utf-8", errors="replace").read()
    for line in text.splitlines():
        m = re.match(r"^\[([^\]]+)\]:\s*\[(.*)\]\s*$", line)   # [key]: [value]
        if m:
            k, v = m.group(1), m.group(2)
        else:
            m = re.match(r"^([A-Za-z0-9_.]+)=(.*)$", line)       # key=value
            if not m:
                continue
            k, v = m.group(1), m.group(2).strip()
        if k in PROP_KEYS:
            out[k] = v
    return out


# ------------------------------------------------------------------------ analysis

def kmi_from_banner(banner):
    """Samsung banners look like

        6.6.127-android15-8-p4a765df-abogkiF966USQUDCZJB-4k
        ^^^^^^^ kernel release      ^ android version
                 ^^^^^^ kernel major.minor from the release itself

    so the KMI is `android<AV>-<X.Y>`, NOT something embedded after "android15-".
    (Assuming `android15-8` meant 8.y was a bug in the first version of this tool.)
    """
    rel = sublevel(banner.split()[2] if len(banner.split()) > 2 else "")
    m = re.search(r"-android(\d+)-", banner)
    if m and rel[:2] != (0, 0):
        return f"android{m.group(1)}-{rel[0]}.{rel[1]}"
    return ""


def sublevel(release):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", release)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def fingerprint(kernel):
    found = {}
    for name, needles in PROBES:
        found[name] = any(n.encode() in kernel for n in needles)
    return found


def decide(release, kmi, feats):
    """Return (verdict_code, verdict_cn, verdict_en, reasons[])."""
    reasons = []
    ver = sublevel(release)
    if not kmi:
        return ("unknown", "无法判定 KMI", "cannot determine the KMI", ["no android<N>-<X.Y> in the banner"])
    if kmi != "android15-6.6":
        reasons.append(
            f"KMI 为 {kmi}：本路线验证过的只有 android15-6.6，"
            f"其他 KMI 需要上游提供对应内核模块（ko vermagic 必须匹配）")
        return ("untested", "未验证的 KMI，先确认是否有对应模块",
                "untested KMI - confirm a matching kernel module exists first", reasons)
    if ver >= FIXED_IN:
        reasons.append(f"kernel {'.'.join(map(str, ver))} >= 修复线 {'.'.join(map(str, FIXED_IN))}")
        return ("patched", "大概率已修复，不建议尝试",
                "likely patched - do not attempt", reasons)
    reasons.append(f"kernel {'.'.join(map(str, ver))} < 修复线 {'.'.join(map(str, FIXED_IN))}")
    risk = []
    if feats.get("kcfi"):
        risk.append("KCFI")
    if feats.get("samsung_defex"):
        risk.append("DEFEX")
    if feats.get("samsung_rkp_kdp"):
        risk.append("RKP/KDP")
    if feats.get("shadow_call_stack"):
        risk.append("SCS")
    if risk:
        reasons.append("这些加固在场：" + " / ".join(risk) +
                       "。本项目在同类设备上遇到过内核模块初始化阶段的可复现 panic，"
                       "见 docs/KP_CASE_STUDY.md")
    return ("maybe", "可以尝试（不保证成功）", "worth trying (no guarantee)", reasons)


def constants(props, release, args):
    model = args.model or props.get("ro.product.model", "")
    build = args.build or props.get("ro.build.display.id", "")
    build_short = args.build_short or props.get("ro.build.id", "")
    fingerprint = args.fingerprint or props.get("ro.build.fingerprint", "")
    kernel = args.kernel or release
    sdk = args.sdk or props.get("ro.build.version.sdk", "")
    fp_prefix = ""
    if fingerprint:
        parts = fingerprint.split("/")
        if len(parts) >= 4:
            fp_prefix = "/".join(parts[:4]) + "/"
    return {
        "MODEL": model,
        "BUILD_ID": build,
        "BUILD_ID_SHORT": build_short,
        "KERNEL_PREFIX": kernel,
        "FINGERPRINT_PREFIX": fp_prefix,
        "SDK_INT": int(sdk) if str(sdk).isdigit() else 0,
    }


def render_md(ctx):
    L = []
    A = L.append
    A(f"# Firmware screening report / 固件筛查报告")
    A("")
    A(f"- input: `{ctx['input']}` ({ctx['input_kind']})")
    A(f"- sha256(boot payload): `{ctx['boot_sha256']}`")
    A(f"- kernel: `{ctx['release']}` (sha256 `{ctx['kernel_sha256']}`)")
    A(f"- KMI: `{ctx['kmi'] or 'unknown'}`")
    A(f"- banner: `{ctx['banner'][:180]}`")
    A("")
    A(f"## Verdict / 结论: **{ctx['verdict_cn']}** — {ctx['verdict_en']}")
    A("")
    for r in ctx["reasons"]:
        A(f"- {r}")
    A("")
    A("> 离线分析只能做筛查，不能证明可利用性；唯一真正的测试是设备本身（请先备份并确认能回滚）。")
    A("> Offline screening cannot prove exploitability; the only real test is the device itself.")
    A("")
    A("## Hardening fingerprint / 加固指纹")
    A("")
    A("| feature | found in image |")
    A("|---|---|")
    for k, v in ctx["features"].items():
        A(f"| {k} | {'yes' if v else 'no'} |")
    A("")
    A("> `no` 是弱证据：kallsyms 名字可能被 token 压缩，明文搜不到不等于没编译进去；")
    A("> `yes` 是强证据。 / `no` is weak evidence, `yes` is strong.")
    A("")
    A("## DeviceLock constants / 需要写进 APK 的六个常量")
    A("")
    A("```json")
    A(json.dumps(ctx["constants"], indent=2, ensure_ascii=False))
    A("```")
    A("")
    A("填法 / how to apply:")
    A("")
    A("```bash")
    A("bash setup_toolchain.sh                 # once")
    A(f"python tools/apply_lock.py --report {ctx['json_path']}")
    A("bash build.sh")
    A("```")
    A("")
    A("## Next steps / 下一步")
    A("")
    A("1. 先用**同型号已成功过的固件**跑一遍本工具，确认输出与已知基线一致（校准）。")
    A("   Calibrate first against a firmware where this route is known to work.")
    A("2. 构建前确认装的是**同一 KMI** 的 SU 管理器，并且 DFRoot 的下拉框里能选到它。")
    A("   Confirm the SU manager matches the KMI and appears in the DFRoot dropdown.")
    A("3. 装机后先看 `/dev/dfm6`（成功）还是 `/dev/dfme2`（失败），再看崩溃日志。")
    A("   After running, check `/dev/dfm6` vs `/dev/dfme2` first, then the crash logs.")
    A("")
    return "\n".join(L)


# ---------------------------------------------------------------------------- main

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boot", required=True, help="boot.img or boot.img.lz4")
    ap.add_argument("--props", help="getprop dump (only %s are read)" % ", ".join(PROP_KEYS))
    ap.add_argument("--out", default="analysis", help="output directory (default: analysis/)")
    ap.add_argument("--model")
    ap.add_argument("--build")
    ap.add_argument("--build-short")
    ap.add_argument("--kernel")
    ap.add_argument("--fingerprint")
    ap.add_argument("--sdk")
    args = ap.parse_args(argv[1:])

    if not os.path.isfile(args.boot):
        raise SystemExit(f"missing input: {args.boot}")
    boot, kind = load_boot(args.boot)
    kernel, koff, hdr_size = split_kernel(boot)
    banner = banner_of(kernel)
    release = banner.split()[2] if len(banner.split()) > 2 else ""
    kmi = kmi_from_banner(banner)
    feats = fingerprint(kernel)
    verdict, v_cn, v_en, reasons = decide(release, kmi, feats)

    props = parse_props(args.props) if args.props else {}
    if not args.props:
        print("note: no --props given; the six constants will be incomplete", file=sys.stderr)
    consts = constants(props, release, args)

    base = (consts["MODEL"] or "unknown") + "_" + (consts["BUILD_ID"] or release or "unknown")
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base)
    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, base + ".json")
    md_path = os.path.join(args.out, base + ".md")

    ctx = {
        "input": args.boot,
        "input_kind": kind,
        "boot_sha256": hashlib.sha256(boot).hexdigest(),
        "kernel_offset": koff,
        "kernel_header_size": hdr_size,
        "kernel_size": len(kernel),
        "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
        "banner": banner,
        "release": release,
        "kmi": kmi,
        "features": feats,
        "verdict": verdict,
        "verdict_cn": v_cn,
        "verdict_en": v_en,
        "reasons": reasons,
        "constants": consts,
        "props_used": {k: v for k, v in props.items()},
        "json_path": json_path,
    }
    io.open(json_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps({k: v for k, v in ctx.items() if k != "json_path"},
                   indent=2, ensure_ascii=False) + "\n")
    io.open(md_path, "w", encoding="utf-8", newline="\n").write(render_md(ctx))

    print(f"kernel      : {release}")
    print(f"KMI         : {kmi or 'unknown'}")
    print(f"verdict     : {v_cn} / {v_en}")
    print(f"report      : {md_path}")
    print(f"json        : {json_path}")
    if not all(consts.values()):
        missing = [k for k, v in consts.items() if not v]
        print(f"missing     : {', '.join(missing)}  (pass --props or the matching flags)", file=sys.stderr)
        print(PROPS_HINT, file=sys.stderr)
        return 3
    return 0 if verdict in ("maybe", "untested") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
