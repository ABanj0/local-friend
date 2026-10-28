import type {Event,Task} from './api';

export type TaskPreview={task:string;image:string};
type VerificationView={kind:'artifact'|'unittest';status:string;reason:string;path?:string;
  observed_bytes?:number|null;observed_sha256?:string|null;
  counts?:{tests_run:number;failures:number;errors:number;skipped:number}};
type Envelope={seq?:number;task?:string;kind:string;payload:unknown};
export type ActivityEntry={key:string;kind:'plan';steps:string[]}
  |{key:string;kind:'verification';observation:VerificationView}
  |{key:string;kind:'record';name:string;payload:unknown};
const hidden=new Set(['token','preview','command_output','background_status','trace','operation_intent','operation_result','context']);

/** Unknown IDs never become an authority to select another conversation's activity. */
export function selectActivityTask(tasks:readonly Task[],conversation:string,requested=''):Task|undefined {
  const scoped=tasks.filter(task=>task.conversation===conversation);
  return scoped.find(task=>task.id===requested)
    ??scoped.find(task=>['running','waiting'].includes(task.status)||task.runtime_state)??scoped[0];
}
export function taskEvents(events:readonly Event[],task:Task|undefined):Event[] {
  return task?events.filter(event=>event.task===task.id):[];
}
export function activityEntries(events:readonly Envelope[]):ActivityEntry[] {
  return events.filter(event=>!hidden.has(event.kind)).map((event,index)=>{
    const key=`${event.seq??0}-${index}`;
    const data=event.payload;
    if(event.kind==='plan'&&data&&typeof data==='object'&&'steps' in data&&Array.isArray(data.steps)
      &&data.steps.length<=30&&data.steps.every(step=>typeof step==='string'&&step.length<=2000))
      return {key,kind:'plan',steps:data.steps};
    if(event.kind==='verification'&&data&&typeof data==='object'){
      const record=data as Record<string,unknown>;
      const {kind,status,reason,path,observed_bytes,observed_sha256}=record;
      const count=record.counts as Record<string,unknown>|undefined;
      if((kind==='artifact'||kind==='unittest')&&typeof status==='string'&&typeof reason==='string'
        &&(path===undefined||typeof path==='string')
        &&(observed_bytes==null||typeof observed_bytes==='number')
        &&(observed_sha256==null||typeof observed_sha256==='string')
        &&(count==null||typeof count==='object'&&['tests_run','failures','errors','skipped'].every(k=>Number.isSafeInteger(count[k])&&(count[k] as number)>=0)))
        return {key,kind:'verification',observation:{kind,status,reason,path,observed_bytes,observed_sha256,
          counts:count as VerificationView['counts']}};
    }
    return {key,kind:'record',name:event.kind,payload:data};
  });
}
export function readPreview(event:Envelope):TaskPreview|undefined {
  const data=event.payload;
  if(event.kind!=='preview'||typeof event.task!=='string'||!event.task||event.task.length>128||!data||typeof data!=='object'||!('image' in data)
    ||typeof data.image!=='string'||!data.image.startsWith('iVBORw0KGgo')||data.image.length>16*1024**2)return;
  return {task:event.task,image:`data:image/png;base64,${data.image}`};
}
export function previewFor(preview:TaskPreview|undefined,task:Task|undefined):string {
  return preview&&task?.id===preview.task?preview.image:'';
}
