# CH32V003: the target drives its own PD7 (the NRST pad) low as a GPIO output (RAM payload, rv32ec).
# Question: with the reset function still enabled, does this reset the chip as a pin reset (PINRSTF)?
    .text
    .globl _start
_start:
    li   t0, 0x40021018      # RCC_APB2PCENR
    lw   t1, 0(t0)
    ori  t1, t1, 0x20        # IOPDEN
    sw   t1, 0(t0)
    li   t0, 0x40011400      # GPIOD
    lw   t1, 0(t0)           # CFGLR
    li   t2, 0x0fffffff
    and  t1, t1, t2
    li   t2, 0x10000000      # PD7: MODE 01 (output 10 MHz), CNF 00 (push-pull)
    or   t1, t1, t2
    sw   t1, 0(t0)
    li   t1, 0x80
    sw   t1, 0x14(t0)        # BCR: PD7 low
1:  j    1b
