# Shared wire vectors

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

This directory holds JSON vectors that host / probe implementations take in in common, and `test_vectors.py`, which checks their self-consistency.

| File | Covers |
|---|---|
| `checks.json`, `cobs.json` | checksum and COBS encoding |
| `hid_reports.json` | HID reports (transports §1): count and first when a frame is packed into reports, and the messages that can be read when a report is missing, when the reading starts in the middle, and when count or first is broken |
| `headers.json`, `confirm.json` | message header and connection confirmation |
| `refusals.json` | refusals of requests and error answers |
| `discovery.json`, `sessions.json` | discovery of functions and sessions |
| `core_extensions.json` | unknown named extension TLVs after a fixed part (including an empty one), unknown names in a request (ignored; unsupported when critical) and length errors |
| `core_lifecycle.json` | credit of an unfinished resend, the processing / sending boundary of a lease, monitoring and transport loss |
| `core_policy.json` | optional policy decisions and the order of resend / force / public discovery. Authentication methods and production endpoints are not implemented |
| `ops.json`, `ops_encoding.json` | request and answer of each op, and encoding |
| `logic_layout.json` | layout inside a segment of logic capture |
| `capture_formats.json` | formats of capture data (capture §1.3 logic blocks, capture §1.4 analog blocks, capture §3.8 timestamped states) and the trigger expression (capture §4.4). For logic: raw and the 4 reductions (sample, any_high, any_low, change_latch), the last partial block and interval of a segment, and change_latch of a segment that follows without a gap and of a segment after a gap |
| `interface_profiles.json` | small declaration examples: no named function, a third-party extension, a receive-only UART, raw ARM transfers. Not behavior traces |
| `settings_file.json` | the settings file ([settings file](../../docs/oep-settings-file.md)): the file written out from the declaration, the values of get and the objects of the memo area, and the import into a probe with different numbers (including write and delete of the memo area). `test_settings_file.py` computes the export and the import independently |
| `interface_boundaries.json` | notification thresholds, stop remainders, frame splitting, the received range on loss, the condition under which a serial jump counts as a loss count, answer / state on a failed save, refusal / failure of a group start, I2C/SPI boundaries. Examples with preconditions and external observations |

The `about` of each JSON tells how to read it, and a case with `spec` also points to the matching normative place. A case with a precondition state is checked with that state prepared. The shared vectors check the listed situations; they do not prove conformance as a whole. Additional tests each implementation needs follow the [conformance requirements](../../docs/conformance.md).

## Updating and checking

Do not edit the JSON directly. Update the computation of [tools/oepvectors1.py](../../tools/README.md) to match the normative rules. Run from the repository root:

```sh
python3 tools/oepvectors1.py
python3 tools/oepvectors1.py --check
cd tests
uv run pytest vectors
```

`test_*.py` reads each JSON again with decoding, checksum and state models written from the text separately from the generator, and compares with the values the normative rules define. `test_replay_state.py` checks the resend history, the resend of open, finished sessions and the 16 bit boundary with an independent state model. The checks of boundary examples do not prove power-loss tolerance of the storage medium or the electrical behavior of SPI. Unit tests and hardware tests of implementations run in each implementation repository.
