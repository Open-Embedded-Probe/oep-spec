import struct, sys, time
from pathlib import Path
from oep_client.v0 import codec
from oep_client.v1 import host, link, target, uiapduino
h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=20000)
wire = target.Wire(h, "oep.wire.swio")
gpio = target.find(h, "oep.fixture.gpio")
def level23():
    b = codec.FixtureGpioReadBankResult.unpack(h.request(gpio, codec.FIXTURE_GPIO_OP_READ_BANK, codec.FixtureGpioReadBankRequest().pack(), locked=False).payload)
    return (b.values >> 23) & 1
print("PD7 as seen by the probe, app running:", level23())
data = Path(sys.argv[2]).read_bytes(); data += b"\0" * (-len(data) % 4)
uiapduino.run_payload(h, wire, list(struct.unpack(f"<{len(data)//4}I", data)))
time.sleep(0.2)
print("PD7 while the payload drives it low:", level23())
conn, _ = wire.attach(halt=True)
dm = target.RiscvDm(h, conn)
print("GPIOD CFGLR / OUTDR / INDR:", [hex(dm.read32(a)) for a in (0x40011400, 0x4001140C, 0x40011408)])
print("reset:", dm.reset(confirm=True))
wire.detach(conn)
print("PD7 after the reset:", level23())
h.end()
