import { useEffect, useRef, useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { Activity, ArrowUp, Bot, ChevronDown, Code2, Cpu, FolderOpen, Globe,
  MessageSquare, Monitor, Plus, RotateCcw, ShieldCheck, Square, X,
  Camera, Download, Paperclip, Pencil, Search, Trash2, FileText, Image as ImageIcon } from 'lucide-react';
import { Approval, Attachment, AttachmentContent, Connection, Conversation, Event, Message, Task, connect, request, upload } from './api';
import { Goal, SlashCommand, SlashResult, type ModelCapabilities } from './api';
import { CommandHelp, GoalPanel, SlashMenu } from './CommandUI';
import { EventHistory, type EventPacket } from './eventHistory';
import { diagnostics } from './api';
import { Recovery } from './recovery';
import { ContextStatus } from './ContextStatus';
import { MemoryPanel } from './MemoryPanel';
import { ActionApproval } from './ActionApproval';
import { ActivityPanel } from './ActivityPanel';
import { ChatMessages } from './ChatMessages';
import { ModelsPanel } from './ModelsPanel';
import { TaskHistory } from './TaskHistory';
import { WorkspacePanel } from './WorkspacePanel';
import {previewFor,readPreview,selectActivityTask,type TaskPreview} from './activity';
import type {ModelStatus,Telemetry} from './api';
import {approvalList,approvalPayload,record} from './eventPayloads';
import {Modal} from './Modal';
import type {HistoryPage} from './api';

const views = [
  { id: 'chat', label: 'Chat', icon: MessageSquare }, { id: 'agent', label: 'Agent', icon: Bot },
  { id: 'browser', label: 'Browser', icon: Globe }, { id: 'desktop', label: 'Desktop', icon: Monitor },
  { id: 'coding', label: 'Workspace', icon: Code2 }, { id: 'models', label: 'Models & settings', icon: Cpu },
  { id: 'history', label: 'Task history', icon: Activity },
  { id: 'memory', label: 'Project memory', icon: FileText },
];
const taskView = (mode:string) => mode==='plan'?'agent':['test','diff','inspection'].includes(mode)?'coding':mode;
type MessagePaging={conversation:string;cursor:string|null;previous:(string|null)[];next:string|null;busy:boolean};

export default function App() {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [online, setOnline] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [view, setView] = useState('chat');
  const [narrow,setNarrow]=useState(()=>window.matchMedia('(max-width:1000px)').matches);
  const [activityOpen,setActivityOpen]=useState(false);
  useEffect(()=>{
    const media=window.matchMedia('(max-width:1000px)');
    const changed=()=>{setNarrow(media.matches);if(!media.matches)setActivityOpen(false);};
    media.addEventListener('change',changed);
    return ()=>media.removeEventListener('change',changed);
  },[]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationCursor,setConversationCursor]=useState<string|null>(null);
  const [conversationQuery,setConversationQuery]=useState('');
  const [conversationLoading,setConversationLoading]=useState(false);
  const conversationRequest=useRef(0);
  const [conversation, setConversation] = useState('');
  const selected = useRef('');
  const selectedConversationMeta=useRef<Conversation|null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagePaging,setMessagePaging]=useState<MessagePaging>({conversation:'',cursor:null,previous:[],next:null,busy:false});
  const messageNavigation=useRef(messagePaging);
  const messageRequest=useRef(0);
  const connectionRef=useRef(connection);
  connectionRef.current=connection;
  const [exporting,setExporting]=useState(false);
  const [models, setModels] = useState<ModelStatus>({ models: [], loaded: [], running: false });
  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.1);
  const [context, setContext] = useState(8192);
  const [maxOutput,setMaxOutput]=useState(2048);
  const [thinking,setThinking]=useState<boolean|string|null>(false);
  const [keepAlive,setKeepAlive]=useState<string|number>('5m');
  const [capabilities,setCapabilities]=useState<ModelCapabilities|null>(null);
  const [capabilityError,setCapabilityError]=useState('');
  const [capabilityVersion,setCapabilityVersion]=useState(0);
  const [telemetry, setTelemetry] = useState<Telemetry>({});
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [draft, setDraft] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const uploadBusy = useRef(false);
  const attachmentInput = useRef<HTMLInputElement>(null);
  const [attachmentViewer, setAttachmentViewer] = useState<AttachmentContent | null>(null);
  const [search, setSearch] = useState('');
  const [chatAction, setChatAction] = useState<{kind:'delete'|'rename'; chat:Conversation} | null>(null);
  const deletingConversation=useRef('');
  const [renameTitle, setRenameTitle] = useState('');
  const [captureConfirm, setCaptureConfirm] = useState(false);
  const [commands, setCommands] = useState<SlashCommand[]>([]);
  const [showCommandHelp, setShowCommandHelp] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);
  const [slashDismissed, setSlashDismissed] = useState(false);
  const [goal, setGoal] = useState<Goal|null>(null);
  const [memoryRequest,setMemoryRequest]=useState('');
  const [memoryVersion,setMemoryVersion]=useState(0);
  const composerInput = useRef<HTMLTextAreaElement>(null);
  const [stream, setStream] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<TaskPreview>();
  const [activityTaskID,setActivityTaskID]=useState('');
  const activitySelection=useRef('');
  const [pinnedActivityTask,setPinnedActivityTask]=useState<Task>();
  const setActivityTask=(id:string)=>{activitySelection.current=id;setActivityTaskID(id);};
  const [project, setProject] = useState('.');
  const [toolProfile, setToolProfile] = useState('unified');
  const [files, setFiles] = useState<string[]>([]);
  const [file, setFile] = useState<{ path: string; text: string } | null>(null);
  const [notice, setNotice] = useState('');
  const [connecting, setConnecting] = useState(true);
  const [backendOutput, setBackendOutput] = useState('');
  const bootBusy = useRef(false);
  const [bootVersion, setBootVersion] = useState(0);
  const recovery = useRef(new Recovery());
  const [sending, setSending] = useState(false);
  const [submittingConversation,setSubmittingConversation]=useState('');
  const stopRequested = useRef(false);
  const [preferencesReady, setPreferencesReady] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const history = useRef(new EventHistory());
  const active = tasks.find(t => ['running', 'waiting'].includes(t.status)||!!t.runtime_state);
  const approval = approvals.at(-1);
  const slashMatches = commands.filter(c=>c.name.startsWith(draft.slice(1).toLowerCase()));
  const slashVisible = !slashDismissed && /^\/[a-z]*$/i.test(draft) && slashMatches.length>0;
  useEffect(()=>{setSlashIndex(0);setSlashDismissed(false);},[draft]);

  const attempt = async (work: () => Promise<unknown>) => {
    const expected=connectionRef.current;
    try { await work(); } catch (error) {
      if(expected===connectionRef.current)setNotice(error instanceof Error ? error.message : String(error));
    }
  };
  const call = <T,>(path: string, body?: unknown) => {
    if (!connection) throw new Error('Backend is not connected');
    return request<T>(connection, path, body);
  };
  const refreshConversations=async(query=search,cursor:string|null=null)=>{
    const version=++conversationRequest.current;
    setConversationLoading(true);
    try {
      const params=new URLSearchParams({limit:'50',query});
      if(cursor)params.set('cursor',cursor);
      const page=await call<HistoryPage<Conversation>>(`/history/conversations?${params}`);
      if(version!==conversationRequest.current)return;
      setConversations(old=>{
        const rows=cursor?[...old,...page.items.filter(item=>!old.some(row=>row.id===item.id))]:page.items;
        const pin=selectedConversationMeta.current?.id===selected.current?selectedConversationMeta.current:null;
        return !query&&pin&&!rows.some(row=>row.id===pin.id)?[pin,...rows]:rows;
      });
      setConversationCursor(page.next);setConversationQuery(query);
    } finally {if(version===conversationRequest.current)setConversationLoading(false);}
  };
  const updateMessagePaging=(value:MessagePaging)=>{messageNavigation.current=value;setMessagePaging(value);};
  const loadMessagePage=async(id:string,cursor:string|null=null,previous:(string|null)[]=[])=>{
    const version=++messageRequest.current,expectedConnection=connection;
    const before=messageNavigation.current;
    updateMessagePaging({conversation:id,cursor,previous,next:null,busy:true});
    try {
      const params=new URLSearchParams({limit:'50'});
      if(cursor)params.set('cursor',cursor);
      const page=await call<HistoryPage<Message>>(`/history/conversations/${id}/messages?${params}`);
      if(version!==messageRequest.current||selected.current!==id||expectedConnection!==connectionRef.current)return;
      setMessages(page.items);
      updateMessagePaging({conversation:id,cursor,previous,next:page.next,busy:false});
      if(cursor)requestAnimationFrame(()=>document.querySelector('.messages')?.scrollTo({top:0}));
    } catch(error) {
      if(version===messageRequest.current&&selected.current===id)updateMessagePaging(
        before.conversation===id?{...before,busy:false}:{conversation:id,cursor:null,previous:[],next:null,busy:false});
      throw error;
    }
  };
  const refreshVisibleMessages=async(id:string)=>{
    if(messageNavigation.current.conversation===id&&messageNavigation.current.cursor!==null)return;
    await loadMessagePage(id);
  };
  useEffect(()=>{
    ++conversationRequest.current;
    setConversationCursor(null);
    if(!connection)return;
    setConversationLoading(true);
    const timer=setTimeout(()=>void attempt(()=>refreshConversations(search)),200);
    return()=>{clearTimeout(timer);++conversationRequest.current;};
  },[connection,search]);
  const boot = async (restart = false) => {
    if (bootBusy.current) return;
    bootBusy.current = true;
    if (restart) recovery.current.reset();
    setConnecting(true); setOnline(false);
    try {
      const value = await connect(restart);
      let ready: any;
      for (let i = 0; i < 10; i++) {
        try { ready = await request(value, '/health', undefined, AbortSignal.timeout(2000)); break; }
        catch { await new Promise(r => setTimeout(r, 200)); }
      }
      if (!ready) throw new Error('Backend started but did not become healthy. Check dependencies or restart.');
      if(ready.restore_pending)throw new Error('Restore is ready. Restart the backend to finish switching saved data.');
      setHealth(ready); setConnection(value); setModel(current => current || ready.default_model);
      setOnline(true); setNotice('');
    } catch (error) {
      setNotice(String(error));
      setBackendOutput(await diagnostics().catch(() => 'Native diagnostics unavailable.'));
    }
    finally { bootBusy.current = false; setConnecting(false); setBootVersion(version => version + 1); }
  };
  const restartAfterRestore=async()=>{
    ++conversationRequest.current;++messageRequest.current;
    selected.current='';selectedConversationMeta.current=null;
    setConversation('');setConversations([]);setConversationCursor(null);setSearch('');
    setMessages([]);const paging={conversation:'',cursor:null,previous:[],next:null,busy:false};
    messageNavigation.current=paging;setMessagePaging(paging);
    setActivityTask('');setPinnedActivityTask(undefined);setTasks([]);setEvents([]);
    history.current=new EventHistory();setStream({});setPreview(undefined);setApprovals([]);setGoal(null);
    setMemoryRequest('');setMemoryVersion(value=>value+1);
    setDraft('');setAttachments([]);setAttachmentViewer(null);setFile(null);setFiles([]);setActivityOpen(false);
    setPreferencesReady(false);setModel('');setCapabilities(null);setHealth(null);
    connectionRef.current=null;setConnection(null);setOnline(false);
    await boot(true);
  };
  useEffect(() => { void boot(); }, []);
  useEffect(() => {
    if (online || connecting) return;
    const delay = recovery.current.nextDelay();
    if (delay === null) return;
    const timer = setTimeout(() => { void boot(); }, delay);
    return () => clearTimeout(timer);
  }, [online, connecting, bootVersion]);
  useEffect(() => { selected.current = conversation; }, [conversation]);

  const refreshTasks = async () => {
    const expected=connection;
    const data = await call<{ tasks: Task[]; approvals: Approval[] }>('/activity');
    if(expected!==connectionRef.current)return;
    setTasks(data.tasks); setApprovals(approvalList(data.approvals));
    await refreshPinnedTask(data.tasks);
  };
  const refreshPinnedTask=async(rows:Task[])=>{
    const id=activitySelection.current;
    if(!id||deletingConversation.current===selected.current)return;
    if(rows.some(task=>task.id===id)){setPinnedActivityTask(undefined);return;}
    const expectedConnection=connection;
    try {
      const task=await call<Task>(`/history/tasks/${encodeURIComponent(id)}`);
      if(activitySelection.current===id&&expectedConnection===connectionRef.current&&task.conversation===selected.current)setPinnedActivityTask(task);
    } catch(error) {
      if(activitySelection.current===id&&expectedConnection===connectionRef.current&&deletingConversation.current!==selected.current)throw error;
    }
  };
  const emergencyStop=()=>void attempt(async()=>{await call('/emergency-stop',{});await refreshTasks();});
  const refreshGoal = async (id = selected.current) => {
    if (!id) {setGoal(null);return;}
    const expected=connection;
    const result=await call<{goal:Goal|null}>(`/conversations/${id}/goal`);
    if(selected.current===id&&expected===connectionRef.current)setGoal(result.goal);
  };
  const refreshModels = async () => {
    const expected=connection;
    const [engine,resources]=await Promise.all([call<ModelStatus>('/models'),call<Telemetry>('/telemetry')]);
    if(expected===connectionRef.current){setModels(engine);setTelemetry(resources);}
  };
  useEffect(() => {
    if (!connection) return;
    let disposed=false;
    void attempt(async () => {
      const saved = await call<{model?:string;context?:number;temperature?:number;max_output?:number;thinking?:boolean|string|null;keep_alive?:string|number}>('/preferences');
      if(disposed||connectionRef.current!==connection)return;
      const preferences={...health?.inference_defaults,...saved};
      if (preferences.model) setModel(preferences.model);
      if (preferences.context) setContext(preferences.context);
      if (preferences.temperature != null) setTemperature(preferences.temperature);
      if (preferences.max_output != null) setMaxOutput(preferences.max_output);
      if ('thinking' in preferences) setThinking(preferences.thinking);
      if (preferences.keep_alive != null) setKeepAlive(preferences.keep_alive);
      setPreferencesReady(true);
      const catalog=await call<SlashCommand[]>('/commands');
      if(disposed||connectionRef.current!==connection)return;
      setCommands(catalog);
      await refreshTasks();
      const engine = await call<{running:boolean}>('/models');
      if(disposed||connectionRef.current!==connection)return;
      if (!engine.running) await call('/models/start', {});
      await refreshModels();
    });
    const timer = setInterval(() => { void attempt(refreshModels); }, 10000);
    return () => {disposed=true;clearInterval(timer);};
  }, [connection]);

  useEffect(() => {
    if (!connection || !preferencesReady) return;
    const timer = setTimeout(() => void attempt(() => call('/preferences', {model, context, temperature,max_output:maxOutput,thinking,keep_alive:keepAlive})), 500);
    return () => clearTimeout(timer);
  }, [model, context, temperature,maxOutput,thinking,keepAlive, preferencesReady, connection]);

  useEffect(()=>{
    setCapabilities(null);setCapabilityError('');
    if(!connection||!model)return;
    const controller=new AbortController();
    const timer=setTimeout(()=>{setCapabilityError('Capability metadata request timed out. Refresh to retry.');controller.abort();},5500);
    void request<ModelCapabilities>(connection,`/models/capabilities?model=${encodeURIComponent(model)}`,undefined,controller.signal)
      .then(value=>{if(!controller.signal.aborted)setCapabilities(value);})
      .catch(error=>{if(!controller.signal.aborted)setCapabilityError(String(error));})
      .finally(()=>clearTimeout(timer));
    return()=>{controller.abort();clearTimeout(timer);};
  },[connection,model,capabilityVersion]);

  useEffect(() => {
    if (!connection) return;
    let disposed = false;
    let socket: WebSocket;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      const result = await request<{ tasks: Task[]; approvals: Approval[] }>(connection, '/activity');
      if (disposed||connectionRef.current!==connection) return;
      setTasks(result.tasks); setApprovals(approvalList(result.approvals));
      await refreshPinnedTask(result.tasks);
      const id = selected.current;
      if (id) {
        if (!disposed && selected.current === id) {await refreshVisibleMessages(id); await refreshGoal(id);}
      }
    };
    const subscribe = () => {
      const peer = new WebSocket(`ws://127.0.0.1:${connection.port}/events`);
      socket = peer;
      history.current.beginConnection();
      peer.onopen = () => {
        if (disposed || socket !== peer||connectionRef.current!==connection) return;
        peer.send(JSON.stringify({ token: connection.token, after: history.current.cursor, store_id: history.current.storeId }));
      };
      peer.onmessage = ({ data }) => {
        if (disposed || socket !== peer||connectionRef.current!==connection) return;
        try {
          const packet = JSON.parse(data) as EventPacket;
          const accepted = history.current.accept(packet);
          if (accepted === null) return;
          if (packet.kind === 'snapshot') {
            setTasks(packet.payload.tasks!); setApprovals(approvalList(packet.payload.approvals));
            setStream(packet.payload.streams || {}); setPreview(undefined);
          }
          setEvents([...history.current.events]);
          if (packet.kind === 'ready') {setOnline(true); void attempt(refresh);}
          if (packet.kind === 'live') {
            let changed = false;
            for (const event of accepted) {
              const payload=record(event.payload);
              if (event.kind === 'token' && event.task && typeof payload?.text==='string') {
                const text=payload.text;
                setStream(old => ({ ...old, [event.task!]: (old[event.task!] || '') + text }));
              }
              const approval=approvalPayload(event);
              if (approval) setApprovals(old => [...old.filter(a=>a.id!==approval.id), approval]);
              if (event.kind === 'approval_resolved' && typeof payload?.id==='string') setApprovals(old => old.filter(a => a.id !== payload.id));
              if (event.kind === 'preview') setPreview(readPreview(event));
              if (event.kind === 'persistence_error' && typeof payload?.text==='string') setNotice(payload.text);
              if (event.kind === 'result') {
                setNotice(current => current === 'Worker stopped. Final outcome is waiting for local storage recovery.' ? '' : current);
                setStream(old => {const next = {...old}; delete next[event.task!]; return next;});
              }
              changed ||= ['result','started','approval','approval_resolved','persistence_error'].includes(event.kind);
            }
            if (changed) void attempt(refresh);
          }
          peer.send(JSON.stringify({ack:packet.delivery}));
        } catch {
          setNotice('Activity synchronization failed. Reconnecting from the last accepted event.');
          peer.close();
        }
      };
      peer.onclose = ({code}) => {
        if (!disposed && socket === peer&&connectionRef.current===connection) {
          setOnline(false); setApprovals([]); setPreview(undefined);
          if (code === 1013) setNotice('Activity delivery timed out. Reconnecting from the last accepted event.');
          if (code === 1009) setNotice('An activity item exceeds the delivery limit. Inspect the local task history.');
          timer = setTimeout(subscribe, 2000);
        }
      };
      peer.onerror = () => peer.close();
    };
    subscribe();
    return () => { disposed = true; clearTimeout(timer); socket?.close(); };
  }, [connection]);

  useEffect(() => { if(messageNavigation.current.cursor===null)end.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, stream]);
  const selectConversation = async (id: string, preserveDraft = false) => {
    const expected=connection;
    setConversation(id); selected.current = id;setActivityTask('');
    setPinnedActivityTask(undefined);
    setMessages([]);
    setGoal(null);
    if (!preserveDraft) setDraft('');
    setAttachments([]);
    const [, nextAttachments, metadata] = await Promise.all([
      loadMessagePage(id), call<Attachment[]>(`/conversations/${id}/attachments`),
      call<Conversation>(`/history/conversations/${id}`),
    ]);
    if (selected.current === id&&expected===connectionRef.current) {
      selectedConversationMeta.current=metadata;
      setConversations(old=>old.some(row=>row.id===id)?old.map(row=>row.id===id?metadata:row):[metadata,...old]);
      setAttachments(nextAttachments); await refreshGoal(id);
    }
  };
  const newConversation = async (title = 'New conversation', preserveDraft = false) => {
    const expected=connection;
    const created = await call<{ id: string }>('/conversations', { title: title.slice(0, 80) });
    if(expected!==connectionRef.current)throw new Error('Connection changed; retry creating the conversation after reconnecting');
    setSearch('');await selectConversation(created.id, preserveDraft);await refreshConversations('');
    return created.id;
  };
  const submit = async (objective = draft, regenerate = false) => {
    if (!regenerate && objective.trim().startsWith('/') && !objective.trim().startsWith('//')) {
      await executeSlash(objective);return;
    }
    if (active || sending || uploadBusy.current || !model || !online) return;
    if (objective.trim().startsWith('//')) objective=objective.trim().slice(1);
    stopRequested.current=false;
    setSending(true);
    setSubmittingConversation(conversation);
    try {
      const id = conversation || await newConversation(objective);
      setSubmittingConversation(id);
      const mode = ['models', 'history','memory'].includes(view) ? 'agent' : view;
      const started=await call<{id:string}>('/tasks', { conversation: id, objective, mode, model, project, profile:toolProfile, context, temperature,max_output:maxOutput,thinking,keep_alive:keepAlive, regenerate,
        attachments: regenerate ? [] : attachments.map(a => a.id) });
      if(selected.current===id)setActivityTask(started.id);
      if(stopRequested.current)await call(`/tasks/${started.id}/cancel`,{});
      if (selected.current === id) {setDraft('');setAttachments([]);await loadMessagePage(id);}
      await refreshTasks();
    } finally { stopRequested.current=false;setSending(false);setSubmittingConversation(''); }
  };
  const chooseProject = async () => {
    const chosen = await open({ directory: true, multiple: false, defaultPath: health?.workspace });
    if (typeof chosen === 'string') {
      const result = await call<{ project: string }>('/project', { path: chosen });
      setMemoryRequest('');
      setProject(result.project); setFile(null);
      setFiles((await call<{ files: string[] }>(`/files?project=${encodeURIComponent(result.project)}`)).files);
    }
  };
  const addFiles = async (incoming: File[]) => {
    if (!connection || uploadBusy.current || !incoming.length) return;
    if (attachments.length + incoming.length > 4) throw new Error('Attach at most four files per message');
    uploadBusy.current = true; setUploading(true);
    try {
      const id = conversation || await newConversation('Attached files', true);
      for (const file of incoming) {
        const attached = await upload(connection, id, file);
        if (selected.current === id) setAttachments(old => [...old, attached]);
      }
    } finally { uploadBusy.current = false; setUploading(false); }
  };
  const showAttachment = async (item: Attachment) => {
    setAttachmentViewer(await call(`/conversations/${conversation}/attachments/${item.id}`));
  };
  const captureScreen = async () => {
    setCaptureConfirm(false);
    if (uploadBusy.current) return;
    uploadBusy.current = true; setUploading(true);
    try {
      if (attachments.length >= 4) throw new Error('Attach at most four files per message');
      const id = conversation || await newConversation('Screen capture', true);
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
      const item = await call<Attachment>(`/conversations/${id}/screenshot`, {confirmed:true});
      if (selected.current === id) {
        setAttachments(old => [...old, item]);
        setAttachmentViewer(await call(`/conversations/${id}/attachments/${item.id}`));
      }
    } finally { uploadBusy.current = false; setUploading(false); }
  };
  const applyChatAction = async () => {
    if (!chatAction) return;
    const {kind, chat} = chatAction;
    if(kind==='delete')deletingConversation.current=chat.id;
    try {
    await call(`/conversations/${chat.id}/${kind}`, kind === 'delete' ? {confirmed:true} : {title:renameTitle});
    if(kind==='rename'&&selected.current===chat.id)selectedConversationMeta.current=await call<Conversation>(`/history/conversations/${chat.id}`);
    if (kind === 'delete') {
      if (selected.current === chat.id) {
        setConversation(''); selected.current = '';selectedConversationMeta.current=null; setMessages([]); setAttachments([]); setDraft('');
        setActivityTask('');setPinnedActivityTask(undefined);
        ++messageRequest.current;updateMessagePaging({conversation:'',cursor:null,previous:[],next:null,busy:false});
        setGoal(null);
        setAttachmentViewer(null);
      }
      history.current.clear(); setEvents([]); await refreshTasks();
    }
    await refreshConversations(); setChatAction(null);
    } finally {if(deletingConversation.current===chat.id)deletingConversation.current='';}
  };
  const exportChat = async () => {
    if(!conversation||exporting)return;
    setExporting(true);
    try {
      const id=conversation;
      const result=await call<{markdown:string;message_count:number;bytes:number;complete:boolean}>(`/history/conversations/${id}/export`);
      if(!result.complete)throw new Error('Incomplete conversation export refused');
      const blob=new Blob([result.markdown],{type:'text/markdown;charset=utf-8'});
      if(blob.size!==result.bytes)throw new Error('Conversation export byte count mismatch');
      const url=URL.createObjectURL(blob),link=document.createElement('a');
      link.href=url;link.download=`conversation-${id}.md`;
      document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      setNotice(`Exported ${result.message_count} messages (${result.bytes} UTF-8 bytes). Attachment contents are not included.`);
    } finally {setExporting(false);}
  };
  const chooseCommand = (command:SlashCommand) => {
    setDraft(`/${command.name} `);setShowCommandHelp(false);setSlashDismissed(true);
    requestAnimationFrame(()=>composerInput.current?.focus());
  };
  const executeSlash = async (input:string) => {
    const match=input.trim().match(/^\/(\S+)(?:\s+([\s\S]*))?$/);
    const name=match?.[1].toLowerCase()||'';
    const argument=match?.[2]?.trim()||'';
    const command=commands.find(c=>c.name===name);
    if (!command) throw new Error(`Unknown command /${name}. Type /help to see available commands.`);
    if (['help','export','delete','stop'].includes(name)&&argument) throw new Error(`Usage: ${command.usage}`);
    if(name==='stop') {
      const snapshot=await call<{tasks:Task[]}>('/activity');
      const running=snapshot.tasks.find(t=>['running','waiting'].includes(t.status)||!!t.runtime_state);
      if(running){await call(`/tasks/${running.id}/cancel`,{});await refreshTasks();}
      else if(sending){stopRequested.current=true;setNotice('Stop requested. The starting task will be cancelled when created.');}
      else setNotice('No active task to stop.');
      setDraft('');return;
    }
    if(sending || uploadBusy.current)throw new Error('Wait for the pending submission or upload; /stop remains available.');
    stopRequested.current=false;
    setSending(true);setSubmittingConversation(conversation);setSlashDismissed(true);setNotice('');
    try {
      if (command.local) {
        if(name==='forget'){
          const ident=argument.replace(/^memory:/,'');
          if(!/^[a-f0-9]{32}$/.test(ident))throw new Error('Usage: /forget <memory-id>');
          setMemoryRequest(ident);setMemoryVersion(v=>v+1);setView('memory');
        }
        if(name==='help')setShowCommandHelp(true);
        if(name==='new')await newConversation(argument||'New conversation');
        if(name==='export') {
          if(!messages.length)throw new Error('There are no messages to export yet.');
          await exportChat();
        }
        if(name==='model') {
          if(!argument)setView('models');
          else {
            const available=await call<any>('/models');setModels(available);
            if(!available.models.some((item:any)=>item.name===argument))throw new Error('Select an installed model by its exact name.');
            setModel(argument);setNotice(`Active model: ${argument}`);
          }
        }
        if(name==='rename'||name==='delete') {
          const chat=conversations.find(c=>c.id===conversation);
          if(!chat)throw new Error('Select a conversation first.');
          if(name==='delete')setChatAction({kind:'delete',chat});
          else {
            if(!argument)throw new Error(`Usage: ${command.usage}`);
            await call(`/conversations/${chat.id}/rename`,{title:argument});
            if(selected.current===chat.id)selectedConversationMeta.current=await call<Conversation>(`/history/conversations/${chat.id}`);
            await refreshConversations();
          }
        }
        setDraft('');return;
      }
      if(!online)throw new Error('Reconnect the backend before running a command.');
      const id=selected.current||await newConversation(input,true);
      setSubmittingConversation(id);
      try {
        const result=await call<SlashResult>('/slash',{conversation:id,objective:input,
          model:model||health?.default_model,project,profile:toolProfile,context,temperature,max_output:maxOutput,thinking,keep_alive:keepAlive,attachments:attachments.map(a=>a.id)});
        if(result.action==='task'&&stopRequested.current)await call(`/tasks/${result.id}/cancel`,{});
        if(result.action==='task') {
          if(selected.current===id)setActivityTask(result.id!);
          if(selected.current===id) {
            setDraft(current=>current.trim()===input.trim()?'':current);
            setAttachments([]);setView(taskView(result.mode!));await loadMessagePage(id);
          }
        } else if(selected.current===id) {
          setDraft(current=>current.trim()===input.trim()?'':current);
          if(result.notice)setNotice(result.notice);
          if(result.action==='memory'){setMemoryVersion(v=>v+1);setMemoryRequest('');setView('memory');}
        }
        await refreshTasks();
      } finally {await refreshGoal(id);}
    } finally {stopRequested.current=false;setSending(false);setSubmittingConversation('');}
  };
  const knownTasks=pinnedActivityTask&&!tasks.some(task=>task.id===pinnedActivityTask.id)?[...tasks,pinnedActivityTask]:tasks;
  const activityTask=selectActivityTask(knownTasks,conversation,activityTaskID);
  const contextReport=events.filter(event=>event.kind==='context'&&event.task===activityTask?.id).slice(-1)[0]?.payload;
  const currentTask=activityTask&&activityTask.id in stream?activityTask:undefined;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Bot size={22}/></div><div>LOCAL AGENT<span>STUDIO</span></div></div>
      <button className="new-chat" disabled={!online || uploading} onClick={() => void attempt(newConversation)}><Plus size={17}/> New conversation</button>
      <nav aria-label="Workspaces">{views.map(item => <button key={item.id} className={view === item.id ? 'nav-item selected' : 'nav-item'}
        onClick={() => {setMemoryRequest('');setView(item.id);}}><item.icon size={17}/>{item.label}</button>)}</nav>
      <div className="section-label">CONVERSATIONS <span>{conversationQuery===search?conversations.length:0} loaded</span></div>
      <label className="chat-search"><Search size={14}/><input aria-label="Search conversations" placeholder="Search chats" maxLength={120} value={search} onChange={e => setSearch(e.target.value)}/></label>
      <div className="conversation-list" aria-busy={conversationLoading}>{(conversationQuery===search?conversations:[]).map(c => <div key={c.id} className={c.id === conversation ? 'conversation-row selected' : 'conversation-row'}>
        <button className="conversation" disabled={uploading} onClick={() => void attempt(() => selectConversation(c.id))}><MessageSquare size={14}/><span>{c.title}</span></button>
        <button className="chat-icon" title={`Rename ${c.title}`} aria-label={`Rename ${c.title}`} onClick={() => {setChatAction({kind:'rename',chat:c});setRenameTitle(c.title);}}><Pencil size={12}/></button>
        <button className="chat-icon" title={`Delete ${c.title}`} aria-label={`Delete ${c.title}`} disabled={uploading || tasks.some(t => t.conversation===c.id && (['running','waiting'].includes(t.status)||!!t.runtime_state))}
          onClick={() => setChatAction({kind:'delete',chat:c})}><Trash2 size={12}/></button>
      </div>)}
      {conversationLoading&&<p className="history-page-status" role="status">Loading conversations…</p>}
      {conversationCursor&&<button className="history-more" disabled={conversationLoading} onClick={()=>void attempt(()=>refreshConversations(search,conversationCursor))}>Older conversations</button>}
      {!conversationLoading&&conversationQuery===search&&!conversations.length&&<p className="history-page-status">No conversations match.</p>}
      </div>
      <div className="local-status"><span className={online ? 'status-dot' : 'status-dot offline'}/><div>{online ? 'Connected locally' : 'Backend disconnected'}<small>No cloud inference</small></div></div>
    </aside>

    <main>
      <header><div><h1>{views.find(v => v.id === view)?.label}</h1><span className="breadcrumb">Local Agent Studio / {project === '.' ? 'Workspace' : project}</span></div>
        <div className="header-actions"><span className="privacy"><ShieldCheck size={14}/> Local & private</span>
          <button className="activity-toggle" aria-haspopup="dialog" aria-expanded={activityOpen} onClick={()=>setActivityOpen(true)}><Activity size={14}/> Activity</button>
          <button title="Export conversation as Markdown" aria-describedby="export-description" disabled={!conversation||exporting} onClick={()=>void attempt(exportChat)}><Download size={14}/> {exporting?'Exporting…':'Export'}</button>
          <span className="sr-only" id="export-description">Complete stored transcript, limited to 5,000 messages or 8 MiB. Attachment contents are omitted.</span>
          <button className="danger subtle" disabled={!connection} onClick={emergencyStop}><Square size={14}/> Emergency stop</button></div>
      </header>
      {notice && <div role="alert" className="notice"><span>{notice}</span><button title="Dismiss notification" onClick={() => setNotice('')}><X size={16}/></button></div>}
      {!online && <div className="connection-banner"><Activity size={18}/><span>{connecting ? 'Starting the local backend…' : 'Connection lost. Your conversations are saved. Interrupted tasks will not restart automatically.'}</span>
        <button disabled={connecting} onClick={() => void boot(true)}><RotateCcw size={14}/> Restart backend</button></div>}
      {!online && backendOutput && <details className="panel"><summary>Backend diagnostics (bounded, redacted)</summary><pre>{backendOutput}</pre></details>}

      {goal && !['models','history','memory'].includes(view) && <GoalPanel goal={goal} busy={!!active||sending||uploading}
        run={command=>void attempt(()=>executeSlash(command))}/>}
      {view === 'models' ? <ModelsPanel models={models} model={model} telemetry={telemetry} permissions={health?.permissions}
        connection={connection} busy={!!active||sending||uploading}
        onRestoreRestart={restartAfterRestore}
        protectedConversation={conversation} onRetentionChanged={async()=>{
          setMemoryRequest('');setMemoryVersion(value=>value+1);
          await refreshConversations(search);await refreshTasks();await refreshGoal();
        }}
        connected={!!connection} context={context} temperature={temperature} maxOutput={maxOutput} thinking={thinking} keepAlive={keepAlive}
        capabilities={capabilities} capabilityError={capabilityError} setModel={setModel} setContext={setContext} setTemperature={setTemperature}
        setMaxOutput={setMaxOutput} setThinking={setThinking} setKeepAlive={setKeepAlive}
        onRefresh={()=>setCapabilityVersion(value=>value+1)} onStart={()=>void attempt(async()=>{
          const result=await call<{message:string}>('/models/start',{});setNotice(result.message);await refreshModels();
        })}/> : view === 'history' ? <TaskHistory tasks={tasks} connection={connection} busy={!!active||sending||uploading}
        onOpen={task=>void attempt(async()=>{await selectConversation(task.conversation);setPinnedActivityTask(task);setActivityTask(task.id);setView(taskView(task.mode));await refreshTasks();})}
        onNewInstruction={task=>void attempt(async()=>{
          await selectConversation(task.conversation,true);setPinnedActivityTask(task);setActivityTask(task.id);setView(taskView(task.mode));await refreshTasks();
          setNotice('Review the journal and describe the next action. This starts a fresh run with fresh approvals.');
          requestAnimationFrame(()=>composerInput.current?.focus());
        })}/> : view==='memory'?<MemoryPanel connection={connection} project={project} conversation={conversation}
        messages={messages} busy={!!active||sending||uploading} ensureConversation={()=>newConversation('Project memory',true)}
        onSource={id=>void attempt(async()=>{await selectConversation(id);setView('chat');})}
        requested={memoryRequest} version={memoryVersion} chooseProject={()=>void attempt(chooseProject)}/>: <div className="work-area">
        <section className="chat-column">
          <WorkspacePanel view={view} toolProfile={toolProfile} busy={!!active||sending} connection={connection}
            model={model} settings={{context,temperature,max_output:maxOutput,thinking,keep_alive:keepAlive}}
            inspectionTask={activityTask} ensureConversation={async()=>conversation||await newConversation('Repository inspection',true)}
            onInspectionStarted={async id=>{setActivityTask(id);await refreshTasks();}}
            onScheduledTask={async(id,chat)=>{await selectConversation(chat);setActivityTask(id);await refreshTasks();}}
            project={project} files={files} file={file} preview={previewFor(preview,activityTask)} setToolProfile={setToolProfile}
            onChooseProject={()=>void attempt(chooseProject)}
            onLaunchNotepad={()=>void attempt(()=>submit('Launch the approved Notepad application, inspect its controls and report what you observe.'))}
            onSelectFile={path=>void attempt(async()=>setFile(await call(`/file?path=${encodeURIComponent(path)}`)))}
            onRefreshFiles={()=>void attempt(async()=>setFiles((await call<{files:string[]}>(`/files?project=${encodeURIComponent(project)}`)).files))}/>
          {conversation&&<nav className="message-pages" aria-label="Message history">
            <button disabled={messagePaging.busy||!messagePaging.next} onClick={()=>void attempt(()=>loadMessagePage(conversation,messagePaging.next,[...messagePaging.previous,messagePaging.cursor]))}>Older messages</button>
            <span role="status">{messagePaging.busy?'Loading messages…':`${messages.length} shown · page ${messagePaging.previous.length+1}`}</span>
            <button disabled={messagePaging.busy||!messagePaging.previous.length} onClick={()=>void attempt(()=>loadMessagePage(conversation,messagePaging.previous.at(-1)!,messagePaging.previous.slice(0,-1)))}>Newer messages</button>
            {messagePaging.cursor&&<button disabled={messagePaging.busy} onClick={()=>void attempt(()=>loadMessagePage(conversation))}>Latest messages</button>}
          </nav>}
          <ChatMessages messages={messages} currentTask={messagePaging.cursor===null?currentTask:undefined} liveText={currentTask?stream[currentTask.id]:''} end={end}
            onSuggestion={(nextView,text)=>{setView(nextView);setDraft(text);}} onAttachment={attachment=>void attempt(()=>showAttachment(attachment))}
            onCopy={text=>void attempt(async()=>{await navigator.clipboard.writeText(text);setNotice('Response copied');})}/>
          <ContextStatus report={contextReport}/>
          <div className="composer-wrap"><div className="composer" onDragOver={e => {e.preventDefault();}}
            onDrop={e => {e.preventDefault(); void attempt(() => addFiles(Array.from(e.dataTransfer.files)));}}>
            {slashVisible && <SlashMenu commands={slashMatches} index={Math.min(slashIndex,slashMatches.length-1)} choose={chooseCommand}/>}
            {!!attachments.length && <div className="attachment-list draft-attachments">{attachments.map(a => <div className="attachment-chip" key={a.id}>
              <button title={`Preview ${a.name}`} onClick={() => void attempt(() => showAttachment(a))}>{a.mime.startsWith('image/') ? <ImageIcon size={15}/> : <FileText size={15}/>}<span>{a.name}</span></button>
              <button title={`Remove ${a.name}`} disabled={uploading || sending} onClick={() => void attempt(async () => {
                await call(`/conversations/${conversation}/attachments/${a.id}/remove`, {}); setAttachments(old => old.filter(item => item.id !== a.id));
              })}><X size={13}/></button></div>)}</div>}
            <textarea ref={composerInput} aria-label="Message" aria-autocomplete="list" aria-controls={slashVisible?'slash-menu':undefined}
            aria-expanded={slashVisible} placeholder={view === 'chat' ? 'Message your local model, or type / for commands…' : 'Describe a task, or type / for commands…'} value={draft} onChange={e => setDraft(e.target.value)}
            onPaste={e => {const images = Array.from(e.clipboardData.files).filter(f => f.type.startsWith('image/')); if (images.length) {e.preventDefault();void attempt(() => addFiles(images));}}}
            onKeyDown={e => {
              if(e.nativeEvent.isComposing)return;
              if(slashVisible && ['ArrowUp','ArrowDown'].includes(e.key)) {
                e.preventDefault();setSlashIndex(i=>(i+(e.key==='ArrowDown'?1:-1)+slashMatches.length)%slashMatches.length);return;
              }
              if(slashVisible&&e.key==='Escape'){e.preventDefault();setSlashDismissed(true);return;}
              if(slashVisible&&(e.key==='Tab'||(e.key==='Enter'&&!e.shiftKey&&!commands.some(c=>draft.toLowerCase()===`/${c.name}`)))) {
                e.preventDefault();chooseCommand(slashMatches[Math.min(slashIndex,slashMatches.length-1)]);return;
              }
              if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void attempt(()=>submit());}
            }}/>
            <div className="composer-bottom"><div className="model-select"><Cpu size={14}/><select aria-label="Active model" value={model} onChange={e => setModel(e.target.value)}><option value="" disabled>Select a model</option>{models.models.map((m:any) => <option key={m.name} value={m.name}>{m.name}</option>)}</select><ChevronDown size={12}/></div>
              <div className="composer-actions">
                <button title="Slash commands" aria-label="Slash commands" onClick={()=>setShowCommandHelp(true)}>/</button>
                <input hidden ref={attachmentInput} type="file" multiple onChange={e => {void attempt(() => addFiles(Array.from(e.target.files || [])));e.target.value='';}}/>
                <button title="Attach images or text/code files" aria-label="Attach files" disabled={uploading || sending || !online} onClick={() => attachmentInput.current?.click()}><Paperclip size={16}/></button>
                <button title="Capture screenshot" aria-label="Capture screenshot" disabled={uploading || sending || !online} onClick={() => setCaptureConfirm(true)}><Camera size={16}/></button>
                <button title="Regenerate the latest request" disabled={!!active || !messages.length || uploading || !!attachments.length} onClick={() => void attempt(() => submit('', true))}><RotateCcw size={16}/></button>
                {active ? <button className="send stop" title="Cancel current task" onClick={() => void attempt(() => call(`/tasks/${active.id}/cancel`, {}))}><Square size={17}/></button>
                  : <button className="send" title="Send message" disabled={!draft.trim() || !online || !model || sending || uploading} onClick={() => void attempt(() => submit())}><ArrowUp size={20}/></button>}</div></div></div>
            <small className="composer-note">{uploading ? 'Adding attachment…' : active ? 'Working locally · /stop cancels the current task' : 'Type / for commands · attach files or paste screenshots · Shift + Enter for a new line'}</small></div>
        </section>
        {!narrow&&<ActivityPanel events={events} tasks={knownTasks.filter(task=>task.conversation===conversation)} task={activityTask}
          globalActive={active} approvals={approvals} sending={sending&&submittingConversation===conversation} onSelect={setActivityTask}
          onOpenActive={()=>void attempt(async()=>{if(active){await selectConversation(active.conversation);setActivityTask(active.id);setView(taskView(active.mode));}})}/>}

      </div>}
    </main>

    {narrow&&activityOpen&&<Modal title="activity-drawer-title" className="activity-drawer" onDismiss={()=>setActivityOpen(false)}>
      <div className="panel-heading"><h2 id="activity-drawer-title">Task activity</h2><button aria-label="Close activity" onClick={()=>setActivityOpen(false)}><X size={18}/></button></div>
      <button className="danger" disabled={!connection} onClick={emergencyStop}>Emergency stop</button>
      <ActivityPanel events={events} tasks={knownTasks.filter(task=>task.conversation===conversation)} task={activityTask}
        globalActive={active} approvals={approvals} sending={sending&&submittingConversation===conversation} onSelect={setActivityTask}
        onOpenActive={()=>void attempt(async()=>{if(active){await selectConversation(active.conversation);setActivityTask(active.id);setView(taskView(active.mode));setActivityOpen(false);}})}/>
    </Modal>}
    {showCommandHelp && <CommandHelp commands={commands} choose={chooseCommand} close={()=>setShowCommandHelp(false)}/>}
    {chatAction && <Modal title="chat-action-title" onDismiss={()=>setChatAction(null)}>
      <h2 id="chat-action-title">{chatAction.kind === 'delete' ? 'Delete conversation?' : 'Rename conversation'}</h2>
      {chatAction.kind === 'delete' ? <p>Delete “{chatAction.chat.title}” and its messages, attachments, task history and saved memories? This also resets affected future memory context. This cannot be undone.</p>
        : <label>Conversation name<input autoFocus maxLength={120} value={renameTitle} onChange={e => setRenameTitle(e.target.value)}/></label>}
      <div className="approval-buttons"><button onClick={() => setChatAction(null)}>Cancel</button><button className={chatAction.kind === 'delete' ? 'danger' : 'primary'}
        disabled={chatAction.kind==='rename' && !renameTitle.trim()} onClick={() => void attempt(applyChatAction)}>{chatAction.kind==='delete' ? 'Delete conversation' : 'Save name'}</button></div>
    </Modal>}
    {captureConfirm && <Modal title="capture-title" onDismiss={()=>setCaptureConfirm(false)}>
      <h2 id="capture-title">Capture your main screen?</h2><p>The screenshot may include other windows. Review it before sending your message. For a selected region, use Win + Shift + S, then paste here.</p>
      <div className="approval-buttons"><button onClick={() => setCaptureConfirm(false)}>Cancel</button><button className="primary" onClick={() => void attempt(captureScreen)}>Capture and preview</button></div>
    </Modal>}
    {attachmentViewer && <Modal title="attachment-title" className="attachment-viewer" onDismiss={()=>setAttachmentViewer(null)}>
      <div className="panel-heading"><h2 id="attachment-title">{attachmentViewer.name}</h2><button aria-label="Close attachment preview" onClick={() => setAttachmentViewer(null)}><X size={18}/></button></div>
      {attachmentViewer.image ? <img alt={attachmentViewer.name} src={`data:${attachmentViewer.mime};base64,${attachmentViewer.image}`}/> : <pre>{attachmentViewer.text}</pre>}
      <small>Stored locally with this chat. Attachment contents do not grant additional agent permissions.</small>
    </Modal>}
    {approval && <ActionApproval approval={approval} count={approvals.length}
      sourceName={conversations.find(chat=>chat.id===tasks.find(task=>task.id===approval.task)?.conversation)?.title??'Unknown conversation'}
      sourceAvailable={tasks.some(task=>task.id===approval.task)}
      onSource={()=>void attempt(async()=>{const task=tasks.find(task=>task.id===approval.task);if(task){await selectConversation(task.conversation);setActivityTask(task.id);setView(taskView(task.mode));}})}
      onStop={emergencyStop} onAnswer={approved=>void attempt(async()=>{await call(`/tasks/${approval.task}/approvals/${approval.id}`,{approved});await refreshTasks();})}/>}
  </div>;
}
