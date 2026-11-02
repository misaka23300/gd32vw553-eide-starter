# Third-party notices

This repository contains original scripts, documentation and example firmware.
The following components are **downloaded at setup time** by
`home/scripts/setup_toolchain.py` and are not redistributed here.

| Component | Version | Source |
| --- | --- | --- |
| Nuclei RISC-V GCC | 2022.04 (GCC 10.2.0) | <https://doc.nucleisys.com/nuclei_tools/toolchain/index.html> |
| Nuclei OpenOCD | 2025.10 (0.12.0) | <https://doc.nucleisys.com/nuclei_tools/openocd/intro.html> |
| Nuclei win32 build tools | 1.2 | <https://doc.nucleisys.com/nuclei_tools/toolchain/index.html> |
| GD32VW55x Firmware Library | V1.6.0 | <https://www.gd32mcu.com/cn/download/0?kw=GD32VW5> |
| GD32VW55x Wi-Fi/BLE SDK | V1.0.3g | <https://www.gd32mcu.com/cn/download/0?kw=GD32VW5> |
| GD32 All-In-One Programmer | V5.4.0.42035 | <https://www.gd32mcu.com/cn/download/0?kw=GD32VW5> |

- **Nuclei GCC** is based on GNU GCC, binutils, newlib and GDB. Its licenses
  (GPL/LGPL and others) are included in the downloaded toolchain under
  `gcc/distro-info/licenses/`.
- **Nuclei OpenOCD** is distributed under GPL-2.0; see the license files in the
  downloaded package.
- **GD32 firmware library / SDK / programmer** are GigaDevice products and are
  governed by GigaDevice's license terms. Review them before redistribution.
- **bsdtar** (`C:\Windows\System32\tar.exe`) is part of Windows and is used only
  to extract 7z archives.

## Files copied from the GD32 firmware library

`home/templates/baremetal/gd32vw55x_libopt.h` and the same file in each example
project are copied from the GD32VW55x Firmware Library V1.6.0. They retain the
original GigaDevice copyright and BSD-3-Clause license header. The rest of the
template and example sources are original code under the repository's MIT
license.
