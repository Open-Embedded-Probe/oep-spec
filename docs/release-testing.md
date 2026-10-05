# Integration tests before a release: who owns what

[日本語](release-testing.ja.md)

Status: **guide** (not normative), **project-internal process**: how the OEP project's own repositories test a release on real hardware.
Someone implementing a probe or a host does not need it; what an implementation must do is in [conformance](conformance.md). Adopted by
the maintainers on 2026-10-01; the tests live in oep-client-python `tests/hw/`; facts found on real hardware added on 2026-10-02. This
English text is authoritative; the Japanese version is its translation.

It started as a proposal written from the maintainers' note of 2026-10-01. A test bench for the ecosystem built around the core
(ArduinoCore-CH32RV) exists. OEP can send firmware to a probe and test it without that core, so **testing the pair "Arduino firmware" and
"Python client" before a release is required**, and this page decides which repository holds the environment and the procedure.

## 1. How the responsibility is split

| What | Repository | Contents |
|---|---|---|
| The protocol's rules, its numbers, the ground on which the fake is a "working specification" | oep-spec | Documents, registry, generated files. No implementation |
| **The environment and procedure of the integration tests** | **oep-client-python** | Besides the tests against the fake (the existing pytest), **tests against real probes** (`tests/hw/`): get the firmware, flash it, run the client through everything. The port is chosen by board-identify's id |
| Building the firmware and its unit tests | oep-probe-arduino | A build per profile (CI), host tests, the release json. Tests on real hardware are left to oep-client-python; this repository holds none |
| JS client | oep-client-js | Tests against the fake. For real hardware it relies on the results of Python's `tests/hw/`, and only checks a browser by hand |
| The core's bench (jigs, fixture wiring) | ArduinoCore-CH32RV | Not a test of OEP but of something that uses OEP. Run after an OEP release, following it (as before) |

Why: a test on real hardware is three things, "flash the firmware", "run the client", "judge the result", and Python can flash (esptool,
picotool / uf2) and judge (oep_client). The firmware repository has only an Arduino build environment, and the knowledge of how a probe is
used is in the client.

## 2. How the firmware is obtained (oep-client-python `tests/hw/`)

Two ways, chosen by an environment variable:

| Way | Set | When |
|---|---|---|
| **Local build** | `OEP_PROBE_DIR=/path/to/oep-probe-arduino` (arduino-cli builds `examples/Firmware/OepProbe` per profile) | Before a release (testing main against main; today's development) |
| **Released version** | `OEP_PROBE_VERSION=0.0.25` (fetch `firmware-<ver>.json` and the images from the GitHub release, check their sha256) | When only the client changed, to reproduce, CI |

Either way, the firmware version before flashing (describe's firmware) and after flashing are recorded in the result.

## 3. What the test on real hardware covers (at least)

The boards are `OEP_HW_BOARDS` (a list of board-identify ids, for example `esp32-pico-d4-50029191fe34`). For each board:

1. Flash (esp32: esptool with merged.bin; rp2: a 1200 baud touch drops it into BOOTSEL and picotool sends the uf2 over PICOBOOT; P4: DFU
   with app.bin). Found on real hardware (2026-10-02):
   - **An RP2 cannot be flashed from WSL through the BOOTSEL drive (Mass Storage)** (the drive attaches to Windows). A 1200 baud touch +
     picotool (the PICOBOOT USB interface attached to WSL with usbipd) works.
   - **P4 DFU reads both the interface number and the transfer size from the descriptors** (the current firmware has interface 4 / 4096
     bytes, older versions 7 / 1024 bytes; hard-coding them breaks when the version changes).
   - **After flashing a firmware whose USB serial number differs, usbipd on Windows sees a different device** (the old `<unit>-hs` →
     unit_id). WSL does not see it until it is bound again as administrator. The second P4 ran into this. The procedure assumes the serial
     number may change after flashing and checks the binding.
2. Wait for the boot, then confirm / list / describe. The boot_id has changed, and the firmware string is the expected version.
3. probe.config: set / get / save / state / unset (disable included). What was saved can be read after a restart.
4. The wire (when a target is connected): scan, attach (with the reset TLV), and halt → read_block → resume (each block op on its own).
5. Fixtures: gpio set / read, uart configure / write / read (when a loopback is wired).
6. port_speed (UART bridge probes only): run the `linktest` matrix under the default conditions (the current speed and the candidate speeds,
   in / out / duplex, 1 and max in flight) and record the results. **First measure the same matrix (the same n) at the boot speed as the
   baseline**, and compare the candidates' broken and lost rates with it (a CH340 drops 1 to 3 % even at 115200, so absolute counts cannot
   decide). How to take the baseline and the thresholds: [host development
   guide](host-development-guide.md) §17.3.2 (a reference procedure; core §3.5 decides only the handshake).
7. Sessions: lease expiry, expired, force there and back.
8. The host's receiving limit on serial ports (CDC, USB-Serial/JTAG, UART bridge): `linktest` in, with the expected amount of outstanding
   answers (in flight × frame length) raised to the client's limit (6 KiB, the note of core §3.4), loses nothing (checks that Linux
   cdc_acm's 8 KiB is not reached).
9. read_block once with a count of exactly describe's max_length (the answer fits in max_frame and is not malformed; boards with a wire
   only).

The results are kept as JSON in `tests/hw/results/<board>-<firmware>-<client>.json`, and the release notes refer to them.

## 4. When to run it

- Before an oep-probe-arduino release: build the local main with `OEP_PROBE_DIR` and run on every board at hand.
- Before an oep-client-python release: run with the latest released firmware (`OEP_PROBE_VERSION`).
- If either fails, there is no release. The core's bench runs afterwards, following it.

## 5. To decide

1. Whether this split (Python owns the tests on real hardware) is right.
2. Which of the boards at hand (ATOM, the P4 jig, the V003 jig, Pro Micro RP2350) can always be used for OEP's tests before a release
   (the jigs are shared with the bench, so rules for when they are used).
3. Where the results go (committed to the repository, or attached to the release).
