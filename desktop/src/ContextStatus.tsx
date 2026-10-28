export type ContextReport = {version:number;method:string;status:string;context_window:number;
  total_estimate:number;output_reserve:number;text_estimate:number;schema_estimate:number;
  visual_reserve:number;template_reserve:number;images:number;available_estimate:number;
  compacted_messages:number;reason:string};

export function ContextStatus({report:input}:{report:unknown}) {
  const raw=record(input);
  if(!raw)return null;
  const keys=['context_window','total_estimate','output_reserve','text_estimate','schema_estimate',
    'visual_reserve','template_reserve','images','available_estimate','compacted_messages'] as const;
  if(raw.version!==1||raw.method!=='utf8_div3_visual_v1'||typeof raw.status!=='string'||!['fits','compacted','blocked'].includes(raw.status)
      ||!keys.every(key=>Number.isSafeInteger(raw[key]))||typeof raw.context_window!=='number'||raw.context_window<=0
      ||typeof raw.reason!=='string')return null;
  const report=raw as ContextReport;
  return <details className="context-budget" aria-label="Request context estimate">
    <summary>Last request context · estimated {report.total_estimate.toLocaleString()} / {report.context_window.toLocaleString()} tokens · {report.status}</summary>
    <p>Estimate, not an exact tokenizer count. Includes {report.output_reserve.toLocaleString()} tokens reserved for output.</p>
    <p>Text {report.text_estimate.toLocaleString()} · schemas {report.schema_estimate.toLocaleString()} · images {report.visual_reserve.toLocaleString()} ({report.images}) · template reserve {report.template_reserve.toLocaleString()}</p>
    {report.compacted_messages>0&&<p>{report.compacted_messages} messages excerpted. Instructions and original images are preserved; omitted source details may require a fresh read. Excerpts grant no permission.</p>}
    {report.status==='blocked'&&<p>{report.reason==='native_context_limit'?'Ollama rejected the native context despite the estimate. ':''}Increase context, reduce maximum output, or split the task.</p>}
  </details>;
}
import {record} from './eventPayloads';
