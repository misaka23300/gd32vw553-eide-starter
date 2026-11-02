# GD32VW553 EIDE Starter

面向 **立创 GD32VW553-HMQ6**（RISC-V `rv32imafdc`）的开源裸机开发模板：VS Code + Embedded IDE（EIDE）、Make、OpenOCD 烧录、串口控制台，以及一条命令拉取整套工具链。

- **一键下载工具链**：Nuclei RISC-V GCC、OpenOCD、GD32 固件库、Wi-Fi/BLE SDK、官方烧录器
- **EIDE 开箱即用**：构建、烧录、JTAG 接口配置齐全，产物在 `build_eide/Debug/`
- **命令行工具 `gd32`**：创建工程、编译、烧录、串口监视、环境自检
- **已有工程可接入**：`eide.py adopt` 自动生成 EIDE 配置与工作区
- **两个示例**：`hello_led`（最小裸机）、`mos8_wifi`（8 路 MOS + 串口命令行）
- **无硬编码本机路径**；工具链与 SDK 不入库，由脚本从官方源下载

> 本项目是社区模板，非 GigaDevice、Nuclei 或立创官方项目。

---

## 环境要求

| 项目 | 要求 |
| --- | --- |
| 系统 | Windows 10/11 x64（脚本使用 Windows 自带的 bsdtar 解压 7z） |
| Python | 3.8+（仅标准库；串口监视需要 pyserial） |
| 编辑器 | VS Code + [Embedded IDE (`cl.eide`)](https://marketplace.visualstudio.com/items?itemName=cl.eide) |
| 调试器 | CMSIS-DAP / GD-Link / J-Link（JTAG 接线） |
| 磁盘 | 工具链下载约 416 MB，解压后约 1.7 GB |

---

## 快速开始

```bat
git clone https://github.com/misaka23300/gd32vw553-eide-starter
cd gd32vw553-eide-starter

:: 1. 下载并安装工具链（会列出组件和大小，输入 y 确认）
python home\scripts\setup_toolchain.py

:: 2. 新建工程（或直接使用 home\projects\hello_led）
python home\scripts\eide.py new demo

:: 3. 用 VS Code 打开工作区文件（不是“打开文件夹”）
code home\projects\demo\demo.code-workspace
```

在 EIDE 侧栏点 **构建** 即可。烧录前接好探针，点 **烧录**。串口监视：

```bat
python -m pip install -r requirements.txt
gd32 monitor -p COMx
```

Git Bash 中把 `gd32` 换成 `./gd32`。自动化环境可加 `--yes` 跳过下载确认。

---

## 工具链

`home/scripts/setup_toolchain.py` 从官方源安装以下组件（已存在的自动跳过）：

| 组件 | 版本 | 来源 |
| --- | --- | --- |
| `gcc` | Nuclei RISC-V GCC 2022.04（GCC 10.2.0） | download.nucleisys.com |
| `openocd` | Nuclei OpenOCD 2025.10（0.12.0） | download.nucleisys.com |
| `buildtools` | Nuclei win32 build tools 1.2 | download.nucleisys.com |
| `fwlib` | GD32VW55x 固件库 V1.6.0 | gd32mcu.com |
| `msdk` | GD32VW55x Wi-Fi/BLE SDK V1.0.3g | gd32mcu.com |
| `aio` | GD32 All-In-One Programmer V5.4.0（可选 GUI） | gd32mcu.com |

```bat
python home\scripts\setup_toolchain.py --check              :: 只检查
python home\scripts\setup_toolchain.py --only gcc,openocd    :: 只装指定组件
python home\scripts\setup_toolchain.py --no-aio              :: 不装 GUI 烧录器
python home\scripts\setup_toolchain.py --force               :: 重新安装
```

下载缓存在 `home/.tmp/setup/downloads`，支持断点续传；固件库会校验官方 SHA256。

---

## 示例

| 工程 | 说明 |
| --- | --- |
| [`home/projects/hello_led`](home/projects/hello_led) | PC13 每 500 ms 翻转，USART0（PB15/PA8）115200 打印 |
| [`home/projects/mos8_wifi`](home/projects/mos8_wifi) | 8 路低边 MOS 控制、串口命令行、Wi-Fi 后端抽象（见工程内 README） |

命令行构建与烧录：

```bat
gd32 build hello_led
gd32 flash hello_led                  :: 默认 CMSIS-DAP + JTAG
gd32 flash hello_led --interface jlink
gd32 monitor -p COMx
gd32 doctor                           :: 检查工具链、SDK、串口
```

| 命令 | 作用 |
| --- | --- |
| `gd32 new <name>` | 从模板创建工程 |
| `gd32 build [name] [-j N] [--clean]` | 编译出 `.elf/.bin/.hex` |
| `gd32 flash [name]` | OpenOCD 烧录并复位 |
| `gd32 erase [name]` | 整片擦除 |
| `gd32 monitor [-p COMx]` | 串口监视 |
| `gd32 doctor` | 环境自检 |
| `gd32 isp` | 打开官方串口 ISP 工具 |
| `gd32 list` | 列出工程 |

---

## EIDE 使用

详细步骤、字段说明、烧录与排错见 **[docs/EIDE-GD32VW553.md](docs/EIDE-GD32VW553.md)**。要点：

1. 必须打开工程目录下的 `<工程名>.code-workspace`，不能只打开文件夹。
2. 工具链和 OpenOCD 路径写在 `.code-workspace` 的 `settings` 里，不读 `.vscode/settings.json`。
3. 首次打开若提示安装 `riscv-none-embed-gcc` 在线资源包，选“否”。
4. GD32VW55x 目标使用 **JTAG**，`.eide/gd32vw553.cfg` 已完成 `transport select jtag`。

把已有工程接入 EIDE：

```bat
python home\scripts\eide.py adopt home\projects\my_project
```

---

## 目录结构

```
gd32vw553-eide-starter/
├─ gd32 / gd32.cmd              # 命令行入口（bash / cmd）
├─ home/
│  ├─ scripts/                  # gd32.py、eide.py、setup_toolchain.py
│  ├─ templates/baremetal/      # 新工程模板（含 EIDE/VS Code 配置）
│  ├─ projects/hello_led/       # 示例：最小裸机
│  ├─ projects/mos8_wifi/       # 示例：8 路 MOS 控制器
│  ├─ tools/                    # 下载获得，已 gitignore
│  ├─ sdk/                      # 下载获得，已 gitignore
│  └─ .tmp/                     # 构建临时目录，已 gitignore
├─ docs/EIDE-GD32VW553.md       # EIDE 完整指南
├─ requirements.txt
├─ LICENSE
├─ THIRD_PARTY_NOTICES.md
└─ CONTRIBUTING.md
```

编译参数：`-march=rv32imafdc -mabi=ilp32d -mcmodel=medlow -O2 -g -Wall`，
链接脚本 `GD32VW553xM.lds`（4 MB Flash / 288 KB RAM），
烧录地址 `0x08000000`。

---

## 注意事项

- `.eide/env.ini` 把构建临时目录指到工程内的 `../../.tmp`，用于规避火绒/Sangfor 等
  HIPS 对 `riscv-nuclei-elf-gcc.exe` 写系统 `%TEMP%` 的拦截。若你的机器没有此类限制，
  可以删掉该文件中的三行。
- 烧录需要探针并采用 JTAG 接线；仓库未在 CI 中做实机烧录验证。
- `mos8_wifi` 的 Wi-Fi 功能通过弱符号后端抽象，接入真实协议栈见该工程 README。

---

## 许可证

本项目自有代码、脚本和文档采用 [MIT License](LICENSE)。
`gd32vw55x_libopt.h` 等来自 GigaDevice 固件库的文件保留其 BSD-3-Clause 版权声明，
详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

工具链、SDK 和烧录器由各自的官方渠道下载，**不随本仓库分发**。
