# mos8_wifi — GD32VW553 八路 MOS 管控制器

基于 GD32VW553（LCKFB-HMQ6 板）的 8 路 MOS 管输出控制器，带串口命令行和 Wi-Fi 链路抽象层。

> **关于 Wi-Fi 的重要说明**
> 本工作区安装的 `GD32VW55x_Firmware_Library` 只有外设驱动（GPIO/USART/ADC…），**不含 Wi-Fi 协议栈**。
> 真正连 AP 需要另一套 `GD32VW55x_RELEASE`（MSDK，内含 FreeRTOS + Wi-Fi/BLE 中间件）以及它配套的
> `riscv-nuclei-elf-gcc` 和 `rom_symbol_m.gcc` 链接符号。所以本工程把 Wi-Fi 做成**可插拔后端**：
> 现在编出来的固件用串口控制 8 路 MOS；装上 MSDK 后加一个 `wifi_backend_msdk.c`，把
> `wifi join <ssid> <pwd>` 接到真实协议栈即可，前端一行不用改。见文末「接入真实 Wi-Fi」。

---

## 1. 功能

- 8 路 GPIO 推挽输出，上电全部关闭（防误动作）
- 串口命令行（USART0，115200 8N1）：单路开关 / 翻转 / 全部开关 / 位图批量设置 / 状态查询
- 状态位图接口 `mosfet_mask()`，方便以后接到网络协议上
- Wi-Fi 链路状态机 + 弱符号后端（当前为空实现）
- 板载 LED 2 秒一次心跳闪烁，说明主循环没卡死

## 2. 硬件接线

低边 NMOS 驱动（推荐，MOS 源极接地、负载接电源正）：

```
             +V_LOAD
                |
             [ 负载 ]        感性负载(电机/继电器/电磁阀)
                |            并联续流二极管，阴极接 +V_LOAD
                +-----------|<|----+
                |                  |
   PA0 ──[100Ω]─┴─ G   (栅极)      |
                   |               |
                 [10k]           D |
                   |             [NMOS]  AO3400 / IRLZ44N / SI2302
                  GND              |
                                  S
                                  |
                                 GND  ← 与 MCU 必须共地
```

要点：

- 选 **逻辑电平** MOS（Vgs(th) < 2.5 V，如 AO3400、SI2302、IRLZ44N），不要用 IRF540 这类 10 V 才完全导通的管子
- 栅极串 100 Ω 抑制振铃，栅源并 10 kΩ 下拉，防止上电瞬间误导通
- 感性负载必须加续流二极管（如 1N4148 / SS34），否则关断瞬间会打穿 MOS
- 8 路共地；如果负载电流较大，建议用光耦/栅极驱动芯片隔离

## 3. 引脚映射

默认占用 PA0 ~ PA7 作为 CH1 ~ CH8。改引脚只改 `src/board.c` 里的 `g_mos_pins[]` 表：

| 通道 | 引脚 | 通道 | 引脚 |
|------|------|------|------|
| CH1  | PA0  | CH5  | PA4  |
| CH2  | PA1  | CH6  | PA5  |
| CH3  | PA2  | CH7  | PA6  |
| CH4  | PA3  | CH8  | PA7  |

已占用、不要再用的引脚：`PB15` = USART0_TX，`PA8` = USART0_RX，`PC13` = 板载 LED。

驱动极性由 `include/board.h` 的 `MOS_ACTIVE_HIGH` 决定：

- `1`（默认）：GPIO 高 → MOS 导通（直接驱动 NMOS 栅极）
- `0`：GPIO 低 → MOS 导通（光耦 / 反相驱动）

## 4. 编译 / 烧录 / 串口

### 4.1 两种构建方式（产物完全相同）

**方式 A：Makefile（`gd32.py` 封装，默认）**

```bash
# 在仓库根目录执行
python home/scripts/gd32.py doctor              # 检查工具链、OpenOCD、SDK
python home/scripts/gd32.py build mos8_wifi     # 编译，产物在 home/projects/mos8_wifi/build/
python home/scripts/gd32.py flash mos8_wifi     # OpenOCD + CMSIS-DAP(GD-Link) 下载
python home/scripts/gd32.py monitor -b 115200   # 串口终端
```

**方式 B：CMake**

```bash
cd home/projects/mos8_wifi
cmake --preset default          # 配置（自动找 home/tools/gcc）
cmake --build --preset default  # 编译，-j8
cmake --build build/cmake --target size   # 看 Flash/RAM 占用
```

CMake 相关文件：

| 文件 | 作用 |
|---|---|
| `CMakeLists.txt` | 源文件、编译/链接选项、objcopy 生成 bin/hex |
| `cmake/riscv-toolchain.cmake` | 交叉工具链（rv32imafdc / ilp32d），自动定位 `home/tools/gcc/bin` |
| `CMakePresets.json` | preset `default`，VS Code 装 CMake Tools 后可直接选 |

两种方式都输出到同一个 `build/` 目录（`mos8_wifi.elf/.bin/.hex/.map`），所以 `gd32.py flash` 对两种构建都适用。
保留 Makefile 只是为了 `gd32.py` 的项目发现与烧录兼容；日常用 CMake 即可。

- 下载器默认 `cmsis-dap`（GD-Link），用 J-Link 时加 `--interface jlink`
- 板子串口是 USART0（TX=PB15，RX=PA8），**115200 8N1**

VS Code 里也可以直接按 `Ctrl+Shift+B`（任务 `build`），或 F5 起 OpenOCD 调试（需装 Cortex-Debug 扩展）。

## 5. 命令

```
help                         打印帮助
status                       打印 8 路状态 + LED + Wi-Fi 状态
on   <1-8|all>               打开某路 / 全部
off  <1-8|all>               关闭某路 / 全部
toggle <1-8|all>             翻转某路 / 全部
mask <0x00-0xFF>             按位图一次设置（bit0=CH1）
led                          查看 LED 状态
led on|off|toggle            LED1 常亮 / 常灭 / 翻转
led blink [ms]               闪烁，默认 2000ms（可 50~60000）
led stop                     停止闪烁，保持当前状态
wifi                         查看链路状态
wifi join <ssid> <password>  连接 AP（需要协议栈后端）
wifi leave                   断开
ver                          版本信息
```

### LED

- 板载 **LED1 = PC13**，按立创 wiki（[库函数点亮LED灯](https://wiki.lckfb.com/zh-hans/gd32vw553/beginner/lib-led.html)）是**高电平点亮**，代码里 `board.h` 的 `LED_ACTIVE_HIGH = 1`；极性相反就改成 `0`。
- 上电默认 **2 秒（2000ms）一次心跳闪烁**；执行 `led on/off/toggle` 会停掉闪烁，执行 `led blink` 重新开始。
- 闪烁是**非阻塞**的：`led_tick()` 在主循环里每 1ms 调一次，不占用 `delay`，不影响串口命令和 8 路控制。

示例会话：

```
> status
channels: 1=OFF 2=OFF 3=OFF 4=OFF 5=OFF 6=OFF 7=OFF 8=OFF
mask: 0x00
led: blink 2000ms
wifi: unavailable
> led blink 200
led: blink 200ms
> led on
led: on
> on 3
on: CH3 ON
> mask 0x81
mask: 0x81 applied
> status
channels: 1=ON 2=OFF 3=ON 4=OFF 5=OFF 6=OFF 7=OFF 8=ON
mask: 0x81
```

## 6. 接入真实 Wi-Fi（MSDK）

### 6.1 后端接口契约

`wifi_link.h` 里定义了一组弱符号，默认全部是空实现（因此 `wifi_link_available()` 返回 0）。
新增一个 `.c` 文件定义下面这些函数，并把它加进 `Makefile` 的 `APP_SRCS`，链接时会自动覆盖：

| 函数 | 语义 |
|------|------|
| `int wifi_backend_init(void)` | 初始化协议栈，返回 0 表示可用 |
| `int wifi_backend_join(const char*, const char*)` | 发起连接，返回 0 表示异步连接已开始 |
| `void wifi_backend_leave(void)` | 断开 |
| `void wifi_backend_poll(void)` | 主循环轮询，驱动协议栈事件 |
| `wifi_state_t wifi_backend_state(void)` | 返回 OFF / CONNECTING / CONNECTED / ERROR |
| `const char *wifi_backend_ip(void)` | 连接成功后返回 IP 字符串 |

`wifi_backend_msdk.c.example` 是一份按这个契约写的骨架，把里面标注 `TODO` 的调用换成
MSDK 里实际的 Wi-Fi 管理 API 即可。

### 6.2 网络控制通道怎么接

命令解析和执行已经和串口解耦：`app_run_command(char *line)`（`console.h`）接收一整行文本，
执行结果通过 `printf` 回。将来 Wi-Fi 通了，在 TCP 收包回调里按行拼好字符串调用它，
就等于把「网页/APP 控制 8 路 MOS」接上了，控制逻辑一行都不用重写。

### 6.3 还要改的编译/链接参数

MSDK 工程不是裸机外设库，编译参数和链接参数都要跟着换，否则库对不上：

```
-march=rv32imafcbp -mabi=ilp32f -Os
-DCFG_RTOS -DPLATFORM_OS_FREERTOS
-L <MSDK>/lib -L <MSDK>/plf/riscv/NMSIS/Library/DSP/GCC
-Wl,--just-symbols=<包根>/ROM-EXPORT/symbol/rom_symbol_m.gcc
-lwifi -lrf -lwpas -lm -lnmsis_dsp_rv32imafcbp
-T <MSDK>/examples/wifi/example_wifi.lds
```

其中 `--just-symbols=rom_symbol_m.gcc` 最关键——Wi-Fi/加密函数固化在芯片 ROM 里，
没有这个符号表就会出现一大堆 undefined reference。

MSDK 自带 FreeRTOS，届时 `main()` 要改成创建任务的形式，命令行也可以从 UART 挪到一个
TCP 端口上（复用 `exec_line()` 那套解析逻辑即可）。

## 7. 已知限制

- 没有 Wi-Fi 协议栈时，`wifi join` 会明确回复 `no protocol stack linked`，不会假装成功
- 控制台只做行解析，不支持历史命令、不支持多行粘贴超 80 字节
- 8 路只有开关，没有 PWM 调光（需要的话把 TIMER 通道映射到同一批引脚）
- 上电状态不保存，掉电重启后全部关闭

## 8. 目录结构

```
mos8_wifi/
├── include/                    对外头文件
│   ├── board.h                 引脚表、LED 极性、驱动极性
│   ├── mosfet.h                8 路输出驱动 API
│   ├── led.h                   板载 LED 控制 + 非阻塞闪烁
│   ├── console.h               命令行 + app_run_command()
│   ├── wifi_link.h             Wi-Fi 前后端抽象
│   ├── systick.h               1 ms 节拍
│   └── gd32vw55x_it.h          中断服务声明
├── src/                        实现
│   ├── main.c                  主流程
│   ├── board.c                 引脚表
│   ├── mosfet.c                8 路输出（状态位图）
│   ├── led.c                   LED1（PC13）驱动 + 闪烁时基
│   ├── console.c               USART0 命令行（中断收 + 环形缓冲）
│   ├── wifi_link.c             Wi-Fi 前端 + 弱符号后端
│   ├── systick.c               1 ms 节拍
│   ├── retarget.c              printf 重定向 + uart_init
│   └── gd32vw55x_it.c          中断服务（节拍 + USART0 接收）
├── gd32vw55x_libopt.h          SDK 头文件裁剪（被 gd32vw55x.h 引用，必须留在根目录）
├── wifi_backend_msdk.c.example MSDK 后端骨架（不参与编译）
├── CMakeLists.txt              CMake 构建
├── cmake/riscv-toolchain.cmake 交叉工具链
├── CMakePresets.json           cmake --preset default
├── Makefile                    gd32.py 用的构建入口
└── .vscode/                    构建/烧录/调试配置
```
