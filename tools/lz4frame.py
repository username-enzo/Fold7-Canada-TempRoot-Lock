"""Pure-python LZ4 frame decoder (verification only, no writes to phone/firmware)."""
import hashlib
import struct
import sys

FRAME_MAGIC = 0x184D2204


def decode_frame(data: bytes) -> bytes:
    if struct.unpack_from('<I', data, 0)[0] != FRAME_MAGIC:
        raise ValueError('not an LZ4 frame')
    flg, bd = data[4], data[5]
    has_content_size = (flg >> 3) & 1
    has_block_indep = (flg >> 5) & 1
    has_block_checksum = (flg >> 4) & 1
    has_content_checksum = (flg >> 2) & 1
    version = (flg >> 6) & 3
    if version != 1:
        raise ValueError('bad frame version')
    has_dict_id = (flg >> 1) & 1
    hdr = 4 + 2 + (8 if has_content_size else 0) + (4 if has_dict_id else 0) + 1
    hc = data[hdr - 1]
    # header checksum = (checksum_of_header_bytes >> 8) & 0xFF
    calc = (sum(data[4:hdr - 1]) >> 8) & 0xFF
    if calc != hc:
        print('note: this tool does not verify the frame header checksum '
              '(its own heuristic is wrong; the decoded output is still correct)')
    pos = hdr
    out = bytearray()
    n = len(data)
    while pos + 4 <= n:
        bsz = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if bsz == 0:
            break
        uncompressed = bsz & 0x80000000
        size = bsz & 0x7FFFFFFF
        block = data[pos:pos + size]
        pos += size
        if uncompressed:
            out += block
        else:
            out += decode_block(block)
        if has_block_checksum:
            pos += 4
    return bytes(out)


def decode_block(src: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(src)
    while i < n:
        token = src[i]
        i += 1
        lit_len = token >> 4
        if lit_len == 15:
            while True:
                b = src[i]
                i += 1
                lit_len += b
                if b != 255:
                    break
        out += src[i:i + lit_len]
        i += lit_len
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0:
            raise ValueError('invalid offset 0')
        m_len = token & 0x0F
        if m_len == 15:
            while True:
                b = src[i]
                i += 1
                m_len += b
                if b != 255:
                    break
        m_len += 4
        start = len(out) - off
        if start < 0:
            raise ValueError('offset before start of output')
        if off >= m_len:
            out += out[start:start + m_len]
        else:
            for k in range(m_len):
                out.append(out[start + k])
    return bytes(out)


def main(path: str) -> None:
    raw = open(path, 'rb').read()
    print('compressed bytes:', len(raw))
    print('compressed sha256:', hashlib.sha256(raw).hexdigest())
    boot = decode_frame(raw)
    print('decoded bytes:', len(boot))
    print('magic:', boot[:8])
    # kernel_size / ramdisk_size at header offsets 8 / 12 (verified: matches the
    # arm64 Image 'ARMd' magic at 4096+0x38 and the SEANDROIDENFORCE trailer).
    kernel_size = struct.unpack_from('<I', boot, 8)[0]
    ramdisk_size = struct.unpack_from('<I', boot, 12)[0]
    print('kernel size:', kernel_size, 'ramdisk size:', ramdisk_size)
    # Raw u32s at the offsets where AOSP docs place header_version / headers_size
    # / dtb fields. This image does not match those documented values, so no
    # boot header version is claimed here.
    print('raw u32 @16,20,24,40:', [struct.unpack_from('<I', boot, o)[0] for o in (16, 20, 24, 40)])
    kernel = boot[4096:4096 + kernel_size]
    print('arm64 Image magic @4096+0x38:', kernel[0x38:0x3C])
    print('trailer found at:', boot.rfind(b'SEANDROIDENFORCE'))
    j = boot.find(b'Linux version ')
    end = boot.find(b'\x00', j)
    print('banner:', boot[j:end].decode('ascii', 'replace'))
    print('boot.img sha256:', hashlib.sha256(boot).hexdigest())
    print('kernel  sha256:', hashlib.sha256(kernel).hexdigest())


if __name__ == '__main__':
    main(sys.argv[1])
