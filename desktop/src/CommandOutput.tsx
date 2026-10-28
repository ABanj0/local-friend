import type { Event, Task } from './api';
import { commandGroups } from './commandHistory';

export function CommandOutput({events,tasks}:{events:Event[];tasks:Task[]}) {
  const groups=commandGroups(events,tasks);
  if(!groups.length)return null;
  return <section className="command-output" aria-label="Command output">
    <h4>Command output <small>Recent commands and active servers</small></h4>
    {groups.map(group=>{
      const active=tasks.some(task=>task.id===group.task&&['running','waiting'].includes(task.status));
      const status=group.background?(group.background.state==='running'&&!active?'Interrupted; final command status unavailable'
        :group.background.state==='running'?'Running':group.background.state)
        :group.finished?(group.reason==='completed'?`Exited ${group.exit_code}`:group.reason)
          :active?'Running':'Interrupted; final command status unavailable';
      return <article key={group.id}>
        <div><strong>{group.profile}</strong><span>{status}</span></div>
        {group.background&&<small>Readiness: {group.background.readiness.status==='ready'?'ready observed'
          :group.background.readiness.status.replaceAll('_',' ')}
          {group.background.readiness.status!=='ready'&&group.background.readiness.last_check&&` · last check ${group.background.readiness.last_check.replaceAll('_',' ')}`}
          {group.background.readiness.last_ready_at!==null&&` · last ready ${new Date(group.background.readiness.last_ready_at*1000).toLocaleTimeString()}`}</small>}
        <pre>{group.text||(group.finished||!active?'No captured output.':'Waiting for output…')}</pre>
        {group.truncated&&<small>Output limited to a 16,000-byte prefix.</small>}
        {group.partial&&<small>Earlier output is outside retained history.</small>}
      </article>;
    })}
  </section>;
}
