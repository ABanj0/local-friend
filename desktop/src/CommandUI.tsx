import { Goal, SlashCommand } from './api';
import { Check, Play, Target, X } from 'lucide-react';
import { useEffect } from 'react';
import {Modal} from './Modal';

export function SlashMenu({commands, index, choose}: {
  commands:SlashCommand[];index:number;choose:(command:SlashCommand)=>void;
}) {
  useEffect(()=>{document.getElementById('slash-menu')?.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest'});},[index]);
  return <div className="slash-menu" role="listbox" id="slash-menu" aria-label="Slash commands">
    <div className="slash-menu-label">COMMANDS <span>↑ ↓ to browse · Tab to insert · Esc to close</span></div>
    {commands.map((command, i) => <button key={command.name} type="button" role="option"
      aria-selected={i===index} className={i===index?'highlighted':''} onMouseDown={e=>e.preventDefault()}
      onClick={()=>choose(command)}><strong>/{command.name}</strong><span>{command.description}</span></button>)}
  </div>;
}

export function CommandHelp({commands, choose, close}: {
  commands:SlashCommand[];choose:(command:SlashCommand)=>void;close:()=>void;
}) {
  return <Modal title="commands-title" className="command-help" onDismiss={close}>
    <div className="panel-heading"><h2 id="commands-title">Slash commands</h2><button aria-label="Close command help" onClick={close}><X size={18}/></button></div>
    <p>Type / to browse commands. Plans do not execute tools; goals keep a checklist across sessions.</p>
    <div className="command-grid">{commands.map(command=><button key={command.name} onClick={()=>choose(command)}>
      <strong>/{command.name}</strong><span>{command.description}</span><code>{command.usage}</code></button>)}</div>
  </Modal>;
}

export function GoalPanel({goal, busy, run}: {goal:Goal;busy:boolean;run:(command:string)=>void}) {
  const done=goal.steps.filter(step=>step.done).length;
  const editable=goal.status==='active'&&!busy;
  return <details className="goal-panel" open>
    <summary><Target size={16}/><strong>Tracked goal</strong><span>{goal.status==='active'?`${done}/${goal.steps.length} reviewed`:goal.status==='completed'?'Completed by you':'Cancelled'}</span></summary>
    <p className="goal-objective">{goal.objective}</p>
    {!goal.steps.length && <p className="muted">Checklist pending. Generate a plan to break this goal into steps.</p>}
    <ol>{goal.steps.map((step,i)=><li key={i}><label><input type="checkbox" checked={step.done} disabled={!editable}
      onChange={()=>run(`/goal ${step.done?'undo':'done'} ${i+1}`)}/><span>{step.text}</span></label></li>)}</ol>
    <div className="goal-actions">{goal.status==='active'&&<>
      <button disabled={!editable} onClick={()=>run('/goal run')}><Play size={13}/> Run goal</button>
      {!goal.steps.length && <button disabled={!editable} onClick={()=>run('/goal plan')}>Generate checklist</button>}
      <button disabled={!editable||!goal.steps.length||done!==goal.steps.length} onClick={()=>run('/goal complete')}><Check size={13}/> Complete goal</button>
      <button disabled={!editable} onClick={()=>run('/goal cancel')}>Cancel goal</button>
    </>}</div>
    <small>Progress is marked by you. Review actual tool results before checking steps. Tasks keep existing scopes and approvals.</small>
  </details>;
}
