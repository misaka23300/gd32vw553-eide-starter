#!/usr/bin/env python3
"""Download and install the GD32VW553 toolchain into the repository.

Usage:
  python home/scripts/setup_toolchain.py                 # install everything
  python home/scripts/setup_toolchain.py --check         # only report status
  python home/scripts/setup_toolchain.py --only gcc,openocd
  python home/scripts/setup_toolchain.py --force         # reinstall existing
  python home/scripts/setup_toolchain.py --no-aio        # skip the GUI programmer
  python home/scripts/setup_toolchain.py --yes           # skip the confirmation prompt

Components (official sources):
  gcc         Nuclei RISC-V GCC 2022.04 (GCC 10.2.0), win32
  openocd     Nuclei OpenOCD 2025.10 (0.12.0), win32
  buildtools  Nuclei win32 build tools 1.2 (bash/make/busybox)
  fwlib       GD32VW55x Firmware Library V1.6.0 (nested 7z, SHA256 checked)
  msdk        GD32VW55x Wi-Fi/BLE SDK V1.0.3g
  aio         GD32 All-In-One Programmer V5.4.0.42035 (optional GUI)

Archives are cached in <home>/.tmp/setup/downloads and support resume.
7z extraction uses Windows' bundled bsdtar (C:\\Windows\\System32\\tar.exe);
zip archives are handled with the Python standard library.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GD32VW553-setup/1.0"
DEFAULT_HOME = Path(__file__).resolve().parents[1]

GCC_URL = ("https://download.nucleisys.com/upload/files/toolchain/gcc/"
           "nuclei_riscv_newlibc_prebuilt_win32_2022.04.zip")
OPENOCD_URL = ("https://download.nucleisys.com/upload/files/toolchain/openocd/"
               "nuclei-openocd-2025.10-win32-x64.zip")
BUILDTOOLS_URL = ("https://download.nucleisys.com/upload/files/toolchain/build-tools/"
                  "win32-buildtools-1.2.zip")
FWLIB_URL = ("https://www.gd32mcu.com/data/documents/toolSoftware/"
             "GD32VW55x_Firmware_Library_V1.6.0.7z")
MSDK_URL = ("https://www.gd32mcu.com/data/documents/toolSoftware/"
            "GD32VW55x_RELEASE_V1.0.3g.zip")
AIO_URL = ("https://www.gd32mcu.com/data/documents/toolSoftware/"
           "GD32AllInOneProgrammer_win_V5.4.0.42035.7z")

COMPONENT_ORDER = ["gcc", "openocd", "buildtools", "fwlib", "msdk", "aio"]


@dataclass
class Component:
    key: str
    title: str
    url: str
    archive: str
    dest: Path
    marker: str
    kind: str = "zip"          # zip | 7z | 7z2 (7z containing a 7z + SHA256.txt)
    subpath: Optional[str] = None  # path inside the archive; None = single top dir
    size: Optional[int] = None     # compressed archive size in bytes


def fail(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


def build_components(home, fwlib_url=None):
    tools = home / "tools"
    sdk = home / "sdk"
    fw_kind, fw_url = "7z2", FWLIB_URL
    fw_archive = "GD32VW55x_Firmware_Library_V1.6.0.7z"
    if fwlib_url:
        fw_url = fwlib_url
        fw_kind = "zip" if fw_url.lower().endswith(".zip") else "7z"
        fw_archive = Path(fw_url.split("?")[0]).name or fw_archive
    return {
        "gcc": Component(
            "gcc", "Nuclei RISC-V GCC 2022.04", GCC_URL,
            "nuclei_riscv_newlibc_prebuilt_win32_2022.04.zip",
            tools / "gcc", "bin/riscv-nuclei-elf-gcc.exe",
            size=290515259),
        "openocd": Component(
            "openocd", "Nuclei OpenOCD 2025.10", OPENOCD_URL,
            "nuclei-openocd-2025.10-win32-x64.zip",
            tools / "Nuclei" / "OpenOCD" / "2025.10", "bin/openocd.exe",
            subpath="Nuclei/OpenOCD/2025.10", size=4105137),
        "buildtools": Component(
            "buildtools", "Nuclei win32 build tools 1.2", BUILDTOOLS_URL,
            "win32-buildtools-1.2.zip",
            tools / "win32-buildtools-1.2", "bin/make.exe",
            subpath="win32-buildtools-1.2", size=3781077),
        "fwlib": Component(
            "fwlib", "GD32VW55x Firmware Library V1.6.0", fw_url,
            fw_archive,
            sdk / "GD32VW55x_Firmware_Library",
            "Firmware/GD32VW55x_standard_peripheral/gd32vw55x.h",
            kind=fw_kind, size=9915145 if fwlib_url is None else None),
        "msdk": Component(
            "msdk", "GD32VW55x Wi-Fi/BLE SDK V1.0.3g", MSDK_URL,
            "GD32VW55x_RELEASE_V1.0.3g.zip",
            sdk / "GD32VW55x_RELEASE_V1.0.3g", "release_notes.txt",
            subpath="GD32VW55x_RELEASE_V1.0.3g", size=112845138),
        "aio": Component(
            "aio", "GD32 All-In-One Programmer V5.4.0", AIO_URL,
            "GD32AllInOneProgrammer_win_V5.4.0.42035.7z",
            tools / "AIO" / "GD32AllInOneProgrammer_win_V5.4.0.42035",
            "GD32 All In One Programmer/GD32AllInOneProgrammer.exe",
            kind="7z", subpath="GD32AllInOneProgrammer_win_V5.4.0.42035",
            size=14877563),
    }


def installed(comp):
    return (comp.dest / comp.marker).is_file()


def find_bsdtar():
    candidates = [
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe",
        Path(shutil.which("bsdtar") or ""),
        Path(shutil.which("tar") or ""),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            out = subprocess.run([str(path), "--version"], capture_output=True,
                                 text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        if "bsdtar" in (out.stdout + out.stderr).lower():
            return path
    return None


def download(comp, cache_dir, redownload=False):
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / comp.archive
    if dest.exists() and dest.stat().st_size > 0 and not redownload:
        print(f"  using cached archive: {dest.name}")
        verify_magic(dest, comp.kind)
        return dest
    if redownload:
        dest.unlink(missing_ok=True)
    part = dest.with_name(dest.name + ".part")
    url = comp.url
    for attempt in range(1, 4):
        resume = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        if resume:
            req.add_header("Range", f"bytes={resume}-")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resume and resp.status != 206:
                    resume = 0
                    part.unlink(missing_ok=True)
                length = resp.headers.get("Content-Length")
                total = (resume + int(length)) if (length and resp.status == 206) else (
                    int(length) if length else None)
                done = resume
                mode = "ab" if resume else "wb"
                last = 0.0
                print(f"  downloading {url}")
                with open(part, mode) as out:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        now = time.monotonic()
                        if now - last >= 0.5 or (total and done >= total):
                            last = now
                            if total:
                                pct = done * 100.0 / total
                                print(f"\r  {pct:5.1f}%  {human(done)} / {human(total)}",
                                      end="", flush=True)
                            else:
                                print(f"\r  {human(done)}", end="", flush=True)
                print()
            if total and part.stat().st_size < total:
                raise OSError("incomplete download")
            os.replace(part, dest)
            verify_magic(dest, comp.kind)
            return dest
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"\n  attempt {attempt}/3 failed: {exc}")
            if attempt == 3:
                fail(f"download failed: {url}")
            time.sleep(2 * attempt)
    return dest


def verify_magic(path, kind):
    with open(path, "rb") as f:
        head = f.read(6)
    ok = head.startswith(b"PK\x03\x04") if kind == "zip" else head.startswith(b"7z\xbc\xaf\x27\x1c")
    if not ok:
        fail(f"downloaded file is not a valid {kind} archive: {path}")


def extract_zip(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            resolved = (target / info.filename).resolve()
            if resolved != root and root not in resolved.parents:
                fail(f"unsafe path in archive: {info.filename}")
        zf.extractall(target)


def extract_7z(archive, target, bsdtar):
    target.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([str(bsdtar), "-xf", str(archive), "-C", str(target)],
                       check=True)
    except subprocess.CalledProcessError as exc:
        fail(f"failed to extract {archive} (exit {exc.returncode})")


def single_dir(path):
    dirs = [p for p in path.iterdir() if p.is_dir() and p.name != "__MACOSX"]
    if len(dirs) != 1:
        names = ", ".join(p.name for p in path.iterdir()) or "(empty)"
        fail(f"unexpected archive layout under {path}: {names}")
    return dirs[0]


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_source(comp, archive, workdir, bsdtar):
    staging = workdir / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    if comp.kind == "zip":
        extract_zip(archive, staging)
        src = staging / comp.subpath if comp.subpath else single_dir(staging)
    elif comp.kind == "7z":
        extract_7z(archive, staging, bsdtar)
        src = staging / comp.subpath if comp.subpath else single_dir(staging)
    else:
        extract_7z(archive, staging, bsdtar)
        outer = single_dir(staging)
        inner_archives = list(outer.glob("*.7z"))
        if len(inner_archives) != 1:
            fail(f"expected one inner .7z in {outer}")
        inner = inner_archives[0]
        sha_file = outer / "SHA256.txt"
        if sha_file.is_file():
            expected = sha_file.read_text(encoding="utf-8").strip().split()[0]
            actual = sha256_of(inner)
            if expected.lower() != actual.lower():
                fail(f"SHA256 mismatch for {inner.name}")
            print("  SHA256 verified")
        inner_staging = workdir / "staging-inner"
        if inner_staging.exists():
            shutil.rmtree(inner_staging)
        extract_7z(inner, inner_staging, bsdtar)
        src = single_dir(inner_staging)
    if not (src / comp.marker).is_file():
        fail(f"unexpected archive layout, missing {comp.marker} in {src}")
    return src


def install(src, dest, force):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if not force:
            return False
        old = dest.with_name(dest.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        dest.rename(old)
        try:
            shutil.move(str(src), str(dest))
        except Exception:
            old.rename(dest)
            raise
        shutil.rmtree(old, ignore_errors=True)
    else:
        shutil.move(str(src), str(dest))
    return True


def show_versions(home):
    checks = [
        ("gcc", home / "tools/gcc/bin/riscv-nuclei-elf-gcc.exe", ["--version"]),
        ("make", home / "tools/win32-buildtools-1.2/bin/make.exe", ["--version"]),
        ("openocd", home / "tools/Nuclei/OpenOCD/2025.10/bin/openocd.exe", ["--version"]),
    ]
    for label, exe, args in checks:
        if not exe.is_file():
            continue
        try:
            out = subprocess.run([str(exe), *args], capture_output=True, text=True,
                                 timeout=15)
            line = (out.stdout or out.stderr).strip().splitlines()[0]
            print(f"  {label:8s}{line}")
        except (OSError, subprocess.SubprocessError, IndexError):
            pass


def main():
    parser = argparse.ArgumentParser(
        prog="setup_toolchain",
        description="Download and install the GD32VW553 toolchain")
    parser.add_argument("--home", default=str(DEFAULT_HOME),
                        help="destination home directory (default: repository home/)")
    parser.add_argument("--only", metavar="LIST",
                        help="comma-separated components: " + ",".join(COMPONENT_ORDER))
    parser.add_argument("--no-aio", action="store_true",
                        help="skip the optional All-In-One Programmer GUI")
    parser.add_argument("--force", action="store_true",
                        help="reinstall components that already exist")
    parser.add_argument("--check", action="store_true",
                        help="only check installed components, download nothing")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="skip the download confirmation prompt")
    parser.add_argument("--redownload", action="store_true",
                        help="discard cached archives and download again")
    parser.add_argument("--keep-archives", action="store_true",
                        help="keep downloaded archives after installation")
    parser.add_argument("--fwlib-url", metavar="URL",
                        help="override firmware library URL (.zip or single-directory .7z)")
    args = parser.parse_args()

    home = Path(args.home).expanduser().resolve()
    components = build_components(home, args.fwlib_url)
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        unknown = [k for k in keys if k not in components]
        if unknown:
            fail("unknown component(s): " + ", ".join(unknown))
        if not keys:
            fail("no components selected")
    else:
        keys = [k for k in COMPONENT_ORDER if not (k == "aio" and args.no_aio)]

    print("GD32VW553 toolchain setup")
    print(f"home: {home}\n")

    if args.check:
        missing = 0
        for key in keys:
            comp = components[key]
            ok = installed(comp)
            missing += 0 if ok else 1
            print(f"[{'OK' if ok else 'MISSING'}] {key:10s} {comp.dest}")
        return 1 if missing else 0

    (home / ".tmp").mkdir(parents=True, exist_ok=True)
    cache = home / ".tmp" / "setup" / "downloads"
    work = home / ".tmp" / "setup" / "work"

    pending, already = [], []
    for key in keys:
        comp = components[key]
        if installed(comp) and not args.force:
            already.append(comp)
            continue
        cached = (cache / comp.archive).is_file() and not args.redownload
        pending.append((comp, cached, comp.size))
    if not pending:
        print("All selected components are already installed:")
        for comp in already:
            print(f"  {comp.key:10s} {comp.dest}")
        return 0

    print("Components to install:")
    total, unknown = 0, False
    for comp, cached, size in pending:
        tag = "reinstall" if installed(comp) else "install"
        if cached:
            size_text = "cached"
        elif size:
            size_text = human(size)
            total += size
        else:
            size_text = "size unknown"
            unknown = True
        print(f"  [{tag:9s}] {comp.key:10s} {comp.title:44s} {size_text}")
    if already:
        print("\nAlready installed (use --force to reinstall):")
        for comp in already:
            print(f"  {comp.key:10s} {comp.dest}")
    print(f"\nTotal download: {'~' if unknown else ''}{human(total)}")
    if not args.yes:
        try:
            answer = input("Proceed with download and installation? [y/N] ")
        except EOFError:
            fail("confirmation required; use --yes for non-interactive runs")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled; nothing was downloaded.")
            return 1
    print()

    bsdtar = None
    needs_7z = any(components[k].kind.startswith("7z")
                   and (args.force or not installed(components[k])) for k in keys)
    if needs_7z:
        bsdtar = find_bsdtar()
        if bsdtar is None:
            fail("bsdtar not found; Windows 10+ provides C:\\Windows\\System32\\tar.exe")

    for key in keys:
        comp = components[key]
        if installed(comp) and not args.force:
            print(f"[{key}] already installed: {comp.dest}")
            continue
        print(f"[{key}] {comp.title}")
        archive = download(comp, cache, redownload=args.redownload)
        workdir = work / key
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        src = prepare_source(comp, archive, workdir, bsdtar)
        try:
            install(src, comp.dest, force=True)
        except OSError as exc:
            fail(f"cannot replace {comp.dest}: {exc} "
                 "(close VS Code/OpenOCD using this toolchain and retry)")
        print(f"  installed: {comp.dest}")
        shutil.rmtree(workdir, ignore_errors=True)
        if not args.keep_archives:
            archive.unlink(missing_ok=True)

    print("\nInstalled toolchain:")
    show_versions(home)
    try:
        import serial  # noqa: F401
    except ImportError:
        print("\nNote: pyserial is not installed; 'gd32 monitor' needs it:")
        print("      python -m pip install pyserial")
    gd32 = home / "scripts" / "gd32.py"
    if gd32.is_file():
        print(f"\nDone. Verify with: python \"{gd32}\" doctor")
    else:
        print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
