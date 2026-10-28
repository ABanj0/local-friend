import {Check,ShieldCheck} from 'lucide-react';
import type {Approval} from './api';
import {Modal} from './Modal';

type Props={approval:Approval;count:number;sourceName:string;sourceAvailable:boolean;onSource:()=>void;onAnswer:(approved:boolean)=>void;onStop:()=>void};

export function ActionApproval(props:Props){
  const {approval,count,sourceName,sourceAvailable,onSource,onAnswer}=props;
  return (<Modal key={approval.id} title="approval-title" onDismiss={()=>onAnswer(false)}>
      <div className="approval-icon"><ShieldCheck size={25}/></div><span className="eyebrow">YOUR PERMISSION IS REQUIRED</span><h2 id="approval-title">Review this action</h2>
      <p>Source: {sourceName} · task {approval.task.slice(0,8)}</p><button disabled={!sourceAvailable} onClick={onSource}>Open approval conversation</button>
      <p>{approval.action.replaceAll('_', ' ')}</p><pre>{JSON.stringify(approval.details, null, 2)}</pre>
      <small>Applies to this action only. Expires at {new Date(approval.expires * 1000).toLocaleTimeString()}. {count > 1 ? `${count} requests pending.` : ''}</small>
      <small>Escape denies this request. Emergency stop cancels all owned tasks.</small>
      <div className="approval-buttons"><button className="danger" onClick={props.onStop}>Emergency stop</button><button data-dialog-initial onClick={()=>onAnswer(false)}>Deny</button>
        <button className="primary" onClick={()=>onAnswer(true)}><Check size={16}/> Approve action</button></div>
    </Modal>);
}
