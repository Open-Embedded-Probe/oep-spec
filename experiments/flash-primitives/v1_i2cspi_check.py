"""Plumbing of the vendor I2C/SPI targets on a v1 probe: plan, configure, lock-free status, release."""
import sys
from oep_client.v0 import codec
from oep_client.v1 import host, link, target
pins = [int(x) for x in sys.argv[2:6]]
h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=5000)
i2c = target.find(h, "io.github.ch32-riscv-ug.esp32.i2c-target")
spi = target.find(h, "io.github.ch32-riscv-ug.esp32.spi-target")
reader = host.Host(h.send)
target.plan_apply(h, [(i2c, 1, pins[0]), (i2c, 2, pins[1])])
h.request(i2c, codec.P4_I2C_TARGET_OP_CONFIGURE, codec.P4I2CTargetConfigureRequest(address=0x42, mode=1).pack())
st = codec.P4I2CTargetStatusResult.unpack(reader.request(i2c, codec.P4_I2C_TARGET_OP_STATUS, codec.P4I2CTargetStatusRequest().pack(), locked=False).payload)
print("i2c status (lock-free):", st)
target.plan_release(h)
target.plan_apply(h, [(spi, 1, pins[0]), (spi, 2, pins[1]), (spi, 3, pins[2]), (spi, 4, pins[3])])
h.request(spi, codec.P4_SPI_TARGET_OP_CONFIGURE, codec.P4SpiTargetConfigureRequest(mode=0, bit_order=0).pack())
st = codec.P4SpiTargetStatusResult.unpack(reader.request(spi, codec.P4_SPI_TARGET_OP_STATUS, codec.P4SpiTargetStatusRequest().pack(), locked=False).payload)
print("spi status (lock-free):", st)
target.plan_release(h)
h.end()
