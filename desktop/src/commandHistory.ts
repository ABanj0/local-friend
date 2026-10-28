import type { Event, Task } from './api';
import {backgroundObservation,commandDelta} from './eventPayloads.ts';

export type CommandGroup = {id:string;task:string;profile:string;text:string;part:number;
  truncated:boolean;partial:boolean;finished:boolean;exit_code:number|null;reason:string;
  background?:{state:string;readiness:{status:string;last_ready_at:number|null;last_check:string|null}}};

/** Fold durable deltas once; a retained-history gap never implies complete output. */
export function commandGroups(events:Event[], tasks:Task[]):CommandGroup[] {
  const permitted=new Set(tasks.map(task=>task.id));
  const groups=new Map<string,CommandGroup>();
  for(const event of events) {
    if(!['command_output','background_status'].includes(event.kind)||!event.task||!permitted.has(event.task))continue;
    const p=event.kind==='command_output'?commandDelta(event.payload):backgroundObservation(event.payload);
    if(!p)continue;
    let group=groups.get(p.command_id);
    if(!group) {
      group={id:p.command_id,task:event.task,profile:String(p.profile),text:'',part:0,
        truncated:false,partial:false,finished:false,exit_code:null,reason:'running'};
      groups.set(group.id,group);
    }
    if('readiness' in p) {
      group.background={state:p.state,readiness:p.readiness};
      continue;
    }
    if(p.part<=group.part)continue;
    group.partial ||= p.part!==group.part+1;
    const raw=new TextEncoder().encode(group.text+p.text);
    group.text=new TextDecoder('utf-8',{fatal:false}).decode(raw.slice(0,16000),{stream:true});
    group.partial ||= raw.length>16000;
    group.part=p.part;group.truncated ||= p.truncated===true;
    group.finished=p.finished===true;
    group.exit_code=Number.isInteger(p.exit_code)?p.exit_code:null;
    group.reason=String(p.reason);
  }
  const ordered=[...groups.values()];
  const active=new Set(tasks.filter(task=>['running','waiting'].includes(task.status)).map(task=>task.id));
  const pinned=ordered.filter(group=>group.background?.state==='running'&&active.has(group.task)).slice(-4);
  const keep=new Set([...ordered.slice(-3),...pinned].map(group=>group.id));
  return ordered.filter(group=>keep.has(group.id));
}
