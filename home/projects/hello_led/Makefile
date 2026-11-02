# GD32VW553 bare-metal project
# Usage: ..\..\gd32.cmd build   (or: make -C .)

ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
MKDIR = if not exist "$(subst /,\,$1)" mkdir "$(subst /,\,$1)"
else
MKDIR = mkdir -p "$1"
endif

ROOT     := $(abspath $(CURDIR)/../..)
SDK      := $(ROOT)/sdk/GD32VW55x_Firmware_Library
TOOLS    := $(ROOT)/tools
PREFIX   := $(TOOLS)/gcc/bin/riscv-nuclei-elf-
CC       := $(PREFIX)gcc
OBJCOPY  := $(PREFIX)objcopy
SIZE     := $(PREFIX)size

TARGET   := $(notdir $(CURDIR))
BUILD    := build
ELF      := $(BUILD)/$(TARGET).elf
LDSCRIPT := $(SDK)/Firmware/RISCV/env_Eclipse/GD32VW553xM.lds

ARCH     := -march=rv32imafdc -mabi=ilp32d
CFLAGS   := $(ARCH) -std=gnu11 -O2 -g -Wall -ffunction-sections -fdata-sections \
            -DUSE_STDPERIPH_DRIVER
INCLUDES := -I. \
            -I$(SDK)/Firmware/GD32VW55x_standard_peripheral \
            -I$(SDK)/Firmware/GD32VW55x_standard_peripheral/Include \
            -I$(SDK)/Firmware/RISCV/drivers \
            -I$(SDK)/Firmware/RISCV/stubs
LDFLAGS  := $(ARCH) -T$(LDSCRIPT) -nostartfiles -Wl,--gc-sections \
            -Wl,-Map=$(BUILD)/$(TARGET).map

APP_SRCS := main.c systick.c gd32vw55x_it.c retarget.c
SDK_C_SRCS := $(wildcard $(SDK)/Firmware/RISCV/env_Eclipse/*.c) \
              $(filter-out %/write.c,$(wildcard $(SDK)/Firmware/RISCV/stubs/*.c)) \
              $(SDK)/Firmware/GD32VW55x_standard_peripheral/system_gd32vw55x.c \
              $(wildcard $(SDK)/Firmware/GD32VW55x_standard_peripheral/Source/*.c)
SDK_ASM_SRCS := $(SDK)/Firmware/RISCV/env_Eclipse/start.S \
                $(SDK)/Firmware/RISCV/env_Eclipse/entry.S

SRCS     := $(APP_SRCS) $(SDK_C_SRCS)
VPATH    := . $(sort $(dir $(SRCS) $(SDK_ASM_SRCS)))
OBJS     := $(addprefix $(BUILD)/obj/,$(addsuffix .o,$(notdir $(basename $(SRCS) $(SDK_ASM_SRCS)))))

.PHONY: all clean size

all: $(ELF) $(BUILD)/$(TARGET).bin $(BUILD)/$(TARGET).hex size

$(ELF): $(OBJS)
	@$(call MKDIR,$(BUILD))
	$(CC) $(LDFLAGS) $(OBJS) -lm -lc -lgcc -o $@

$(BUILD)/obj/%.o: %.c
	@$(call MKDIR,$(@D))
	$(CC) $(CFLAGS) $(INCLUDES) -MMD -MP -c $< -o $@

$(BUILD)/obj/%.o: %.S
	@$(call MKDIR,$(@D))
	$(CC) $(ARCH) $(INCLUDES) -c $< -o $@

$(BUILD)/%.bin: $(ELF)
	$(OBJCOPY) -O binary $< $@

$(BUILD)/%.hex: $(ELF)
	$(OBJCOPY) -O ihex $< $@

size: $(ELF)
	@$(SIZE) $<

clean:
	@if exist "$(subst /,\,$(BUILD))" rmdir /s /q "$(subst /,\,$(BUILD))"

-include $(OBJS:.o=.d)
