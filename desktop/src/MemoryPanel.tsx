import {useCallback,useEffect,useRef,useState} from 'react';
import {type Connection,type Message,request} from './api';
import {Modal} from './Modal';
import {SemanticMemoryControls} from './SemanticMemoryControls';
import {FileMemoryControls} from './FileMemoryControls';

type Note={id:string;text:string;conversation:string;message:string|null;sha256:string;created:number;
  file?:{id:string;path:string;sha256:string;version:string;state:string;start_line:number;end_line:number;freshness_checked?:boolean}};
export function MemoryPanel({connection,project,conversation,messages,busy,ensureConversation,onSource,requested,version,chooseProject}: {
  connection:Connection|null;project:string;conversation:string;messages:Message[];busy:boolean;
  ensureConversation:()=>Promise<string>;onSource:(id:string)=>void;requested:string;version:number;chooseProject:()=>void;
}) {
  const [notes,setNotes]=useState<Note[]>([]),[query,setQuery]=useState(''),[text,setText]=useState('');
  const [source,setSource]=useState(''),[error,setError]=useState(''),[working,setWorking]=useState(false);
  const [forget,setForget]=useState<Note|null>(null);
  const [indexVersion,setIndexVersion]=useState(0),[embeddingBusy,setEmbeddingBusy]=useState(false);
  const [fileBusy,setFileBusy]=useState(false);
  const [semanticReady,setSemanticReady]=useState(false),[semantic,setSemantic]=useState(false);
  const onIndexReady=useCallback((ready:boolean)=>{setSemanticReady(ready);if(!ready)setSemantic(false);},[]);
  const blocked=busy||working||embeddingBusy||fileBusy;
  const generation=useRef(0);
  const call=<T,>(path:string,body?:unknown)=>{
    if(!connection)throw new Error('Backend is not connected');
    return request<T>(connection,path,body);
  };
  const refresh=async(expected=generation.current)=>{
    if(expected!==generation.current)return;
    const rows=await call<Note[]>(`${semantic&&query.trim()?'/memory/hybrid':'/memory'}?project=${encodeURIComponent(project)}&query=${encodeURIComponent(query)}`);
    if(expected===generation.current)setNotes(rows);
  };
  const run=async(work:(expected:number)=>Promise<unknown>)=>{
    const expected=generation.current;setWorking(true);setError('');
    try{await work(expected);}catch(e){if(expected===generation.current)setError(String(e));}
    finally{if(expected===generation.current)setWorking(false);}
  };
  useEffect(()=>{let cancelled=false;generation.current++;setWorking(false);setForget(null);setSource('');setNotes([]);setError('');setQuery('');
    if(connection)void call<Note[]>(`/memory?project=${encodeURIComponent(project)}`).then(rows=>{if(!cancelled)setNotes(rows);}).catch(e=>{if(!cancelled)setError(String(e));});
    return()=>{cancelled=true;generation.current++;};
    // Search is explicit; changing project resets results instead of reusing another project's data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[connection,project,version]);
  useEffect(()=>{setSource('');},[conversation]);
  useEffect(()=>{let cancelled=false;
    if(requested&&connection)void call<Note>(`/memory/${encodeURIComponent(requested)}?project=${encodeURIComponent(project)}`)
      .then(note=>{if(!cancelled)setForget(note);}).catch(e=>{if(!cancelled)setError(String(e));});
    return()=>{cancelled=true;};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[requested,connection,project,version]);
  return <section className="settings-page memory-page">
    <div className="page-intro"><span className="eyebrow">EXPLICIT LOCAL MEMORY</span><h2>Project memory</h2>
      <p>Save selected facts for later conversations. Notes are historical data, not tool permissions or verified current state.</p>
      <p>Conversations using memory stay bound to this project. Start a new conversation to use another project's memory.</p>
      <button disabled={blocked} onClick={chooseProject}>Choose project</button> <code>{project}</code></div>
    {error&&<p role="alert">{error}</p>}
    <SemanticMemoryControls connection={connection} project={project} version={version+indexVersion} busy={busy||working||fileBusy}
      onBusy={setEmbeddingBusy} onReady={onIndexReady}/>
    <FileMemoryControls connection={connection} project={project} conversation={conversation} version={version+indexVersion}
      busy={busy||working||embeddingBusy} ensureConversation={ensureConversation} onBusy={setFileBusy} onChanged={()=>{
        setIndexVersion(v=>v+1);setQuery('');setSemantic(false);
        const expected=generation.current;
        void call<Note[]>(`/memory?project=${encodeURIComponent(project)}`).then(rows=>{
          if(expected===generation.current)setNotes(rows);
        }).catch(e=>{if(expected===generation.current)setError(String(e));});
      }}/>
    <form className="panel" onSubmit={e=>{e.preventDefault();void run(async(expected)=>{
      const id=conversation||await ensureConversation();
      await call('/memory',{project,conversation:id,...(source?{message:source}:{text})});
      if(expected!==generation.current)return;
      setText('');setSource('');setIndexVersion(v=>v+1);await refresh(expected);
    });}}><h3>Remember a note</h3>
      <label>Source<select aria-label="Memory source" value={source} onChange={e=>setSource(e.target.value)}>
        <option value="">Explicit note</option>{messages.map(m=><option key={m.id} value={m.id}>{m.role}: {m.content.slice(0,70)}</option>)}
      </select></label>
      {!source&&<label>Note<textarea aria-label="Memory note" maxLength={4000} rows={4} value={text} onChange={e=>setText(e.target.value)}/></label>}
      <p>Only this text or the selected message is saved. Source-chat deletion removes its notes. Do not save credentials.</p>
      <button className="primary" disabled={blocked||(!source&&!text.trim())||!connection}>Remember</button>
    </form>
    <form className="panel memory-search" onSubmit={e=>{e.preventDefault();void run(refresh);}}>
      <label>Search notes<input aria-label="Search project memory" maxLength={500} value={query} onChange={e=>setQuery(e.target.value)}/></label>
      <label>Search mode<select aria-label="Memory search mode" value={semantic?'semantic':'keyword'} onChange={e=>setSemantic(e.target.value==='semantic')}>
        <option value="keyword">Keywords</option><option value="semantic" disabled={!semanticReady}>Related wording (local model)</option></select></label>
      <button disabled={working||fileBusy||!connection||(semantic&&(busy||embeddingBusy))}>Search</button><small>Search returns up to 5 matches; empty search shows the newest 100 of at most 1,000 notes.</small>
    </form>
    {!notes.length&&<p>No matching project memories.</p>}
    {notes.map(note=><article className="panel" key={note.id}>
      <code>memory:{note.id}</code><pre>{note.text}</pre>
      <small>{new Date(note.created*1000).toLocaleString()} · {note.file?'Saved file excerpt':note.message?'Selected message':'Explicit note'} · SHA-256 {note.sha256}</small>
      {note.file&&<p>Saved file: <code>{note.file.path}</code>, lines {note.file.start_line}–{note.file.end_line}. Source state: {note.file.state}.{note.file.freshness_checked===false?' Saved snapshot; file freshness was not checked.':''}</p>}
      <div className="approval-buttons"><button onClick={()=>onSource(note.conversation)}>Open source chat</button>
        <button disabled={blocked} onClick={()=>setForget(note)}>Forget</button></div>
    </article>)}
    {forget&&<Modal title="forget-title" onDismiss={()=>{if(!working)setForget(null);}}>
      <h2 id="forget-title">{forget.file?'Forget this saved file?':'Forget this memory?'}</h2><p>{forget.file?`Remove all saved excerpts and vectors for ${forget.file.path}? The original file remains.`:`Remove memory:${forget.id}?`} Earlier messages and generated goal checklists in this project's memory-bound conversations will be excluded from future model context. Visible chat transcripts remain; delete those chats to remove their messages. This is not a secure disk wipe.</p>
      <div className="approval-buttons"><button disabled={working} onClick={()=>setForget(null)}>Cancel</button>
        <button className="danger" disabled={blocked} onClick={()=>void run(async(expected)=>{
          await call(`/memory/${forget.id}/forget`,{project,confirmed:true});
          if(expected!==generation.current)return;
          setForget(null);setIndexVersion(v=>v+1);await refresh(expected);
        })}>Forget memory</button></div>
    </Modal>}
  </section>;
}
