import {useEffect,useRef,useState} from 'react';
import {request,type Connection,type Task} from './api';

type Checkpoint={supported:boolean;state?:string;completed_step?:number;attempt?:number;project?:string;
  source_task?:string|null;resumed_by?:string|null;files?:string[];pause_requested?:boolean;can_pause?:boolean;can_resume?:boolean};
type Props={connection:Connection|null;project:string;model:string;settings:Record<string,unknown>;busy:boolean;
  task:Task|undefined;selectedFile:string;ensureConversation:()=>Promise<string>;onStarted:(id:string)=>Promise<void>};

export function InspectionPanel({connection,project,model,settings,busy,task,selectedFile,ensureConversation,onStarted}:Props){
  const [files,setFiles]=useState(''),[question,setQuestion]=useState('Explain these files and report potential issues.');
  const [checkpoint,setCheckpoint]=useState<Checkpoint|null>(null),[working,setWorking]=useState(false),[error,setError]=useState('');
  const [expanded,setExpanded]=useState(false);
  const generation=useRef(0),requestNumber=useRef(0);
  const inspected=task?.mode==='inspection'?task:undefined;
  useEffect(()=>{if(inspected)setExpanded(true);},[inspected?.id]);
  useEffect(()=>{setFiles('');},[project]);
  useEffect(()=>{
    const version=++generation.current;
    setCheckpoint(null);setWorking(false);setError('');
    const load=async()=>{
      if(!connection||!inspected)return;
      const number=++requestNumber.current;
      try{
        const result=await request<Checkpoint>(connection,`/tasks/${inspected.id}/inspection`);
        if(version===generation.current&&number===requestNumber.current)setCheckpoint(result);
      }catch(e){if(version===generation.current&&number===requestNumber.current)setError(String(e));}
    };
    void load();
    const timer=inspected&&(['running','waiting'].includes(inspected.status)||inspected.runtime_state)?setInterval(()=>void load(),1500):null;
    return()=>{generation.current++;if(timer)clearInterval(timer);};
  },[connection,inspected?.id,inspected?.status,inspected?.runtime_state]);
  const start=async()=>{
    if(!connection||busy||working)return;
    const version=generation.current;
    setWorking(true);setError('');
    try{
      const conversation=await ensureConversation();
      if(version!==generation.current)return;
      const result=await request<{id:string}>(connection,'/inspections',{
        ...settings,conversation,objective:question,model,project,files:files.split('\n').map(value=>value.trim()).filter(Boolean)});
      if(version===generation.current)await onStarted(result.id);
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current)setWorking(false);}
  };
  const control=async(action:'pause'|'resume')=>{
    if(!connection||!inspected||working||(action==='resume'&&busy))return;
    const version=generation.current,number=++requestNumber.current;
    setWorking(true);setError('');
    try{
      const result=await request<{id?:string}>(connection,`/tasks/${inspected.id}/inspection/${action}`,{});
      if(version!==generation.current)return;
      if(result.id)await onStarted(result.id);
      else{
        const status=await request<Checkpoint>(connection,`/tasks/${inspected.id}/inspection`);
        if(version===generation.current&&number===requestNumber.current)setCheckpoint(status);
      }
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current)setWorking(false);}
  };
  const addSelected=()=>{
    let path=selectedFile.replaceAll('\\','/');
    const prefix=project.replaceAll('\\','/');
    if(prefix!=='.'&&path.startsWith(prefix+'/'))path=path.slice(prefix.length+1);
    setFiles(value=>[...new Set([...value.split('\n').filter(Boolean),path])].join('\n'));
  };
  return <section className="panel inspection-panel" aria-label="Resumable repository inspection">
    <details open={expanded} onToggle={event=>setExpanded(event.currentTarget.open)}>
    <summary>Read-only inspection with checkpoints</summary><div className="inspection-body">
    <p>Ask the local model about up to eight selected UTF-8 files (64 KB each). This mode only reads those files; it receives no earlier chat, memories or attachments.</p>
    <label>Project-relative files, one per line<textarea aria-label="Inspection files" rows={3} maxLength={2000}
      value={files} disabled={busy||working} onChange={event=>setFiles(event.target.value)}/></label>
    <button disabled={!selectedFile||busy||working} onClick={addSelected}>Add open file to inspection</button>
    <label>Inspection question<textarea aria-label="Inspection question" rows={2} maxLength={12000} value={question}
      disabled={busy||working} onChange={event=>setQuestion(event.target.value)}/></label>
    <button disabled={!connection||!model||busy||working||!files.trim()||!question.trim()} onClick={()=>void start()}>Start read-only inspection</button>
    {inspected&&<div className="inspection-state"><h4>Selected inspection · {inspected.id.slice(0,8)}</h4>
      <p>{inspected.model} · recorded project {checkpoint?.project??'unavailable'}</p>
      {checkpoint?.supported&&<><p>Checkpoint: {checkpoint.state??'unavailable'} · completed step {checkpoint.completed_step??0} · attempt {checkpoint.attempt??'unknown'} / 3</p>
        {checkpoint.files&&<p>Files: {checkpoint.files.join(', ')}</p>}
        {checkpoint.source_task&&<p>Continues task {checkpoint.source_task.slice(0,8)}. Earlier evidence remains with that task.</p>}
        {checkpoint.resumed_by&&<p>Already continued as task {checkpoint.resumed_by.slice(0,8)}.</p>}
        {checkpoint.pause_requested&&<p role="status">Pause requested; waiting for an acknowledged completed step and worker cleanup.</p>}
        <button disabled={working||!checkpoint.can_pause} onClick={()=>void control('pause')}>Pause at next inspection boundary</button>
        <button disabled={busy||working||!checkpoint.can_resume} onClick={()=>void control('resume')}>Resume inspected files</button>
      </>}
    </div>}
    <p className="muted">Pause is available after a completed checkpoint. Resume rechecks the recorded files, scope, model and settings, then starts a linked task with the remaining step budget. Changed inputs require a new inspection. Other agent modes cannot pause or resume.</p>
    {working&&<p role="status">Submitting inspection request…</p>}{error&&<p role="alert">{error}</p>}
    </div></details>
  </section>;
}
