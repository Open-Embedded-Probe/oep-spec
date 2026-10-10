"""Evaluate session vectors independently, including execution counts and cache eviction."""
from collections import OrderedDict
import json
from pathlib import Path
import struct
import tomllib
import pytest

ROOT = Path(__file__).resolve().parents[2]
REG = tomllib.loads((ROOT / 'registry/oep-v1.toml').read_text())
OPS = {o['name']: o['code'] for o in REG['core']['op']}
REASONS = REG['reject_reasons']


SCENARIOS = json.loads((Path(__file__).parent / 'sessions.json').read_text())['scenarios']


@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda scenario: scenario['name'])
def test_session_vectors_obey_replay_and_lock_state(scenario):
    last_session, locked, highwater = None, False, 0
    cache = OrderedDict()
    executions = {}
    for step in scenario['steps']:
        req = bytes.fromhex(step['request_hex'])
        ans = bytes.fromhex(step['answer_hex'])
        _, corr, fn, op, session = struct.unpack_from('<BHHBI', req)
        _, reply_corr, resolution, detail = struct.unpack_from('<BHBB', ans)
        assert corr == reply_corr and fn == 0
        opening = op == OPS['open']
        needs_session = op in (OPS['end'], OPS['keepalive'])
        reason = None
        replay = False
        if corr == 0 or (opening and session == 0):
            reason = 'malformed'
        elif needs_session and session == 0:
            reason = 'session_required'
        elif session and session == last_session and corr in cache:
            previous_req, previous_ans = cache[corr]
            replay = True
            if req != previous_req:
                reason = 'malformed'
            else:
                assert ans == previous_ans, step['note']
        elif session and session == last_session and corr <= highwater:
            reason = 'result_lost'
        elif session:
            force = opening and req[14] != 0
            if not locked and not (opening and session != last_session):
                reason = 'no_session'
            elif locked and session != last_session and not force:
                reason = 'locked'
        if reason:
            assert (resolution, detail) == (0, REASONS[reason]), (scenario['name'], step['note'])
        elif not replay:
            assert (resolution, detail) == (1, 0), step['note']
            if session:
                key = (session, corr)
                executions[key] = executions.get(key, 0) + 1
                assert executions[key] == 1, step['note']
            if opening:
                if session != last_session:
                    last_session, highwater = session, 0
                    cache.clear()
                locked = True
            elif op == OPS['end']:
                locked = False
        # Cache responses that passed the replay stage for the current/last session;
        # a malformed reused corr must not replace its original response.
        if session and session == last_session and not replay and reason != 'result_lost':
            highwater = max(highwater, corr)
            cache[corr] = (req, ans)
            while len(cache) > 4:
                cache.popitem(last=False)
