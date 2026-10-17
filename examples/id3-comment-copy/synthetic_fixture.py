"""Create original synthetic ID3 tags and silent MPEG frames for the example."""

from pathlib import Path
from mutagen.id3 import APIC, COMM, ID3, PRIV, TALB, TPE2, TXXX, WXXX


MAIN_COMMENT = "練習用の長い注釈です。元の全文を残します。"
OTHER_COMMENT = "Keep this separate comment."
CONVERTED_TEXT = "作業メモ"
LEGACY_COMMENT = "Short legacy note"
IMPORTED_KEY = "COMM:ID3v1 Comment:eng"
# An original transparent 1x1 RGBA PNG, including valid chunk checksums.
PICTURE_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c6360000200000500017a5eab3f0000000049454e44ae426082")
# MPEG-1 Layer III, 128 kb/s, 44.1 kHz, stereo. Zero-length coded granules
# in zeroed side information give silence; each unpadded frame is 417 bytes.
AUDIO_PAYLOAD = (bytes.fromhex("fffb9000") + bytes(413)) * 12


def make_fixture(path: Path, *, v2=True, v1=True, physical_imported=False):
    """Exclusively create a small original file; never use a downloaded song."""
    with path.open("xb") as output:
        output.write(AUDIO_PAYLOAD)
    if v2:
        tags = ID3()
        tags.add(COMM(encoding=1, lang="jpn", desc="Main", text=[MAIN_COMMENT]))
        tags.add(COMM(encoding=3, lang="fra", desc="Notes", text=[OTHER_COMMENT]))
        if physical_imported:
            tags.add(COMM(encoding=3, lang="eng", desc="ID3v1 Comment",
                          text=[LEGACY_COMMENT]))
        tags.add(TALB(encoding=3, text=["Actual v2 album"]))
        tags.add(TPE2(encoding=3, text=["Album artist"]))
        # Deliberately mislabel Shift-JIS bytes as Latin-1, the input that
        # mid3iconv is designed to repair. The fixture's encoding is known.
        tags.add(TXXX(encoding=0, desc="Work note", text=[
            CONVERTED_TEXT.encode("shift_jis").decode("latin1")]))
        tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Sample",
                      data=PICTURE_BYTES))
        tags.add(PRIV(owner="example.invalid", data=b"private frame\x00\xff"))
        tags.add(WXXX(encoding=3, desc="Reference", url="https://example.com/"))
        tags.save(path, v1=0, v2_version=3)
    if v1:
        def field(value, size):
            return value.encode("latin1").ljust(size, b"\x00")[:size]
        tail = (b"TAG" + field("Legacy title", 30) + field("Legacy artist", 30)
                + field("Legacy album", 30) + b"2026"
                + field(LEGACY_COMMENT, 28) + bytes([0, 7, 17]))
        assert len(tail) == 128
        with path.open("ab") as output:
            output.write(tail)
    return path


def media_payload(path: Path):
    """Independently locate the ID3v2 length and optional fixed v1 tail."""
    data = path.read_bytes()
    start = 0
    if data[:3] == b"ID3":
        size = 0
        for byte in data[6:10]:
            size = (size << 7) | byte
        start = 10 + size
    stop = -128 if len(data) >= 128 and data[-128:-125] == b"TAG" else None
    return data[start:stop]
