# Contributing

Thanks for taking the time to contribute.

## Development setup

1. Install Python 3.8+ and VS Code with the Embedded IDE (`cl.eide`) extension.
2. Install the toolchain:

   ```bat
   python home\scripts\setup_toolchain.py
   ```

3. Verify the environment and build the examples:

   ```bat
   python home\scripts\setup_toolchain.py --check
   gd32 build hello_led
   gd32 build mos8_wifi
   ```

## Pull requests

- Keep Python scripts dependency-free (standard library only). `pyserial` is
  optional and used only by `gd32 monitor`.
- Do not commit anything under `home/tools/`, `home/sdk/`, `home/.tmp/`,
  `build/`, `build_eide/`, or generated `.elf/.bin/.hex` files.
- Keep the EIDE and VS Code configuration paths relative; the repository must
  work after being cloned to any directory.
- For template changes, verify that both EIDE and the CLI build the generated
  project (`gd32 new demo`, then build).
- Describe the board/toolchain version you tested with in the pull request.

## Reporting issues

Include:

- host OS and Python version
- the component versions printed by `python home\scripts\setup_toolchain.py --check`
- the failing command and its output
- for EIDE builds, `build_eide/Debug/compiler.log` or `unify_builder.log`

Do not paste Wi-Fi credentials, tokens or other secrets.
