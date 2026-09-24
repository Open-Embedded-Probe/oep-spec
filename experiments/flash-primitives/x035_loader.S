# CH32X035 RAM flash loader for experiment F4 (2026-09-24). Position independent.
# in:  a0 = flash page address (256-byte aligned), a1 = source buffer in RAM (256 bytes)
# out: a0 = 0 on success, else STATR | 0x80000000; stops on ebreak (ok / fail).
# The flash must already be unlocked (KEYR + MODEKEYR). Same controller sequence as the
# v0 probe (OepCh32Dm::flashErasePage / flashProgramPage), run by the target's own CPU.
    .option norvc
    .text
    .globl _start
_start:
    lui   t0, 0x40022          # FLASH registers
    li    t1, 0x20000          # FTER
    sw    t1, 0x10(t0)         # CTLR = FTER
    sw    a0, 0x14(t0)         # ADDR = page
    ori   t1, t1, 0x40         # FTER | STRT
    sw    t1, 0x10(t0)
1:  lw    t2, 0x0c(t0)         # STATR
    andi  t3, t2, 1
    bnez  t3, 1b
    andi  t3, t2, 0x10         # WRPRTERR
    bnez  t3, fail
    sw    zero, 0x10(t0)

    li    t1, 0x10000          # FTPG
    sw    t1, 0x10(t0)
    li    t4, 0x80000          # BUFRST
    or    t4, t4, t1
    sw    t4, 0x10(t0)
2:  lw    t2, 0x0c(t0)
    andi  t3, t2, 1
    bnez  t3, 2b

    li    t4, 0x40000          # BUFLOAD
    or    t4, t4, t1
    mv    t5, a0
    addi  t6, a0, 256
3:  lw    t2, 0(a1)
    sw    t2, 0(t5)
    sw    t4, 0x10(t0)         # CTLR = FTPG | BUFLOAD
4:  lw    t2, 0x0c(t0)
    andi  t3, t2, 1
    bnez  t3, 4b
    addi  a1, a1, 4
    addi  t5, t5, 4
    bne   t5, t6, 3b

    sw    t1, 0x10(t0)         # CTLR = FTPG
    sw    a0, 0x14(t0)         # ADDR = page
    ori   t4, t1, 0x40         # FTPG | STRT
    sw    t4, 0x10(t0)
5:  lw    t2, 0x0c(t0)
    andi  t3, t2, 1
    bnez  t3, 5b
    andi  t3, t2, 0x10
    bnez  t3, fail
    sw    zero, 0x10(t0)
    li    a0, 0
    .globl done_ok
done_ok:
    ebreak
fail:
    sw    zero, 0x10(t0)
    li    a0, 0x80000000
    or    a0, a0, t2
    .globl done_fail
done_fail:
    ebreak
