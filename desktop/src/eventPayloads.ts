import type {Approval,Event} from './api';

export function record(value:unknown):Record<string,unknown>|undefined {
  return value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:undefined;
}
export function approvalPayload(event:Event):Approval|undefined {
  const p=record(event.payload),details=record(p?.details);
  if(event.kind!=='approval'||typeof event.task!=='string'||!event.task||!p||p.transient===true||!details
    ||typeof p.id!=='string'||!p.id||typeof p.action!=='string'||!p.action
    ||typeof p.expires!=='number'||!Number.isFinite(p.expires)||p.expires<=0)return;
  return {task:event.task,id:p.id,action:p.action,details,expires:p.expires};
}
export function approvalList(value:unknown):Approval[] {
  if(!Array.isArray(value))return [];
  return value.flatMap(item=>{
    const p=record(item);
    const approval=approvalPayload({kind:'approval',task:typeof p?.task==='string'?p.task:undefined,payload:item});
    return approval?[approval]:[];
  });
}
export type CommandDelta={command_id:string;profile:string;part:number;text:string;truncated:boolean;
  finished:boolean;exit_code:number|null;reason:string};
export type BackgroundObservation={command_id:string;profile:string;state:string;
  readiness:{status:string;last_ready_at:number|null;last_check:string|null}};

export function commandDelta(value:unknown):CommandDelta|undefined {
  const p=record(value);
  if(!p||typeof p.command_id!=='string'||!/^[a-f0-9]{32}$/.test(p.command_id)||typeof p.profile!=='string'
    ||typeof p.part!=='number'||!Number.isSafeInteger(p.part)||p.part<1||p.part>64||typeof p.text!=='string'
    ||typeof p.truncated!=='boolean'||typeof p.finished!=='boolean'||typeof p.reason!=='string'
    ||!(p.exit_code===null||typeof p.exit_code==='number'&&Number.isSafeInteger(p.exit_code)))return;
  return {command_id:p.command_id,profile:p.profile,part:p.part,text:p.text,truncated:p.truncated,
    finished:p.finished,reason:p.reason,exit_code:p.exit_code};
}
export function backgroundObservation(value:unknown):BackgroundObservation|undefined {
  const p=record(value),ready=record(p?.readiness);
  if(!p||!ready||typeof p.command_id!=='string'||!/^[a-f0-9]{32}$/.test(p.command_id)
    ||typeof p.profile!=='string'||typeof p.state!=='string'||typeof ready.status!=='string'
    ||!(ready.last_ready_at==null||typeof ready.last_ready_at==='number'&&Number.isFinite(ready.last_ready_at)&&ready.last_ready_at>=0)
    ||!(ready.last_check==null||typeof ready.last_check==='string'))return;
  return {command_id:p.command_id,profile:p.profile,state:p.state,readiness:{status:ready.status,
    last_ready_at:ready.last_ready_at as number|null|undefined??null,last_check:ready.last_check as string|null|undefined??null}};
}
