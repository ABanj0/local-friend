import {Activity,Terminal} from 'lucide-react';
import type {Approval,Event,Task} from './api';
import {activityEntries,taskEvents} from './activity';
import {CommandOutput} from './CommandOutput';

type Props={events:Event[];tasks:Task[];task:Task|undefined;globalActive:Task|undefined;
  approvals:Approval[];sending:boolean;onSelect:(id:string)=>void;onOpenActive:()=>void};
export function ActivityPanel({events,tasks,task,globalActive,approvals,sending,onSelect,onOpenActive}:Props){
  const scoped=taskEvents(events,task),entries=activityEntries(scoped);
  const active=task&&(['running','waiting'].includes(task.status)||task.runtime_state)?task:undefined;
  const pending=approvals.some(approval=>approval.task===task?.id);
  return <aside className="activity-panel"><div className="activity-heading"><Activity size={16}/><h3>Agent activity</h3>{active&&<span className="status-dot"/>}</div>
    <label className="activity-task">Activity task<select aria-label="Activity task" value={task?.id??''} onChange={e=>onSelect(e.target.value)} disabled={!tasks.length}>
      {!tasks.length&&<option value="">No task in this conversation</option>}
      {tasks.map(item=><option key={item.id} value={item.id}>{item.mode} · {item.status} · {item.id.slice(0,8)}</option>)}
    </select></label>
    <div className="activity-status"><span className="eyebrow">CURRENT STATE</span><strong>{active?.runtime_state==='storage'?'Waiting for storage':active?.runtime_state==='cleanup'?'Stopping worker':pending?'Needs your approval':active?'Working':sending?'Submitting':'Ready'}</strong>
      <p>{task?`${task.mode} · ${task.model}`:'Plans, actions and results will appear here.'}</p>
      {globalActive&&!tasks.some(item=>item.id===globalActive.id)&&<button onClick={onOpenActive}>Open active conversation</button>}
    </div>
    <CommandOutput events={scoped} tasks={task?[task]:[]}/>
    <div className="event-list" aria-label={`${entries.length} retained activity events for this task`}>
      {entries.slice(-40).reverse().map(entry=><div className="event" key={entry.key}>
        <span className={`event-kind ${entry.kind==='record'?entry.name:entry.kind}`}>{entry.kind==='record'?entry.name.replaceAll('_',' '):entry.kind}</span>
        {entry.kind==='plan'?<ol>{entry.steps.map((step,index)=><li key={index}>{step}</li>)}</ol>
          :entry.kind==='verification'?<><strong>{entry.observation.kind==='artifact'?'Artifact readback':'Test run'}: {entry.observation.status}</strong>
            {entry.observation.kind==='artifact'?<p>{entry.observation.path}: {entry.observation.observed_bytes??'unknown'} bytes; SHA-256 {entry.observation.observed_sha256??'unavailable'}</p>
              :<p>{entry.observation.counts?`${entry.observation.counts.tests_run} executed, ${entry.observation.counts.failures+entry.observation.counts.errors} failures/errors, ${entry.observation.counts.skipped} skipped`:'Test count unavailable'}</p>}
            <small>{entry.observation.reason.replaceAll('_',' ')}. This observation does not certify the whole task.</small></>
          :<pre>{JSON.stringify(entry.payload,null,2)}</pre>}
      </div>)}
    </div><div className="activity-footer"><Terminal size={14}/><span>Tools run only within approved scopes.</span></div>
  </aside>;
}
