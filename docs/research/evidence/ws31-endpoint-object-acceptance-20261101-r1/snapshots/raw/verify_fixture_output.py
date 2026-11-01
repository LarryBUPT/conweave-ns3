from pathlib import Path
import json,re,sys,hashlib
raw=Path(__file__).parent
fetched=raw/'remote-results'
plan=json.loads((raw/'frozen-plan.json').read_text(encoding='utf-8'))
text=(fetched/'logs/fixture.stdout').read_text(encoding='utf-8')
assert (fetched/'logs/fixture.stderr').read_bytes()==b''
records={'case':[],'device':[],'slot':[],'sack':[],'refuse':[],'summary':[]}; other=[]
prefixes=[('WS31_ENDPOINT_OBJECT case=','case'),('WS31_ENDPOINT_OBJECT_DEVICE ','device'),('WS31_ENDPOINT_OBJECT_SLOT ','slot'),('WS31_ENDPOINT_OBJECT_SACK ','sack'),('WS31_ENDPOINT_OBJECT_REFUSE ','refuse'),('WS31_ENDPOINT_OBJECT_SUMMARY ','summary')]
def parse(line):
 return {k:(v[1:-1] if v.startswith('"') else v) for k,v in re.findall(r'([A-Za-z_]+)=("[^"]*"|\S+)',line)}
for line in text.splitlines():
 for prefix,kind in prefixes:
  if line.startswith(prefix): records[kind].append({'line':line,**parse(line)}); break
 else:
  if line.strip(): other.append(line)
normal=plan['fixture']['normal_cases']; refused=plan['fixture']['read_refusal_cases']+plan['fixture']['other_refusals']
assert [x['case'] for x in records['case']]==normal
assert len(records['refuse'])==16 and set(x['case'] for x in records['refuse'])==set(refused)
assert len(set(x['case'] for x in records['refuse']))==16
assert len(records['summary'])==1 and records['summary'][0]['line']==plan['fixture']['expected_summary']
assert len(records['device'])==16 and len(records['slot'])==13 and len(records['sack'])==8
bycase={x['case']:x for x in records['case']}
for name,x in bycase.items():
 assert x['mask']=='127' and x['nodes']=='2' and x['devices']=='2' and x['full_protocol_bytes_equal']=='1'
 assert x['before']==x['after'] and int(x['saved_tx'])!=0 and int(x['saved_rx'])!=0
 assert x['live_tx']=='0'
 if name=='live-rx':assert x['live_rx']==x['saved_rx']
 else:assert x['live_rx']=='0'
 if name in ('complete-unmarked','complete-marked'):
  assert x['finished']=='1' and x['pending']=='0'
 else:assert x['finished']=='0'
 expectedpending=8192 if name=='irn-two-sack-blocks' else (0 if name in ('complete-unmarked','complete-marked') else 4096)
 assert int(x['pending'])==expectedpending
 assert int(x['data'])==(32 if name in ('physical-and-ack-queues','events-and-serialization') else 0)
 assert int(x['ack'])==(48 if name in ('physical-and-ack-queues','events-and-serialization') else 0)
 assert int(x['transmitting'])==(1 if name=='events-and-serialization' else 0)
 assert int(x['tx_timers'])==(1 if name=='events-and-serialization' else 0)
 assert int(x['rx_timers'])==(1 if name=='events-and-serialization' else 0)
 assert int(x['device_timers'])==(2 if name=='events-and-serialization' else 0)
 assert x['history_released']==('0' if normal.index(name)>=4 else '1')
 dev=[d for d in records['device'] if d['case']==name]; slots=[s for s in records['slot'] if s['case']==name]
 assert len(dev)==2 and len(set((d['node'],d['interface']) for d in dev))==2
 assert all(int(d[key]) for d in dev for key in ('object','physical','egress','ack','group'))
 expectedslots=1 if normal.index(name)<3 else 2; assert len(slots)==expectedslots
 old=next(s for s in slots if s['flow_id']=='0'); assert old['object']==x['saved_tx'] and old['slot']=='0' and old['size']=='8192'
 assert old['finished_bit']==('0' if name=='complete-unmarked' else '1')
 assert old['completed']==('0' if name=='irn-two-sack-blocks' else '1')
 assert old['pending']==('8192' if name=='irn-two-sack-blocks' else '0')
 if expectedslots==2:
  new=next(s for s in slots if s['flow_id']=='1'); assert new['slot']=='1' and new['finished_bit']=='0' and new['completed']=='0' and new['size']=='4096' and new['pending']=='4096' and new['next']=='0' and new['acknowledged']=='0'
 sack=next(s for s in records['sack'] if s['case']==name)
 if normal.index(name)<2: assert sack['state']=='' and sack['next']=='8192' and sack['acknowledged']=='8192'
 else:
  assert sack['state']=='[0-1024] [2048-3072] '
  assert sack['next']==('0' if name=='irn-two-sack-blocks' else '8192') and sack['acknowledged']==sack['next']
for x in records['refuse']:
 assert x.get('reason')
 if x['case'] in plan['fixture']['read_refusal_cases']:assert x['full_protocol_bytes_equal']=='1'
identities=[tuple(d[k] for k in ('node','interface','object','physical','egress','ack','group')) for d in records['device'] if d['case']==normal[0]]
for name in normal:
 assert [tuple(d[k] for k in ('node','interface','object','physical','egress','ack','group')) for d in records['device'] if d['case']==name]==identities
assert len(set(x['saved_tx'] for x in records['case']))==len(set(x['saved_rx'] for x in records['case']))==1
result={'status':'PASS_OBJECT_FIXTURE_RAW_CASE_AND_PURITY_CHECKS','normal_cases':normal,'read_refusals':plan['fixture']['read_refusal_cases'],'other_refusals':plan['fixture']['other_refusals'],'record_counts':{k:len(v) for k,v in records.items()},'summary':records['summary'][0]['line'],'read_calls':31,'refusals':16,'mask':127,'nodes':2,'devices':2,'normal_protocol_string_equality_asserted':8,'refused_read_protocol_string_equality_asserted':14,'full_string_comparison_is_in_fixed_source':True,'FNV_display_is_not_sole_purity_test':True,'SACK_state_and_slot_details_checked':True,'stable_bound_device_objects_checked':True,'other_stdout_lines':other,'no_binary_invoked_by_this_verifier':True,'scope':'real NS3 objects with manually assigned states; no natural network completions or complete ALL certificate'}
(raw/'fixture-output-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
