AVR_CC ?= avr-gcc
AVR_SIZE ?= avr-size
AVR_NM ?= avr-nm

INCLUDES := -Isrc
AVR_CFLAGS := -std=c11 -mmcu=atmega328p -Os -Wall -Wextra -Werror \
	-ffunction-sections -fdata-sections
AVR_LDFLAGS := -mmcu=atmega328p -Wl,--gc-sections
PAYLOAD_SIZES := 8 16 32 64 128
PAYLOAD_ELFS := $(foreach size,$(PAYLOAD_SIZES),build/payload-$(size).elf)

.PHONY: avr-size avr-stack avr-payload-sizes clean

build:
	mkdir -p build

build/detect.elf: size_detect.c src/uart_frame.c src/uart_frame.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_detect.c src/uart_frame.c -o $@

build/derived.elf: size_derived.c \
		src/alternatives/derived_length_frame.c \
		src/alternatives/derived_length_frame.h src/uart_frame.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_derived.c src/alternatives/derived_length_frame.c -o $@

build/slip.elf: size_slip.c src/alternatives/slip_frame.c \
		src/alternatives/slip_frame.h src/uart_frame.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_slip.c src/alternatives/slip_frame.c -o $@

build/stopwait.elf: size_stopwait.c src/alternatives/derived_length_frame.c \
		src/uart_stopwait.c src/alternatives/derived_length_frame.h \
		src/uart_frame.h src/uart_stopwait.h | build
	$(AVR_CC) $(AVR_CFLAGS) $(INCLUDES) $(AVR_LDFLAGS) \
		size_stopwait.c src/alternatives/derived_length_frame.c \
		src/uart_stopwait.c -o $@

build/payload-%.elf: size_payload.c \
		src/alternatives/derived_length_frame.c src/uart_stopwait.c \
		src/alternatives/derived_length_frame.h src/uart_frame.h \
		src/uart_stopwait.h | build
	$(AVR_CC) $(AVR_CFLAGS) -DOEP_UART_MAX_PAYLOAD=$*u \
		$(INCLUDES) $(AVR_LDFLAGS) size_payload.c \
		src/alternatives/derived_length_frame.c src/uart_stopwait.c -o $@

avr-size: build/detect.elf build/derived.elf build/slip.elf build/stopwait.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/detect.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/derived.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/slip.elf
	$(AVR_SIZE) -C --mcu=atmega328p build/stopwait.elf
	$(AVR_NM) --print-size --size-sort --radix=d build/detect.elf | tail -n 12
	$(AVR_NM) --print-size --size-sort --radix=d build/derived.elf | tail -n 12
	$(AVR_NM) --print-size --size-sort --radix=d build/slip.elf | tail -n 12
	$(AVR_NM) --print-size --size-sort --radix=d build/stopwait.elf | tail -n 16

avr-stack: | build
	cd build && $(AVR_CC) $(AVR_CFLAGS) -fstack-usage -I../src $(AVR_LDFLAGS) \
		../size_stopwait.c ../src/alternatives/derived_length_frame.c \
		../src/uart_stopwait.c -o stopwait-stack.elf
	@sed -n '1,240p' build/*.su

avr-payload-sizes: $(PAYLOAD_ELFS)
	@for size in $(PAYLOAD_SIZES); do \
		echo "payload $$size bytes"; \
		$(AVR_SIZE) -C --mcu=atmega328p build/payload-$$size.elf; \
		$(AVR_NM) --print-size --radix=d build/payload-$$size.elf | \
			awk '$$4 == "link" { print "stopwait state:", $$2, "bytes" }'; \
	done

clean:
	rm -rf build
