"""Finite in-memory encoding checks, not C++/ns3 execution."""
from pathlib import Path
import unittest
import ws31_native_declarations as codec
import ws31_native_lexical_corpus as lexical

ROOT=Path(__file__).resolve().parents[1]/'results/ws31-consensus-v2-inputs-r1/K0'


def mutate(text,row,column,value):
    lines=text.splitlines()
    words=lines[3+row].split()
    words[column]=str(value)
    lines[3+row]=' '.join(words)
    return '\n'.join(lines)+'\n'


class NativeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d1=codec.encode_bundle(ROOT/'D1-5310001')[0].decode('ascii')
        cls.d2=codec.encode_bundle(ROOT/'D2-5310001')[0].decode('ascii')

    def test_source_bound_ip_examples(self):
        self.assertEqual(codec.node_ip(0),0x0b000001)
        self.assertEqual(codec.node_ip(15),0x0b000f01)
        self.assertEqual(codec.node_ip(64),0x0b004001)
        self.assertEqual(codec.node_ip(79),0x0b004f01)

    def test_all16_roundtrips_and_original_fields(self):
        for family in ('D1','D2'):
            for seed in range(5310001,5310009):
                raw,summary=codec.encode_bundle(ROOT/'{}-{}'.format(family,seed))
                header,rows=codec.parse_text(raw.decode('ascii'))
                self.assertEqual(header,summary)
                self.assertEqual(len(rows),1120)
                self.assertEqual([r['request_id'] for r in rows],list(range(1120)))
                self.assertTrue(all(r['original_tag']==r['policy_tag'] for r in rows))
                self.assertNotIn('business_task',rows[0])

    def test_policy_is_separate_from_original(self):
        _,before=codec.parse_text(self.d1)
        flipped=1 if before[0]['policy_tag']==2 else 2
        _,after=codec.parse_text(mutate(self.d1,0,11,flipped))
        self.assertEqual(after[0]['original_tag'],before[0]['original_tag'])
        self.assertEqual(after[0]['policy_tag'],flipped)
        absent=mutate(mutate(self.d1,0,10,0),0,11,0)
        _,rows=codec.parse_text(absent)
        self.assertEqual(rows[0]['policy_present'],0)

    def test_unsigned_width_identity_and_order_rejections(self):
        for column,value in [(0,1),(1,1),(4,0),(6,8),(8,2004999999),(9,0),(10,2),
                             (11,2**32),(12,65536),(14,65536),(7,'-1'),(0,'00')]:
            with self.subTest(column=column,value=value),self.assertRaises(ValueError):
                codec.parse_text(mutate(self.d1,0,column,value))
        with self.assertRaises(ValueError):
            codec.parse_text(mutate(self.d1,0,10,0))

    def test_truncation_extra_fields_and_stage_identity(self):
        lines=self.d1.splitlines()
        for bad in ['\n'.join(lines[:-1])+'\n',self.d1+'\n',self.d1+'0\n',
                    self.d1.replace(' K0 ',' K1 ',1),self.d1.replace('PROTOCOL_SHA256','PROTOCOL_BROKEN',1),
                    mutate(self.d1,0,14,'0 1')]:
            with self.assertRaises(ValueError):
                codec.parse_text(bad)

    def test_explicit_lexical_positives_preserve_all_fields(self):
        base=self.d1.encode('ascii')
        for name,data,accepted in lexical.cases(base):
            if accepted:
                with self.subTest(case=name):
                    lexical.check(data,True,base)

    def test_explicit_lexical_negatives_and_reported_witnesses(self):
        for name,data,accepted in lexical.cases(self.d1.encode('ascii')):
            if not accepted:
                with self.subTest(case=name):
                    lexical.check(data,False)


if __name__=='__main__':
    unittest.main(verbosity=2)
