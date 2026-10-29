"""Fixed guest bootstrap. Repository contents are bytes, never bootstrap instructions."""

LOAD_STAGE = "import base64,sys; code=sys.stdin.buffer.readline(16385); " \
             "assert len(code)<=16384 and code.endswith(b'\\n'); " \
             "exec(base64.b64decode(code.rstrip(b'\\r\\n'),validate=True))"

STAGE = r'''
import base64,json,os,subprocess,sys
from pathlib import Path,PurePosixPath
sys.stdout.reconfigure(encoding='utf-8')
raw=sys.stdin.buffer.read(8*1024*1024+1)
if len(raw)>8*1024*1024:raise ValueError('Input budget')
p=json.loads(raw)
if set(p)!={'root','run_id','files','cwd','argv','runner','timeout'}:raise ValueError('Input schema')
ident=p['run_id']
if not isinstance(ident,str) or len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Run identity')
base=Path(p['root'])
if not base.is_absolute() or not base.resolve().is_relative_to(Path.home()) or base.resolve()==Path.home():raise ValueError('Guest scope')
base.mkdir(exist_ok=True)
if base.is_symlink() or base.stat().st_file_attributes&0x400:raise ValueError('Guest link')
run=base/ident;run.mkdir()
work=run/'project';work.mkdir()
def relative(value):
 if not isinstance(value,str) or not value or any(c in value for c in '\\:\x00\r\n'):raise ValueError('Relative path')
 path=PurePosixPath(value)
 if path.is_absolute() or '..' in path.parts:return None
 return Path(*path.parts)
seen=set();size=0
if not isinstance(p['files'],list) or not 1<=len(p['files'])<=200:raise ValueError('Files budget')
for entry in p['files']:
 if set(entry)!={'path','data'}:raise ValueError('File schema')
 name=relative(entry['path'])
 if name is None or str(name).casefold() in seen:raise ValueError('Duplicate or invalid file')
 seen.add(str(name).casefold())
 data=base64.b64decode(entry['data'],validate=True);size+=len(data)
 if size>4*1024*1024 or len(data)>256*1024:raise ValueError('Bytes budget')
 destination=work/name;destination.parent.mkdir(parents=True,exist_ok=True)
 with destination.open('xb') as stream:stream.write(data)
cwd=relative(p['cwd'])
if cwd is None or not (work/cwd).is_dir():raise ValueError('Working directory not staged')
argv=p['argv']
if not isinstance(argv,list) or not 1<=len(argv)<=128 or argv[0]!=sys.executable or any(not isinstance(a,str) or '\x00' in a or len(a)>4096 for a in argv):raise ValueError('Command schema')
if type(p['timeout']) is not int or not 1<=p['timeout']<=120:raise ValueError('Time budget')
report=run/'counts.json'
if p['runner'] is not None:
 if not isinstance(p['runner'],str) or len(p['runner'])>16000 or argv[1:3]!=['-m','unittest']:raise ValueError('Verifier schema')
 runner=run/'runner.py';runner.write_text(p['runner'],encoding='utf-8')
 argv=[sys.executable,'-I','-X','utf8','-u',str(runner),str(report),ident,*argv[3:]]
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','TEMP','TMP'}}
env.update(PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1',GIT_TERMINAL_PROMPT='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
process=subprocess.Popen(argv,cwd=work/cwd,env=env,stdin=subprocess.DEVNULL,stderr=subprocess.STDOUT)
try:code=process.wait(timeout=p['timeout'])
except subprocess.TimeoutExpired:
 process.kill();process.wait(timeout=5);raise
counts=None
try:
 if p['runner'] is None:raise ValueError('No configured verifier')
 with report.open('rb') as stream:data=stream.read(4097)
 if len(data)<=4096:
  observed=json.loads(data)
  if observed.get('schema')==1 and observed.get('run_id')==ident:counts=observed.get('counts')
except (OSError,ValueError,TypeError,AttributeError):pass
with (run/'outcome.json').open('x',encoding='utf-8') as stream:json.dump({'schema':1,'run_id':ident,'exit_code':code,'counts':counts},stream)
raise SystemExit(code)
'''

FETCH = r'''
import base64,json,sys
from pathlib import Path
p=json.loads(base64.b64decode(sys.argv[1]));root=Path(p['root'])
if not root.resolve().is_relative_to(Path.home()):raise ValueError('Scope')
ident=p['run_id']
if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Identity')
with (root/ident/'outcome.json').open('rb') as stream:raw=stream.read(4097)
if len(raw)>4096:raise ValueError('Budget')
sys.stdout.buffer.write(raw)
'''
