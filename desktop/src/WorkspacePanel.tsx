import {FolderOpen,Monitor,RotateCcw} from 'lucide-react';
import type {Connection} from './api';
import {RepositorySearch} from './RepositorySearch';
import {InspectionPanel} from './InspectionPanel';
import {SchedulePanel} from './SchedulePanel';
import {DirectoryWatchPanel} from './DirectoryWatchPanel';
import type {Task} from './api';

type Props={view:string;toolProfile:string;busy:boolean;connection:Connection|null;project:string;files:string[];
  file:{path:string;text:string}|null;preview:string;setToolProfile:(profile:string)=>void;
  model:string;settings:Record<string,unknown>;inspectionTask:Task|undefined;
  ensureConversation:()=>Promise<string>;onInspectionStarted:(id:string)=>Promise<void>;
  onScheduledTask:(id:string,conversation:string)=>Promise<void>;
  onChooseProject:()=>void;onLaunchNotepad:()=>void;onSelectFile:(path:string)=>void;onRefreshFiles:()=>void};

export function WorkspacePanel(props:Props){
  const {view,toolProfile,busy,connection,project,files,file,preview,setToolProfile,onChooseProject,onLaunchNotepad,onSelectFile,onRefreshFiles}=props;
  const isWorkspace=['agent','browser','desktop','coding'].includes(view);
  return (<>{isWorkspace && <div className="workspace-toolbar"><div><span className="eyebrow">{view.toUpperCase()} WORKSPACE</span>
            <p>{view === 'agent' ? 'Plan, execute and verify with the selected tools' : view === 'browser' ? 'Visible isolated browser · approvals for submissions' : view === 'desktop' ? 'Approved Windows apps · emergency stop available' : 'Scoped files · reviewed edits · approved commands'}</p></div>
            <label>Tool access <select aria-label="Tool access" value={toolProfile} disabled={busy}
              onChange={event=>setToolProfile(event.target.value)}>
              <option value="unified">Unified: coding, browser, desktop</option>
              <option value="coding">Coding only</option><option value="browser">Browser only</option>
              <option value="desktop">Desktop only</option>
            </select></label>
            {view === 'coding' && <button onClick={onChooseProject}><FolderOpen size={15}/> Choose project</button>}
            {view === 'desktop' && <button disabled={busy} onClick={onLaunchNotepad}>Launch Notepad</button>}</div>}
          {view === 'coding' && <div className="coding-tools" tabIndex={0} role="region" aria-label="Coding tools">
          <RepositorySearch connection={connection} project={project} onOpen={onSelectFile}/>
          <InspectionPanel connection={connection} project={project} model={props.model}
            settings={props.settings} busy={busy} task={props.inspectionTask} selectedFile={file?.path??''}
            ensureConversation={props.ensureConversation} onStarted={props.onInspectionStarted}/>
          <SchedulePanel connection={connection} project={project} model={props.model} settings={props.settings}
            ensureConversation={props.ensureConversation} onTask={props.onScheduledTask}/>
          <DirectoryWatchPanel connection={connection} project={project} model={props.model} settings={props.settings}
            ensureConversation={props.ensureConversation} onTask={props.onScheduledTask}/>
          <div className="code-workspace"><div className="file-tree"><button onClick={onRefreshFiles}><RotateCcw size={13}/> Refresh files</button>
            {files.map(path => <button key={path} onClick={()=>onSelectFile(path)}>{path}</button>)}</div>
            <div className="code-view"><div className="code-title">{file?.path || 'Select a file to inspect'}</div><pre>{file?.text || 'Files stay inside your approved workspace. Edit proposals appear in the approval panel.'}</pre></div></div></div>}
          {['browser','desktop'].includes(view) && <div className="preview-panel">{preview ? <img alt="Latest agent screenshot" src={preview}/> : <div><Monitor size={30}/><p>Screenshot preview</p><small>Ask the agent to take a screenshot. Only actual observations appear here.</small></div>}</div>}</>);
}
