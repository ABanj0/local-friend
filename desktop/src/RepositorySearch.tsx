import { useEffect, useRef, useState } from 'react';
import { type Connection, request } from './api';

type Results = {
  matches: {path:string;line:number;column:number;text:string;preview_truncated:boolean;sha256:string}[];
  complete:boolean;stop_reason:string|null;scanned_files:number;skipped:Record<string,number>;
};

export function RepositorySearch({connection, project, onOpen}: {
  connection:Connection|null;project:string;onOpen:(path:string)=>void;
}) {
  const [query,setQuery]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [result,setResult]=useState<{connection:Connection;project:string;data:Results}|null>(null);
  const generation=useRef(0);
  useEffect(()=>{generation.current++;setBusy(false);setError('');setResult(null);},[connection,project]);
  const visible=result?.connection===connection&&result?.project===project?result.data:null;
  const submit=async()=>{
    if(!connection||!query.length)return;
    const current=++generation.current;
    setBusy(true);setError('');setResult(null);
    try {
      const data=await request<Results>(connection,`/search?query=${encodeURIComponent(query)}&project=${encodeURIComponent(project)}`,
        undefined,AbortSignal.timeout(6000));
      if(current===generation.current)setResult({connection,project,data});
    } catch(problem) {
      if(current===generation.current)setError(problem instanceof Error?problem.message:String(problem));
    } finally {if(current===generation.current)setBusy(false);}
  };
  return <section className="repository-search" aria-label="Project text search">
    <form onSubmit={event=>{event.preventDefault();void submit();}}>
      <label htmlFor="repository-query">Search project text</label>
      <input id="repository-query" value={query} maxLength={256} placeholder="Literal text, case-sensitive"
        onChange={event=>setQuery(event.target.value)} />
      <button disabled={!connection||!query.length||busy} type="submit">{busy?'Searching…':'Search project'}</button>
    </form>
    {error&&<p role="alert">{error}</p>}
    {visible&&<div className="repository-results" role="status">
      <p>{visible.matches.length} matching lines · {visible.scanned_files} files searched.
        {!visible.complete&&` Incomplete: ${String(visible.stop_reason).replaceAll('_',' ')}.`}
        {Object.values(visible.skipped).some(Boolean)&&' Some inputs were excluded or skipped.'}</p>
      {visible.matches.map((match,index)=><button key={`${match.path}-${match.line}-${index}`} type="button"
        onClick={()=>onOpen(match.path)} title={`Open ${match.path} at matching line ${match.line}`}>
        <strong>{match.path}:{match.line}:{match.column}</strong>
        <code>{match.text}{match.preview_truncated?' …':''}</code>
      </button>)}
      {!visible.matches.length&&<p>No matching lines in the searched text scope.</p>}
    </div>}
  </section>;
}
