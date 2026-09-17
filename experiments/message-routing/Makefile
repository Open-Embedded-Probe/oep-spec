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

build/avr-correlation-1.elf: size_request_correlation.c \
		src/request_correlation.c src/request_correlation.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p -DOEP_SIZE_SLOT_COUNT=1 \
		-Wl,--gc-sections size_request_correlation.c \
		src/request_correlation.c -o $@

build/avr-correlation-4.elf: size_request_correlation.c \
		src/request_correlation.c src/request_correlation.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p -DOEP_SIZE_SLOT_COUNT=4 \
		-Wl,--gc-sections size_request_correlation.c \
		src/request_correlation.c -o $@

build/ch32-correlation-1.elf: size_request_correlation.c \
		src/request_correlation.c src/request_correlation.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-DOEP_SIZE_SLOT_COUNT=1 -nostartfiles \
		-Wl,--gc-sections,-e,main size_request_correlation.c \
		src/request_correlation.c -lc -lgcc -o $@

build/ch32-correlation-4.elf: size_request_correlation.c \
		src/request_correlation.c src/request_correlation.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-DOEP_SIZE_SLOT_COUNT=4 -nostartfiles \
		-Wl,--gc-sections,-e,main size_request_correlation.c \
		src/request_correlation.c -lc -lgcc -o $@

build/avr-allocator-8.elf: size_correlation_allocator.c \
		src/request_correlation.c src/request_correlation.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-DOEP_SIZE_CORRELATION_MAXIMUM=0xff \
		-Wl,--gc-sections size_correlation_allocator.c \
		src/request_correlation.c -o $@

build/avr-allocator-16.elf: size_correlation_allocator.c \
		src/request_correlation.c src/request_correlation.h | build
	$(AVR_CC) $(COMMON_CFLAGS) -mmcu=atmega328p \
		-DOEP_SIZE_CORRELATION_MAXIMUM=0xffff \
		-Wl,--gc-sections size_correlation_allocator.c \
		src/request_correlation.c -o $@

build/ch32-allocator-8.elf: size_correlation_allocator.c \
		src/request_correlation.c src/request_correlation.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-DOEP_SIZE_CORRELATION_MAXIMUM=0xff -nostartfiles \
		-Wl,--gc-sections,-e,main size_correlation_allocator.c \
		src/request_correlation.c -lc -lgcc -o $@

build/ch32-allocator-16.elf: size_correlation_allocator.c \
		src/request_correlation.c src/request_correlation.h | build
	$(CH32_CC) $(COMMON_CFLAGS) -march=rv32ec -mabi=ilp32e \
		-DOEP_SIZE_CORRELATION_MAXIMUM=0xffff -nostartfiles \
		-Wl,--gc-sections,-e,main size_correlation_allocator.c \
		src/request_correlation.c -lc -lgcc -o $@

sizes: build/avr.elf build/ch32.elf build/avr-fixed.elf build/ch32-fixed.elf \
		build/avr-header-uniform.elf build/ch32-header-uniform.elf \
		build/avr-header-role.elf build/ch32-header-role.elf \
		build/avr-correlation-1.elf build/avr-correlation-4.elf \
		build/ch32-correlation-1.elf build/ch32-correlation-4.elf \
		build/avr-allocator-8.elf build/avr-allocator-16.elf \
		build/ch32-allocator-8.elf build/ch32-allocator-16.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr.elf
	$(CH32_SIZE) -A build/ch32.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-fixed.elf
	$(CH32_SIZE) -A build/ch32-fixed.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-header-uniform.elf
	$(CH32_SIZE) -A build/ch32-header-uniform.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-header-role.elf
	$(CH32_SIZE) -A build/ch32-header-role.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-correlation-1.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-correlation-4.elf
	$(CH32_SIZE) -A build/ch32-correlation-1.elf
	$(CH32_SIZE) -A build/ch32-correlation-4.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-allocator-8.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/avr-allocator-16.elf
	$(CH32_SIZE) -A build/ch32-allocator-8.elf
	$(CH32_SIZE) -A build/ch32-allocator-16.elf

clean:
	rm -rf build
