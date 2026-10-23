"""Independent native ExifTool and Pillow checks; never trust browser status."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
from PIL import Image

TRAILER = b"Owned example trailer: removable payload 2026\n" * 7
TOOL = os.environ.get("EXIFTOOL", "exiftool")
def exif(path, *args):
    cmd = (["perl", TOOL] if TOOL.endswith("/exiftool") else [TOOL]) + list(args) + [str(path)]
    result = subprocess.run(cmd, capture_output=True, env={**os.environ, "LC_ALL": "C"})
    if result.returncode: raise RuntimeError(result.stderr.decode())
    return result.stdout

def fingerprint(path):
    with Image.open(path) as image:
        image.load()
        pixels = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
        dimensions = image.size
    tags = json.loads(exif(path, "-j", "-Artist", "-ImageDescription"))[0]
    return {"dimensions": dimensions, "pixels": pixels,
            "Artist": tags.get("Artist"), "ImageDescription": tags.get("ImageDescription")}

def generate(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for number in [1, 2]:
        image = Image.new("RGB", (73 + number, 49 + number))
        image.putdata([((x*17 + y*3 + number)%256, (x*5 + y*19)%256, (x*x+y*13)%256)
                       for y in range(image.height) for x in range(image.width)])
        metadata = Image.Exif(); metadata[315] = f"Fixture artist {number}"
        metadata[270] = f"Owned JPEG description {number}"
        plain = folder / f"plain{number}.jpg"
        image.save(plain, quality=91, exif=metadata)
        assert plain.read_bytes().endswith(b"\xff\xd9")
        trailer = folder / f"trailer{number}.jpg"
        trailer.write_bytes(plain.read_bytes() + TRAILER)
        assert exif(trailer, "-b", "-Trailer") == TRAILER
        assert not exif(plain, "-b", "-Trailer")
        assert fingerprint(plain) == fingerprint(trailer)
    image.save(folder / "valid.png", format="PNG")
    assert json.loads(exif(folder / "valid.png", "-j", "-FileType"))[0]["FileType"] == "PNG"
    (folder / "invalid.jpg").write_bytes(b"\xff\xd8\xffOwned corrupt JPEG fixture\n")
    print(json.dumps({"native_version": subprocess.check_output((["perl", TOOL] if TOOL.endswith("/exiftool") else [TOOL]) + ["-ver"], env={**os.environ, "LC_ALL": "C"}).decode().strip(),
                      "fixture": fingerprint(folder / "trailer1.jpg"), "trailer_bytes": len(TRAILER)}))

def verify(source, output):
    trailer = exif(output, "-b", "-Trailer")
    assert not trailer, f"Saved output still contains {len(trailer)} trailer bytes"
    assert fingerprint(source) == fingerprint(output), "Pixels, dimensions or retained metadata changed"
    assert Path(output).read_bytes().endswith(b"\xff\xd9"), "Unexpected bytes after JPEG EOI"
    print(json.dumps({"output": str(output), "trailer_bytes": len(trailer), **fingerprint(output)}))

if __name__ == "__main__":
    if sys.argv[1] == "generate": generate(Path(sys.argv[2]))
    else: verify(Path(sys.argv[2]), Path(sys.argv[3]))
