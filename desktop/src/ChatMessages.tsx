import type {RefObject} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Bot,Code2,Copy,FileText,Globe,Image as ImageIcon} from 'lucide-react';
import type {Attachment,Message,Task} from './api';

type Props={messages:Message[];currentTask:Task|undefined;liveText:string;end:RefObject<HTMLDivElement|null>;
  onSuggestion:(view:string,draft:string)=>void;onAttachment:(attachment:Attachment)=>void;onCopy:(text:string)=>void};

export function ChatMessages(props:Props){
  const {messages,currentTask,liveText,end,onSuggestion,onAttachment,onCopy}=props;
  return (<div className="messages" aria-live="polite">
            {!messages.length && !currentTask && <div className="welcome"><div className="welcome-icon"><Bot size={30}/></div><span className="eyebrow">ON YOUR MACHINE. UNDER YOUR CONTROL.</span>
              <h2>What would you like to work on?</h2><p>Talk with your local model, inspect a project, or let the agent handle a multi-step task.</p>
              <div className="suggestions"><button onClick={()=>onSuggestion('coding','Inspect the current project, run its configured tests, and report the results.')}><Code2 size={19}/><strong>Work on a project</strong><small>Inspect, test and verify</small></button>
                <button onClick={()=>onSuggestion('browser','Open https://example.com, read its title, and take a screenshot.')}><Globe size={19}/><strong>Explore in the browser</strong><small>Navigate with your approval</small></button></div></div>}
            {messages.map(m => <article key={m.id} className={`message ${m.role}`}><div className="avatar">{m.role === 'assistant' ? <Bot size={17}/> : 'You'}</div><div className="message-body"><div className="message-label">{m.role === 'assistant' ? 'Local Agent' : 'You'}</div>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={{img: ({alt}) => <span>[Image: {alt}]</span>, a: ({children, href}) => <span title={href}>{children}</span>}}>{m.content}</ReactMarkdown>
              {!!m.attachments?.length && <div className="attachment-list">{m.attachments.map(a => <button key={a.id} className="attachment-chip" onClick={()=>onAttachment(a)}>
                {a.mime.startsWith('image/') ? <ImageIcon size={15}/> : <FileText size={15}/>}<span>{a.name}<small>{Math.ceil(a.size/1024)} KiB</small></span>
              </button>)}</div>}
              {m.role === 'assistant' && <>
                {m.metrics && <div className="response-metrics" aria-label="Generation statistics"
                  title="Speed uses Ollama's generated tokens divided by generation time, excluding loading and prompt processing. Elapsed time includes the full request, tools and approval waits. Agent totals cover measured task model calls; compatibility probes are separate.">
                  <span>{m.metrics.tokens_per_second == null ? 'Speed unavailable' : `${m.metrics.tokens_per_second.toFixed(1)} tokens/s`}</span>
                  <span>{m.metrics.generated_tokens.toLocaleString()} tokens</span>
                  <span>{m.metrics.elapsed_seconds.toFixed(1)}s elapsed</span>
                  {m.metrics.scope === 'task' && <span>Task total · {m.metrics.model_calls} model calls</span>}
                  {m.metrics.inference&&<details><summary>Inference details ({m.metrics.inference.calls.length} calls)</summary>
                  {m.metrics.inference.calls.map((call,index)=><p key={index}>Call {index+1+(m.metrics?.inference?.omitted_calls??0)}: {call.finish_reason} · prompt {call.prompt_tokens??'unknown'} tokens
                    {call.load_ns!==null?` · load ${(call.load_ns/1e9).toFixed(2)}s`:''}
                    {call.prompt_ns!==null?` · prompt ${(call.prompt_ns/1e9).toFixed(2)}s`:''}
                    {call.first_token_seconds!==null?` · first token ${call.first_token_seconds.toFixed(2)}s`:''}
                    {call.first_content_seconds!==null?` · first content ${call.first_content_seconds.toFixed(2)}s`:''}</p>)}
                  {!!m.metrics.inference?.compatibility_probes&&<span>Compatibility checks: {m.metrics.inference.compatibility_probes} · {m.metrics.inference.compatibility_probe_seconds.toFixed(2)}s (outside task token counts)</span>}
                  {!!m.metrics.inference?.omitted_calls&&<span>{m.metrics.inference.omitted_calls} earlier call details omitted</span>}
                  </details>}
                </div>}
                <button className="copy" onClick={()=>onCopy(m.content)}><Copy size={13}/> Copy</button>
              </>}</div></article>)}
            {currentTask && <article className="message assistant"><div className="avatar"><Bot size={17}/></div><div className="message-body"><div className="message-label">Local Agent <span className="streaming">generating</span></div><pre className="stream-text">{liveText}</pre></div></article>}
            <div ref={end}/>
          </div>);
}
