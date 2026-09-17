AVR_CC ?= avr-gcc
AVR_SIZE ?= avr-size
AVR_NM ?= avr-nm
CH32_CC ?= riscv-none-elf-gcc
CH32_SIZE ?= riscv-none-elf-size
CH32_NM ?= riscv-none-elf-nm

AVR_CFLAGS := -std=c11 -mmcu=atmega328p -Os -Wall -Wextra -Werror \
	-ffunction-sections -fdata-sections -Isrc
AVR_LDFLAGS := -mmcu=atmega328p -Wl,--gc-sections
CH32_CFLAGS := -std=c11 -march=rv32ec -mabi=ilp32e -Os -Wall -Wextra \
	-Werror -ffunction-sections -fdata-sections -Isrc
CH32_LDFLAGS := -nostartfiles -Wl,--gc-sections,-e,main

.PHONY: avr-size ch32-size clean

build:
	mkdir -p build

build/candidate-b.elf: size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b_core.c src/bootstrap_candidate_b.h \
		src/bootstrap_candidate_b_core.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(AVR_LDFLAGS) \
		size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b_core.c -o $@

build/candidate-b-strict.elf: size_candidate_b.c \
		src/bootstrap_candidate_b.c src/bootstrap_candidate_b_core.c \
		src/bootstrap_candidate_b.h src/bootstrap_candidate_b_core.h | build
	$(AVR_CC) $(AVR_CFLAGS) -DOEP_BOOTSTRAP_B_STRICT_PADDING \
		$(AVR_LDFLAGS) size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b_core.c -o $@

build/candidate-c.elf: size_candidate_c.c src/bootstrap_candidate_c.c \
		src/bootstrap_candidate_c.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(AVR_LDFLAGS) \
		size_candidate_c.c src/bootstrap_candidate_c.c -o $@

avr-size: build/candidate-b.elf build/candidate-b-strict.elf \
		build/candidate-c.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/candidate-b.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/candidate-b-strict.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/candidate-c.elf
	$(AVR_NM) --print-size --size-sort --radix=d build/candidate-b.elf | tail -n 8
	$(AVR_NM) --print-size --size-sort --radix=d build/candidate-c.elf | tail -n 8

build/ch32-candidate-b.elf: size_candidate_b.c \
		src/bootstrap_candidate_b.c src/bootstrap_candidate_b_core.c \
		src/bootstrap_candidate_b.h src/bootstrap_candidate_b_core.h | build
	$(CH32_CC) $(CH32_CFLAGS) $(CH32_LDFLAGS) \
		size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b_core.c -lc -lgcc -o $@

build/ch32-candidate-b-strict.elf: size_candidate_b.c \
		src/bootstrap_candidate_b.c src/bootstrap_candidate_b_core.c \
		src/bootstrap_candidate_b.h src/bootstrap_candidate_b_core.h | build
	$(CH32_CC) $(CH32_CFLAGS) -DOEP_BOOTSTRAP_B_STRICT_PADDING \
		$(CH32_LDFLAGS) size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b_core.c -lc -lgcc -o $@

build/ch32-candidate-c.elf: size_candidate_c.c \
		src/bootstrap_candidate_c.c src/bootstrap_candidate_c.h | build
	$(CH32_CC) $(CH32_CFLAGS) $(CH32_LDFLAGS) \
		size_candidate_c.c src/bootstrap_candidate_c.c -lc -lgcc -o $@

ch32-size: build/ch32-candidate-b.elf build/ch32-candidate-b-strict.elf \
		build/ch32-candidate-c.elf
	$(CH32_SIZE) -A build/ch32-candidate-b.elf
	$(CH32_SIZE) -A build/ch32-candidate-b-strict.elf
	$(CH32_SIZE) -A build/ch32-candidate-c.elf
	$(CH32_NM) --print-size --size-sort --radix=d \
		build/ch32-candidate-b.elf | tail -n 8
	$(CH32_NM) --print-size --size-sort --radix=d \
		build/ch32-candidate-c.elf | tail -n 8

clean:
	rm -rf build
