AVR_CC ?= avr-gcc
AVR_SIZE ?= avr-size
AVR_NM ?= avr-nm

INCLUDES := -Isrc
AVR_CFLAGS := -std=c11 -mmcu=atmega328p -Os -Wall -Wextra -Werror \
	-ffunction-sections -fdata-sections
AVR_LDFLAGS := -mmcu=atmega328p -Wl,--gc-sections

.PHONY: avr-size clean

build:
	mkdir -p build

build/detect.elf: size_detect.c src/uart_frame.c src/uart_frame.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_detect.c src/uart_frame.c -o $@

build/stopwait.elf: size_stopwait.c src/uart_frame.c src/uart_stopwait.c \
		src/uart_frame.h src/uart_stopwait.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_stopwait.c src/uart_frame.c src/uart_stopwait.c -o $@

avr-size: build/detect.elf build/stopwait.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/detect.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/stopwait.elf
	$(AVR_NM) --print-size --size-sort --radix=d build/detect.elf | tail -n 12
	$(AVR_NM) --print-size --size-sort --radix=d build/stopwait.elf | tail -n 16

clean:
	rm -rf build
