"""Check the frozen actual-object fixture transcript without running NS-3."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex


NORMAL = ['complete-unmarked', 'complete-marked', 'irn-two-sack-blocks',
          'retain-old-append-new', 'completion-history-present', 'live-rx',
          'physical-and-ack-queues', 'events-and-serialization']
REASONS = {
    'incomplete-mask': 'Endpoint snapshot is incomplete, stale, or belongs to another generation',
    'missing-saved-qp': 'Saved sender QP missing from its actual retained group',
    'duplicate-qp-slot': 'Duplicate QP in retained groups or slots',
    'device-group-binding': 'Actual device/egress/ACK/retained-group binding changed',
    'hardware-group-binding': 'Hardware NIC/group binding changed',
    'missing-physical-queue': 'Frozen physical queue identity changed',
    'empty-live-tx': 'Live sender map contains an empty QP reference',
    'empty-live-rx': 'Live receiver map contains an empty QP reference',
    'wrong-saved-flow': 'Saved sender object does not belong to the requested generation',
    'wrong-reversed-rx': 'Saved receiver object has the wrong reversed endpoint identity',
    'wrong-original-clock': 'Saved sender object does not belong to the requested generation',
    'paused-device': 'Endpoint fixture scope contains a down or paused device',
    'down-device': 'Endpoint fixture scope contains a down or paused device',
    'changed-shared-queue': 'Frozen physical queue identity changed',
    'changed-device-scope': 'Frozen device count changed',
    'unknown-non-qbb': 'Unknown non-Qbb data-plane device in endpoint scope',
}


def fields(tokens):
    result = {}
    for token in tokens:
        key, separator, value = token.partition('=')
        assert separator and key not in result, token
        result[key] = value if key in ('case', 'reason', 'state') else int(value)
    return result


def verify(path):
    data = path.read_bytes()
    assert data.endswith(b'\n')
    records, order = defaultdict(list), defaultdict(list)
    for line in data.decode('utf-8').splitlines():
        tokens = shlex.split(line)
        assert tokens
        prefix = tokens.pop(0)
        assert prefix in ('WS31_ENDPOINT_OBJECT', 'WS31_ENDPOINT_OBJECT_DEVICE',
                          'WS31_ENDPOINT_OBJECT_SLOT', 'WS31_ENDPOINT_OBJECT_SACK',
                          'WS31_ENDPOINT_OBJECT_REFUSE', 'WS31_ENDPOINT_OBJECT_SUMMARY'), line
        if prefix == 'WS31_ENDPOINT_OBJECT_SUMMARY':
            assert tokens.pop(0) == 'PASS'
        row = fields(tokens)
        records[prefix].append(row)
        if 'case' in row:
            order[prefix].append(row['case'])
    assert order['WS31_ENDPOINT_OBJECT'] == NORMAL
    assert order['WS31_ENDPOINT_OBJECT_REFUSE'] == list(REASONS)
    assert len(records['WS31_ENDPOINT_OBJECT_DEVICE']) == 16
    assert len(records['WS31_ENDPOINT_OBJECT_SLOT']) == 13
    assert order['WS31_ENDPOINT_OBJECT_SACK'] == NORMAL
    assert records['WS31_ENDPOINT_OBJECT_SUMMARY'] == [
        {'reads': 31, 'refusals': 16, 'network_runs': 0, 'event_calls': 0,
         'actual_network_completions': 0}]
    assert sum(map(len, records.values())) == 62
    baseline_devices = None
    saved_tx = saved_rx = source_device = new_qp = None
    for index, row in enumerate(records['WS31_ENDPOINT_OBJECT']):
        name = row['case']
        assert set(row) == {'case', 'mask', 'finished', 'pending', 'tx_timers', 'rx_timers',
                            'device_timers', 'data', 'ack', 'transmitting', 'history_released',
                            'before', 'after', 'full_protocol_bytes_equal', 'nodes', 'devices',
                            'saved_tx', 'saved_rx', 'live_tx', 'live_rx'}
        assert row['mask'] == 127 and row['nodes'] == row['devices'] == 2
        assert row['before'] == row['after'] and row['full_protocol_bytes_equal'] == 1
        assert row['finished'] == int(index < 2)
        expected_pending = 0 if index < 2 else (8192 if index == 2 else 4096)
        assert row['pending'] == expected_pending
        active = name == 'events-and-serialization'
        queued = index >= 6
        assert row['tx_timers'] == row['rx_timers'] == row['transmitting'] == int(active)
        assert row['device_timers'] == 2*int(active)
        assert row['data'] == 32*int(queued) and row['ack'] == 48*int(queued)
        assert row['history_released'] == int(index < 4)
        if saved_tx is None:
            saved_tx, saved_rx = row['saved_tx'], row['saved_rx']
            assert saved_tx > 0 and saved_rx > 0 and saved_tx != saved_rx
        assert (row['saved_tx'], row['saved_rx']) == (saved_tx, saved_rx)
        assert row['live_tx'] == 0
        assert row['live_rx'] == (saved_rx if name == 'live-rx' else 0)
        devices = [r for r in records['WS31_ENDPOINT_OBJECT_DEVICE'] if r['case'] == name]
        assert len(devices) == 2
        device_map = {}
        for device in devices:
            assert set(device) == {'case', 'node', 'interface', 'object', 'physical', 'egress', 'ack', 'group'}
            key = (device['node'], device['interface'])
            assert key not in device_map
            for field in ('object', 'physical', 'egress', 'ack', 'group'):
                assert device[field] > 0
            device_map[key] = {k: v for k, v in device.items() if k != 'case'}
        for field in ('object', 'physical', 'egress', 'ack', 'group'):
            assert len({r[field] for r in devices}) == 2
        if baseline_devices is None:
            baseline_devices = device_map
        assert device_map == baseline_devices
        slots = [r for r in records['WS31_ENDPOINT_OBJECT_SLOT'] if r['case'] == name]
        assert len(slots) == (1 if index < 3 else 2)
        if source_device is None:
            source_device = (slots[0]['node'], slots[0]['interface'])
        for slot in slots:
            assert (slot['node'], slot['interface']) == source_device
            assert set(slot) == {'case', 'node', 'interface', 'slot', 'object', 'flow_id',
                                 'finished_bit', 'completed', 'next', 'acknowledged', 'size', 'pending', 'timers'}
        old = slots[0]
        assert old['slot'] == old['flow_id'] == 0 and old['object'] == saved_tx
        assert old['finished_bit'] == int(index != 0)
        assert old['completed'] == int(index != 2)
        assert old['next'] == old['acknowledged'] == (0 if index == 2 else 8192)
        assert old['size'] == 8192 and old['pending'] == (8192 if index == 2 else 0)
        assert old['timers'] == int(active)
        if index >= 3:
            new = slots[1]
            assert new['slot'] == new['flow_id'] == 1
            if new_qp is None:
                new_qp = new['object']
                assert new_qp > 0 and new_qp not in (saved_tx, saved_rx)
            assert new['object'] == new_qp
            assert new['size'] == new['pending'] == 4096
            assert new['finished_bit'] == new['completed'] == new['next'] == new['acknowledged'] == new['timers'] == 0
        sack = [r for r in records['WS31_ENDPOINT_OBJECT_SACK'] if r['case'] == name]
        assert len(sack) == 1
        assert set(sack[0]) == {'case', 'next', 'acknowledged', 'state'}
        assert sack[0]['next'] == sack[0]['acknowledged'] == old['next']
        assert sack[0]['state'] == ('' if index < 2 else '[0-1024] [2048-3072] ')
    for row in records['WS31_ENDPOINT_OBJECT_REFUSE']:
        name = row['case']
        assert row['reason'] == REASONS[name]
        expected = {'case', 'reason'}
        if name not in ('incomplete-mask', 'unknown-non-qbb'):
            expected.add('full_protocol_bytes_equal')
            assert row['full_protocol_bytes_equal'] == 1
        assert set(row) == expected
    return {'at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'MAIN_PASS_CONTROLLED_ACTUAL_OBJECT_TRANSCRIPT_ONLY',
            'stdout_sha256': hashlib.sha256(data).hexdigest(),
            'normal_pairs': 8, 'read_calls_including_refusals': 31,
            'refusals': 16, 'device_rows': 16, 'retained_slot_rows': 13,
            'SACK_rows': 8, 'mask': 127, 'scope_nodes': 2, 'scope_Qbb_devices': 2,
            'object_identities_consistent': True, 'retained_old_and_new_observed': True,
            'IRN_SACK_original_intervals_retained': True,
            'raw_before_after_display_hashes_equal_and_full_string_check_flags_present': True,
            'scope': 'Real NS3 objects with manually assigned states; no event advancement, network completion or complete drain certificate'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stdout', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite acceptance'
    result = verify(args.stdout)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'normal_pairs', 'refusals', 'mask')}))
