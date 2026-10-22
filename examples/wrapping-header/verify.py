"""Generate both headers, then compile and run consumers against Rust."""
from pathlib import Path
import os
import platform
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def run(*args, cwd=ROOT):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def main():
    if platform.system() not in {"Darwin", "Linux"}:
        raise SystemExit("This build example supports macOS/Linux compiler commands.")
    generator = os.environ.get("CBINDGEN", "cbindgen")
    run(generator, "--version")
    run("rustc", "--version")
    run("cargo", "build", "--locked")
    library_dir = ROOT / "target" / "debug"
    with tempfile.TemporaryDirectory(prefix="wrapping header ") as temporary:
        output = Path(temporary)
        for mode, compiler, language, standard in [
            ("c", os.environ.get("CC", "cc"), "c", "c11"),
            ("cpp", os.environ.get("CXX", "c++"), "c++", "c++11"),
        ]:
            directory = output / mode
            directory.mkdir()
            run(generator, "--config", ROOT / f"cbindgen-{mode}.toml",
                "--output", directory / "counter.h")
            # The executable's checks compare the actual returned structure and
            # Rust layout, not just generated text or compiler exit status.
            executable = directory / "client"
            run(compiler, "-x", language, f"-std={standard}", "-Wall", "-Wextra",
                "-Werror", "-I", directory, ROOT / "client.c", "-L", library_dir,
                "-lwrapping_header_example", f"-Wl,-rpath,{library_dir}",
                "-o", executable)
            run(executable)
        print("PASS: C11 and C++11 consumers called the Rust library")


if __name__ == "__main__":
    main()
