"""Decode minimal declaration examples independently from their producer."""
import json
from pathlib import Path
import struct

import pytest

DATA = json.loads(Path(__file__).with_name('interface_profiles.json').read_text())['profiles']


def list_entries(message):
    role, corr, resolution, outcome, total, count = struct.unpack_from('<BHBBHB', message)
    assert (role, corr, resolution, outcome) == (2, 1, 1, 0)
    at = 8
    entries = []
    for _ in range(count):
        fn, instance, revision, size = struct.unpack_from('<HHBB', message, at)
        assert fn != 0 and instance == 0 and revision == 1 and 1 <= size <= 48
        at += 6
        name = message[at:at + size].decode('ascii')
        assert len(name) == size
        assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-.' for c in name)
        at += size
        entries.append((fn, instance, revision, name))
    assert at == len(message) and total == count == len(entries)
    return entries


def description(message, fn):
    assert struct.unpack_from('<BHBBB', message) == (2, fn, 1, 0, 0)
    at = 6
    values = []
    while at < len(message):
        tag, size = struct.unpack_from('<BH', message, at)
        at += 3
        assert 1 <= tag <= 127 and at + size <= len(message)
        values.append((tag, message[at:at + size]))
        at += size
    assert at == len(message)
    return values


@pytest.mark.parametrize('profile', DATA, ids=lambda row: row['name'])
def test_minimal_declaration_bytes(profile):
    listed = bytes.fromhex(profile['list_answer_hex'])
    assert len(listed) <= 64
    assert list_entries(listed) == [(row['fn'], 0, 1, row['name']) for row in profile['entries']]
    for row in profile['entries']:
        decoded = description(bytes.fromhex(row['describe_answer_hex']), row['fn'])
        bitmap = next(value for tag, value in decoded if tag == 7)
        base = bitmap[0]
        offered = {base + bit for bit in range(8 * (len(bitmap) - 1)) if bitmap[1 + bit // 8] & (1 << (bit % 8))}
        assert offered == set(row['ops'])
        assert not offered.intersection({0, *range(3, 16)})
        assert (1 in offered) == (2 in offered)
        if row['name'] == 'oep.fixture.uart':
            assert offered == {0x10, 0x11, 0x16}
            assert next(value for tag, value in decoded if tag == 0x40) == b'\x01\0'
            assert all(value[0] == 1 for tag, value in decoded if tag == 1)  # RX only.
        elif row['name'] == 'oep.target.arm-adi':
            assert offered == {0x10} and all(tag != 3 for tag, _ in decoded)
        elif row['name'] == 'oep.target.riscv-dm':
            assert offered == {0x10}  # No high-level CPU or scratch-restore helpers required.
        elif row['name'] == 'oep.fixture.spi-target':
            assert offered == {0x10,0x11,0x12,0x13}
            assert next(v for t,v in decoded if t==0x41)==b'\1'
            assert next(v for t,v in decoded if t==2)==struct.pack('<I',1000000)
            assert len(bytes.fromhex(row['describe_answer_hex']))<=64
        elif row['name'] == 'oep.fixture.logic':
            assert offered == {0x10,0x11,0x12,0x14,0x15,0x16}
            assert next(v for t,v in decoded if t==0x40)==struct.pack('<BII',1,16,0)
            assert {1,0x40,0x41,0x44,0x45}.issubset({t for t,_ in decoded})
            assert len(bytes.fromhex(row['describe_answer_hex']))<=64
        elif row['name'] in ('oep.wire.swd','oep.wire.rvswd'):
            assert offered == {0x11, 0x12, 0x13}  # No scan required.
        elif row['name'] == 'oep.probe.config':
            assert offered == {0x10,0x11,0x14}
            assert next(v for t,v in decoded if t==0x41)==b'\2\3\7'
            assert all(t!=0x40 for t,_ in decoded)
        elif row['name'] == 'oep.target.console':
            assert offered == {0x10,0x11,0x16,0x17}  # No marks or TX queue required.
            value = next(value for tag,value in decoded if tag == 0x40)
            assert value[0] == 1 and len(value) == 2 and value[1] in (0,2)
        else:
            assert offered == {0x10}  # No standard OEP operations required.


def test_old_list_flags_byte_is_not_a_valid_new_entry():
    message = bytes.fromhex(DATA[2]['list_answer_hex'])
    old = message[:13] + b'\0' + message[13:]  # Old flags before name_len.
    with pytest.raises(AssertionError):
        list_entries(old)


def test_raw_connection_producer_and_consumer_have_different_functions():
    entries = list_entries(bytes.fromhex(DATA[3]['list_answer_hex']))
    assert entries == [(8, 0, 1, 'oep.wire.swd'), (9, 0, 1, 'oep.target.arm-adi')]
    # This proves distinct declarations, not that an endpoint routes the resource.
