# CH32V003: start the independent watchdog with a ~3 ms timeout and wait for it (RAM payload, rv32ec).
    .text
    .globl _start
_start:
    li   t0, 0x40003000      # IWDG
    li   t1, 0x5555
    sw   t1, 0(t0)           # CTLR: unlock PSCR / RLDR
    sw   zero, 4(t0)         # PSCR = 0: LSI / 4
    li   t1, 100
    sw   t1, 8(t0)           # RLDR = 100 (~3 ms)
    li   t1, 0xcccc
    sw   t1, 0(t0)           # CTLR: start (LSI on by hardware)
1:  j    1b
