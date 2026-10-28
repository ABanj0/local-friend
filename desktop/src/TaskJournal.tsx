import { useEffect, useRef, useState } from 'react';
import { type Connection, type Task, request } from './api';

type Artifact = {path:string|null;resource_sha256:string;observation:string;sha256:string|null;proposed_sha256:string|null};
type Operation = {id:string;step:string;ordinal:number;tool:string;effect:string;state:string;outcome:string|null;
  arguments_sha256:string;preconditions:Artifact[];verification_ids:string[]};
type Journal = {available:boolean;partial:boolean;steps:{id:string;ordinal:number;state:string;outcome:string|null}[];operations:Operation[]};
type Inspection = {note:string;artifacts:{path:string|null;current:string;matches_before:boolean|null;matches_proposed:boolean|null}[]};

export function TaskJournal({connection,task,onNewInstruction,disabled}:{connection:Connection|null;task:Task;onNewInstruction:()=>void;disabled:boolean}) {
  const [journal,setJournal]=useState<Journal|null>(null);
  const [inspections,setInspections]=useState<Record<string,Inspection>>({});
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const generation=useRef(0);
  useEffect(()=>{generation.current++;setJournal(null);setInspections({});setError('');setBusy(false);
    return()=>{generation.current++;};},[connection,task.id,task.status]);
  const load=async(operation?:string)=>{
    if(!connection)return;
    const current=++generation.current;
    setBusy(true);setError('');
    try {
      const path=`/tasks/${encodeURIComponent(task.id)}/journal`;
      if(operation){
        const result=await request<Inspection>(connection,`${path}/${encodeURIComponent(operation)}/inspect`,undefined,AbortSignal.timeout(5000));
        if(current===generation.current)setInspections(previous=>({...previous,[operation]:result}));
      } else {
        const result=await request<Journal>(connection,path,undefined,AbortSignal.timeout(5000));
        if(current===generation.current){setJournal(result);setInspections({});}
      }
    } catch(problem){if(current===generation.current)setError(problem instanceof Error?problem.message:String(problem));}
    finally {if(current===generation.current)setBusy(false);}
  };
  const match=(value:boolean|null)=>value===null?'unavailable':value?'yes':'no';
  return <details className="task-diagnostics task-journal"><summary>Execution journal and recovery</summary>
    <p>Inspect evidence before writing a new instruction. Unknown effects require manual reconciliation. Actions and approvals are never replayed; checkpoint resume is unavailable.</p>
    <button type="button" disabled={!connection||busy} onClick={()=>void load()}>{busy?'Loading…':'Load execution journal'}</button>
    {error&&<p role="alert">{error}</p>}
    {journal&&<div className="journal-result">
      {!journal.available?<p>No operation journal was captured for this older run.</p>:<>
        {journal.partial&&<p role="status">Partial journal: some records are unavailable.</p>}
        {journal.steps.length===0&&<p>No tool decisions were recorded.</p>}
        {journal.steps.map(step=><section key={step.id}>
          <h4>Decision {step.ordinal} · {step.state}</h4>
          {journal.operations.filter(op=>op.step===step.id).map(op=><div className="journal-operation" key={op.id}>
            <p>{op.tool} · {op.effect} · {op.state==='completed'?'result observed':op.state==='intent'?'intent committed':op.state}{op.outcome?` · ${op.outcome.replaceAll('_',' ')}`:''}</p>
            <p>{op.verification_ids.length} verifier references. Result observation does not certify whole-task success.</p>
            <details><summary>Recorded artifact preconditions ({op.preconditions.length})</summary>
              <ul>{op.preconditions.map(artifact=><li key={artifact.resource_sha256}>{artifact.path??'Path withheld'} · {artifact.observation}
                {artifact.sha256&&<pre>Before SHA-256: {artifact.sha256}</pre>}
                {artifact.proposed_sha256&&<pre>Proposed SHA-256: {artifact.proposed_sha256}</pre>}</li>)}</ul>
            </details>
            <button type="button" disabled={!connection||busy||op.preconditions.length===0} onClick={()=>void load(op.id)}>Inspect current artifacts</button>
            {inspections[op.id]&&<div className="journal-inspection" role="status"><p>{inspections[op.id].note}</p>
              <ul>{inspections[op.id].artifacts.map((artifact,index)=><li key={index}>{artifact.path??'Path withheld'} · current: {artifact.current} · matches recorded: {match(artifact.matches_before)} · matches proposed: {match(artifact.matches_proposed)}</li>)}</ul>
            </div>}
          </div>)}
        </section>)}
      </>}
      <button type="button" disabled={disabled} onClick={onNewInstruction}>Write a new instruction</button>
    </div>}
  </details>;
}
