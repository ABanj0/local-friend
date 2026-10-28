import {useEffect,useRef,useState} from 'react';
import {type Connection,type ModelStatus,request} from './api';
import {Modal} from './Modal';

type IndexStatus={state:string;notes:number;vectors:number;model:string|null;dimensions?:number;
  model_check:string;automatic_retrieval:boolean};

export function SemanticMemoryControls({connection,project,version,busy,onBusy,onReady}:{
  connection:Connection|null;project:string;version:number;busy:boolean;
  onBusy:(busy:boolean)=>void;onReady:(ready:boolean)=>void;
}) {
  const [index,setIndex]=useState<IndexStatus|null>(null),[models,setModels]=useState<string[]>([]);
  const [model,setModel]=useState(''),[error,setError]=useState(''),[working,setWorking]=useState(false);
  const [dialog,setDialog]=useState<'index'|'enable'|null>(null);
  const generation=useRef(0);
  const read=async()=>{
    if(!connection)throw new Error('Backend is not connected');
    return request<IndexStatus>(connection,`/memory/index?project=${encodeURIComponent(project)}`);
  };
  const apply=(status:IndexStatus)=>{setIndex(status);onReady(status.state==='locally_current');};
  useEffect(()=>{
    const current=++generation.current;
    setIndex(null);setModels([]);setModel('');setError('');setDialog(null);setWorking(false);onReady(false);onBusy(false);
    if(connection)void Promise.all([read(),request<ModelStatus>(connection,'/models')]).then(([status,installed])=>{
      if(current!==generation.current)return;
      apply(status);setModels(installed.models.map(m=>m.name));
      setModel(status.model&&installed.models.some(m=>m.name===status.model)?status.model:'');
    }).catch(e=>{if(current===generation.current)setError(String(e));});
    return()=>{generation.current++;onBusy(false);};
    // The connection/project/version define the request scope; helper functions use that snapshot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[connection,project,version,onBusy,onReady]);
  const run=async(path:string,body:unknown)=>{
    if(!connection)return;
    const current=generation.current;
    setWorking(true);onBusy(true);setError('');setDialog(null);
    try{
      await request(connection,path,body);
      if(current!==generation.current)return;
      const status=await read();
      if(current!==generation.current)return;
      setDialog(null);apply(status);
    }catch(e){if(current===generation.current)setError(String(e));}
    finally{if(current===generation.current){setWorking(false);onBusy(false);}}
  };
  const ready=index?.state==='locally_current';
  return <section className="panel semantic-memory" aria-label="Semantic project memory">
    <h3>Related-note retrieval</h3>
    <p>Use a local embedding model to find saved notes with related wording.</p>
    <p role="status">{working?'Waiting for local embeddings…':index?
      `${index.vectors} indexed / ${index.notes} saved · ${ready?'Saved notes match the index':index.state==='not_indexed'?'Not indexed':'Reindex required'}`:'Loading index status…'}</p>
    {index?.model&&<p>Embedding model: <code>{index.model}</code>. Model identity is checked before retrieval.</p>}
    <p>Chat context: <strong>{index?.automatic_retrieval?'Related wording':'Keywords'}</strong></p>
    {error&&<p role="alert">{error}</p>}
    <div className="approval-buttons">
      <button disabled={!connection||busy||working||!index?.notes} onClick={()=>setDialog('index')}>Index saved notes</button>
      {index?.automatic_retrieval?<button disabled={busy||working} onClick={()=>void run('/memory/index/enabled',{project,enabled:false})}>Use keyword context</button>:
        <button disabled={!connection||busy||working||!ready} onClick={()=>setDialog('enable')}>Enable related-note context</button>}
    </div>
    <small>Reindexing returns chats to keyword context. Emergency stop interrupts pending embedding requests.</small>
    {dialog&&<Modal title="semantic-memory-title" onDismiss={()=>{if(!working)setDialog(null);}}>
      <h2 id="semantic-memory-title">{dialog==='index'?'Index saved project notes?':'Enable related-note context?'}</h2>
      {dialog==='index'?<>
        <p>Send the {index?.notes} explicitly saved notes in <code>{project}</code> to the selected local embedding model. This replaces this project’s derived index.</p>
        <label>Embedding model<select aria-label="Embedding model" value={model} disabled={working} onChange={e=>setModel(e.target.value)}>
          <option value="">Select an installed embedding model</option>{models.map(name=><option key={name} value={name}>{name}</option>)}
        </select></label><p>The backend verifies embedding support before indexing.</p>
      </>:<p>Include relevant indexed notes in future chats and agent instructions for <code>{project}</code>. Notes remain historical context with visible source references.</p>}
      {error&&<p role="alert">{error}</p>}
      <div className="approval-buttons"><button disabled={working} onClick={()=>setDialog(null)}>Cancel</button>
        <button className="primary" disabled={working||(dialog==='index'&&!model)} onClick={()=>void run(
          dialog==='index'?'/memory/index':'/memory/index/enabled',dialog==='index'?{project,model,confirmed:true}:{project,enabled:true,confirmed:true})}>
          {working?'Working…':dialog==='index'?'Index notes':'Enable retrieval'}</button></div>
    </Modal>}
  </section>;
}
