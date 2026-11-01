
assert result['mem_available_gib']>=64 and result['disk_available_gib']>=100 and result['load'][0]<=4
assert not result['old_driver_22440_present'] and not any(result['maintenance_markers'].values())
assert result['cache']['origin']['stdout'].strip()=='https://github.com/LarryBUPT/conweave-ns3.git' and result['cache']['status']['stdout']=='' and not result['cache']['symlink']
assert result['cache']['tree_entries']==4847 and result['cache']['tree_sha256']=='8096510b5b068ef31269f88d836112a6e53b2b351984694bc796a0a4a4c05855'
assert result['cache']['refs']['stdout'].strip().endswith(sha) and result['cache']['head']['stdout'].strip()=='236a801a00e35de9078635e04acae2f701c21ded'
assert result['worker']['LF_sha256']=='096695c22597b30ecd24ad3ed69284f851b26743f9be4c810bafee82d90ff569' and not result['worker']['symlink']
byid={x['pid']:x for x in result['processes']}; own=set(); q=os.getpid()
while q in byid and q not in own: own.add(q); q=byid[q]['ppid']
known={215645,302325,348833,377959,397391,415208,420873,420878,457365}
for x in result['processes']:
 if x['uid']>=1000 and x['pid'] not in own: assert x['pid'] in known and x['uid']==1000 and x['state']=='S' and x['ppid'] in (1,420873), x
 if x['argv'] and x['pid'] not in own:
  a=' '.join(x['argv']); exe=(x.get('exe') or '').split('/')[-1]
  assert '/home/fnl/lzy' not in a and '/home/fnl/lzy' not in (x.get('cwd') or ''),x
  assert not exe.startswith(('git','g++','gcc','cc1plus','make','ns3','waf','scp','rsync')),x
result['decision']='PASS_FRESH_GATE'
