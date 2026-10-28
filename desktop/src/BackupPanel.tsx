import {useEffect,useRef,useState} from 'react';
import {request,type Connection} from './api';
import {Modal} from './Modal';

type Summary={id:string;filename:string;bytes:number;created:number};
type Backup=Summary&{sha256:string;schema_version?:number;encrypted:false};
type Inventory={items:Summary[];entries:number;capacity:number;incomplete:boolean};
type RestoreStatus={generation:string|null;rollback:string|null;rollback_sha256?:string|null};
export function BackupPanel({connection,busy,onRestart}:{connection:Connection|null;busy:boolean;onRestart:()=>Promise<void>}){
  const [confirm,setConfirm]=useState(false),[working,setWorking]=useState(false);
  const [operation,setOperation]=useState('');
  const [saved,setSaved]=useState<Backup|null>(null),[error,setError]=useState('');
  const [inventory,setInventory]=useState<Inventory>({items:[],entries:0,capacity:20,incomplete:false});
  const [status,setStatus]=useState<RestoreStatus|null>(null),[chosen,setChosen]=useState('');
  const [inspected,setInspected]=useState<Backup|null>(null),[restoreConfirm,setRestoreConfirm]=useState<Backup|null>(null);
  const [undo,setUndo]=useState(false);
  const generation=useRef(0);
  const refreshRequest=useRef(0);
  const refresh=async(conn:Connection,version:number)=>{
    const requestID=++refreshRequest.current;
    try{
      const [rows,current]=await Promise.all([request<Inventory>(conn,'/backups'),request<RestoreStatus>(conn,'/restore/status')]);
      if(version===generation.current&&requestID===refreshRequest.current){setInventory(rows);setStatus(current);}
    }catch(error){if(version===generation.current&&requestID===refreshRequest.current)throw error;}
  };
  useEffect(()=>{generation.current++;setConfirm(false);setWorking(false);setSaved(null);setError('');
    setOperation('');
    setInventory({items:[],entries:0,capacity:20,incomplete:false});setStatus(null);setChosen('');setInspected(null);setRestoreConfirm(null);
    const version=generation.current;
    if(connection)void refresh(connection,version).catch(e=>{if(version===generation.current)setError(String(e));});
    return()=>{generation.current++;};
  },[connection]);
  const create=async()=>{
    if(!connection||busy||working)return;
    const version=generation.current;
    setConfirm(false);setWorking(true);setOperation('backup');setError('');setSaved(null);
    try{
      const result=await request<Backup>(connection,'/backups',{confirmed:true});
      if(version===generation.current){setSaved(result);setChosen(result.id);setInspected(result);await refresh(connection,version);}
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current){setWorking(false);setOperation('');}}
  };
  const inspect=async(id=chosen,previous=false)=>{
    if(!connection||busy||working||!id)return;
    const version=generation.current;
    setWorking(true);setOperation('inspect');setError('');setInspected(null);
    try{
      const result=await request<Backup>(connection,`/backups/${encodeURIComponent(id)}`);
      if(version===generation.current){setChosen(id);setInspected(result);if(previous){setUndo(true);setRestoreConfirm(result);}}
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current){setWorking(false);setOperation('');}}
  };
  const restore=async()=>{
    if(!connection||busy||working||!restoreConfirm)return;
    const item=restoreConfirm,version=generation.current;
    setRestoreConfirm(null);setWorking(true);setOperation('restore');setError('');setSaved(null);
    try{
      const draft=await request<{id:string;database_sha256:string;activated:false}>(connection,'/restore/prepare',
        {backup:item.id,sha256:item.sha256,confirmed:true});
      if(version!==generation.current)return;
      const result=await request<{restart_required:boolean}>(connection,'/restore/activate',
        {preparation:draft.id,sha256:draft.database_sha256,confirmed:true});
      if(version===generation.current&&result.restart_required)await onRestart();
    }catch(e){if(version===generation.current)setError(String(e));}
    finally{if(version===generation.current){setWorking(false);setOperation('');}}
  };
  const hasRoom=inventory.entries<=inventory.capacity-2&&!inventory.incomplete;
  return <div className="panel backup-panel"><h3>Studio data backup</h3>
    <p>Save chats, attachments, goals, preferences, memory and execution records to the app state directory's backups folder.</p>
    <p>Backups are private, unencrypted database files. Project files, model weights, configuration and pending screen previews are excluded.</p>
    <button disabled={!connection||busy||working} onClick={()=>setConfirm(true)}>{operation==='backup'?'Creating backup…':'Create Studio backup'}</button>
    <p aria-live="polite">{operation==='inspect'?'Inspecting saved backup…':operation==='restore'?'Validating restored data and preparing restart…':''}</p>
    {busy&&<p>Finish or cancel the active task first, including worker cleanup.</p>}
    <p className="muted">Up to 20 saved entries, 512 MiB per backup and 30 seconds per backup attempt. Automatic retention is not available yet.</p>
    {error&&<p role="alert">{error}</p>}
    {saved&&<div role="status"><p>Backup saved: <code>{saved.filename}</code> ({saved.bytes.toLocaleString()} bytes, schema{saved.schema_version}).</p>
      <p>SHA-256: <code>{saved.sha256}</code></p></div>}
    <h3>Restore saved Studio data</h3>
    <p>Select a backup, inspect its hash, then confirm restoring and restarting. The original database and a fresh rollback copy are retained.</p>
    <p>Storage: {inventory.incomplete?'at least ':''}{inventory.entries} / {inventory.capacity} entries. Restoring needs two free backup slots and one of five staging slots.</p>
    <label>Saved backup<select aria-label="Saved backup" value={chosen} disabled={!connection||busy||working}
      onChange={e=>{setChosen(e.target.value);setInspected(null);}}>
      <option value="">Choose a saved backup</option>{inventory.items.map(item=><option key={item.id} value={item.id}>
        {new Date(item.created*1000).toLocaleString()} · {item.filename} · {item.bytes.toLocaleString()} bytes</option>)}
    </select></label>
    <div className="approval-actions"><button disabled={!connection||busy||working} onClick={()=>{
      const version=generation.current;
      if(connection)void refresh(connection,version).catch(e=>{if(version===generation.current)setError(String(e));});
    }}>Refresh backups</button>
      <button disabled={!connection||busy||working||!chosen} onClick={()=>void inspect()}>Inspect backup</button>
      <button disabled={!connection||busy||working||!inspected||!hasRoom} onClick={()=>{setUndo(false);setRestoreConfirm(inspected);}}>Restore selected backup</button></div>
    {inspected&&<p>Inspected SHA-256: <code>{inspected.sha256}</code>. Schema and integrity are validated before restoration.</p>}
    {!hasRoom&&<p>Make room for two rollback copies before restoring. Saved files are managed explicitly while Studio is closed.</p>}
    {status?.generation&&<div><p>Restored data is active.</p><button disabled={!connection||busy||working||!hasRoom||!status.rollback}
      onClick={()=>void inspect(status.rollback!,true)}>Restore previous state</button></div>}
    {confirm&&<Modal title="backup-confirm-title" onDismiss={()=>setConfirm(false)}>
      <h2 id="backup-confirm-title">Save a private Studio backup?</h2>
      <p>This copies your stored conversations and attachments into an unencrypted file in the app state directory. Keep saved copies private.</p>
      <div className="approval-actions"><button data-dialog-initial onClick={()=>setConfirm(false)}>Cancel</button>
        <button disabled={!connection||busy||working} onClick={()=>void create()}>Save backup</button></div>
    </Modal>}
    {restoreConfirm&&<Modal title="restore-confirm-title" onDismiss={()=>setRestoreConfirm(null)}>
      <h2 id="restore-confirm-title">{undo?'Restore previous Studio state?':'Restore this Studio backup?'}</h2>
      <p>Saved chats, attachments, goals, preferences and memory will switch to this backup. The backend will restart.</p>
      <p>A fresh rollback copy and the original database are retained. Project files and model weights are excluded.</p>
      <p><code>{restoreConfirm.filename}</code> · {restoreConfirm.bytes.toLocaleString()} bytes</p>
      <p>SHA-256: <code>{restoreConfirm.sha256}</code></p>
      <div className="approval-actions"><button data-dialog-initial onClick={()=>setRestoreConfirm(null)}>Cancel</button>
        <button className="primary" disabled={!connection||busy||working||!hasRoom} onClick={()=>void restore()}>Restore and restart</button></div>
    </Modal>}
  </div>;
}
