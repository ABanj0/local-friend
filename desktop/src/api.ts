import { invoke } from '@tauri-apps/api/core';

export type Connection = { port: number; token: string };
export type Conversation = { id: string; title: string; created: number };
export type HistoryPage<T> = {items:T[];next:string|null;limit:number;order:'oldest_first'|'newest_first'};
export type SlashCommand = { name: string; description: string; usage: string; local: boolean };
export type Goal = { id: string; conversation: string; objective: string; status: 'active'|'completed'|'cancelled';
  steps: {text:string;done:boolean}[]; created:number; updated:number };
export type SlashResult = { action:'task'|'goal'|'memory'; id?:string; mode?:string; goal?:Goal|null; notice?:string };
export type ResponseMetrics = { generated_tokens: number; tokens_per_second: number | null;
  elapsed_seconds: number; model_calls: number; scope: 'response' | 'task';
  inference?:{version:number;compatibility_probes:number;compatibility_probe_seconds:number;omitted_calls:number;calls:{finish_reason:string;prompt_tokens:number|null;load_ns:number|null;
    prompt_ns:number|null;first_token_seconds:number|null;first_content_seconds:number|null;wall_seconds:number}[]} };
export type ModelCapabilities = {model:string;digest:string;server_version:string;capabilities:string[];
  thinking_values:(boolean|string)[];schema_probe:string;ttl_seconds:number};
export type OllamaModel = {name:string;size?:number};
export type ModelStatus = {running:boolean;models:OllamaModel[];loaded:OllamaModel[];error?:string;
  diagnostics?:{output:string;exit_code:number|null;owned:boolean}};
export type Telemetry = {cpu_percent?:number|null;memory_used?:number|null;memory_total?:number|null;
  gpu?:{percent:number;used_mib:number;total_mib:number}|null};
export type Attachment = { id: string; name: string; mime: string; size: number };
export type AttachmentContent = Attachment & { text: string | null; image: string | null };
export type Message = { id: string; role: string; content: string; metrics?: ResponseMetrics | null; attachments?: Attachment[] };
export type Task = { id: string; conversation: string; mode: string; status: string; model: string; created: number;
  profile?: 'unified'|'coding'|'browser'|'desktop';
  runtime_state?: 'storage' | 'cleanup' };
export type Event = { seq?: number; live_seq?: number; task?: string; kind: string; payload: unknown };
export type Approval = { id: string; task: string; action: string; details: Record<string, unknown>; expires: number };
export async function connect(restart = false): Promise<Connection> {
  return invoke(restart ? 'restart_backend' : 'backend_connection');
}
export async function diagnostics(): Promise<string> {
  return invoke('backend_diagnostics');
}
export async function request<T>(connection: Connection, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`http://127.0.0.1:${connection.port}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    signal,
    headers: { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || `Request failed (${response.status})`);
  return result as T;
}

export async function upload(connection: Connection, conversation: string, file: File): Promise<Attachment> {
  if (!file.size || file.size > 5 * 1024 * 1024) throw new Error('Each attachment must contain data and be at most 5 MiB');
  const response = await fetch(`http://127.0.0.1:${connection.port}/conversations/${conversation}/attachments?name=${encodeURIComponent(file.name)}`, {
    method: 'POST', headers: { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/octet-stream' }, body: file,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Attachment upload failed');
  return result;
}
