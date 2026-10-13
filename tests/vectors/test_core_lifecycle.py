"""Independent sequential lifecycle model; not a production endpoint or transport."""
import json
from pathlib import Path
import struct

import pytest

SCENARIOS = json.loads(Path(__file__).with_name('core_lifecycle.json').read_text())['scenarios']


@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda case: case['name'])
def test_sequential_lifecycle(scenario):
    now, owner, last_sid, last_corr, deadline, lease, executions = 0, 0, 0, None, 0, 5000, 0
    routes = {}
    for event in scenario['events']:
        action = event['action']
        if action == 'advance':
            now += event['ms']
        elif action == 'receive':
            message = bytes.fromhex(event['request_hex'])
            role, corr, fn, op, sid = struct.unpack_from('<BHHBI', message)
            assert role == 1 and corr and fn in (0, 3) and len(message) <= 64
            if fn == 3:
                assert op == 0x10 and sid == 0
            route = event['route']
            if route in routes:
                previous = routes[route]['message']
                _, previous_corr, _, _, previous_sid = struct.unpack_from('<BHHBI', previous)
                assert (previous_corr, previous_sid) == (corr, sid)
                assert previous == message and event['expect'] == 'coalesced'
            else:
                assert event['expect'] == 'queued'
                routes[route] = {'message': message, 'phase': 'queued'}
        elif action == 'process':
            if owner and now >= deadline:
                owner = 0  # Expire before replay/session processing, including after observer work.
            entry = routes[event['route']]
            assert entry['phase'] == 'queued'
            _, corr, fn, op, sid = struct.unpack_from('<BHHBI', entry['message'])
            opening = fn == 0 and op == 0x10
            bound = 1000 if fn == 0 and op in (0x01, 0x02, 0x03, 0x04, 0x12, 0x13) else 10000
            assert event['duration_ms'] <= bound
            reason = None
            if sid and sid == last_sid and last_corr is not None and not 0 < ((corr - last_corr) & 0xffff) < 0x8000:
                reason = 'result_lost'
            elif sid and not opening and not owner:
                reason = 'no_session'
            elif sid and owner and owner != sid:
                reason = 'locked'
            accepted_owner = bool(sid and sid == owner and reason is None)
            if reason != 'result_lost' and sid == last_sid and sid:
                last_corr = corr  # Rejected fresh requests advance replay order.
            if reason is None:
                if opening:
                    assert len(entry['message']) == 15 and sid
                    lease, force = struct.unpack_from('<IB', entry['message'], 10)
                    assert 1000 <= lease <= 60000 and force == 0
                    owner, last_sid, last_corr = sid, sid, corr
                reason = event.get('reject')
                if reason == 'unsupported':
                    assert entry['message'][10:] == bytes([0xBE, 1, 0, ord('x')])
                if reason is None:
                    executions += 1
            now += event['duration_ms']
            if (opening and reason is None) or accepted_owner:
                deadline = now + lease  # Generation, not transmission, renews the owner.
            elif owner and now >= deadline:
                owner = 0  # Observer/rejection work does not pause an unrelated lease.
            assert reason == event.get('reason')
            entry['phase'] = 'answer'
        elif action == 'sent':
            entry = routes.pop(event['route'])
            assert entry['phase'] == 'answer'
        elif action == 'close':
            entry = routes.pop(event['route'])
            assert entry['phase'] == 'queued'  # Chosen permitted behavior: discard unexecuted input.
        elif action == 'check':
            if owner and now >= deadline:
                owner = 0
            if 'owner' in event:
                assert owner == event['owner']
            if 'remaining_ms' in event:
                assert (max(0, deadline - now) if owner else 0) == event['remaining_ms']
            if 'executions' in event:
                assert executions == event['executions']
            if 'credits' in event:
                assert {str(route): 1 for route in routes} == event['credits']
        else:
            raise AssertionError(action)
