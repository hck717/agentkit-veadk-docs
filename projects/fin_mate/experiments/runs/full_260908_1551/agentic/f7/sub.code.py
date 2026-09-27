import sys, asyncio, time, json
sys.path.insert(0, '.')
from experiments import _lib
from experiments.rag_bench import strategies as S
from experiments.rag_bench.eval_set import all_doc_uris
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
q='Wells Fargo 講 E7 新 SKU 每月每位用戶幾多錢？包含咩？'; eid='f7'; cat='fact'; out='experiments/runs/full_260908_1551/agentic/f7/item.json'
_lib.load_env()
kb=S._kb(S.STRATS['agentic']['read_limit']); before=S._ov_snapshot(); agent=S._build_agent(kb)
events=[]; t0=time.perf_counter()
ss=InMemorySessionService()
sid='rag-'+eid
new_msg=types.Content(role='user', parts=[types.Part(text=q)])
asyncio.run(ss.create_session(app_name='rag_bench', user_id='bench', session_id=sid))
runner=Runner(agent=agent, app_name='rag_bench', session_service=ss)
tr=[]
for ev in runner.run(user_id='bench', session_id=sid, new_message=new_msg):
    kind='final' if ev.is_final_response() else 'function_call' if ev.get_function_calls() else ('function_response' if ev.get_function_responses() else 'llm')
    p={'kind':kind,'ts':str(getattr(ev,'timestamp',''))}
    if ev.content is not None and ev.content.parts:
        p['parts']=[]
        for x in ev.content.parts:
            xv=getattr(x,'text',None)
            if xv is None: continue
            p['parts'] += [str(y) for y in (xv if isinstance(xv,list) else [xv])]
    for fc in ev.get_function_calls() or []:
        p.setdefault('calls',[]).append({'name':getattr(fc,'name',''),'args':getattr(fc,'args',{})})
    for fr in ev.get_function_responses() or []:
        p.setdefault('responses',[]).append({'name':getattr(fr,'name',''),'response':getattr(fr,'response','')})
    if ev.usage_metadata is not None:
        um=ev.usage_metadata
        p['usage']={'prompt':getattr(um,'prompt_token_count',0) or 0,'completion':getattr(um,'response_token_count',0) or 0,'cached':getattr(um,'cached_content_token_count',0) or 0}
    tr.append(p)
ms=(time.perf_counter()-t0)*1000
_final=[]
for _ev in tr:
    if _ev['kind']=='final': _final += _ev.get('parts') or []
answer='\n'.join(str(_p) for _p in _final)
usage={'prompt':sum(e.get('usage',{}).get('prompt',0) for e in tr),'completion':sum(e.get('usage',{}).get('completion',0) for e in tr),'cached':sum(e.get('usage',{}).get('cached',0) for e in tr)}
tools=[c.get('name') for e in tr for c in e.get('calls',[])]
cite=S._cite(tr, answer); after=S._ov_snapshot()
S._emit(events,'agentic',eid,cat,'agent',ms=ms,tokens=usage,detail={'tool_calls':tools,'citation':cite,'observer_delta':{'vectors':after.get('vectors')}})
res={'strategy':'agentic','eid':eid,'category':cat,'uris':cite.get('retrieved',[]),'answer':answer,'events':events,'extra':{'transcript':tr,'usage':usage,'citation':cite,'tools':tools}}
open(out,'w').write(json.dumps(res, ensure_ascii=False, default=str))
