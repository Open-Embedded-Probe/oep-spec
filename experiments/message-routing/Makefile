AVR_CC ?= avr-gcc
AVR_SIZE ?= avr-size
CH32_CC ?= riscv-none-elf-gcc
CH32_SIZE ?= riscv-none-elf-size

COMMON_CFLAGS := -std=c11 -Os -Wall -Wextra -Werror \
	-ffunction-sections -fdata-sections -Isrc

.PHONY: sizes clean

build:
	mkdir -p build

build/avr.elf: size_message_routing.c src/message_routing.c \
		src/message_routing.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-Wl,--gc-sections size_message_routing.c src/message_routing.c -o $@

build/ch32.elf: size_message_routing.c src/message_routing.c \
		src/message_routing.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-nostartfiles -Wl,--gc-sections,-e,main \
		size_message_routing.c src/message_routing.c -lc -lgcc -o $@

build/avr-fixed.elf: size_message_routing_fixed.c src/message_routing.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-Wl,--gc-sections size_message_routing_fixed.c -o $@

build/ch32-fixed.elf: size_message_routing_fixed.c src/message_routing.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-nostartfiles -Wl,--gc-sections,-e,main \
		size_message_routing_fixed.c -lc -lgcc -o $@

build/avr-header-uniform.elf: size_header_uniform.c \
		src/message_header_layout.c src/message_header_layout.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-Wl,--gc-sections size_header_uniform.c \
		src/message_header_layout.c -o $@

build/ch32-header-uniform.elf: size_header_uniform.c \
		src/message_header_layout.c src/message_header_layout.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-nostartfiles -Wl,--gc-sections,-e,main \
		size_header_uniform.c src/message_header_layout.c -lc -lgcc -o $@

build/avr-header-role.elf: size_header_role.c \
		src/message_header_layout.c src/message_header_layout.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-Wl,--gc-sections size_header_role.c \
		src/message_header_layout.c -o $@

build/ch32-header-role.elf: size_header_role.c \
		src/message_header_layout.c src/message_header_layout.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-nostartfiles -Wl,--gc-sections,-e,main \
		size_header_role.c src/message_header_layout.c -lc -lgcc -o $@

sizes: build/avr.elf build/ch32.elf build/avr-fixed.elf build/ch32-fixed.elf \
		build/avr-header-uniform.elf build/ch32-header-uniform.elf \
		build/avr-header-role.elf build/ch32-header-role.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr.elf
	$(CH32_SIZE) -A build/ch32.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-fixed.elf
	$(CH32_SIZE) -A build/ch32-fixed.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-header-uniform.elf
	$(CH32_SIZE) -A build/ch32-header-uniform.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-header-role.elf
	$(CH32_SIZE) -A build/ch32-header-role.elf

clean:
	rm -rf build
