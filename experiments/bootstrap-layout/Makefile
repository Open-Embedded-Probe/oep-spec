AVR_CC ?= avr-gcc
AVR_SIZE ?= avr-size
AVR_NM ?= avr-nm

AVR_CFLAGS := -std=c11 -mmcu=atmega328p -Os -Wall -Wextra -Werror \
	-ffunction-sections -fdata-sections -Isrc
AVR_LDFLAGS := -mmcu=atmega328p -Wl,--gc-sections

.PHONY: avr-size clean

build:
	mkdir -p build

build/candidate-b.elf: size_candidate_b.c src/bootstrap_candidate_b.c \
		src/bootstrap_candidate_b.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(AVR_LDFLAGS) \
		size_candidate_b.c src/bootstrap_candidate_b.c -o $@

build/candidate-c.elf: size_candidate_c.c src/bootstrap_candidate_c.c \
		src/bootstrap_candidate_c.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(AVR_LDFLAGS) \
		size_candidate_c.c src/bootstrap_candidate_c.c -o $@

avr-size: build/candidate-b.elf build/candidate-c.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/candidate-b.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/candidate-c.elf
	$(AVR_NM) --print-size --size-sort --radix=d build/candidate-b.elf | tail -n 8
	$(AVR_NM) --print-size --size-sort --radix=d build/candidate-c.elf | tail -n 8

clean:
	rm -rf build
