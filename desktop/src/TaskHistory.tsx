import {useEffect,useRef,useState} from 'react';
import {request,type Connection,type HistoryPage,type Task} from './api';
import {TaskDiagnostics} from './TaskDiagnostics';
import {TaskJournal} from './TaskJournal';

type Props={tasks:Task[];connection:Connection|null;busy:boolean;onOpen:(task:Task)=>void;onNewInstruction:(task:Task)=>void};

export function TaskHistory(props:Props){
  const {tasks,connection,busy,onOpen,onNewInstruction}=props;
  type Paging={cursor:string|null;previous:(string|null)[];next:string|null;loading:boolean};
  const initial:Paging={cursor:null,previous:[],next:null,loading:false};
  const [items,setItems]=useState<Task[]>([]),[paging,setPaging]=useState(initial),[error,setError]=useState('');
  const navigation=useRef(initial),generation=useRef(0),latest=useRef(tasks);
  latest.current=tasks;
  const update=(value:Paging)=>{navigation.current=value;setPaging(value);};
  const load=async(cursor:string|null=null,previous:(string|null)[]=[])=>{
    if(!connection)return;
    const version=++generation.current,before=navigation.current;
    update({cursor,previous,next:null,loading:true});setError('');
    try {
      const params=new URLSearchParams({limit:'50'});if(cursor)params.set('cursor',cursor);
      const page=await request<HistoryPage<Task>>(connection,`/history/tasks?${params}`);
      if(version!==generation.current)return;
      setItems(page.items.map(row=>latest.current.find(task=>task.id===row.id)??row));
      update({cursor,previous,next:page.next,loading:false});
    } catch(reason) {
      if(version!==generation.current)return;
      setError(String(reason));update({...before,loading:false});
    }
  };
  useEffect(()=>{void load();return()=>{++generation.current;};},[connection]);
  useEffect(()=>{
    if(!navigation.current.loading&&navigation.current.cursor===null)void load();
    else setItems(old=>old.map(row=>tasks.find(task=>task.id===row.id)??row));
  },[tasks]);
  return (<section className="settings-page"><div className="page-intro"><span className="eyebrow">EXECUTION RECORD</span><h2>Task history</h2><p>Completed actions, interrupted runs and their conversation context.</p></div>
        <nav className="message-pages" aria-label="Task history pages">
          <button disabled={paging.loading||!paging.next} onClick={()=>void load(paging.next,[...paging.previous,paging.cursor])}>Older tasks</button>
          <span role="status">{paging.loading?'Loading tasks…':`${items.length} shown · page ${paging.previous.length+1}`}</span>
          <button disabled={paging.loading||!paging.previous.length} onClick={()=>void load(paging.previous.at(-1)!,paging.previous.slice(0,-1))}>Newer tasks</button>
          <button disabled={paging.loading} onClick={()=>void load()}>Latest tasks</button>
        </nav>
        {error&&<p role="alert">{error} Reload Latest tasks to retry.</p>}
        {!paging.loading&&!error&&items.length === 0 && <div className="empty-panel">Your tasks will appear here after your first request.</div>}
        {items.map(t => <div key={t.id}><button className="history-row" disabled={paging.loading} onClick={()=>onOpen(t)}>
          <div><strong>{t.mode} task</strong><small>{t.model} · {t.profile || 'unified'} · {new Date(t.created * 1000).toLocaleString()}</small></div><span className={`badge ${t.status}`}>{t.status}</span></button>
          <TaskDiagnostics connection={connection} task={t}/>
          <TaskJournal connection={connection} task={t} disabled={busy} onNewInstruction={()=>onNewInstruction(t)}/></div>)}
      </section>);
}
