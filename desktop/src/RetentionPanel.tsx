import {useEffect,useRef,useState} from 'react';
import {request,type Connection} from './api';
import {Modal} from './Modal';

type Policy={older_than_days:number;keep_recent:number;batch_size:number};
type Summary={created:number;deleted:number;counts:Record<string,number>};
type Preview={id:string|null;expires:number|null;cutoff:number;policy:Policy;more:boolean;
  items:{id:string;title:string;last_activity:number}[];counts:Record<string,number>};
const initial:Policy={older_than_days:90,keep_recent:50,batch_size:20};
const same=(left:Policy,right:Policy|null)=>!!right&&Object.keys(left).every(key=>left[key as keyof Policy]===right[key as keyof Policy]);

export function RetentionPanel({connection,busy,protectedConversation,onChanged}:{
  connection:Connection|null;busy:boolean;protectedConversation:string;onChanged:()=>Promise<void>;
}){
  const [policy,setPolicy]=useState<Policy>(initial),[saved,setSaved]=useState<Policy|null>(null);
  const [working,setWorking]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [preview,setPreview]=useState<Preview|null>(null),[confirm,setConfirm]=useState(false);
  const [summary,setSummary]=useState<Summary|null>(null);
  const generation=useRef(0),reviewRequest=useRef(0);
  useEffect(()=>{
    const version=++generation.current;
    setPolicy(initial);setSaved(null);setWorking(false);setError('');setNotice('');setPreview(null);setConfirm(false);setSummary(null);
    if(connection)void request<{policy:Policy;automatic:false;last_action:Summary|null}>(connection,'/retention')
      .then(data=>{if(version===generation.current){setPolicy(data.policy);setSaved(data.policy);setSummary(data.last_action);}})
      .catch(e=>{if(version===generation.current)setError(String(e));});
    return()=>{generation.current++;};
  },[connection]);
  useEffect(()=>{reviewRequest.current++;setPreview(null);setConfirm(false);},[protectedConversation]);
  const change=(key:keyof Policy,value:number)=>{reviewRequest.current++;setPolicy(old=>({...old,[key]:value}));setPreview(null);setConfirm(false);};
  const save=async()=>{
    if(!connection||busy||working)return;
    const version=generation.current;
    setWorking(true);setError('');setNotice('');setPreview(null);setConfirm(false);
    try{
      const data=await request<{policy:Policy}>(connection,'/retention/policy',policy);
      if(version===generation.current){setSaved(data.policy);setNotice('Retention settings saved. No conversations were deleted.');}
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current)setWorking(false);}
  };
  const inspect=async()=>{
    if(!connection||busy||working||!same(policy,saved))return;
    const version=generation.current,review=++reviewRequest.current;
    setWorking(true);setError('');setNotice('');setPreview(null);
    try{
      const data=await request<Preview>(connection,'/retention/preview',
        {protected:protectedConversation?[protectedConversation]:[]});
      if(version===generation.current&&review===reviewRequest.current)setPreview(data);
    }catch(e){if(version===generation.current&&review===reviewRequest.current)setError(String(e));}
    finally{if(version===generation.current)setWorking(false);}
  };
  const apply=async()=>{
    if(!connection||busy||working||!preview?.id)return;
    const version=generation.current;
    setWorking(true);setError('');setNotice('');
    try{
      const result=await request<Summary>(connection,'/retention/apply',{preview:preview.id,confirmed:true});
      if(version!==generation.current)return;
      setSummary(result);setPreview(null);setNotice(`Deleted ${result.deleted} conversations in the reviewed batch.`);
      await onChanged();
    }catch(e){
      if(version===generation.current){setPreview(null);setError(String(e));await onChanged().catch(()=>{});}
    }finally{if(version===generation.current){setWorking(false);setConfirm(false);}}
  };
  const counts=preview?.counts||{};
  const description=`${counts.conversations||0} conversations, ${counts.messages||0} messages, ${counts.tasks||0} tasks, ${counts.attachments||0} attachments, ${counts.goals||0} saved goals and ${counts.memories||0} saved memories`;
  return <div className="panel retention-panel"><h3>Conversation retention</h3>
    <p>Manually review old conversations across this Studio. Saving settings never deletes data.</p>
    <p>The selected chat, recent activity, unfinished goals, pending uploads and active tasks are protected. Project files, backups and generation folders are excluded.</p>
    <form onSubmit={event=>{event.preventDefault();void save();}}>
      <label>Older than (days)<input aria-label="Retention age in days" type="number" required min="1" max="3650" step="1"
        disabled={!connection||busy||working} value={policy.older_than_days} onChange={e=>change('older_than_days',Number(e.target.value))}/></label>
      <label>Keep newest conversations<input aria-label="Retention recent conversations" type="number" required min="0" max="5000" step="1"
        disabled={!connection||busy||working} value={policy.keep_recent} onChange={e=>change('keep_recent',Number(e.target.value))}/></label>
      <label>Conversations per batch<input aria-label="Retention batch size" type="number" required min="1" max="50" step="1"
        disabled={!connection||busy||working} value={policy.batch_size} onChange={e=>change('batch_size',Number(e.target.value))}/></label>
      <button type="submit" disabled={!connection||busy||working}>Save retention settings</button>
    </form>
    <div><button disabled={!connection||busy||working||!same(policy,saved)} onClick={()=>void inspect()}>Preview retention</button>
      {!same(policy,saved)&&saved&&<p>Save changed settings before previewing.</p>}</div>
    {working&&!confirm&&<p aria-live="polite">Processing retention settings or preview…</p>}
    {error&&<p role="alert">{error}</p>}
    {notice&&<p role="status">{notice}</p>}
    {summary&&<p className="muted">Last recorded batch: {summary.deleted} conversations, {new Date(summary.created*1000).toLocaleString()}.</p>}
    {preview&&<div className="retention-preview"><p>{description} in this batch.</p>
      <p>{counts.context_recipients||0} kept chats will have their future memory context reset; visible transcripts remain.</p>
      {preview.more&&<p>More eligible conversations remain. Every further batch needs a new preview and confirmation.</p>}
      {preview.items.length?<><ul>{preview.items.map(item=><li key={item.id}><strong>{item.title||'Untitled conversation'}</strong>
        <span> · last activity {new Date(item.last_activity*1000).toLocaleDateString()}</span></li>)}</ul>
        <button className="danger" disabled={busy||working||!preview.id} onClick={()=>setConfirm(true)}>Review retention deletion</button></>
        :<p>No conversations match these settings.</p>}
    </div>}
    <p className="muted">Reviews expire after five minutes. Each preview is limited to 50 conversations, 50,000 related rows and 64 MiB; processing has a cooperative five-second budget.</p>
    <p className="muted">Chat export is limited to 5,000 messages / 8 MiB and omits attachment contents. Private backups retain deleted history; this is not secure erasure.</p>
    {confirm&&preview&&<Modal title="retention-confirm-title" onDismiss={()=>{if(!working)setConfirm(false);}}>
      <h2 id="retention-confirm-title">Delete this reviewed retention batch?</h2>
      <p>Delete {description}, including their execution and verification records?</p>
      <p>Source memories are removed. Future memory context for {counts.context_recipients||0} kept chats will reset. Project files and saved backups remain.</p>
      <ul>{preview.items.map(item=><li key={item.id}>{item.title||'Untitled conversation'}</li>)}</ul>
      {working&&<p aria-live="polite">Applying the approved batch. Wait for the result before navigating.</p>}
      <div className="approval-buttons"><button data-dialog-initial disabled={working} onClick={()=>setConfirm(false)}>Cancel</button>
        <button className="danger" disabled={busy||working} onClick={()=>void apply()}>Delete reviewed conversations</button></div>
    </Modal>}
  </div>;
}
