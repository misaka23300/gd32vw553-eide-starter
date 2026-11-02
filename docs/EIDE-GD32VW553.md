# Embedded IDE (EIDE) 使用指南 · GD32VW553

本文说明如何用 VS Code 的 **Embedded IDE（`cl.eide`）** 打开、编译、烧录本仓库的 GD32VW553 工程。
以 `home/projects/mos8_wifi` 为例，`hello_led` 和 `gd32 new` 新建的工程步骤完全相同。

适用环境（运行 `home/scripts/setup_toolchain.py` 安装，之后可离线使用）：

| 组件 | 版本 | 位置 |
| --- | --- | --- |
| VS Code 扩展 | Embedded IDE `cl.eide` 3.27.2 | VS Code 扩展目录 |
| 交叉编译器 | Nuclei RISC-V GCC 2022.04（GCC 10.2.0） | `home/tools/gcc`，前缀 `riscv-nuclei-elf-` |
| 烧录/调试服务 | Nuclei OpenOCD 0.12.0（2025.10） | `home/tools/Nuclei/OpenOCD/2025.10` |
| 固件库 | GD32VW55x Firmware Library V1.6.0 | `home/sdk/GD32VW55x_Firmware_Library` |
| 链接脚本 | `GD32VW553xM.lds`（4 MB Flash / 288 KB RAM） | `.../Firmware/RISCV/env_Eclipse` |
| 开发板 | 立创 GD32VW553-HMQ6 | USART0：PB15/PA8，115200 8N1 |

---

## 1. 一页速览

```
1. VS Code 打开 home/projects/<工程名>/<工程名>.code-workspace   ← 不是“打开文件夹”
2. EIDE 侧栏点“构建”                                            ← 首次会提示安装在线资源包，选“否”
3. 产物：build_eide/Debug/<工程名>.elf / .hex / .bin
4. 接好 CMSIS-DAP（JTAG 接线），点 EIDE 的“烧录”
5. 串口：gd32 monitor -p COMx
```

命令行入口仍然可用（`gd32 build/flash`），与 EIDE 互不干扰，区别见 [4.5](#45-与命令行构建的关系)。

---

## 2. 打开工程

1. 用 VS Code 打开工程根目录下的 **`<工程名>.code-workspace`**：
   `home/projects/mos8_wifi/mos8_wifi.code-workspace`。
2. 工作区加载后，EIDE 会自动识别 `.eide/eide.yml` 并在侧栏显示工程。
   若没有自动加载，点 EIDE 侧栏的 **“打开项目”**，选择该 `.code-workspace` 文件。
3. 首次打开若弹出：

   > 无法找到编译器 `riscv-none-embed-gcc` 的位置 ！, [path]: 'null\bin',
   > 已找到在线资源包，需要安装它吗？

   选 **“否”**。本仓库用的是 `riscv-nuclei-elf-` 前缀的 Nuclei GCC，已在工作区里配置好。

> **必须打开 `.code-workspace`，不能只打开文件夹。**
> EIDE 的“打开项目”对话框只接受 `.code-workspace`；直接打开文件夹时 EIDE 不会加载工程。
> 另外，EIDE 读取的是 **`.code-workspace` 里的 `settings`**，不是工程下的
> `.vscode/settings.json`（它会用 `workspace.getConfiguration("EIDE")` 读取，且不绑定具体文件）。
> 工具链设置如果放到 `.vscode/settings.json`，EIDE 会显示 `[path]: 'null\bin'`。

工作区里与 EIDE 相关的设置只有三项：

```json
{
    "folders": [{ "path": "." }],
    "settings": {
        "EIDE.RISCV.InstallDirectory": "${workspaceFolder}/../../tools/gcc",
        "EIDE.RISCV.ToolPrefix": "riscv-nuclei-elf-",
        "EIDE.OpenOCD.ExePath": "${workspaceFolder}/../../tools/Nuclei/OpenOCD/2025.10/bin/openocd.exe"
    }
}
```

- `InstallDirectory` 填工具链 **根目录**（EIDE 自己会拼 `\bin`），不要填到 `bin`。
- 改完设置后若 EIDE 仍找不到编译器，执行一次 `Developer: Reload Window`。

---

## 3. 工程文件说明

`mos8_wifi` 的目录结构：

```
home/projects/mos8_wifi/
├─ mos8_wifi.code-workspace     # VS Code 工作区 + EIDE 工具链/OpenOCD 路径
├─ .eide/
│  ├─ eide.yml                  # EIDE 工程配置（源目录、宏、编译/链接选项、烧录）
│  ├─ env.ini                   # 构建环境变量（本机必须的 TMP/TEMP 设置）
│  ├─ gd32vw553.cfg             # OpenOCD 接口配置（CMSIS-DAP + JTAG）
│  └─ files.options.yml         # 单文件额外编译参数（EIDE 自动生成，通常留空）
├─ src/                         # 应用源码，自动参与编译
├─ include/                     # 应用头文件，已通过 -Iinclude 加入
├─ gd32vw55x_libopt.h           # 标准外设库裁剪头文件（工程根目录）
├─ build_eide/Debug/            # EIDE 构建产物与日志
├─ Makefile / build/            # 命令行构建（gd32 build）使用
└─ .vscode/                     # C/C++ IntelliSense、任务与调试配置（独立于 EIDE）
```

`.eide/eide.yml` 中 `srcDirs` 除了工程自己的 `src`、`include`，还列出了 SDK 的三个目录，
因此 **启动文件、系统初始化、全部标准外设驱动都会自动参与编译**，新增外设不用改工程配置。

---

## 4. 构建配置

### 4.1 eide.yml 关键字段

以 `home/projects/mos8_wifi/.eide/eide.yml`（配置格式 4.1）为例：

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `type` | `RISC-V` | 工程类型 |
| `toolchain` | `RISCV_GCC` | 对应 EIDE 的 RISC-V GCC 模型 |
| `srcDirs` | `src`、`include` + SDK 三个目录 | 自动扫描源文件 |
| `virtualFolder.files` | `gd32vw55x_libopt.h` | 工程根目录下的独立文件 |
| `outDir` | `build_eide` | 构建输出根目录 |
| `defineList` | `USE_STDPERIPH_DRIVER` | 标准外设库必需宏 |
| `incList` | `.`、`include`、SDK 头文件目录 | 头文件搜索路径 |
| `excludeList` | `.../RISCV/stubs/write.c` | 排除重复的 `_write` 实现 |
| `linkerScriptPath` | `.../env_Eclipse/GD32VW553xM.lds` | 4 MB Flash 链接脚本 |
| `uploader` | `OpenOCD` | 烧录器类型 |
| `uploadConfigMap.OpenOCD.interface` | `${workspaceFolder}/.eide/gd32vw553` | 自定义接口配置 |
| `uploadConfigMap.OpenOCD.target` | `gd32vw55x` | OpenOCD 自带目标脚本 |
| `uploadConfigMap.OpenOCD.baseAddr` | `0x08000000` | 仅烧录 `.bin` 时使用 |

`excludeList` 里的 `stubs/write.c` 不能删：工程自己的 `src/retarget.c` 已经实现了 `_write`，
两个都参与链接会报 `multiple definition of '_write'`。同理，若自己实现 `_sbrk`，需要排除
`stubs/sbrk.c`。

### 4.2 编译与链接参数

EIDE 按 `eide.yml` 的 `options` 生成实际命令行，与 Makefile 构建完全一致：

| 项 | 值 | eide.yml 位置 |
| --- | --- | --- |
| 架构 | `-march=rv32imafdc` | `global.arch` |
| ABI | `-mabi=ilp32d` | `global.abi` |
| 代码模型 | `-mcmodel=medlow` | `global.code-model` |
| 调试信息 | `-g` | `global.output-debug-info: enable` |
| C 标准 | `-std=gnu11` | `c/cpp-compiler.language-c` |
| 优化 | `-O2` | `c/cpp-compiler.optimization: level-2` |
| 警告 | `-Wall` | `c/cpp-compiler.warnings: all-warnings` |
| 分段 | `-ffunction-sections -fdata-sections` | `one-elf-section-per-function/data` |
| 链接 | `-T GD32VW553xM.lds -nostartfiles --gc-sections` | `linkerScriptPath` / `LD_FLAGS` / `remove-unused-input-sections` |
| 库 | `-lm -lc -lgcc` | `LIB_FLAGS` |

`-march/-mabi/-mcmodel` 会同时传给编译、汇编和链接阶段。

### 4.3 构建产物

```
build_eide/Debug/
├─ mos8_wifi.elf       # ELF，调试用（也可指定为烧录文件）
├─ mos8_wifi.hex       # Intel HEX，串口 ISP / 官方下载器用
├─ mos8_wifi.bin       # 原始镜像，起始地址 0x08000000
├─ compiler.log        # 编译输出
├─ unify_builder.log   # 失败时的完整命令与退出码
├─ builder.params      # EIDE 本次构建的完整参数（含 env）
├─ ref.json            # 源文件依赖信息
└─ compile_commands.json  # 编译数据库，可供 clangd/IntelliSense 使用
```

> 构建日志里 RAM 可能显示 `288 KB / 288 KB 100.00%`，这不代表溢出：该统计把链接脚本中
> 位于 RAM 顶端的 `.stack` 也算进了地址跨度。实际静态占用用
> `home/tools/gcc/bin/riscv-nuclei-elf-size.exe build_eide/Debug/mos8_wifi.elf` 查看
> （当前 data + bss 约 5 KB），判断是否溢出以这个结果为准。

### 4.4 添加、排除源文件

- **新增 `.c`**：放进 `src/`（模板工程是工程根目录），下次构建自动编译。
- **新增 `.h`**：放进 `include/` 或工程根目录，`-I.`、`-Iinclude` 已包含。
- **排除某个文件**：在 `excludeList` 中加相对路径；或在 EIDE 工程树里右键文件 → 属性 →
  取消“参与构建”。
- **单文件特殊参数**：写入 `.eide/files.options.yml`（EIDE 生成，格式 2.1），一般不需要动。

### 4.5 与命令行构建的关系

| | EIDE | 命令行 |
| --- | --- | --- |
| 入口 | EIDE 侧栏“构建” | `gd32 build <name>` |
| 输出目录 | `build_eide/Debug/` | `build/` |
| 配置来源 | `.eide/eide.yml` | `Makefile` |
| 编译参数 | 与 Makefile 一致 | 与 EIDE 一致 |
| 用途 | 日常开发、烧录、看编译数据库 | 脚本化、CI、快速验证 |

两套产物互不覆盖，可以同时使用。

---

## 5. 编译

1. 打开 `<工程名>.code-workspace`，等待 EIDE 加载工程。
2. 点 EIDE 侧栏的 **构建**（Build）；需要全量重编时点 **重新构建**（Rebuild）。
3. 输出窗口会显示每个文件的编译进度、链接结果与产物路径。

常用操作与面板：

| 操作 | 说明 |
| --- | --- |
| 构建 / 重新构建 | 增量 / 全量编译并链接 |
| 清理（Clean） | 删除 `build_eide/Debug`，遇到缓存异常时使用 |
| 显示构建参数 | 查看本次生成的完整命令行，排查参数问题 |
| `build_eide/Debug/compiler.log` | 编译输出与报错 |
| `build_eide/Debug/unify_builder.log` | 失败时的完整命令、退出码 |

首次构建会编译约 50 个文件（SDK 全量 + 应用代码），耗时约 1–2 秒。

---

## 6. 烧录

### 6.1 硬件连接

GD32VW553 的 OpenOCD 目标脚本使用 **JTAG**（`jtag newtap ... -irlen 5 -expected-id 0x10307a6d`），
而 OpenOCD 接口默认是 SWD，所以必须显式切换。

CMSIS-DAP / GD-Link / DAPLink 接线（JTAG 模式）：

```
TCK  -> 板子 TCK
TMS  -> 板子 TMS
TDI  -> 板子 TDI
TDO  -> 板子 TDO
GND  -> GND
3V3  -> 3V3（板子独立供电时可不接）
```

> 立创板调试接口的丝印与具体引脚以原理图/板卡教程为准；核心要求是
> **用 JTAG 模式，不要用 SWD**。J-Link 同样支持 JTAG，接线相同。

### 6.2 接口配置 `.eide/gd32vw553.cfg`

```cfg
# GD32VW55x requires JTAG; OpenOCD defaults to SWD.
# EIDE loads this file before target/gd32vw55x.cfg.
# J-Link: change the "adapter driver" line to "adapter driver jlink".
adapter driver cmsis-dap
transport select jtag
adapter speed 1000
```

EIDE 的 OpenOCD 烧录器没有“附加命令”输入框，`transport select jtag` 只能写在这个自定义接口
文件里。EIDE 实际执行的是：

```
openocd -s "<工程根目录>" -f .eide/gd32vw553.cfg -f target/gd32vw55x.cfg \
        -c "program \"<工程名>.hex\" verify" -c "reset run" -c "exit"
```

`target/gd32vw55x.cfg` 由 Nuclei OpenOCD 自带的脚本目录提供，不需要复制到工程里。

### 6.3 EIDE 烧录配置

对应 `eide.yml` 的 `uploadConfigMap.OpenOCD`：

| 字段 | 值 |
| --- | --- |
| 烧录器 | OpenOCD |
| 接口 | `${workspaceFolder}/.eide/gd32vw553`（填到文件名，不写 `.cfg`） |
| 目标 | `gd32vw55x` |
| 基地址 | `0x08000000` |
| `bin` | 留空 |

`bin` 留空时，EIDE 烧录的是输出目录下的 **`<工程名>.hex`**。也可以在这里指定其他文件：
`xxx.elf`，或 `xxx.bin,0x08000000`（原始二进制必须带地址）。

### 6.4 操作步骤

1. 接好探针，给板子上电。
2. 先点 **构建**，确认 `build_eide/Debug/<工程名>.hex` 已生成（默认烧录 `.hex`）。
3. 点 EIDE 的 **烧录**（Upload）。
4. OpenOCD 输出窗口出现以下内容即成功：

   ```
   ** Programming Started **
   ** Programming Finished **
   ** Verified OK **
   ** Resetting Target **
   ```

5. 打开串口看输出：`gd32 monitor -p COMx`（115200 8N1）。

### 6.5 切换到 J-Link

把 `.eide/gd32vw553.cfg` 中的 `adapter driver cmsis-dap` 改成：

```cfg
adapter driver jlink
```

`transport select jtag` 与 `adapter speed` 保持不变；`adapter speed 1000` 即 1 MHz。

### 6.6 备选：串口 ISP

没有调试探针时，可以用官方 GUI 串口下载（BOOT0=1 进入 Bootloader），
加载 `build_eide/Debug/<工程名>.hex`。运行 `gd32 isp` 启动
GD32 All-In-One Programmer（需先执行 `setup_toolchain.py` 安装 `aio`）。

---

## 7. 调试（可选）

EIDE 侧栏的“调试”按钮本工程未配置调试器。推荐沿用工程内 `.vscode/launch.json`
的 OpenOCD + GDB 方式：

1. 安装扩展 `marus25.cortex-debug`（Cortex-Debug）。
2. `.vscode/launch.json` 默认调试的是命令行产物 `build/<工程名>.elf`。只用 EIDE 时，
   把两个配置里的 `executable` 改成：

   ```json
   "executable": "${workspaceFolder}/build_eide/Debug/${workspaceFolderBasename}.elf"
   ```

   并删除 `"preLaunchTask": "build"`（否则 F5 会先走命令行构建）。
3. `F5` 选择 `Debug (CMSIS-DAP / GD-Link)` 或 `Debug (J-Link)`。

Cortex-Debug 官方只标注支持 Arm，GD32VW553 属于社区用法；若断点或寄存器异常，
可改用 C/C++ 的 `cppdbg` 连接 OpenOCD 的 GDB 端口（3333），配置见
`.vscode/launch.json`。

---

## 8. 新建工程

```bat
gd32 new demo
```

该命令会：

1. 从 `home/templates/baremetal` 复制模板到 `home/projects/demo`；
2. 把 `baremetal.code-workspace` 重命名为 `demo.code-workspace`；
3. 重写 `.eide/eide.yml` 的 `name` 并生成新的 `uid`；
4. 确保 `home/.tmp` 存在（构建临时目录）。

然后直接用 VS Code 打开 `home/projects/demo/demo.code-workspace` 即可构建、烧录。

### 8.1 接入已有工程

用 `home/scripts/eide.py` 把已有工程目录接入 EIDE：

```bat
python home\scripts\eide.py adopt home\projects\my_project
```

脚本会扫描工程内的 `.c/.S` 与头文件目录（跳过 `build`、`build_eide`、`.git` 等），生成：

- `.eide/eide.yml`：源目录、头文件路径、SDK、链接脚本、烧录配置
- `.eide/env.ini`：临时目录设置
- `.eide/gd32vw553.cfg`：OpenOCD JTAG 接口
- `.eide/files.options.yml`：单文件参数（空）
- `<工程名>.code-workspace`：已写入工具链与 OpenOCD 路径

常用选项：

| 选项 | 作用 |
| --- | --- |
| `--name NAME` | 指定 EIDE 里的工程名（默认目录名） |
| `--ld FILE` | 指定链接脚本（相对工程目录或绝对路径） |
| `--repo-sdk` | 强制加入本仓库 SDK |
| `--no-sdk` | 不加本仓库 SDK（工程自带固件库） |
| `--workspace FILE` | 把工程加入已有 `.code-workspace`（多根工作区），设置项使用绝对路径 |
| `--force` | 重新生成已存在的 `.eide/eide.yml`（备份为 `.bak`） |

默认情况下，若工程内检测到 `system_gd32vw55x.c` 或 `gd32vw55x.h`，视为自带固件库，
不会重复加入本仓库 SDK，此时需要 `--ld` 指定工程自己的链接脚本（或让脚本找到唯一的
`.lds/.ld`）。工程定义了 `_write`/`_sbrk` 时，脚本会自动把 SDK 的
`stubs/write.c`/`stubs/sbrk.c` 加入排除列表。

注意：

- 模板工程的源文件在 **工程根目录**（`main.c`、`retarget.c` 等），与 `mos8_wifi` 的
  `src/`+`include/` 布局不同；两种布局 EIDE 都能自动识别。
- `eide.yml` 和 `.code-workspace` 全部使用相对路径（`../../sdk/...`、`../../tools/...`），
  因此工程必须放在 `home/projects/` 下。移动工程后需要同步调整这些相对路径。
- 模板里的 `uid` 是占位值，`gd32 new` 会生成新的。手工复制工程目录时也要换一个 `uid`，
  否则 EIDE 可能把两个工程当成同一个。

---

## 9. 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| EIDE 侧栏没有工程，构建按钮不可用 | 打开的是文件夹，不是 `.code-workspace` | 重新打开 `<工程名>.code-workspace`，或用“打开项目”选择它 |
| 提示找不到 `riscv-none-embed-gcc`，`[path]: 'null\bin'` | 工作区缺少 EIDE 设置，或设置放进了 `.vscode/settings.json` | 确认 `.code-workspace` 里三项设置齐全；`Developer: Reload Window` |
| 弹窗询问是否安装在线资源包 | EIDE 模型默认前缀是 `riscv-none-embed-` | 选“否”，我们已配置 `riscv-nuclei-elf-` |
| `Cannot create temporary file in C:\Users\...\Temp: Permission denied` | 火绒/Sangfor HIPS 拦截 GCC 在工程外写临时文件 | 保留 `.eide/env.ini`，并确保 `home/.tmp` 存在；彻底解决见下 |
| 链接报 `multiple definition of '_write'` / `'_sbrk'` | `retarget.c` 与 SDK stubs 重复实现 | 在 `excludeList` 排除 `stubs/write.c` 或 `stubs/sbrk.c` |
| 构建产物不是最新 / 行为异常 | 增量缓存或手工改过 `build_eide` | 点“清理”，再“重新构建” |
| 烧录报 `unable to find a matching CMSIS-DAP device` | 探针未接、驱动未装、或探针不支持 JTAG | 检查 USB、驱动与接线；换 J-Link 试 |
| 烧录报 `Unsupported DTM version` / 无法识别目标 | 接线错误、目标未供电，或实际走的是 SWD | 确认 `.eide/gd32vw553.cfg` 中 `transport select jtag`，检查 JTAG 接线与供电 |
| 烧录成功但不运行 | 没有复位，或链接脚本/启动文件不对 | OpenOCD 已执行 `reset run`；再按一次复位；确认使用 `GD32VW553xM.lds` |
| 串口无输出 | 串口线未接 USART0（PB15/PA8），或波特率不对 | 改接 PB15/PA8，115200 8N1；用 `gd32 ports` 确认端口 |
| 修改 `eide.yml` 不生效 | EIDE 以界面配置为准，加载后会重写文件 | 尽量在 EIDE 属性界面修改；改完 Reload Window |

### 临时目录权限问题（本机特有）

报错示例：

```
Cannot create temporary file in C:\Users\<user>\AppData\Local\Temp\: Permission denied
```

根因不是 EIDE 配置错误，而是本机 HIPS（火绒 `HipsDaemon`/`HipsTray`，另有 Sangfor 终端防护）
拦截了 `riscv-nuclei-elf-gcc.exe` 在工程目录之外创建文件。实测 Python/Node 可正常写系统
Temp，只有该工具链被拦。

工程内 `.eide/env.ini` 已通过 `[debug]` 段把临时目录指到 `home/.tmp`：

```ini
[debug]
TMP=..\..\.tmp
TEMP=..\..\.tmp
TMPDIR=..\..\.tmp
```

EIDE 构建时会把这些变量合并进 `builder.params` 的 `env` 并传给 GCC。
`[debug]` 对应目标名 `Debug`（大小写不敏感）；如果新建了 `Release` 目标，需要再加一个
`[release]` 段。

彻底解决（可选）：在火绒的“自定义防护/程序规则”中放行 `home/tools/gcc` 整个目录，
之后可删除 `env.ini` 中的三行。不要删除 `home/.tmp` 目录本身。

---

## 10. 相关文件速查

| 内容 | 路径 |
| --- | --- |
| 工程配置 | `.eide/eide.yml` |
| 构建环境变量 | `.eide/env.ini` |
| OpenOCD 接口（JTAG） | `.eide/gd32vw553.cfg` |
| 单文件编译参数 | `.eide/files.options.yml` |
| 工具链 / OpenOCD 路径 | `<工程名>.code-workspace` 的 `settings` |
| 构建产物 | `build_eide/Debug/` |
| 编译数据库 | `build_eide/Debug/compile_commands.json` |
| C/C++ IntelliSense | `.vscode/c_cpp_properties.json` |
| 调试配置 | `.vscode/launch.json` |
| 命令行构建 | `gd32 build <name>` → `build/` |
| 串口监视 | `gd32 monitor -p COMx` |
| 工程接入脚本 | `home/scripts/eide.py` |
| 工具链下载脚本 | `home/scripts/setup_toolchain.py` |

更多内容：

- 仓库总览、命令行用法、组件来源：`README.md`
- 立创 GD32VW553 资料：<https://wiki.lckfb.com/zh-hans/gd32vw553/>
- GD32VW55x 固件库：<https://github.com/GigaDevice-GD32-MCU/GD32VW55x_Firmware_Library>
- Nuclei 工具链与 OpenOCD：<https://doc.nucleisys.com/nuclei_tools/toolchain/index.html>
