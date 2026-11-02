#!/usr/bin/env python3
"""Create a project or wire an existing project into the EIDE workspace.

Usage:
  python home/scripts/eide.py new <name>
  python home/scripts/eide.py adopt <path> [options]

adopt options:
  --name NAME        project name shown in EIDE (default: directory name)
  --ld FILE          linker script, relative to the project or absolute
  --repo-sdk         force adding the SDK from this repo
  --no-sdk           never add the repo SDK (project bundles its own)
  --workspace FILE   add the folder to an existing multi-root .code-workspace
  --force            overwrite an existing .eide/eide.yml (backed up as .bak)

Generated for an adopted project:
  .eide/eide.yml, .eide/env.ini, .eide/gd32vw553.cfg, .eide/files.options.yml
  <name>.code-workspace (or an entry in --workspace)

The script is stdlib-only and expects the default repository layout:
home/sdk, home/tools, home/templates/baremetal.
"""

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
SDK = HOME / "sdk" / "GD32VW55x_Firmware_Library"
GCC_DIR = HOME / "tools" / "gcc"
OPENOCD_EXE = (HOME / "tools" / "Nuclei" / "OpenOCD" / "2025.10"
               / "bin" / "openocd.exe")
LDSCRIPT = SDK / "Firmware" / "RISCV" / "env_Eclipse" / "GD32VW553xM.lds"
TEMPLATE = HOME / "templates" / "baremetal"
PROJECTS = HOME / "projects"
TMP_DIR = HOME / ".tmp"

SDK_SRC_DIRS = [
    SDK / "Firmware" / "RISCV" / "env_Eclipse",
    SDK / "Firmware" / "RISCV" / "stubs",
    SDK / "Firmware" / "GD32VW55x_standard_peripheral",
]
SDK_INC_DIRS = [
    SDK / "Firmware" / "GD32VW55x_standard_peripheral",
    SDK / "Firmware" / "GD32VW55x_standard_peripheral" / "Include",
    SDK / "Firmware" / "RISCV" / "drivers",
    SDK / "Firmware" / "RISCV" / "stubs",
]

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".s"}
HEADER_SUFFIXES = {".h", ".hh", ".hpp"}
IGNORE_DIRS = {
    ".git", ".svn", ".hg", ".eide", ".vscode", ".idea", ".tmp",
    "build", "build_eide", "out", "obj", "bin", "docs",
    "node_modules", "__pycache__",
}

ENV_TEMPLATE = """###########################################################
#              Project Environment Variables
###########################################################

## Global Variables

# append command prefix for toolchain
#COMPILER_CMD_PREFIX=

# mcu ram size (used to print memory usage)
#MCU_RAM_SIZE=0x00

# mcu rom size (used to print memory usage)
#MCU_ROM_SIZE=0x00

[debug]
# 火绒/Sangfor HIPS 会拦截 RISC-V GCC 写系统 %TEMP%，这里改用项目内临时目录。
TMP={tmp}
TEMP={tmp}
TMPDIR={tmp}
"""

OPENOCD_CFG = """# GD32VW55x requires JTAG; OpenOCD defaults to SWD.
# EIDE loads this file before target/gd32vw55x.cfg.
# J-Link: change the "adapter driver" line to "adapter driver jlink".
adapter driver cmsis-dap
transport select jtag
adapter speed 1000
"""

FILES_OPTIONS = """##########################################################################################
#                        Append Compiler Options For Source Files
##########################################################################################

# syntax:
#   <your pattern>: <compiler options>
# For get pattern syntax, please refer to: https://www.npmjs.com/package/micromatch
#
# examples:
#   'main.cpp':           --cpp11 -Og ...
#   'src/*.c':            -gnu -O2 ...
#   'src/lib/**/*.cpp':   --cpp11 -Os ...
#   '!Application/*.c':   -O0
#   '**/*.c':             -O2 -gnu ...

version: "2.1"
options:
    Debug:
        files: {}
        virtualPathFiles: {}
"""


def fail(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def posix(path):
    return str(path).replace("\\", "/")


def rel_or_abs(target, start):
    try:
        rel = os.path.relpath(str(target), str(start))
    except ValueError:
        return posix(Path(target).resolve())
    return posix(Path(rel))


def env_temp_path(start):
    try:
        rel = os.path.relpath(str(TMP_DIR.resolve()), str(start))
    except ValueError:
        rel = str(TMP_DIR.resolve())
    if os.name == "nt":
        return rel.replace("/", "\\")
    return rel.replace("\\", "/")


def ws_setting_path(target, workspace_dir):
    try:
        rel = os.path.relpath(str(target), str(workspace_dir))
    except ValueError:
        return posix(Path(target).resolve())
    if os.path.isabs(rel):
        return posix(Path(rel))
    return "${workspaceFolder}/" + posix(Path(rel))


def yq(value):
    return "'" + str(value).replace("'", "''") + "'"


def backup(path):
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))


def write_text(path, text, force=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not force:
            return False
        backup(path)
    path.write_text(text, encoding="utf-8")
    return True


def iter_files(root):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d.lower() not in IGNORE_DIRS
            and not d.lower().startswith("cmake-build")
        )
        for name in filenames:
            yield Path(dirpath) / name


def scan_project(root):
    src_dirs, header_dirs, root_files, sources, ld_files = [], [], [], [], []
    bundled_sdk = False
    root = Path(root)
    for path in iter_files(root):
        suffix = path.suffix.lower()
        rel = path.relative_to(root)
        if path.name in ("system_gd32vw55x.c", "gd32vw55x.h"):
            bundled_sdk = True
        if suffix in (".lds", ".ld"):
            ld_files.append(path)
        if suffix in SOURCE_SUFFIXES:
            sources.append(path)
            if rel.parent == Path("."):
                root_files.append(path.name)
            elif rel.parent not in src_dirs:
                src_dirs.append(rel.parent)
        elif suffix in HEADER_SUFFIXES:
            if rel.parent == Path("."):
                root_files.append(path.name)
            elif rel.parent not in header_dirs:
                header_dirs.append(rel.parent)
    return {
        "src_dirs": sorted(src_dirs),
        "header_dirs": sorted(header_dirs),
        "root_files": sorted(set(root_files)),
        "sources": sources,
        "ld_files": ld_files,
        "bundled_sdk": bundled_sdk,
    }


def defines_symbol(sources, symbol):
    pattern = re.compile(
        r"(?m)^[ \t]*(?:__attribute__\s*\(\([^)]*\)\)\s*)?"
        r"(?:[A-Za-z_][\w\t *]*[\t ])?"
        + re.escape(symbol) + r"[\t ]*\([^;{}]*\)[\t \r\n]*\{"
    )
    for path in sources:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if pattern.search(text):
            return True
    return False


def pick_linker_script(root, args, repo_sdk, ld_files):
    if args.ld:
        path = Path(args.ld)
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if not path.is_file():
            fail(f"linker script not found: {path}")
        return path
    if repo_sdk:
        return LDSCRIPT
    if len(ld_files) == 1:
        return ld_files[0].resolve()
    if not ld_files:
        fail("project has no .lds/.ld linker script; pass --ld FILE")
    names = ", ".join(posix(p.relative_to(root)) for p in ld_files)
    fail(f"multiple linker scripts found ({names}); pass --ld FILE")


def build_eide_yml(name, src_dirs, root_files, inc_dirs, excludes, ld_path):
    lines = [
        'version: "4.1"',
        f"name: {yq(name)}",
        "type: RISC-V",
        "deviceName: null",
        "packDir: null",
    ]
    if src_dirs:
        lines.append("srcDirs:")
        lines += [f"  - {yq(d)}" for d in src_dirs]
    else:
        lines.append("srcDirs: []")
    lines += ["virtualFolder:", "  name: <virtual_root>"]
    if root_files:
        lines += ["  files:"]
        lines += [f"  - path: {yq(f)}" for f in root_files]
    else:
        lines += ["  files: []"]
    lines += [
        "  folders: []",
        "dependenceList: []",
        "outDir: build_eide",
        "miscInfo:",
        f"  uid: {yq(uuid.uuid4().hex)}",
        "targets:",
        "  Debug:",
        "    cppPreprocessAttrs:",
        "      defineList:",
        "        - USE_STDPERIPH_DRIVER",
        "      incList:",
    ]
    lines += [f"        - {yq(d)}" for d in inc_dirs]
    lines += ["      libList: []"]
    if excludes:
        lines += ["    excludeList:"]
        lines += [f"      - {yq(e)}" for e in excludes]
    else:
        lines += ["    excludeList: []"]
    lines += [
        "    settings: {}",
        "    toolchain: RISCV_GCC",
        "    toolchainConfigMap:",
        "      RISCV_GCC:",
        f"        linkerScriptPath: {yq(ld_path)}",
        "        options:",
        "          version: 2",
        "          afterBuildTasks: []",
        "          asm-compiler:",
        '            ASM_FLAGS: ""',
        "          beforeBuildTasks: []",
        "          c/cpp-compiler:",
        '            C_FLAGS: ""',
        "            language-c: gnu11",
        "            language-cpp: gnu++17",
        "            one-elf-section-per-data: true",
        "            one-elf-section-per-function: true",
        "            optimization: level-2",
        "            warnings: all-warnings",
        "          global:",
        "            abi: ilp32d",
        "            arch: rv32imafdc",
        "            code-model: medlow",
        '            misc-control: ""',
        "            output-debug-info: enable",
        "          linker:",
        "            $toolName: auto",
        "            LD_FLAGS: -nostartfiles",
        "            LIB_FLAGS: -lm -lc -lgcc",
        "            output-format: elf",
        "            remove-unused-input-sections: true",
        "    uploadConfigMap:",
        "      OpenOCD:",
        '        baseAddr: "0x08000000"',
        '        bin: ""',
        "        interface: '${workspaceFolder}/.eide/gd32vw553'",
        "        target: gd32vw55x",
        "    uploader: OpenOCD",
    ]
    return "\n".join(lines) + "\n"


def load_workspace(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        fail(f"cannot parse {path} ({exc}); remove comments/trailing commas and retry")
    if not isinstance(data, dict):
        fail(f"invalid workspace file (expected a JSON object): {path}")
    return data


def ensure_project_workspace(root, name):
    target = root / f"{name}.code-workspace"
    candidates = sorted(root.glob("*.code-workspace"))
    if not target.exists() and len(candidates) == 1:
        target = candidates[0]
    if target.exists():
        data = load_workspace(target)
        backup(target)
    else:
        data = {"folders": [{"path": "."}], "settings": {}}
    folders = data.setdefault("folders", [])
    if not any(isinstance(f, dict) and f.get("path") == "." for f in folders):
        folders.insert(0, {"path": "."})
    settings = data.setdefault("settings", {})
    settings["EIDE.RISCV.InstallDirectory"] = ws_setting_path(GCC_DIR, root)
    settings["EIDE.RISCV.ToolPrefix"] = "riscv-nuclei-elf-"
    settings["EIDE.OpenOCD.ExePath"] = ws_setting_path(OPENOCD_EXE, root)
    target.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    return target


def add_to_workspace(ws_file, root):
    ws_file = Path(ws_file).expanduser().resolve()
    if not ws_file.is_file():
        fail(f"workspace not found: {ws_file}")
    data = load_workspace(ws_file)
    backup(ws_file)
    rel = rel_or_abs(root, ws_file.parent)
    folders = data.setdefault("folders", [])
    known = {
        (ws_file.parent / f["path"]).resolve() for f in folders
        if isinstance(f, dict) and isinstance(f.get("path"), str)
    }
    if root.resolve() not in known:
        folders.append({"path": rel})
    # Absolute paths avoid ${workspaceFolder} ambiguity in a multi-root workspace.
    settings = data.setdefault("settings", {})
    settings["EIDE.RISCV.InstallDirectory"] = posix(GCC_DIR.resolve())
    settings["EIDE.RISCV.ToolPrefix"] = "riscv-nuclei-elf-"
    settings["EIDE.OpenOCD.ExePath"] = posix(OPENOCD_EXE.resolve())
    ws_file.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    return ws_file


def cmd_new(args):
    name = args.name
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", name):
        fail("project name must contain only letters, digits, '_', '.', '-'")
    dest = PROJECTS / name
    if dest.exists():
        fail(f"project already exists: {dest}")
    if not TEMPLATE.is_dir():
        fail(f"template not found: {TEMPLATE}")
    PROJECTS.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)
    shutil.copytree(TEMPLATE, dest,
                    ignore=shutil.ignore_patterns("build", "build_eide", "*.o", "*.d"))
    workspaces = list(dest.glob("*.code-workspace"))
    if workspaces:
        workspaces[0].rename(dest / f"{name}.code-workspace")
    eide_file = dest / ".eide" / "eide.yml"
    if eide_file.is_file():
        text = eide_file.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^name: .*$", f'name: "{name}"', text, count=1)
        text = re.sub(r"(?m)^  uid: .*$", f"  uid: '{uuid.uuid4().hex}'", text, count=1)
        eide_file.write_text(text, encoding="utf-8")
    print(f"Created {dest}")
    print(f"Open in VS Code: {dest / (name + '.code-workspace')}")
    return 0


def cmd_adopt(args):
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        fail(f"project directory not found: {root}")
    name = args.name or root.name
    if any(c in name for c in '\\/:*?"<>|'):
        fail('project name must not contain path characters: \\ / : * ? " < > |')
    if not (GCC_DIR / "bin").is_dir():
        fail(f"toolchain not found: {GCC_DIR}")
    info = scan_project(root)
    if not info["sources"]:
        fail(f"no C/asm sources found under {root}")
    if args.repo_sdk:
        repo_sdk, sdk_label = True, "repo"
    elif args.no_sdk:
        repo_sdk, sdk_label = False, "none"
    else:
        repo_sdk = not info["bundled_sdk"]
        sdk_label = "project-bundled" if info["bundled_sdk"] else "repo"
    for d in SDK_SRC_DIRS + SDK_INC_DIRS:
        if repo_sdk and not d.is_dir():
            fail(f"SDK directory not found: {d}")
    if repo_sdk and not LDSCRIPT.is_file():
        fail(f"linker script not found: {LDSCRIPT}")
    ld_path = pick_linker_script(root, args, repo_sdk, info["ld_files"])
    excludes = []
    if repo_sdk:
        if defines_symbol(info["sources"], "_write"):
            excludes.append(rel_or_abs(SDK / "Firmware/RISCV/stubs/write.c", root))
        if defines_symbol(info["sources"], "_sbrk"):
            excludes.append(rel_or_abs(SDK / "Firmware/RISCV/stubs/sbrk.c", root))
    src_dirs = [posix(d) for d in info["src_dirs"]]
    header_only = [d for d in info["header_dirs"] if d not in info["src_dirs"]]
    src_dirs += [posix(d) for d in header_only]
    if repo_sdk:
        src_dirs += [rel_or_abs(d, root) for d in SDK_SRC_DIRS]
    inc_dirs = ["."]
    inc_dirs += [posix(d) for d in info["header_dirs"]]
    if repo_sdk:
        inc_dirs += [rel_or_abs(d, root) for d in SDK_INC_DIRS]
    inc_dirs = list(dict.fromkeys(inc_dirs))
    eide_text = build_eide_yml(
        name, src_dirs, info["root_files"], inc_dirs, excludes,
        rel_or_abs(ld_path, root),
    )
    TMP_DIR.mkdir(exist_ok=True)
    eide_dir = root / ".eide"
    eide_yml = eide_dir / "eide.yml"
    if eide_yml.exists() and not args.force:
        fail(f"{eide_yml} already exists; pass --force to regenerate (backup: .bak)")
    created, kept = [], []
    if write_text(eide_yml, eide_text, force=args.force):
        created.append(eide_yml)
    for path, text in (
        (eide_dir / "env.ini", ENV_TEMPLATE.format(tmp=env_temp_path(root))),
        (eide_dir / "gd32vw553.cfg", OPENOCD_CFG),
        (eide_dir / "files.options.yml", FILES_OPTIONS),
    ):
        if write_text(path, text, force=args.force):
            created.append(path)
        elif path.exists():
            kept.append(path)
    if args.workspace:
        ws = add_to_workspace(args.workspace, root)
    else:
        ws = ensure_project_workspace(root, name)

    print(f"Adopted {root}")
    print(f"  name        : {name}")
    print(f"  srcDirs     : {', '.join(src_dirs) or '(none)'}")
    print(f"  root files  : {', '.join(info['root_files']) or '(none)'}")
    print(f"  include dirs: {', '.join(inc_dirs)}")
    print(f"  linker      : {rel_or_abs(ld_path, root)}")
    print(f"  SDK         : {sdk_label}")
    if excludes:
        print(f"  excluded    : {', '.join(excludes)}")
    print(f"  workspace   : {ws}")
    print(f"  generated   : {', '.join(str(p.relative_to(root)) for p in created)}")
    if kept:
        print(f"  kept        : {', '.join(str(p.relative_to(root)) for p in kept)}")
    if not OPENOCD_EXE.is_file():
        print(f"WARNING: OpenOCD not found, burning will fail: {OPENOCD_EXE}")
    print("Next: open the .code-workspace in VS Code and click Build in EIDE.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="eide",
        description="Create a GD32VW553 project or add an existing project to EIDE")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a project from the baremetal template")
    p.add_argument("name")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("adopt", help="generate EIDE files for an existing project")
    p.add_argument("path")
    p.add_argument("--name")
    p.add_argument("--ld", metavar="FILE")
    p.add_argument("--workspace", metavar="FILE",
                   help="add the project to an existing multi-root .code-workspace")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing EIDE files (backup as .bak)")
    sdk = p.add_mutually_exclusive_group()
    sdk.add_argument("--repo-sdk", action="store_true",
                     help="always add the SDK from this repository")
    sdk.add_argument("--no-sdk", action="store_true",
                     help="never add the repo SDK (project bundles its own)")
    p.set_defaults(func=cmd_adopt)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
