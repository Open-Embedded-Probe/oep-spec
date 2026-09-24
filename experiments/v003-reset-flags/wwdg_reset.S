# CH32V003: reset through the window watchdog at once (counter written with T6 = 0) (RAM payload, rv32ec).
    .text
    .globl _start
_start:
    li   t0, 0x4002101c      # RCC_APB1PCENR
    lw   t1, 0(t0)
    li   t2, 0x800           # WWDGEN
    or   t1, t1, t2
    sw   t1, 0(t0)
    li   t0, 0x40002c00      # WWDG
    li   t1, 0xbf            # CTLR: WDGA | T = 0x3f (T6 = 0) -> reset now
    sw   t1, 0(t0)
1:  j    1b
