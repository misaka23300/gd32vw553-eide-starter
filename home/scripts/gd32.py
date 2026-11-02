#!/usr/bin/env python3
"""GD32VW553 project helper: create, build, flash, monitor, doctor."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
SDK = HOME / "sdk" / "GD32VW55x_Firmware_Library"
TOOLS = HOME / "tools"
GCC_BIN = TOOLS / "gcc" / "bin"
PREFIX = "riscv-nuclei-elf-"
MAKE = GCC_BIN / "make.exe" if os.name == "nt" else GCC_BIN / "make"
OPENOCD = TOOLS / "Nuclei" / "OpenOCD" / "2025.10" / "bin" / "openocd.exe"
OPENOCD_SCRIPTS = TOOLS / "Nuclei" / "OpenOCD" / "2025.10" / "scripts"
AIO = (TOOLS / "AIO" / "GD32AllInOneProgrammer_win_V5.4.0.42035"
       / "GD32 All In One Programmer" / "GD32AllInOneProgrammer.exe")
PROJECTS = HOME / "projects"
TEMPLATES = HOME / "templates"
LDSCRIPT = SDK / "Firmware" / "RISCV" / "env_Eclipse" / "GD32VW553xM.lds"

INTERFACES = {
    "cmsis-dap": "interface/cmsis-dap.cfg",
    "jlink": "interface/jlink.cfg",
    "ft232r": "interface/ft232r.cfg",
}


def fail(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def resolve_project(name=None):
    if name:
        proj = PROJECTS / name
        if not (proj / "Makefile").is_file():
            fail(f"project not found: {proj}")
        return proj
    found = [d for d in PROJECTS.iterdir() if (d / "Makefile").is_file()] \
        if PROJECTS.is_dir() else []
    if len(found) == 1:
        return found[0]
    if not found:
        fail("no project yet, run: gd32 new <name>")
    names = ", ".join(sorted(d.name for d in found))
    fail(f"multiple projects ({names}), specify one: gd32 build <name>")


def run(cmd, cwd=None):
    print("+ " + " ".join(str(c) for c in cmd))
    return subprocess.call([str(c) for c in cmd], cwd=None if cwd is None else str(cwd))


def cmd_new(args):
    name = args.name
    if not name or any(c in name for c in '\\/:*?"<>| '):
        fail("project name must be a simple file name (no spaces or path chars)")
    template = TEMPLATES / args.template
    if not template.is_dir():
        fail(f"template not found: {template}")
    dest = PROJECTS / name
    if dest.exists():
        fail(f"project already exists: {dest}")
    PROJECTS.mkdir(parents=True, exist_ok=True)
    (HOME / ".tmp").mkdir(exist_ok=True)
    shutil.copytree(template, dest,
                    ignore=shutil.ignore_patterns("build", "build_eide", "*.o", "*.d"))
    ws_files = list(dest.glob("*.code-workspace"))
    if ws_files:
        ws_files[0].rename(dest / f"{name}.code-workspace")
    eide_file = dest / ".eide" / "eide.yml"
    if eide_file.is_file():
        text = eide_file.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^name: .*$", f'name: "{name}"', text, count=1)
        text = re.sub(r"(?m)^  uid: .*$", f"  uid: '{uuid.uuid4().hex}'", text, count=1)
        eide_file.write_text(text, encoding="utf-8")
    print(f"Created {dest}")
    print(f"Next: gd32 build {name}")
    return 0


def cmd_build(args):
    proj = resolve_project(args.name)
    for sub in ("build", "build/obj"):
        (proj / sub).mkdir(exist_ok=True)
    if args.clean:
        shutil.rmtree(proj / "build", ignore_errors=True)
        for sub in ("build", "build/obj"):
            (proj / sub).mkdir(exist_ok=True)
    if not MAKE.exists():
        fail(f"make not found: {MAKE}")
    env = os.environ.copy()
    env["PATH"] = str(GCC_BIN) + os.pathsep + env.get("PATH", "")
    tmp = HOME / ".tmp"
    tmp.mkdir(exist_ok=True)
    env["TMP"] = env["TEMP"] = env["TMPDIR"] = str(tmp)
    jobs = [] if args.jobs == 0 else [f"-j{args.jobs}"]
    rc = subprocess.call([str(MAKE)] + jobs, cwd=str(proj), env=env)
    if rc != 0:
        return rc
    elf = proj / "build" / f"{proj.name}.elf"
    print(f"\nArtifacts in {proj / 'build'}")
    print(f"  {elf.name} / {proj.name}.bin / {proj.name}.hex")
    return 0


def cmd_clean(args):
    proj = resolve_project(args.name)
    shutil.rmtree(proj / "build", ignore_errors=True)
    print(f"Cleaned {proj / 'build'}")
    return 0


def _openocd_prefix(args):
    if not OPENOCD.exists():
        fail(f"openocd not found: {OPENOCD}")
    interface = args.interface
    if interface not in INTERFACES:
        fail(f"unknown interface '{interface}', choose from: {', '.join(INTERFACES)}")
    cmd = [OPENOCD, "-s", OPENOCD_SCRIPTS, "-f", INTERFACES[interface],
           "-c", "transport select jtag"]
    if args.speed:
        cmd += ["-c", f"adapter speed {args.speed}"]
    if args.serial:
        cmd += ["-c", f"adapter serial {args.serial}"]
    cmd += ["-f", "target/gd32vw55x.cfg"]
    return cmd


def cmd_flash(args):
    proj = resolve_project(args.name)
    elf = proj / "build" / f"{proj.name}.elf"
    if not elf.is_file():
        fail(f"{elf} not found, run: gd32 build {proj.name}")
    cmd = _openocd_prefix(args)
    action = "program {" + str(elf) + "} " + ("verify " if not args.no_verify else "") + "reset exit"
    cmd += ["-c", action]
    return run(cmd)


def cmd_erase(args):
    cmd = _openocd_prefix(args)
    cmd += ["-c", "flash erase_sector 0 0 last", "-c", "shutdown"]
    return run(cmd)


def _list_ports():
    try:
        from serial.tools import list_ports
    except ImportError:
        fail("pyserial is not installed: python -m pip install pyserial")
    return list(list_ports.comports())


def cmd_ports(args):
    ports = _list_ports()
    if not ports:
        print("No serial port found.")
        return 0
    for p in ports:
        print(f"{p.device:8s} {p.description}")
        if p.hwid:
            print(f"         {p.hwid}")
    return 0


def cmd_monitor(args):
    try:
        import serial
    except ImportError:
        fail("pyserial is not installed: python -m pip install pyserial")
    port = args.port
    if not port:
        ports = _list_ports()
        if len(ports) == 1:
            port = ports[0].device
        elif not ports:
            fail("no serial port found; connect the board or use --port COMx")
        else:
            fail("several serial ports found, use --port: "
                 + ", ".join(p.device for p in ports))
    print(f"Listening on {port} @ {args.baud} 8N1, Ctrl+C to quit")
    try:
        with serial.Serial(port, args.baud, timeout=0.1) as ser:
            while True:
                data = ser.read(256)
                if data:
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
    except KeyboardInterrupt:
        print("\nClosed.")
    except serial.SerialException as exc:
        fail(f"cannot open {port}: {exc}")
    return 0


def _version_line(exe, *extra):
    try:
        out = subprocess.run([str(exe), *extra], capture_output=True, text=True,
                             timeout=10)
        return (out.stdout or out.stderr).splitlines()[0].strip()
    except Exception as exc:  # noqa: BLE001
        return f"failed: {exc}"


def cmd_doctor(args):
    checks = [
        ("RISC-V GCC", GCC_BIN / (PREFIX + "gcc.exe" if os.name == "nt" else PREFIX + "gcc")),
        ("GNU make", MAKE),
        ("OpenOCD", OPENOCD),
        ("OpenOCD target cfg", OPENOCD_SCRIPTS / "target" / "gd32vw55x.cfg"),
        ("SDK", SDK / "Firmware" / "GD32VW55x_standard_peripheral" / "gd32vw55x.h"),
        ("Linker script", LDSCRIPT),
        ("All-In-One Programmer", AIO),
    ]
    ok = True
    for label, path in checks:
        exists = path.exists()
        ok &= exists
        print(f"[{'OK' if exists else 'MISSING'}] {label}: {path}")
    print()
    print("GCC    :", _version_line(GCC_BIN / (PREFIX + "gcc.exe" if os.name == "nt" else PREFIX + "gcc"), "--version"))
    print("make   :", _version_line(MAKE, "--version"))
    print("openocd:", _version_line(OPENOCD, "--version"))
    print("python :", sys.version.split()[0])
    try:
        import serial
        print("pyserial:", serial.__version__)
    except ImportError:
        print("pyserial: not installed (run: python -m pip install pyserial)")
    print()
    print("Serial ports:")
    try:
        ports = _list_ports()
        if not ports:
            print("  (none)")
        for p in ports:
            print(f"  {p.device:8s} {p.description}")
    except SystemExit:
        pass
    return 0 if ok else 1


def cmd_isp(args):
    if not AIO.exists():
        fail(f"GD32 All-In-One Programmer not found: {AIO}")
    print("Launching GD32 All-In-One Programmer (official serial ISP tool).")
    print("Serial ISP: set BOOT0=1, BOOT1=0, press RESET, connect UART (115200 8N1),")
    print("download the .hex/.bin, then set BOOT0=0 and press RESET to run.")
    subprocess.Popen([str(AIO)])
    return 0


def cmd_list(args):
    if not PROJECTS.is_dir() or not any(PROJECTS.iterdir()):
        print("No projects. Create one with: gd32 new hello_led")
        return 0
    for d in sorted(PROJECTS.iterdir()):
        if (d / "Makefile").is_file():
            print(d.name)
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="gd32", description="GD32VW553 (LCKFB-HMQ6) build & flash helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a project from a template")
    p.add_argument("name")
    p.add_argument("--template", default="baremetal")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("build", help="compile a project")
    p.add_argument("name", nargs="?")
    p.add_argument("-j", "--jobs", type=int, default=4, help="parallel jobs, 0 = auto")
    p.add_argument("--clean", action="store_true", help="clean before building")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("clean", help="remove build output")
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_clean)

    for name, func, text in (("flash", cmd_flash, "flash ELF through OpenOCD"),
                             ("erase", cmd_erase, "erase the whole flash")):
        p = sub.add_parser(name, help=text)
        p.add_argument("name", nargs="?")
        p.add_argument("--interface", default="cmsis-dap",
                       choices=sorted(INTERFACES),
                       help="debug probe (GD-Link/DAPLink = cmsis-dap)")
        p.add_argument("--speed", type=int, default=1000, help="adapter speed in kHz")
        p.add_argument("--serial", help="probe serial number when several are attached")
        if name == "flash":
            p.add_argument("--no-verify", action="store_true")
        p.set_defaults(func=func)

    p = sub.add_parser("monitor", help="open a serial console")
    p.add_argument("-p", "--port", help="COM port, auto-detect when only one exists")
    p.add_argument("-b", "--baud", type=int, default=115200)
    p.set_defaults(func=cmd_monitor)

    sub.add_parser("ports", help="list serial ports").set_defaults(func=cmd_ports)
    sub.add_parser("doctor", help="check the toolchain installation").set_defaults(func=cmd_doctor)
    sub.add_parser("isp", help="launch the official serial ISP GUI").set_defaults(func=cmd_isp)
    sub.add_parser("list", help="list projects").set_defaults(func=cmd_list)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
