"""The v1 draft fixtures on a probe, checked without the target taking part.

  uart + capture: uart TX on an unused pin, capture line 0 observing the same pin (an observer may share a
                  channel in the same plan); the host decodes the sampled bits and compares with what was sent
  gpio:           an unused pin switched between pull-up and pull-down, read with the lock-free read_bank

Default pins 20/21/22 are not wired to the X035 on the P4 jig (tests/manual/oep_smoke/targets.py lists the
wired ones). On the V003 jig every probe pin reaches the V003; use pins whose V003 side stays an input
(21 = PD6/RX, 22 = PD5/TX with USART1 off, 25 = PA1).

  usage: v1_fixture_check.py PORT [TX RX PULL]
"""
import struct
import sys
import time

from oep_client.v0 import codec
from oep_client.v1 import host, link, target

TX, RX, PULL = (int(a) for a in sys.argv[2:5]) if len(sys.argv) >= 5 else (20, 21, 22)
BAUD, RATE = 115200, 1_000_000       # a 50 ms window: over a 115200 bps link the write arrives a few ms after arm
SENT = b"\x55OEP\xa3"

h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=5000)
uart = target.find_all(h, "oep.fixture.uart")[0]
cap = target.find(h, "oep.fixture.capture")
gpio = target.find(h, "oep.fixture.gpio")
out = []

target.plan_apply(h, [(uart, 1, RX), (uart, 2, TX), (cap, 0, TX)])
h.request(uart, codec.FIXTURE_UART_OP_CONFIGURE, codec.FixtureUartConfigureRequest(baud=BAUD).pack())
r = codec.FixtureCaptureConfigureResult.unpack(h.request(
    cap, codec.FIXTURE_CAPTURE_OP_CONFIGURE, codec.FixtureCaptureConfigureRequest(sample_rate_hz=RATE, samples=50000).pack()).payload)
rate = r.actual_sample_rate_hz
h.request(cap, codec.FIXTURE_CAPTURE_OP_ARM, codec.FixtureCaptureArmRequest().pack())
h.request(uart, codec.FIXTURE_UART_OP_WRITE, codec.FixtureUartWriteRequest(data=SENT).pack())
for _ in range(100):
    st = codec.FixtureCaptureStatusResult.unpack(h.request(cap, codec.FIXTURE_CAPTURE_OP_STATUS,
                                                           codec.FixtureCaptureStatusRequest().pack(), locked=False).payload)
    if st.flags & 4:
        break
    time.sleep(0.01)
samples = b""
while len(samples) < st.samples:
    samples += codec.FixtureCaptureReadResult.unpack(h.request(
        cap, codec.FIXTURE_CAPTURE_OP_READ,
        codec.FixtureCaptureReadRequest(offset=len(samples), maximum=400).pack(), locked=False).payload).data

# decode 8N1 from line 0: find each start bit (a fall), sample the middle of each bit
bits = [s & 1 for s in samples]
per_bit = rate / BAUD
decoded, i = bytearray(), 1
while i < len(bits) - int(10 * per_bit):
    if bits[i - 1] == 1 and bits[i] == 0:
        value = 0
        for b in range(8):
            value |= bits[int(i + (1.5 + b) * per_bit)] << b
        decoded.append(value)
        i += int(9.5 * per_bit)
    else:
        i += 1
out.append(f"uart->capture at {rate} Hz: sent {SENT.hex()} decoded {bytes(decoded).hex()} match={bytes(decoded) == SENT}")
target.plan_release(h)

levels = []
reader = host.Host(h.send)                       # a second host with no session: read_bank is lock-free
for mode in (1, 2, 1):                           # pull-up, pull-down, pull-up
    h.request(gpio, codec.FIXTURE_GPIO_OP_CONFIGURE, codec.FixtureGpioConfigureRequest(channel=PULL, mode=mode).pack())
    time.sleep(0.01)
    bank = codec.FixtureGpioReadBankResult.unpack(reader.request(
        gpio, codec.FIXTURE_GPIO_OP_READ_BANK, codec.FixtureGpioReadBankRequest().pack(), locked=False).payload)
    levels.append((bank.values >> PULL) & 1)
h.request(gpio, codec.FIXTURE_GPIO_OP_CONFIGURE, codec.FixtureGpioConfigureRequest(channel=PULL, mode=0).pack())
out.append(f"gpio {PULL} pull-up/down/up read lock-free: {levels} (expect [1, 0, 1])")
h.end()
print("\n".join(out))
