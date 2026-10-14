"""Check boundary vectors independently; this is not an endpoint or hardware test."""
import json
from pathlib import Path
import struct

import pytest


DATA = json.loads(Path(__file__).with_name("interface_boundaries.json").read_text())


@pytest.mark.parametrize("row", DATA["batching"], ids=lambda row: row["name"])
def test_batch_eligibility_and_frame_capacity(row):
    size = row["pending_bytes"]
    byte_trigger = row["min_bytes"] > 0 and size >= row["min_bytes"]
    time_trigger = row["max_delay_ms"] > 0 and row["age_ms"] >= row["max_delay_ms"]
    immediate = row["min_bytes"] == row["max_delay_ms"] == 0
    eligible = row["stopped"] or byte_trigger or time_trigger or immediate
    chunks = row["expected_data_lengths"]
    assert sum(chunks) == (size if eligible else 0)
    # Do not reapply the threshold to each fragment, including the last one.
    assert all(0 < n <= row["max_frame"] - 49 for n in chunks)


@pytest.mark.parametrize("row", DATA["reception"], ids=lambda row: row["name"])
def test_tail_reached_is_not_complete_coverage(row):
    spans = sorted((a, b) for gen, a, b in row["spans"] if gen == row["generation"])
    cursor = 0
    for start, end in spans:
        if start > cursor:
            break
        cursor = max(cursor, end)
    assert (cursor >= row["write_pos"]) == row["expected_complete"]
    assert (max((b for _, b in spans), default=0) == row["write_pos"]) == row["expected_tail_reached"]


@pytest.mark.parametrize("row", DATA["serial_loss"], ids=lambda row: row["name"])
def test_serial_jump_is_loss_only_within_one_stream(row):
    lost = None
    if row["same_stream"] and row["last_serial"] is not None:
        diff = (row["first_serial"] - row["last_serial"]) % (1 << 32)
        if 0 < diff < 1 << 30:                                       # forward, inside the held range (core §2.6)
            lost = diff - 1
    assert lost == row["expected_lost"]


@pytest.mark.parametrize("row", DATA["storage"], ids=lambda row: row["name"])
def test_storage_outcomes_and_fixed_payloads(row):
    req = bytes.fromhex(row["request_hex"])
    code = {"save": 0x12, "erase": 0x13}[row["action"]]
    assert struct.unpack("<BHHBI", req) == (1, 1, 8, code, 0x11223344)
    raw = bytes.fromhex(row["answer_hex"])
    outcome = 0 if row["result"] == "success" else 1
    assert struct.unpack_from("<BHBB", raw) == (2, 1, 1, outcome)
    if row["action"] == "save":
        assert len(raw) == 9
        assert struct.unpack_from("<I", raw, 5)[0] == row["generation"]
    else:
        assert len(raw) == 5
    if outcome == 0:
        state = [1, row["generation"], 0] if code == 0x12 else [0, 0, 0]
    else:
        state = {"old": row["before"], "none": [0, 0, 0], "unreadable": [2, 0, 1]}[row["observed"]]
    assert row["expected_state"] == state
    status = bytes.fromhex(row["state_answer_hex"])
    assert struct.unpack("<BHBBBIB", status) == (2, 2, 1, 0, *state)


@pytest.mark.parametrize("row", DATA["groups"], ids=lambda row: row["name"])
def test_group_rejection_and_failure_generations(row):
    req = bytes.fromhex(row["request_hex"])
    assert struct.unpack("<BHHBI", req) == (1, 1, 12, 0x11, 0x11223344)
    raw = bytes.fromhex(row["answer_hex"])
    accepted = all(state in (1, 4, 6) for state in row["states"])
    if not accepted:
        assert struct.unpack("<BHBBBHB", raw) == (2, 1, 0, 4, 1, 1, 6)
        assert row["expected_generations"] == row["generations"]
    else:
        assert struct.unpack_from("<BHBB", raw) == (2, 1, 1, 1)
        timestamp, generation, count = struct.unpack_from("<QIB", raw, 5)
        assert timestamp == 7000000 and count == 2 and len(raw) == 30
        fn0, gen0, fn1, gen1 = struct.unpack_from("<HIHI", raw, 18)
        assert (fn0, fn1) == (9, 13)
        assert [generation, gen0, gen1] == [g + 1 for g in row["generations"]]
        assert row["expected_generations"] == [generation, gen0, gen1]
        states = [1, 1]
        if row["completed_first"]:
            states[0] = 4
        states[row["failed_index"]] = 6
        assert row["expected_states"] == states


def test_fixture_transaction_and_counter_boundaries():
    row = DATA["fixtures"]
    slots = [bytes.fromhex(x) for x in row["i2c_slots_hex"]]
    received = []
    for length in row["i2c_read_lengths"]:
        slot = slots.pop(0) if slots else b""
        received.append((slot + b"\xff" * length)[:length].hex())
    assert received == row["expected_i2c_reads_hex"]
    value = row["counter_before"]
    for _ in range(row["increments"]):
        if value < (1 << 32) - 1:
            value += 1
    assert value == row["expected_counter"]
    empty = bytes.fromhex(row["spi_empty_answer_hex"])
    assert struct.unpack("<BHBBBIH", empty) == (2, 1, 1, 0, 0, 0, 0)
