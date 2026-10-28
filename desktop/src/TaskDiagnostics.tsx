import { useEffect, useRef, useState } from 'react';
import { type Connection, type Task, request } from './api';

type Diagnostic = {version:number;run_id:string|null;task_state:string;available:boolean;partial:boolean;
  spans:{id:string|null;kind:string;tool:string|null;observation_state:string;duration_ns:number|null;index:number|null}[];
  summary:{latency_ms:Record<string,number|null>;tool_outcomes:Record<string,number>;incomplete_spans:number};
  inference: {generated_tokens:number;tokens_per_second:number|null;model_calls:number}|null;
  verifications:{id:string;kind:string;status:string}[]};

export function TaskDiagnostics({connection,task}:{connection:Connection|null;task:Task}) {
  const [result,setResult]=useState<Diagnostic|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const generation=useRef(0);
  useEffect(()=>{generation.current++;setResult(null);setError('');setBusy(false);return()=>{generation.current++;};},[connection,task.id,task.status]);
  const load=async()=>{
    if(!connection)return;
    const current=++generation.current;
    setBusy(true);setError('');
    try {const data=await request<Diagnostic>(connection,`/tasks/${encodeURIComponent(task.id)}/diagnostics`,undefined,AbortSignal.timeout(5000));
      if(current===generation.current)setResult(data);}
    catch(problem){if(current===generation.current)setError(problem instanceof Error?problem.message:String(problem));}
    finally {if(current===generation.current)setBusy(false);}
  };
  const download=()=>{
    if(!result)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download=`diagnostic-${Date.now()}.json`;
    document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const ms=(key:string)=>result?.summary.latency_ms[key]==null?'unknown':`${(result.summary.latency_ms[key]!/1000).toFixed(3)}s`;
  return <details className="task-diagnostics"><summary>Run diagnostics</summary>
    <p>Content-free timing and execution observations. Reported output does not certify task success.</p>
    <button type="button" onClick={()=>void load()} disabled={!connection||busy}>{busy?'Loading…':'Load diagnostics'}</button>
    {error&&<p role="alert">{error}</p>}
    {result&&<div className="diagnostic-result" role="status">
      <p>Run {result.run_id??'redacted'} · {result.task_state}</p>
      <p>{!result.available?'No trace was captured for this run.':result.partial?'Partial observations; interrupted or omitted work is unknown.':'Trace captured; whole-task verification is not assessed.'}</p>
      <dl><dt>Worker wall time</dt><dd>{ms('worker_wall_ms')}</dd><dt>Model calls</dt><dd>{ms('model_ms')}</dd>
        <dt>Tools excluding approval</dt><dd>{ms('tool_active_ms')}</dd><dt>Approval waits</dt><dd>{ms('approval_ms')}</dd>
        <dt>Cleanup</dt><dd>{ms('cleanup_ms')}</dd></dl>
      <p>{result.inference?`${result.inference.generated_tokens} generated tokens across ${result.inference.model_calls} measured model calls.`:'Inference counters unavailable.'}</p>
      <p>{result.verifications.length} verifier observations · {result.summary.incomplete_spans} incomplete spans</p>
      <p>Tool outcomes: {Object.entries(result.summary.tool_outcomes).map(([status,count])=>`${status.replaceAll('_',' ')}: ${count}`).join(', ')||'none observed'}</p>
      <ul>{result.verifications.map(check=><li key={check.id}>{check.kind}: {check.status}</li>)}</ul>
      <details><summary>Trace spans ({result.spans.length})</summary><ul>{result.spans.map((span,index)=><li key={span.id??index}>
        {span.kind}{span.index!==null?` ${span.index}`:''}{span.tool?` · ${span.tool}`:''} · {span.observation_state} · {span.duration_ns===null?'duration unknown':`${(span.duration_ns/1e9).toFixed(3)}s`}</li>)}</ul></details>
      <button type="button" onClick={download}>Download diagnostic JSON</button>
    </div>}
  </details>;
}
