# Layers of peripheral testing and probe functions

[日本語](peripheral-testing.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It divides the testing of MCU peripherals and the software that uses them by the layer at which it is done, and, for the layers an OEP probe takes on,
sorts out which tests can be done with which functions and which tests need functions not in the standard.

## 1. Layers

Outside the boundary of what is tested, put a stub (a stand-in for the counterpart) or a measuring instrument suited to the purpose. Where the boundary is cut decides the layer. They are listed from the inside out.

| Layer | Boundary | Counterpart and judgement | Examples |
|---|---|---|---|
| 1 Logic | The code under test runs without hardware | The counterpart is a software stub. The judgement is the record of calls the stub received | Run a library with a model of the device. Check the core's calculations (division, timing register values, pin assignment) on the host. Run an OEP host with a virtual probe |
| 2 Inside the DUT | Functions on the real device that do not appear on pins | No counterpart needed. The DUT's own checks, and the inside of the DUT read over the debug wire | DMA, interrupts, flash, CRC, cryptography, random numbers |
| 3 Observation | On the physical IF | A measuring instrument that only listens. Signal timing, frequency, whether the protocol is not broken | Logic analyzers and their analysis (OEP capture and wireskein), oscilloscopes, frequency counters |
| 4 Generic counterpart | Beyond the physical IF | A generic device becomes the stimulus and the counterpart (a stub on the wire). Switching the fixture's circuits is also here | The fixtures of OEP probes |
| 5 Dedicated counterpart | Beyond the physical IF | A device with dedicated hardware for that peripheral (controller, transceiver, PHY) and the counterpart's protocol stack | Boards with a USB controller, CAN nodes, PCs, PD testers |
| 6 The real thing | Beyond the physical IF | Real parts and equipment | Sensors, SD cards, LCDs, chargers |

- **Test at the innermost layer that can test it.** In outer layers, check only what cannot be checked inside (signals, time, connection with the real thing).
- **Set up stubs per purpose.** If what is tested changes, set up another stub even at the same boundary. Stubs and measuring instruments are checked by the tests of their
  respective implementations (conformance tests of models, conformance tests of probes).
- **Reduce layer 6.** Record the behaviour of the real thing and make it the content of the layer 1 stubs and the layer 4 counterparts. Keep in layer 6 only the check of the connection with representative parts and
  what cannot be made by layer 5.
- **Recording is preparation before the test, not the test.** Record once at layer 5 or layer 6, analyze it, and make it the content or behaviour of the stub
  (answer values, time to answer, SD images).
- **The border between layer 4 and layer 5**: layer 4 is a counterpart a generic device can make at the level of wires. Layer 5 is a counterpart that needs dedicated peripherals, physical layers or the counterpart's protocol stack.
  A probe with dedicated peripherals may become a layer 5 counterpart with an extension under its own name (core §12), but that is kept apart from the standard generic functions.

## 2. Peripherals and layers

As an example, MCU peripherals are listed by layer. Layer 1 is the testing of libraries that use the peripheral, so it exists for every peripheral (omitted from the table).
The peripheral names are examples; their presence and names differ by family (in parentheses, examples of peripherals of that kind).

| Peripheral | 2 Inside the DUT | 3 Observation | 4 Generic counterpart | 5 Dedicated counterpart | 6 The real thing |
|---|---|---|---|---|---|
| CPU, interrupts, SysTick, DMA, memory | Self-checks, the debug wire | Interrupt and DMA timing (brought out on a pin) | Interrupt stimuli | — | — |
| Multicore (FIFOs between cores, spinlocks, interpolators) | Handover, exclusion | Per-core timing (brought out on a pin) | — | — | — |
| Event wiring (ETM, chained timer triggers, DMA requests) | Connection settings | Delay from the event to the pin | Event stimuli | — | — |
| Coprocessors, low-power cores (ULP, LP core) | Shared memory, wake conditions | Time to wake | Wake stimuli (pins, touch) | — | — |
| flash, option bytes, EEPROM emulation | Writing, erasing, protection | — | Power loss during writing | — | — |
| External memory (flash XIP, PSRAM) | Reads and writes, cache | Bus timing | — | — | flash and PSRAM parts |
| CRC, cryptography (AES, SHA, RSA, ECC, HMAC), random numbers | Known values, statistics | — | — | — | — |
| Security (eFuse, OTP, secure boot, flash encryption, glitch detection) | Write-once values, signature verification | — | Power glitches (hard) | — | — |
| Boot (strapping pins, bootloader, USB programming mode) | Boot reason | Boot time, bootloader output | Setting strapping pins, reset | PC (USB programming) | — |
| Clock, RTC | PLL settings | Frequency of MCO and RTC output | Feeding and stopping an external clock | — | Crystal |
| Reset, power, low power, wake conditions | Reset reason | Boot and wake times | Reset pin, wake pin, power, current | — | — |
| GPIO, external interrupts | — | Level, switching speed | Levels, pulse trains | — | Buttons, LEDs |
| Timers, PWM (general-purpose timers, LED PWM, motor control PWM: complementary, dead time, brake) | Connections between timers | Frequency, duty, phase, dead time | Brake input | — | Motors, servos |
| Input measurement (input capture, pulse counting, quadrature encoder) | — | — | Pulse trains, 2 phases | — | Encoders |
| Programmable I/O (PIO, RMT, PARLIO, PIOC, parallel modes of I2S and LCD) | The logic of state machine instructions | The waveforms it outputs (protocols it makes) | Stimuli and counterparts for the receiving side | — | — |
| ADC, DAC, comparators, op amps, internal sensors (temperature, Hall) | Internal channels | DAC and comparator outputs | Voltages, waveforms | — | Sensors |
| Touch | Measured values | — | Capacitance of the fixture | — | Electrodes |
| UART (synchronous, IrDA, LIN, RS-485, smart card, low-power UART) | — | baud, format, protocol | Sending and receiving, break, errors | — | GPS, modems |
| I2C, SMBus, I3C | — | Timing, protocol | target, controller, faults (none for I3C) | — | Sensors, EEPROM |
| SPI, QSPI, OSPI | — | mode, timing | target, controller, answers | — | flash, displays |
| SD, SDIO (host, and the DUT as SDIO slave), eMMC | — | Timing, command sequences | An answering counterpart (FAT image), SDIO host | — | SD cards |
| I2S, SAI, PDM | — | Format, sample rate | An answering counterpart | — | Codecs, microphones |
| Single-wire (RGB LED, 1-Wire, IR) | — | Bit timing | Patterns, an answering counterpart | — | LEDs, temperature sensors, receiver modules |
| Parallel buses, video (FSMC / FMC, parallel LCD, DVP, RGB LCD, HSTX) | — | Bus timing (fast ones are hard) | An answering counterpart, fast patterns | — | SRAM, SDRAM, LCD, cameras |
| MIPI DSI / CSI | — | — | — | Receiving and sending sides of displays and cameras | Displays, cameras |
| CAN, CAN FD | — | Bit timing (loopback) | — | CAN nodes | Real equipment |
| USB (device, host, OTG, built-in serial and JTAG) | — | Part of the low-speed and FS signals | VBUS, ID pin | Boards with a USB controller, PCs | Real USB devices |
| USB PD, Type-C | — | CC waveforms | — | PD testers, PD power supplies | Chargers |
| Ethernet | — | RMII signals | — | PCs, switches | LAN |
| Wireless (Wi-Fi, Bluetooth, IEEE 802.15.4) | — | — | — | A counterpart radio (another board of the same family and so on) | APs, smartphones |
| Programming and debug (SWD, SDI, JTAG, ISP) | — | Wire timing | Debug wires, boot pins, ISP UART | Another debugger | — |

### 2.1 Parts on the testing side

The same peripherals, on the testing side (the probe), become the parts that make layer 3 and layer 4 functions. A probe maker chooses from the chip's peripherals as follows.

| OEP function | Examples of parts that make it |
|---|---|
| Logic capture | Parallel input (PARLIO receive, the camera mode of LCD and camera peripherals, the parallel mode of I2S), PIO, interrupts that read GPIO |
| Edge count and frequency | Pulse counting (PCNT, the counting input of PWM slices), the external clock of timers |
| Analog capture | ADC and DMA |
| PWM output | LED PWM, motor control PWM (phase, complementary, dead time), timers |
| Pattern output | RMT send, PARLIO send, parallel output of I2S and LCD, PIO, HSTX |
| Analog output | DAC. On chips without one, PWM and an RC filter, or an external DAC on the fixture |
| UART, I2C, SPI counterparts | Hardware peripherals, PIO |
| An answering counterpart | PIO (can react per byte or bit), an SPI slave that does not prefetch the data to send |
| Dedicated counterparts (layer 5) | USB OTG, CAN controllers and transceivers, wireless, Ethernet MACs |

## 3. Layers OEP takes on

An OEP probe takes on layer 3 observation and layer 4 generic counterparts. In layer 2, it reads the inside of the DUT over the debug wire (`oep.target.riscv-dm`,
`oep.target.arm-adi`).

- **Layer 3**: logic capture (`oep.fixture.logic`), analog capture (`oep.fixture.analog`), edge count and frequency (`oep.fixture.counter`).
  Logic capture and edge counting only listen, so they can share pins with other functions (capture pin sharing, core §8.1).
  They can be used at the same time as layer 4 counterparts. Reading protocols is the job of analyzers (wireskein and so on); capture is the same for every protocol.
- **Layer 4**: the standard interfaces below become the stimuli and counterparts. A test decides first what is sent and what comes back.

### 3.1 Standard stimuli and counterparts

| Interface | What it can do as a stimulus or counterpart | What it cannot do |
|---|---|---|
| `oep.fixture.gpio` | Output levels, pulls, open drain. Read DUT pins | Output at decided times (the order within one request is kept, but the time between is not decided) |
| `oep.fixture.pwm` | Keep outputting a square wave with decided frequency and duty | Phase between outputs, a decided number of pulses, single pulses |
| `oep.fixture.dac` | Set an analog value | Waveforms that change over time |
| `oep.fixture.uart` | Send and receive with decided baud (within ±5% of the request) and format (data length, parity, stop bits) | break, 9 bits, half duplex on one wire, flow control lines |
| `oep.fixture.i2c-target`, `oep.fixture.spi-target` | The counterpart when the DUT is the master. Answers placed beforehand, records of what was received, the same stretch on every byte, NACK from the n-th data byte of I2C (nack_from) | The "none" entries of §7 and §8 |
| `oep.fixture.i2c-controller`, `oep.fixture.spi-controller` | The counterpart when the DUT is the slave. SPI sends with specified CS timing | The "none" entries of §7 and §8 |
| `oep.fixture.capture-group` | A probe with event sources outputs one pulse on an event (trigger_out) | Trains of pulses after it |

### 3.2 Functions not in the standard

Things needed for layer 4 tests but not in the standard. Listed in decreasing order of how widely they apply across peripherals.

| Function | Content | Main peripherals it serves |
|---|---|---|
| Pattern output | Output timed sequences of levels on several pins. Can also repeat, or start on an event | IR reception, encoders, a decided number of pulses, single pulse widths, contact bounce, UART break, LIN, bursts of interrupts |
| I2C NACK and stretch specification | NACK the address k times, which byte to stretch and by how much, hold SDA low and release it after SCL comes k times | I2C |
| SPI answer sequences | For back-to-back transfers, line up beforehand a different answer per transfer | SPI |
| Analog waveforms | Change the DAC value over time (sequences, repetition) | Continuous ADC conversion, DMA, comparator response |
| An answering counterpart | Follow the DUT's lines and answer according to what was received, within the time the DUT waits (§3.3) | SD, SPI flash, FSMC, 1-Wire, I2S, I2C arbitration and bus errors |
| Power | Turn the DUT's power on and off, change the voltage. Measure current | Boot, brown-out detection, low-power modes, power loss during writing |
| Master extensions | In I2C, send with specified timing, cut off midway. In SPI, cut off midway, put a weak pull on MISO | I2C, SPI slave |
| Address and line extensions | 10 bit addresses, general call, 3-wire SPI, several counterparts on one SPI bus | I2C, SPI |
| Fast pattern output | Keep outputting fast data on clock and data lines | The input side of DVP and RGB LCD |

### 3.3 Timing of an answering counterpart

An answering counterpart that answers according to what it received is decided by whether it can prepare the answer within the time the DUT waits. The content of answers (SD images, flash contents) is
held beforehand. For things with long waits, the content may be fetched from the host.

| Counterpart | Time the DUT waits |
|---|---|
| SD card (SPI mode) | The command answer within 0 to 8 bytes (NCR). For read data, it can return 0xFF before the data token (0xFE) and make the DUT wait up to the read time limit. After a write it can return busy (0x00) to make it wait |
| SD card (SD bus mode) | The command answer within 2 to 64 clocks. Data can be made to wait as in SPI mode. The CRC is attached on the spot |
| SPI flash | ID and status can be set beforehand. A read without wait starts from the bit after the last bit of the address. fast read by the amount of dummy clocks |
| QSPI memory-mapped | Dummy clocks (depending on the DUT's settings) |
| FSMC / FMC asynchronous SRAM | The data phase (depending on the DUT's settings) |
| 1-Wire slave | From the master pulling the line low until the master reads (about 15 µs) |
| I2S counterpart | One bit of BCLK |
| I2C arbitration, START or STOP midway | Within a bit (100 ns or less at 1 MHz) |

For things where the wait is in units of bits or bytes, software is often too late, and a mechanism that runs with hardware-decided timing is needed.
For things where the DUT's settings can lengthen the wait (dummy clocks, data phase, slow clocks), those settings widen the range that can be tested.

## 4. Tests per peripheral (layers 3 and 4)

The "Layer" in the tables below is one of 3 (observation only), 4 (generic counterpart: a standard interface, or a function not in the standard from §3.2), 5, 6, or hard (§15).

## 5. GPIO and external interrupts

| Test | Judgement | Layer |
|---|---|---|
| Output level, modes (push-pull, open drain) | Capture, read with gpio | 3 (open drain is 4: gpio pull-up) |
| Reading inputs, pulls | The DUT's report | 4: gpio |
| Output switching speed | Capture | 3 |
| Kinds of interrupt edges and delay | Capture (between the stimulus edge and the pin the DUT returns) | 4: pwm or gpio |
| Missed fast interrupts | The count the DUT counted, and counter | 4: pwm. A decided number is pattern output (none) |
| Debouncing | The DUT's report | 4: pattern output (none) |
| Output strength, slew rate, input voltage tolerance | Voltage | Hard |

## 6. Time, clocks, reset, power

| Test | Judgement | Layer |
|---|---|---|
| Accuracy of millis, micros, delay | Capture, counter (the DUT toggles a pin) | 3 |
| Clock output (MCO), RTC frequency | counter | 3 |
| Running on an external clock, switching over when the external clock stops | The DUT's report, capture | 4: pwm (output as the DUT's clock, and stop it) |
| Reset pin, reset reason | The DUT's report, the debug wire | 4: gpio |
| Watchdog time | Capture (from the DUT's pin stopping until restart) | 3 |
| Waking from sleep by a pin, and its delay | Capture | 4: gpio or pwm |
| Booting by how power is applied, brown-out detection, power loss during writing | The DUT's report, capture | 4: power (none) |
| Current in low-power modes | Current | 4: power (none) |

Time judgements are based on the probe's clock, so errors finer than its accuracy cannot be judged.

## 7. I2C

When the DUT is the master, the counterpart is i2c-target. An I2C master does not output data unless an ACK comes back for the address, so even observing data needs a counterpart that returns ACK.
Judging by capture is fine (the ACK / NACK the master returned for each read byte is also visible).

| Test | Judgement | Layer |
|---|---|---|
| The address byte, handling when there is no counterpart (return value and STOP) | Capture, the DUT's return value | 3 |
| Timing (tLOW, tHIGH, tSU;STA, tHD;STA, tSU;DAT, tHD;DAT, tSU;STO, tBUF) and frequency | Capture | 3 (with 4: i2c-target returning ACK) |
| Writes, reads, distinguishing repeated START from STOP, the NACK at the end of a read | Capture, the counterpart's record | 4: i2c-target |
| Waiting for stretch | Capture | 4: stretch of i2c-target |
| Stretch beyond the timeout, SCL stuck, SMBus timeout | The DUT's return value, and the next transfer | 4: stretch, or hold the line with gpio |
| Not starting while another master uses the bus | Capture | 4: hold the bus with i2c-controller |
| Whether it outputs clocks and STOP when SDA is stuck | Capture | 4: hold SDA with gpio |
| Whether it can recover from SDA stuck | The DUT's return value, capture | 4: release after SCL comes k times (none) |
| SMBus PEC | The DUT's judgement | 4: i2c-target (the PEC is also placed as a byte) |
| NACK from the n-th data byte | The DUT's return value, capture | 4: nack_from of i2c-target |
| ACK polling (NACK to the address) | The DUT's return value, capture | 4: NACK (none) |
| Stretching only on a particular byte | Capture | 4: stretch specification (none) |
| 10 bit addresses, general call | Capture, the counterpart's record | 4: address extensions (none) |
| Arbitration, START or STOP midway (bus errors) | The DUT's return value | 4: an answering counterpart (none, §3.3) |
| Glitch filter (spikes of 50 ns or less) | The DUT's return value | Hard |
| Rise time, whether open drain is kept | Voltage | Hard |

When the DUT is the slave, i2c-controller is the counterpart. The probe outputs the clock, so cutting off midway and specifying timing can be done with the probe's own timing.

| Test | Judgement | Layer |
|---|---|---|
| Reception, answers, writing then reading with repeated START, being read more than the DUT holds | The counterpart's result, the DUT's report | 4: i2c-controller |
| Length of the DUT's stretch | Capture | 4: i2c-controller |
| NACK when the address does not match, general call | The counterpart's result | 4: i2c-controller (can also send reserved addresses) |
| The highest clock the DUT can receive | The counterpart's result | 4: i2c-controller (up to the probe's max_clock_hz) |
| Whether it can receive when sent at the lower-limit times of the standard | The counterpart's result, capture | 4: timing specification (none) |
| The master vanishing mid-byte, a START midway | The DUT's report, the next transfer | 4: cutting off midway (none) |
| 10 bit addresses, several addresses | The counterpart's result | 4: address extensions (none) |

## 8. SPI

An SPI master moves the lines even without a counterpart, so tests of what the master outputs can be done at layer 3.

| Test | Judgement | Layer |
|---|---|---|
| mode (CPOL and CPHA) | Capture: the SCK level before CS becomes active, and the edge on which MOSI changes | 3 |
| SCK when the mode changes | Capture: whether SCK has settled at the new level before CS becomes active | 3 |
| MOSI values, bit order, byte order of 16 / 32 bit words | Capture | 3 |
| Clock frequency | Capture. counter for those faster than capture | 3 |
| CS timing, hardware CS (including per-word pulses), gaps in DMA transfers, the clock count of receive-only mode | Capture | 3 |
| Receiving MISO, whether a wrong CRC is detected | The DUT's report | 4: spi-target (the CRC is also placed as bytes) |
| MISO of long transfers | The DUT's report | 4: spi-target (the length depends on the probe's declaration) |
| MISO of back-to-back transfers | The DUT's report | 4: answer sequences (none) |
| Reading SPI flash, QSPI memory-mapped | The DUT's report | 4: an answering counterpart (none, §3.3) |
| 3-wire, several devices on a shared bus | Capture, the DUT's report | 4: line extensions (none) |
| Margin at the point MISO is captured | The DUT's report | Hard |

From the data the counterpart received, mode 0 and 3, and mode 1 and 2, cannot be told apart (the edge on which data is captured is the same). The mode is judged by capture.

When the DUT is the slave, spi-controller is the counterpart.

| Test | Judgement | Layer |
|---|---|---|
| The values the DUT received, the MISO it outputs, mode, bit order | The counterpart's record, capture | 4: spi-controller |
| The lower limit of setup time from CS to the first bit, the minimum time between transfers, overrun | The counterpart's record, the DUT's report | 4: spi-controller (varying setup_ns and gap_ns) |
| The highest clock the DUT can receive | The counterpart's record | 4: spi-controller (up to the probe's max_clock_hz) |
| Whether MISO is released while CS is inactive | Capture, voltage | 4: put a weak pull on MISO (none) |
| Cutting CS mid-byte, 3-wire | The DUT's report | 4: master extensions (none) |

## 9. UART

| Test | Judgement | Layer |
|---|---|---|
| baud accuracy, format, gaps in DMA on the sending side | Capture | 3 |
| The direction line of RS-485 sending (DE), RTS | Capture | 3 |
| Values and format on the receiving side, long reception and receive overflow | The DUT's report | 4: uart |
| Whether it can receive a sender with a shifted baud | The DUT's report | 4: uart (ask for a shifted baud within ±5%) |
| Whether parity errors and framing errors are detected | The DUT's report | 4: uart (send in a format different from the DUT's) |
| Automatic baud detection | The DUT's report | 4: uart |
| CTS | The DUT's report | 4: gpio. Timed switching is pattern output (none) |
| Receiving in synchronous mode (with a clock) | The DUT's report | 4: spi-controller (with LSB first it becomes a synchronous sender) |
| break, LIN break and sync, DMX | The DUT's report | 4: pattern output (none) |
| 9 bits, multiprocessor addresses, half duplex on one wire | The DUT's report | 4: uart extensions (none) |
| IrDA | Capture (sending side), the DUT's report (receiving side) | 3; the receiving side is 4: pattern output (none) |

## 10. PWM and timers

| Test | Judgement | Layer |
|---|---|---|
| Frequency, duty, resolution, polarity | Capture, counter | 3 |
| Glitches when settings change and when stopped | Capture | 3 |
| Phase between outputs, center alignment, complementary outputs and dead time | Capture | 3 (dead time in ns is hard) |
| One pulse, a decided number of pulses, servos, tone | Capture | 3 |
| How fast the brake input stops the outputs | Capture | 4: gpio or pwm |
| Measuring frequency and duty, PWM input mode | The DUT's report | 4: pwm |
| Counting on an external clock | The DUT's report and counter | 4: pwm. A decided number is pattern output (none) |
| Single pulse widths (input capture) | The DUT's report | 4: pattern output (none). pwm for continuously repeated widths |
| Encoders (2 phases 90° apart, reversing direction) | The DUT's report | 4: pattern output (none) |
| Input filters | The DUT's report | 4: pattern output (none). ns units are hard |

## 11. ADC, DAC, comparators, op amps

| Test | Judgement | Layer |
|---|---|---|
| Values and waveforms of the DUT's DAC | Analog capture | 3 (rise speed within the bandwidth of capture) |
| ADC values (offset, gain, linearity) | The DUT's report, and the actual voltage measured by analog capture | 4: dac (needs a dac with finer resolution than the DUT's ADC) |
| Switching channels, internal channels (reference voltage, temperature) | The DUT's report | 4: dac; internal channels are 2 |
| Conversion on an external trigger | The DUT's report, capture | 4: pwm |
| Continuous conversion, DMA, conversion speed | The DUT's report | 4: analog waveforms (none) |
| Input impedance and sampling time | The DUT's report | 4: fixture (a circuit that switches the source resistance) |
| Comparator threshold and hysteresis, op amp gain | Capture (the DUT's output) | 4: dac |
| Comparator response speed | Capture | 4: analog waveforms (none) |
| Touch keys | The DUT's report | 4: fixture (a circuit that switches capacitance) |

## 12. Single-wire protocols, I2S, parallel buses

| Test | Judgement | Layer |
|---|---|---|
| Bit timing and reset time of RGB LEDs (WS2812 and so on) | Capture | 3 |
| IR sending (modulation frequency and duty, codes such as NEC) | Capture, counter | 3 |
| IR reception (receiving the output of a receiver module) | The DUT's report | 4: pattern output (none) |
| 1-Wire reset pulse, master write slots | Capture | 3 |
| 1-Wire presence pulse, reads, ROM search | The DUT's report, capture | 4: an answering counterpart (none, §3.3) |
| I2S sent with the DUT as master (BCLK, WS, data, format, sample rate) | Capture | 3 |
| I2S received with the DUT as master, the DUT as slave | The DUT's report | 4: an answering counterpart (none) |
| Parallel LCD bus (the DUT outputs) | Capture (needs as many channels as lines) | 3 |
| FSMC / FMC SRAM | The DUT's report | 4: an answering counterpart (none, §3.3) |
| DVP (camera input) | The DUT's report | 4: fast pattern output (none) |

## 13. SD, SDIO

| Test | Judgement | Layer |
|---|---|---|
| Initialization and command sequence, clock switching | Capture | 3 (with 4: an answering counterpart that answers the commands) |
| Block reads and writes, FAT file operations | The DUT's report | 4: an answering counterpart (none, §3.3). The content is held as a FAT image |
| Write busy, read wait | The DUT's report, capture | 4: an answering counterpart (none) |

## 14. Peripherals that need a dedicated counterpart (layer 5)

There are signals that can be seen at layer 3, but the counterpart needs dedicated hardware and a protocol stack.

| Peripheral | What can be seen at layer 3 | Examples of layer 5 counterparts |
|---|---|---|
| CAN, CAN FD | Bit timing and frames on the TX pin in the DUT's loopback or listen-only mode | A node with a CAN controller and transceiver |
| USB (device, host, OTG) | Part of the low-speed and FS signals, VBUS and ID lines | Boards with a USB controller, PCs |
| USB PD, Type-C | CC waveforms | PD testers, PD power supplies |
| Ethernet | RMII signals | PCs, switches |
| Wireless | — | A counterpart radio |

LIN and RS-485 can be tested at layer 4 by connecting the transceiver as a fixture to the layer 4 uart.

## 15. Things that are hard in principle

Things that are hard whatever layer's equipment is used. Answering counterparts that answer according to what they received can be made depending on the time the DUT waits, so they are not included here (§3.3).

1. **Timing in ns** (SPI capture margin, dead time, filters that ignore spikes of 50 ns or less).
   - Both the sending side and the measuring side need a resolution of a few ns.
2. **Electrical matters** (output strength, slew rate, rise time, voltage tolerance).
   - They can be measured only within the bandwidth of analog capture.
