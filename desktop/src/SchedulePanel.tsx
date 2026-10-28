import {useEffect,useRef,useState} from 'react';
import {request,type Connection} from './api';
import {scheduleTime} from './schedule-time.mjs';

type Item={id:string;conversation?:string;enabled:boolean;status:string;project?:string;objective?:string;
  files?:string[];model?:string;interval_ms?:number;next_ms?:number;misfire?:string;timezone?:string;
  last?:{id:string;state:string;task:string|null;task_status:string|null;due_ms:number}|null};
type State={items:Item[];paused:boolean;error:string|null;timezones:string[]};
type Props={connection:Connection|null;project:string;model:string;settings:Record<string,unknown>;
  ensureConversation:()=>Promise<string>;onTask:(id:string,conversation:string)=>Promise<void>};

export function SchedulePanel({connection,project,model,settings,ensureConversation,onTask}:Props){
  const [state,setState]=useState<State|null>(null),[files,setFiles]=useState(''),[question,setQuestion]=useState('Inspect these files and report changes or potential issues.');
  const [minutes,setMinutes]=useState(60),[misfire,setMisfire]=useState('coalesce'),[zone,setZone]=useState('UTC');
  const [working,setWorking]=useState(false),[error,setError]=useState('');
  const generation=useRef(0),sequence=useRef(0);
  const load=async(version:number)=>{
    if(!connection)return;
    const number=++sequence.current;
    try{
      const result=await request<State>(connection,'/schedules');
      if(version===generation.current&&number===sequence.current)setState(result);
    }catch(e){if(version===generation.current&&number===sequence.current)setError(String(e));}
  };
  useEffect(()=>{
    const version=++generation.current;
    setState(null);setFiles('');setError('');setWorking(false);
    void load(version);
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
    await request(connection,'/schedules',{...settings,conversation,objective:question,model,project,
      files:files.split('\n').map(value=>value.trim()).filter(Boolean),interval_ms:minutes*60000,misfire,timezone:zone});
  };
  return <section className="panel inspection-panel" aria-label="Scheduled read-only inspections">
    <details><summary>Scheduled read-only inspections</summary><div className="inspection-body">
    <p>Runs while Studio is open, using only your selected files and model. Each run uses current file contents. No edits, commands, browser or desktop actions are allowed.</p>
    {state?.paused&&<p role="status">Automatic inspections are paused. Emergency stop keeps this pause across restarts.</p>}
    <button disabled={!state||working} onClick={()=>void action(()=>request(connection!,'/scheduler/pause',{
      paused:!state?.paused,confirmed:state?.paused===true}))}>{state?.paused?'Resume scheduled inspections':'Pause scheduled inspections'}</button>
    <label>Schedule files, one project-relative path per line<textarea aria-label="Schedule files" rows={2} maxLength={2000}
      disabled={working} value={files} onChange={e=>setFiles(e.target.value)}/></label>
    <label>Schedule question<textarea aria-label="Schedule question" rows={2} maxLength={12000}
      disabled={working} value={question} onChange={e=>setQuestion(e.target.value)}/></label>
    <label>Interval in minutes<input aria-label="Schedule interval in minutes" type="number" min={1} max={43200} step={1}
      value={minutes} disabled={working} onChange={e=>setMinutes(Number(e.target.value))}/></label>
    <label>Missed runs<select aria-label="Schedule missed runs" value={misfire} disabled={working} onChange={e=>setMisfire(e.target.value)}>
      <option value="coalesce">Run the latest missed slot once</option><option value="skip">Skip missed intervals</option></select></label>
    <label>Display timezone<select aria-label="Schedule timezone" value={zone} disabled={working} onChange={e=>setZone(e.target.value)}>
      {(state?.timezones??['UTC']).map(value=><option key={value}>{value}</option>)}</select></label>
    <p className="muted">Intervals use elapsed UTC time. DST changes the displayed offset, not the interval. Busy Studio keeps at most one pending run per schedule. Disabling cancels pending work; an already running task has its own Cancel control.</p>
    <button disabled={!connection||!state||working||!model||!files.trim()||!question.trim()||!Number.isInteger(minutes)||minutes<1||minutes>43200}
      onClick={()=>void action(create)}>Enable interval inspection</button>
    <div aria-label="Saved interval schedules">{state?.items.filter(item=>item.project===project||item.status==='invalid').map(item=><article className="inspection-state" key={item.id}>
      <h4>{item.objective??'Invalid saved schedule'}</h4><p>{item.enabled?'Enabled':'Disabled'} · {item.status} · {item.model}</p>
      {item.next_ms!==undefined&&<p>Next slot: {scheduleTime(item.next_ms,item.timezone!)} ({item.timezone}) · every {item.interval_ms!/60000} minutes · {item.misfire}</p>}
      <p>{item.files?.join(', ')}</p>
      {item.last&&<p>Latest run: {item.last.state}{item.last.task_status?` · task ${item.last.task_status}`:''}</p>}
      <button disabled={working||item.status==='invalid'} onClick={()=>void action(()=>request(connection!,`/schedules/${item.id}/enabled`,{enabled:!item.enabled}))}>{item.enabled?'Disable interval inspection':'Enable saved inspection'}</button>
      {item.last?.task&&item.conversation&&<button disabled={working} onClick={()=>void action(()=>onTask(item.last!.task!,item.conversation!))}>Open latest inspection task</button>}
    </article>)}</div>
    {state?.error&&!state.paused&&<p role="status">{state.error}</p>}{working&&<p role="status">Saving schedule control…</p>}
    {error&&<p role="alert">{error}</p>}
    </div></details>
  </section>;
}
