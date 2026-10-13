"""Independent wire admission harness; no authentication mechanism or endpoint."""
import json
from pathlib import Path
import struct

import pytest

CASES = json.loads(Path(__file__).with_name('core_policy.json').read_text())['scenarios']


@pytest.mark.parametrize('case', CASES, ids=lambda row: row['name'])
def test_admission_before_replay(case):
    state = {'owner': 0x12345678, 'corr': 12, 'lease': 1000, 'resource': 42}
    before = dict(state)
    role, corr, fn, operation, sid = struct.unpack_from('<BHHBI', bytes.fromhex(case['request_hex']))
    assert role == 1
    known = {0: {1, 2, 3, 4, 16, 17, 18, 19}, 2: {16}}
    reason, payload = None, b''
    if corr == 0:
        reason = 3
    elif fn not in known:
        reason = 1
    elif operation not in known[fn]:
        reason = 2
    elif fn == 0 and operation in (17, 18) and sid == 0:
        reason = 9
    elif not case['allowed'] and (fn, operation) not in {(0, 1), (0, 2), (0, 3), (0, 4), (0, 19)}:
        reason, payload = 4, bytes([1, 1, 0, 7])
    if reason is not None:
        actual = struct.pack('<BHBB', 2, corr, 0, reason) + payload
    elif 'cache_response_hex' in case:
        assert sid == state['owner'] and corr == state['corr']
        actual = bytes.fromhex(case['cache_response_hex'])
    else:
        actual = bytes.fromhex(case['downstream_response_hex'])
    assert actual.hex() == case['expected_response_hex']
    assert state == before
    if reason == 4:
        assert b'secret' not in actual
