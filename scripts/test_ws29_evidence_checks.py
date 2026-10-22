"""Reject corrupted independent evidence, rather than trusting decision labels."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from ws29_evidence_checks import (verify_control, verify_lifecycle, verify_provenance,
                                  verify_runtime, verify_settings, verify_reference)


class EvidenceIntegrityTests(unittest.TestCase):
    def cell(self, arm=1):
        return dict(arm=arm, fault=0, fault_tor=32, fault_port=6, fault_start_ns=0,
                    fault_end_ns=0, ns3_seed=1, pfc=0, irn=1, synthetic=False, label='main-c1')

    def test_settings_reject_fault_or_enable_drift(self):
        cell = self.cell()
        p = {('ws29_' + k): cell[k] for k in
             ('arm', 'fault', 'fault_tor', 'fault_port', 'fault_start_ns', 'fault_end_ns')}
        p.update(ws21_identity=1, ws21_feedback=1, ws21_heartbeat=1,
                 ws21_feedback_interval_ns=10000, ws21_heartbeat_interval_ns=200000)
        cfg = {k.upper(): str(v) for k, v in p.items()}
        cfg.update(RANDOM_SEED='1', ENABLE_PFC='0', ENABLE_IRN='1')
        verify_settings({'parameters': p}, cfg, cell)
        for key in ('ws29_fault_port', 'ws21_feedback', 'ws21_heartbeat_interval_ns'):
            changed = copy.deepcopy(p); changed[key] += 1
            with self.assertRaises(ValueError):
                verify_settings({'parameters': changed}, cfg, cell)

    def test_runtime_ttl_must_be_frozen(self):
        cell = self.cell()
        row = ('WS29_SETTINGS arm=1 fault=0 fault_tor=32 fault_port=6 fault_start_ns=0 '
               'fault_end_ns=0 identity=1 state=1 heartbeat=1 state_interval_ns=10000 '
               'heartbeat_interval_ns=200000 decision_ttl_ns=20000')
        verify_runtime([row], cell)
        with self.assertRaises(ValueError): verify_runtime([row.replace('ttl_ns=20000', 'ttl_ns=20001')], cell)

    def state_ledger(self):
        return ['WS29_STATE_SEND time_ns=1',
                'WS29_CONTROL time_ns=1 switch=34 port=6 event=enqueue type=state bytes=72',
                'WS29_CONTROL time_ns=2 switch=34 port=6 event=dequeue type=state bytes=72',
                'WS21_FEEDBACK generated=1 delivered=0 delivered_bytes=0 hop_enqueues=1 '
                'hop_dequeues=1 hop_bytes=72 hop_rejects=0 rejected=0 expired=0',
                'WS29_SUMMARY arm=3 rows=3 overflow=0']

    def test_packet_and_byte_ledger_reconciles(self):
        counts = dict(state_enqueue_packets=1, state_enqueue_bytes=72,
                      state_dequeue_packets=1, state_dequeue_bytes=72)
        lines = self.state_ledger()
        verify_control(lines, self.cell(3), counts)
        for changed in ([x for x in lines if not x.startswith('WS29_CONTROL')],
                        [x.replace('bytes=72', 'bytes=71') for x in lines],
                        [x.replace('hop_enqueues=1', 'hop_enqueues=2') for x in lines]):
            with self.assertRaises(ValueError): verify_control(changed, self.cell(3), counts)

    def test_c0_cannot_hide_control_counts(self):
        with self.assertRaises(ValueError):
            verify_control(['WS29_SUMMARY arm=0 rows=0 overflow=0'], self.cell(0), {'state_enqueue_bytes': 72})

    def provenance(self):
        lines = []
        for port in ('5', '6'):
            lines.append('WS21_HEARTBEAT_EVENT time_ns=10000 tor=32 port=' + port + ' event=activate epoch=1 sequence=0')
        for port in ('5', '6'):
            lines.append('WS29_STATE_SEND time_ns=22000 switch=34 source_tor=32 candidate=' + port +
                         ' session=1 sequence=2 start_ns=15000 end_ns=20000 ce=1 samples=10 bytes=72')
        for port in ('5', '6'):
            lines.append('WS29_ACK time_ns=24000 switch=32 port=' + port + ' epoch=1 sequence=1')
        for port in ('5', '6'):
            lines.append('WS29_STATE_CACHE time_ns=25000 switch=32 destination=34 candidate=' + port +
                         ' session=1 sequence=2 start_ns=15000 end_ns=20000 ce=1 samples=10 bytes=72')
        row = 'WS29_DECISION time_ns=30000 switch=32 dst=8 first=5 second=6 reason=equal_ce'
        for p in ('a', 'b'):
            row += ' ' + ' '.join(p + '_' + k + '=' + v for k, v in
                                 dict(session='1', sequence='2', start='15000', end='20000', ce='1', samples='10').items())
        return lines + [row]

    def test_natural_decision_requires_real_send_and_current_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            topo = Path(tmp) / 'topology.txt'
            topo.write_text('4 2 2\n32 34\n0 32\n8 34\n')
            lines = self.provenance()
            verify_provenance(lines, topo, self.cell())
            damaged = [[x for x in lines if not x.startswith('WS29_STATE_SEND')],
                       lines[:-1] + ['WS29_SESSION time_ns=26000 switch=32 session=2'] + lines[-1:],
                       lines[:-1] + ['WS29_LINK time_ns=26000 switch=32 port=5 up=0'] + lines[-1:],
                       [x.replace('a_sequence=2', 'a_sequence=3') for x in lines],
                       [x.replace('epoch=1 sequence=1', 'epoch=2 sequence=1') for x in lines]]
            for changed in damaged:
                with self.assertRaises(ValueError): verify_provenance(changed, topo, self.cell())

    def test_invalid_ack_and_old_timer_need_independent_rows(self):
        cell = self.cell(); cell['fault'] = 3
        with self.assertRaises(ValueError):
            verify_lifecycle(['WS29_ACK_INJECT fault=3 rejected_delta=1'], cell, {})
        row = 'WS29_ACK_CHECK accepted=0 last_ack_before=10 last_ack_after=11 missed_before=1 missed_after=1 outstanding_before=2 outstanding_after=2 epoch_before=1 epoch_after=1'
        with self.assertRaises(ValueError): verify_lifecycle([row], self.cell(), {})
        with self.assertRaises(ValueError): verify_lifecycle([], self.cell(), {'hb_old_timer_ignored': 1})

    def test_reference_metadata_hash_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir(); (root / 'raw/1').mkdir(parents=True)
            (root / 'metadata.json').write_text(json.dumps(dict(git_commit='fixed', seed=1, parameters={}, raw_directory=1)))
            files = {'config/config.txt': 'config_sha256', 'config/traffic_trace.txt': 'trace_sha256',
                     'config/topology.txt': 'topology_sha256', 'raw/1/1_out_fct.txt': 'fct_sha256'}
            old = dict(root=str(root), source_sha='fixed', seed=1, parameters={})
            for name, key in files.items():
                (root / name).write_text('fixed evidence')
                old[key] = hashlib.sha256((root / name).read_bytes()).hexdigest()
            old['metadata_sha256'] = hashlib.sha256((root / 'metadata.json').read_bytes()).hexdigest()
            verify_reference(old)
            with (root / 'metadata.json').open('a') as out: out.write(' ')
            with self.assertRaises(ValueError): verify_reference(old)


if __name__ == '__main__':
    unittest.main()
