import {useEffect,useRef,useState} from 'react';
import {request,type Connection} from './api';

type Watch={id:string;conversation?:string;enabled:boolean;status:string;project?:string;directory?:string;
  objective?:string;model?:string;files?:string[];debounce_ms?:number;generation?:number;
  last?:{id:string;state:string;task:string|null;task_status:string|null}|null};
type State={items:Watch[];paused:boolean;scan_ms:number;invalid_records:number};
type Props={connection:Connection|null;project:string;model:string;settings:Record<string,unknown>;
  ensureConversation:()=>Promise<string>;onTask:(id:string,conversation:string)=>Promise<void>};

export function DirectoryWatchPanel({connection,project,model,settings,ensureConversation,onTask}:Props){
  const [state,setState]=useState<State|null>(null),[directory,setDirectory]=useState('.'),[files,setFiles]=useState('');
  const [question,setQuestion]=useState('Inspect these files and report potential issues.'),[debounce,setDebounce]=useState(3);
  const [working,setWorking]=useState(false),[error,setError]=useState('');
  const generation=useRef(0),sequence=useRef(0);
  const load=async(version:number)=>{
    if(!connection)return;
    const number=++sequence.current;
    try{
      const result=await request<State>(connection,'/watches');
      if(version===generation.current&&number===sequence.current)setState(result);
    }catch(e){if(version===generation.current&&number===sequence.current)setError(String(e));}
  };
  useEffect(()=>{
    const version=++generation.current;
    setState(null);setDirectory('.');setFiles('');setWorking(false);setError('');void load(version);
    const timer=setInterval(()=>void load(version),2000);
    return()=>{generation.current++;clearInterval(timer);};
  },[connection,project]);
  const action=async(callback:()=>Promise<unknown>)=>{
    if(!connection||working)return;
    const version=generation.current;
    setWorking(true);setError('');
    try{await callback();if(version===generation.current)await load(version);}
    catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current)setWorking(false);}
  };
  const create=async()=>{
    const version=generation.current,conversation=await ensureConversation();
    if(version!==generation.current||!connection)return;
    await request(connection,'/watches',{...settings,conversation,objective:question,model,project,directory,
      files:files.split('\n').map(value=>value.trim()).filter(Boolean),debounce_ms:debounce*1000});
  };
  return <section className="panel inspection-panel" aria-label="Directory-triggered inspections"><details>
    <summary>Inspect after directory changes</summary><div className="inspection-body">
    <p>Watch an approved project directory and inspect only the files you select. The first scan establishes a baseline without running a task. Matching changed observations separated by the debounce may queue one read-only inspection.</p>
    <label>Watched project-relative directory<input aria-label="Watched directory" maxLength={240} value={directory}
      disabled={working} onChange={event=>setDirectory(event.target.value)}/></label>
    <label>Files to inspect, one per line<textarea aria-label="Watch inspection files" rows={2} maxLength={2000}
      disabled={working} value={files} onChange={event=>setFiles(event.target.value)}/></label>
    <label>Question after changes<textarea aria-label="Watch inspection question" rows={2} maxLength={12000}
      disabled={working} value={question} onChange={event=>setQuestion(event.target.value)}/></label>
    <label>Debounce in seconds<input aria-label="Directory debounce seconds" type="number" min={1} max={60} step={1}
      disabled={working} value={debounce} onChange={event=>setDebounce(Number(event.target.value))}/></label>
    <button disabled={!connection||!state||working||!model||!directory.trim()||!files.trim()||!question.trim()||!Number.isInteger(debounce)||debounce<1||debounce>60}
      onClick={()=>void action(create)}>Enable directory inspection</button>
    <p className="muted">While Studio is open, observations run serially with a five-second minimum rescan delay. A busy agent defers scans. Credentials, links, known generated folders and agent state are excluded. Large or changing trees can be incomplete; incomplete scans never trigger work. Changes entirely between polls can be missed.</p>
    <p>All automatic inspections: {state?.paused?'paused':'enabled when their own controls permit'}. Pause/resume applies to interval and directory inspections.</p>
    <button disabled={!state||working} onClick={()=>void action(()=>request(connection!,'/scheduler/pause',{
      paused:!state?.paused,confirmed:state?.paused===true}))}>{state?.paused?'Resume automatic inspections':'Pause automatic inspections'}</button>
    <div aria-label="Saved directory watches">{state?.items.filter(item=>item.project===project||item.status==='invalid').map(item=><article className="inspection-state" key={item.id}>
      <h4>{item.objective??'Invalid saved watch'}</h4><p>{item.enabled?'Enabled':'Disabled'} · {item.status} · {item.model}</p>
      <p>Directory: {item.directory??'unavailable'} · debounce {item.debounce_ms===undefined?'unknown':item.debounce_ms/1000} seconds · queued generation {item.generation??'unknown'}</p>
      <p>Selected inspection files: {item.files?.join(', ')}</p>
      {item.status==='incomplete'&&<p role="status">Observation incomplete. Use a smaller readable directory within the limits; no task was authorized by that scan.</p>}
      {['input_changed','model_unavailable','queue_full','invalid'].includes(item.status)&&<p role="status">Review this watch's inputs, model and retained history before re-enabling. Changed project or restored history requires a new watch.</p>}
      {item.last&&<p>Latest directory run: {item.last.state}{item.last.task_status?` · task ${item.last.task_status}`:''}</p>}
      <button disabled={working||item.status==='invalid'} onClick={()=>void action(()=>request(connection!,`/watches/${item.id}/enabled`,{enabled:!item.enabled}))}>{item.enabled?'Disable directory inspection':'Enable saved directory inspection'}</button>
      {item.last?.task&&item.conversation&&<button disabled={working} onClick={()=>void action(()=>onTask(item.last!.task!,item.conversation!))}>Open directory inspection task</button>}
    </article>)}</div>
    {!!state?.invalid_records&&<p role="alert">Some saved watch records are invalid and cannot run. Review saved data; emergency stop remains available.</p>}
    <p className="muted">Re-enabling establishes a fresh baseline. Disabling cancels pending work; an admitted task has its own Cancel control. Emergency stop pauses all automatic inspections until explicit resume. No edits, commands, browser or desktop actions are available to these runs.</p>
    {working&&<p role="status">Saving watch control…</p>}{error&&<p role="alert">{error}</p>}
    </div></details></section>;
}
