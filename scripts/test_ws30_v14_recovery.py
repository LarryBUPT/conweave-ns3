"""Local subprocess and recovery guards; no SSH, builds or simulations."""
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_ws25_preflight as base
import run_ws30_v14 as v
import resume_ws30_v14 as resume


@contextmanager
def scratch():
    root = v.ROOT/'results/ws30-v14-recovery-tests'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as name:
        folder = Path(name).resolve()
        assert root.resolve() in folder.parents
        yield folder


class OutputTests(unittest.TestCase):
    def child(self, root, code):
        path = root/'child.py'
        path.write_text(code, encoding='utf-8')
        return path

    def test_real_child_utf8_output_ignores_windows_code_page(self):
        with scratch() as root:
            child = self.child(root, "print('\\u4e2d\\u6587 \\U0001f600')\n")
            with patch.object(base, 'ROOT', root), patch.object(base, 'CONTROLLER', child):
                self.assertEqual(base.command('check').strip(), '\u4e2d\u6587 \U0001f600')

    def test_real_child_invalid_bytes_preserve_full_error(self):
        raw = b'begin\xff\xfe original-child-failure\n'
        with scratch() as root:
            child = self.child(root, 'import sys\nsys.stdout.buffer.write('+repr(raw)+')\nsys.exit(7)\n')
            with patch.object(base, 'ROOT', root), patch.object(base, 'CONTROLLER', child):
                with self.assertRaisesRegex(RuntimeError, 'exit 7.*output retained'):
                    base.command('fetch','20261026-120000-test')
            log = next((root/'results/controller-command-errors').glob('*.log'))
            self.assertEqual(log.read_bytes(), raw)
            receipt = json.loads(log.with_suffix('.json').read_text())
            self.assertEqual(receipt['returncode'],7)
            self.assertEqual(receipt['output_sha256'],hashlib.sha256(raw).hexdigest())

    def test_none_stdout_does_not_mask_nonzero_exit(self):
        with scratch() as root, patch.object(base,'ROOT',root), patch.object(base.subprocess,'run',return_value=subprocess.CompletedProcess([],3,None)):
            with self.assertRaisesRegex(RuntimeError, 'exit 3'):
                base.command('check')
            receipt=json.loads(next((root/'results/controller-command-errors').glob('*.json')).read_text())
            self.assertTrue(receipt['output_missing'])

    def test_timeout_preserves_partial_bytes(self):
        with scratch() as root, patch.object(base,'ROOT',root), patch.object(base.subprocess,'run',side_effect=subprocess.TimeoutExpired(['child'],120,output=b'partial\xff')):
            with self.assertRaisesRegex(RuntimeError, 'timed out.*output retained'):
                base.command('check')
            log=next((root/'results/controller-command-errors').glob('*.log'))
            self.assertEqual(log.read_bytes(),b'partial\xff')

    def test_streamed_build_diagnostic_survives_ascii_parent_stdout(self):
        experiment='20261026-120000-recovery-test'
        with scratch() as root:
            child=self.child(root,'import sys\nsys.stdout.buffer.write('+repr(b'diagnostic\xff\n'+('build complete='+experiment+'\n').encode())+')\n')
            buffer=io.BytesIO();stream=io.TextIOWrapper(buffer,encoding='ascii',errors='strict')
            with patch.object(base.remote,'ssh_base',return_value=[sys.executable,str(child)]),patch.object(base.remote.sys,'stdout',stream):
                base.remote.worker_call({},'build','--id',experiment)
            stream.flush()
            self.assertIn(b'build complete=',buffer.getvalue())
            self.assertIn(b'\\ufffd',buffer.getvalue())


class LogTests(unittest.TestCase):
    cell={'id':'20261026-120000-recovery-test'}
    def paths(self,root):
        folder=root/'results'/self.cell['id'];(folder/'logs').mkdir(parents=True)
        (folder/'raw/123').mkdir(parents=True)
        return folder/'raw/123/config.log',folder/'logs/config.log'

    def test_config_log_recovers_locally_and_idempotently(self):
        with scratch() as root:
            source,dest=self.paths(root);source.write_bytes(b'raw-observation\xff\n')
            with patch.object(base,'ROOT',root),patch.object(base.remote,'config',side_effect=AssertionError('SSH forbidden')):
                base.fetch_config_log(self.cell,{'raw_directory':'123'})
                first=dest.stat().st_mtime_ns
                base.fetch_config_log(self.cell,{'raw_directory':'123'})
                self.assertEqual(dest.read_bytes(),source.read_bytes())
                self.assertEqual(dest.stat().st_mtime_ns,first)

    def test_existing_mismatched_log_is_retained_and_rejected(self):
        with scratch() as root:
            source,dest=self.paths(root);source.write_bytes(b'raw');dest.write_bytes(b'partial-old-copy')
            with patch.object(base,'ROOT',root),self.assertRaisesRegex(AssertionError,'differs; retained'):
                base.fetch_config_log(self.cell,{'raw_directory':'123'})
            self.assertEqual(dest.read_bytes(),b'partial-old-copy')

    def test_interrupted_scp_never_publishes_partial_log(self):
        with scratch() as root:
            _,dest=self.paths(root)
            def broken(args,**kwargs):
                Path(args[-1]).write_bytes(b'partial')
                return subprocess.CompletedProcess(args,1,b'scp failed\xff')
            with patch.object(base,'ROOT',root),patch.object(base.remote,'config',return_value={'REMOTE_USER':'test','REMOTE_HOST':'test'}),patch.object(base.remote,'ssh_base',return_value=[]),patch.object(base.subprocess,'check_output',return_value=hashlib.sha256(b'complete').hexdigest()),patch.object(base.subprocess,'run',side_effect=broken):
                with self.assertRaisesRegex(RuntimeError,'transfer failed; staging and output retained'):
                    base.fetch_config_log(self.cell,{'raw_directory':'123'})
            self.assertFalse(dest.exists())
            self.assertEqual(next(dest.parent.glob('.incoming-config-*')).read_bytes(),b'partial')

    def test_existing_local_result_recovers_log_before_validation(self):
        with scratch() as root:
            source,dest=self.paths(root);source.write_bytes(b'observer')
            (dest.parent.parent/'metadata.json').write_text(json.dumps({'raw_directory':'123'}))
            backend=v.Backend([self.cell])
            def validate(c):
                self.assertEqual(dest.read_bytes(),b'observer')
                return {'id':c['id']}
            with patch.object(base,'ROOT',root),patch.object(v,'ROOT',root),patch.object(v,'verify_common',side_effect=validate),patch.object(base.remote,'config',side_effect=AssertionError('SSH forbidden')):
                state=v.Runner([self.cell],backend,root/'state.json',cap=8)
                state.collect([self.cell],{self.cell['id']:{'status':'SUCCEEDED'}})
            self.assertIn(self.cell['id'],state.state['verified'])


class ResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=v.read(v.CONTRACT);cls.sched=v.schedule(cls.plan)
        cls.cells={c['id']:c for g in v.GROUPS for c in cls.plan[g]}
        cls.rec=v.read(resume.RECONCILED);cls.failed=v.read(resume.FAILED)

    def test_partition_skips_exactly_24_and_preserves_frozen_140(self):
        kept,remaining=resume.partition(self.sched,self.cells,self.rec,self.failed)
        self.assertEqual(len(kept),24);self.assertEqual(len(remaining),140)
        self.assertFalse({c['id'] for c in kept}&{c['id'] for c in remaining})
        self.assertEqual([c['id'] for c in kept+remaining],self.sched['phases']['formal-rest']['ids'])

    def test_reconciliation_id_change_is_rejected(self):
        changed=dict(self.rec,not_started_ids=list(reversed(self.rec['not_started_ids'])))
        with self.assertRaisesRegex(RuntimeError,'140 untouched IDs changed'):
            resume.partition(self.sched,self.cells,changed,self.failed)

    def test_metadata_absence_does_not_hide_orphan_remote_directory(self):
        c=self.cells[self.sched['phases']['formal-rest']['ids'][24]]
        with patch.object(resume,'local_inventory',return_value=[]),self.assertRaisesRegex(RuntimeError,'metadata-free residue'):
            resume.require_empty([c],{'states':{c['id']:None}},{c['id']:{'runs':True,'results':False}})

    def test_build_intent_or_staging_blocks_new_id(self):
        c=self.cells[self.sched['phases']['formal-rest']['ids'][24]]
        with patch.object(resume,'local_inventory',return_value=[Path('retained-build-intent')]),self.assertRaisesRegex(RuntimeError,'Local ID, staging or build intent occupied'):
            resume.require_empty([c],{'states':{c['id']:None}},{c['id']:{'runs':False,'results':False}})

    def test_pending_acceptance_stops_before_ssh_or_runner_writes(self):
        with scratch() as root:
            auth=root/'authorization.json';auth.write_text(json.dumps({'approved':False}))
            with patch.object(resume,'AUTH',auth),patch.object(v,'Backend',side_effect=AssertionError('SSH forbidden')),patch.object(v.recovery,'controller_lock',side_effect=AssertionError('write forbidden')):
                with self.assertRaisesRegex(RuntimeError,'main-chat acceptance pending'):resume.run(None)

    def test_owned_terminal_resumption_does_not_rebuild_or_rerun(self):
        cells=[self.cells[i] for i in self.sched['phases']['formal-rest']['ids'][24:26]]
        class Backend:
            def gate(self):return {'load_1m':0,'mem_available_gib':100,'free_gib':1000}
            def snapshot(self,cs,known=None,drain=False):
                return {'states':{c['id']:{'status':'SUCCEEDED','git_commit':c['source_sha']} for c in cs},'resource':self.gate()}
            def local(self,c):return False
            def finish(self,c):return {'id':c['id']}
            def build(self,c):raise AssertionError('rebuild forbidden')
            def start(self,c,cap):raise AssertionError('rerun forbidden')
        with scratch() as root:
            runner=v.Runner(cells,Backend(),root/'state.json',cap=8)
            runner.state['pending']=[c['id'] for c in cells]
            runner.save('batch_reserved',ids=runner.state['pending'])
            self.assertEqual(len(runner.run()['verified']),2)


if __name__=='__main__':
    unittest.main()
