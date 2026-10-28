import {useEffect,useRef,useState} from 'react';
import {type Connection,request} from './api';
import {Modal} from './Modal';

type Source={id:string;path:string;sha256:string;version:string;generation:string;state:string;reason:string};
type Preview={path:string;sha256:string;version:string;view:string;expected_generation:string|null;
  chunks:{text:string;start_char:number;end_char:number;start_line:number;end_line:number}[]};

export function FileMemoryControls({connection,project,conversation,version,busy,ensureConversation,onBusy,onChanged}:{
  connection:Connection|null;project:string;conversation:string;version:number;busy:boolean;
  ensureConversation:()=>Promise<string>;onBusy:(busy:boolean)=>void;onChanged:()=>void;
}) {
  const [sources,setSources]=useState<Source[]>([]),[path,setPath]=useState('');
  const [preview,setPreview]=useState<Preview|null>(null),[forget,setForget]=useState<Source|null>(null);
  const [working,setWorking]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const generation=useRef(0),currentConversation=useRef(conversation);
  currentConversation.current=conversation;
  useEffect(()=>{
    const expected=++generation.current;
    setSources([]);setPreview(null);setForget(null);setWorking(false);setError('');onBusy(false);
    if(connection)void request<Source[]>(connection,`/memory/sources?project=${encodeURIComponent(project)}`)
      .then(rows=>{if(expected===generation.current)setSources(rows);})
      .catch(e=>{if(expected===generation.current)setError(String(e));});
    return()=>{generation.current++;onBusy(false);};
  },[connection,project,version,onBusy]);
  useEffect(()=>{setPath('');setNotice('');},[connection,project]);
  useEffect(()=>{setPreview(null);setForget(null);},[conversation]);
  const run=async(work:(expected:number)=>Promise<void>)=>{
    if(!connection||busy||working)return;
    const expected=generation.current;setWorking(true);onBusy(true);setError('');setNotice('');
    try{await work(expected);}catch(e){if(expected===generation.current)setError(String(e));}
    finally{if(expected===generation.current){setWorking(false);onBusy(false);}}
  };
  const review=(selected:string)=>void run(async expected=>{
    const chat=conversation;
    setPreview(null);setForget(null);setPath(selected);
    const result=await request<Preview>(connection!,'/memory/sources/preview',{project,path:selected});
    if(expected===generation.current&&chat===currentConversation.current)setPreview(result);
  });
  const blocked=busy||working||!connection;
  return <section className="panel file-memory" aria-label="Saved file sources">
    <h3>Saved file sources</h3>
    <p>Save a selected UTF-8 project file as historical context. Original files stay unchanged.</p>
    <form onSubmit={e=>{e.preventDefault();review(path);}}>
      <label>Project-relative source file<input aria-label="Project-relative source file" maxLength={240}
        placeholder="docs/decisions.md" value={path} disabled={blocked} onChange={e=>setPath(e.target.value)}/></label>
      <button disabled={blocked||!path.trim()}>Preview file</button>
    </form>
    <small>Up to16 files,64,000 bytes/file. Review all excerpts before saving; never include credentials.</small>
    <p role="status">{working?'Working on saved file sources…':notice||'Saved metadata only. Check sources to observe current files.'}</p>
    {error&&<p role="alert">{error}</p>}
    <button disabled={blocked||!sources.length} onClick={()=>void run(async expected=>{
      const rows=await request<Source[]>(connection!,'/memory/sources/check',{project});
      if(expected!==generation.current)return;
      setSources(rows);setNotice('Sources checked. Matches are point-in-time observations.');onChanged();
    })}>Check sources</button>
    {!sources.length&&<p>No saved file sources.</p>}
    <ul>{sources.map(source=><li key={source.id}>
      <p><code>{source.path}</code> · Source state: <strong>{source.state}</strong>{source.reason?` (${source.reason})`:''}</p>
      <details><summary>Saved source identity</summary><p>Raw SHA-256: <code>{source.sha256}</code></p>
        <p>Resource version: <code>{source.version}</code></p></details>
      <div className="approval-buttons">
        <button disabled={blocked} onClick={()=>review(source.path)}>Review reimport</button>
        <button disabled={blocked} onClick={()=>setForget(source)}>Forget saved file</button>
      </div>
    </li>)}</ul>
    {preview&&<Modal title="file-preview-title" className="file-memory-review" onDismiss={()=>setPreview(null)}>
      <h2 id="file-preview-title">{preview.expected_generation?'Replace saved file excerpts?':'Save this file as memory?'}</h2>
      <p>Project: <code>{project}</code> · File: <code>{preview.path}</code></p>
      <p>Review {preview.chunks.length} excerpts below. This saves local historical text and source references;
        it grants no tool permissions. Source-chat deletion removes these excerpts. The original file remains.</p>
      <p>Raw SHA-256: <code>{preview.sha256}</code></p>
      <p>Resource version: <code>{preview.version}</code></p>
      <p>View: {preview.view}. Character offsets are zero-based and end-exclusive; lines are one-based.</p>
      {preview.expected_generation&&<p>Confirmation replaces all prior excerpts and vectors for this file.
        Earlier memory-influenced history is excluded. Reindex saved notes afterward if using related wording.</p>}
      <div className="file-excerpts">{preview.chunks.map((chunk,i)=><div key={i}>
        <h3>Excerpt {i+1} · lines {chunk.start_line}–{chunk.end_line} · characters {chunk.start_char}–{chunk.end_char}</h3>
        <pre>{chunk.text}</pre>
      </div>)}</div>
      <div className="approval-buttons"><button data-dialog-initial onClick={()=>setPreview(null)}>Cancel</button>
        <button className="primary" disabled={blocked} onClick={()=>{
          const reviewed=preview;setPreview(null);
          void run(async expected=>{
            const chat=conversation||await ensureConversation();
            if(expected!==generation.current||currentConversation.current&&currentConversation.current!==chat)return;
            await request(connection!,'/memory/sources',{project,conversation:chat,path:reviewed.path,
              sha256:reviewed.sha256,version:reviewed.version,expected_generation:reviewed.expected_generation,confirmed:true});
            if(expected!==generation.current)return;
            setNotice('File excerpts saved. Reindex saved notes before using related wording.');onChanged();
          });
        }}>{preview.expected_generation?'Replace saved excerpts':'Save file memory'}</button></div>
    </Modal>}
    {forget&&<Modal title="file-forget-title" onDismiss={()=>setForget(null)}>
      <h2 id="file-forget-title">Forget saved file source?</h2>
      <p>Remove all saved excerpts and vectors for <code>{forget.path}</code>? Earlier memory-influenced history
        is excluded; visible transcripts remain. The original file stays unchanged. This is not secure disk erasure.</p>
      <div className="approval-buttons"><button data-dialog-initial onClick={()=>setForget(null)}>Cancel</button>
        <button className="danger" disabled={blocked} onClick={()=>{
          const selected=forget;setForget(null);
          void run(async expected=>{
            await request(connection!,`/memory/sources/${selected.id}/forget`,{project,confirmed:true});
            if(expected!==generation.current)return;
            setNotice('Saved file excerpts forgotten. Original file unchanged.');onChanged();
          });
        }}>Forget all excerpts</button></div>
    </Modal>}
  </section>;
}
