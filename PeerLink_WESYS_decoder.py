#!/usr/bin/env python3
"""
PeerLink / eFootball WESYS decoder for current PESDB containers.

Target verified format:
    FF 22 83 WESYS
    16-byte header
    uint32_le compressed_size @ +0x08
    uint32_le original_size   @ +0x0C
    encrypted zlib payload    @ +0x10

Current 0x22 keystream constants:
    x = 0xED5B2960
    y = 0x4A523B4E
    z = 0xF3A31BAD
    w = ((original_size << 16) | compressed_size) & 0xFFFFFFFF

The payload is XORed in complete little-endian uint32 words.
Any trailing 1-3 bytes are left unchanged.
After decryption, zlib-decompress the payload.

This is distinct from the older/simple QWESYS container used by
constant_*.bin files.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

MAGIC = b"\xFF\x22\x83WESYS"
HEADER_SIZE = 16

X0 = 0xED5B2960
Y0 = 0x4A523B4E
Z0 = 0xF3A31BAD


class WesysError(RuntimeError):
    pass


def _u32(v: int) -> int:
    return v & 0xFFFFFFFF


def decrypt_payload(payload: bytes, original_size: int, compressed_size: int) -> bytes:
    """
    Decrypt the WESYS 0x22 payload exactly as used by the current PESDB format.
    """
    if compressed_size != len(payload):
        raise WesysError(
            f"compressed-size mismatch: header={compressed_size}, actual={len(payload)}"
        )

    x = X0
    y = Y0
    z = Z0
    w = _u32((original_size << 16) | compressed_size)

    out = bytearray(payload)
    full_words = len(out) // 4

    for i in range(full_words):
        t = _u32(x ^ _u32(x << 11))

        x, y, z, prev = y, z, w, w
        w = _u32(
            prev
            ^ _u32((((prev >> 11) ^ t) >> 8))
            ^ t
        )

        off = i * 4
        word = struct.unpack_from("<I", out, off)[0]
        struct.pack_into("<I", out, off, _u32(word ^ w))

    # Intentionally leave the final 1-3 bytes untouched.
    return bytes(out)


def decode_bytes(data: bytes) -> bytes:
    if len(data) < HEADER_SIZE:
        raise WesysError("file is shorter than the 16-byte WESYS header")

    if data[:8] != MAGIC:
        got = data[:8]
        raise WesysError(
            f"unsupported/invalid magic: {got!r}; expected {MAGIC!r}"
        )

    compressed_size, original_size = struct.unpack_from("<II", data, 8)

    payload = data[HEADER_SIZE:]
    if len(payload) != compressed_size:
        raise WesysError(
            f"payload length mismatch: header={compressed_size}, actual={len(payload)}"
        )

    decrypted = decrypt_payload(
        payload,
        original_size=original_size,
        compressed_size=compressed_size,
    )

    # A correctly decrypted current PESDB payload should expose a zlib stream.
    if len(decrypted) < 2 or decrypted[0] != 0x78:
        raise WesysError(
            "decryption did not produce a zlib-looking payload; "
            f"first bytes={decrypted[:8].hex(' ')}"
        )

    try:
        raw = zlib.decompress(decrypted)
    except zlib.error as exc:
        raise WesysError(f"zlib decompression failed: {exc}") from exc

    if len(raw) != original_size:
        raise WesysError(
            f"decoded-size mismatch: header={original_size}, actual={len(raw)}"
        )

    return raw


def decode_file(src: str | Path, dst: str | Path) -> Path:
    src = Path(src)
    dst = Path(dst)

    raw = decode_bytes(src.read_bytes())
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(raw)
    return dst


def inspect_file(src: str | Path) -> dict:
    src = Path(src)
    data = src.read_bytes()

    if len(data) < HEADER_SIZE:
        raise WesysError("file too short")
    if data[:8] != MAGIC:
        raise WesysError(f"not current 0x22 WESYS: {data[:8]!r}")

    compressed_size, original_size = struct.unpack_from("<II", data, 8)
    payload = data[HEADER_SIZE:]

    decrypted_prefix = decrypt_payload(
        payload,
        original_size=original_size,
        compressed_size=compressed_size,
    )[:16]

    return {
        "file": str(src),
        "compressed_size": compressed_size,
        "original_size": original_size,
        "payload_size": len(payload),
        "decrypted_prefix_hex": decrypted_prefix.hex(" "),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Decode current eFootball FF 22 83 WESYS PESDB files."
    )
    p.add_argument("input", help="input WESYS file, e.g. Player.bin")
    p.add_argument(
        "output",
        nargs="?",
        help="decoded raw output; defaults to <input>.decoded",
    )
    p.add_argument(
        "--inspect",
        action="store_true",
        help="print header/decrypted-prefix information without writing output",
    )
    args = p.parse_args(argv)

    src = Path(args.input)

    if args.inspect:
        info = inspect_file(src)
        for k, v in info.items():
            print(f"{k}: {v}")
        return 0

    dst = Path(args.output) if args.output else src.with_name(src.name + ".decoded")
    decode_file(src, dst)
    print(dst)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WesysError as exc:
        print(f"WESYS error: {exc}", file=sys.stderr)
        raise SystemExit(2)
