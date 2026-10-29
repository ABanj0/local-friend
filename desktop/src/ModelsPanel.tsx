import {Activity,Check,Cpu,Monitor,Settings2} from 'lucide-react';
import type {Connection,ModelCapabilities,ModelStatus,Telemetry} from './api';
import {BackupPanel} from './BackupPanel';
import {RetentionPanel} from './RetentionPanel';

type Props={models:ModelStatus;model:string;telemetry:Telemetry;permissions:Record<string,unknown>|undefined;
  connection:Connection|null;busy:boolean;
  onRestoreRestart:()=>Promise<void>;
  protectedConversation:string;onRetentionChanged:()=>Promise<void>;
  connected:boolean;context:number;temperature:number;maxOutput:number;thinking:boolean|string|null;keepAlive:string|number;
  capabilities:ModelCapabilities|null;capabilityError:string;setModel:(value:string)=>void;
  setContext:(value:number)=>void;setTemperature:(value:number)=>void;setMaxOutput:(value:number)=>void;
  setThinking:(value:boolean|string|null)=>void;setKeepAlive:(value:string|number)=>void;onStart:()=>void;onRefresh:()=>void};
const bytes=(n?:number|null)=>n==null?'Unavailable':`${(n/1024**3).toFixed(1)} GB`;
export function ModelsPanel(props:Props){
  const {models,model,telemetry,permissions,connected,context,temperature,maxOutput,thinking,keepAlive,capabilities,capabilityError,setModel,setContext,setTemperature,setMaxOutput,setThinking,setKeepAlive,onStart,onRefresh}=props;
  const execution=permissions?.coding_execution;
  const executionLabel=execution&&typeof execution==='object'&&'label' in execution&&typeof execution.label==='string'?execution.label:'Execution status unavailable';
  return (<section className="settings-page">
        <div className="page-intro"><span className="eyebrow">YOUR LOCAL ENGINE</span><h2>Models & resources</h2><p>Choose a model installed in Ollama. Settings apply to your next task.</p></div>
        <div className="metrics"><div><Cpu/><small>GPU utilization</small><strong>{telemetry.gpu ? `${telemetry.gpu.percent}%` : 'Unavailable'}</strong></div>
          <div><Activity/><small>CPU utilization</small><strong>{telemetry.cpu_percent == null ? 'Unavailable' : `${telemetry.cpu_percent}%`}</strong></div>
          <div><Monitor/><small>GPU memory</small><strong>{telemetry.gpu ? `${telemetry.gpu.used_mib} / ${telemetry.gpu.total_mib} MiB` : 'Unavailable'}</strong></div>
          <div><Settings2/><small>System memory</small><strong>{bytes(telemetry.memory_used)} / {bytes(telemetry.memory_total)}</strong></div></div>
        <div className="panel"><div className="panel-heading"><h3>Ollama {models.running ? 'is running' : 'is offline'}</h3>
          <button onClick={onStart}>Start / connect</button></div>
          {!models.models.length && <p className="muted">No installed models detected. Start Ollama or install a model using the setup guide.</p>}
          {models.error && <p role="status">{models.error}</p>}
          {models.diagnostics?.output && <details><summary>Ollama diagnostics{models.diagnostics.exit_code != null ? ` (exit ${models.diagnostics.exit_code})` : ''}</summary><pre>{models.diagnostics.output}</pre></details>}
          {models.models.map((item) => <button className={`model-row ${model === item.name ? 'active' : ''}`} key={item.name} onClick={() => setModel(item.name)}>
            <div className="model-icon"><Cpu/></div><div><strong>{item.name}</strong><small>{bytes(item.size)} · {models.loaded.some((m) => m.name === item.name) ? 'Loaded in memory' : 'Loads on first request'}</small></div>{model === item.name && <Check size={18}/>}</button>)}
        </div>
        <div className="panel settings-form"><label>Context window<select aria-label="Context window" value={context} onChange={e => setContext(Number(e.target.value))}>{[2048,4096,8192,16384,32768].map(n => <option key={n}>{n}</option>)}</select></label>
          <label>Temperature <span>{temperature.toFixed(1)}</span><input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(Number(e.target.value))}/></label>
          <label>Maximum output tokens<input type="number" min="1" max="32768" value={maxOutput} onChange={e=>setMaxOutput(Number(e.target.value))}/></label>
          <label>Thinking<select aria-label="Thinking" value={JSON.stringify(thinking)} onChange={e=>setThinking(JSON.parse(e.target.value))}>
            <option value="null">Model default</option>
            {capabilities?.thinking_values.map(value=><option key={JSON.stringify(value)} value={JSON.stringify(value)}>{value===true?'On':value===false?'Off':value}</option>)}
            {thinking!==null&&!capabilities?.thinking_values.some(value=>value===thinking)&&<option value={JSON.stringify(thinking)}>Current setting (not verified)</option>}
          </select></label>
          <label>Keep model loaded<select aria-label="Keep model loaded" value={String(keepAlive)} onChange={e=>setKeepAlive(e.target.value)}>
            {['0','60s','5m','15m','30m','60m'].map(value=><option key={value} value={value}>{value==='0'?'Unload after request':value}</option>)}
            {!['0','60s','5m','15m','30m','60m'].includes(String(keepAlive))&&<option value={String(keepAlive)}>{keepAlive}</option>}
          </select></label></div>
        <div className="panel"><h3>Model compatibility</h3>
          <button type="button" disabled={!connected||!model} onClick={onRefresh}>Refresh capabilities</button>
          {capabilityError?<p role="status">{capabilityError}</p>:!capabilities?<p>Checking local model metadata…</p>:<>
            <p>Advertised: {capabilities.capabilities.join(', ')} · Ollama {capabilities.server_version}</p>
            <p>Structured-output probe: {capabilities.schema_probe.replaceAll('_',' ')}. Planning performs a bounded compatibility check that may load the model.</p>
          </>}
          <p>Output limits apply to each model call, including planning. Token-limit responses are incomplete. Settings apply to the next task; they do not change the Ollama server configuration.</p>
        </div>
        <BackupPanel connection={props.connection} busy={props.busy} onRestart={props.onRestoreRestart}/>
        <RetentionPanel connection={props.connection} busy={props.busy} protectedConversation={props.protectedConversation} onChanged={props.onRetentionChanged}/>
        <div className="panel"><h3>Permissions</h3><p className="muted">Sensitive actions always require approval. Scope changes are made in agent.toml.</p>
          <p>Code/test commands: <strong>{executionLabel}</strong>. File edits, browser and desktop actions use their existing scopes.</p>
          <pre>{JSON.stringify(permissions || {}, null, 2)}</pre><p className="muted">General agent tasks cannot pause or resume. Workspace offers a separate selected-file read-only inspection with validated checkpoints.</p></div>
      </section>);
}
