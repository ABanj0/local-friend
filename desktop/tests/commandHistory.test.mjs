import assert from 'node:assert/strict';
import test from 'node:test';
import { commandGroups } from '../src/commandHistory.ts';
import { EventHistory } from '../src/eventHistory.ts';

const tasks=[{id:'task',conversation:'chat',status:'running'}];
const event=(part,text,extra={})=>({seq:part,task:'task',kind:'command_output',payload:{
  command_id:'a'.repeat(32),part,text,profile:'test',finished:false,truncated:false,reason:'running',exit_code:null,...extra}});

test('command deltas replay once and finish without inventing test verification',()=>{
  const history=new EventHistory();
  const events=[event(1,''),event(2,'first\n'),event(3,'last\n',{finished:true,reason:'completed',exit_code:0})];
  const packet={delivery:1,kind:'snapshot',payload:{events,after:0,cursor:3,through:3,epoch:'epoch',store_id:'store',live_seq:0}};
  history.accept(packet);history.beginConnection();history.accept(packet);
  const [group]=commandGroups(history.events,tasks);
  assert.equal(group.text,'first\nlast\n');assert.equal(group.finished,true);
  assert.equal(group.exit_code,0);assert.equal(group.partial,false);
  assert.ok(!('verification' in group));
});

test('scope, duplicate parts and retained-history gaps are explicit',()=>{
  const rows=[event(2,'kept'),event(2,'duplicate'),event(4,'end')];
  const [group]=commandGroups(rows,tasks);
  assert.equal(group.text,'keptend');assert.equal(group.partial,true);
  assert.equal(commandGroups(rows,[{id:'other'}]).length,0);
});

test('only three recent commands survive and large output is bounded',()=>{
  const rows=Array.from({length:5},(_,index)=>event(1,'x'.repeat(20000),{command_id:String(index).repeat(32)}));
  const groups=commandGroups(rows,tasks);
  assert.equal(groups.length,3);
  assert.ok(groups.every(group=>group.text.length<=16000&&group.partial));
  assert.equal(groups[0].id,'2'.repeat(32));
  const [unicode]=commandGroups([event(1,'\u2603'.repeat(10000))],tasks);
  assert.ok(new TextEncoder().encode(unicode.text).length<=16000);
});

test('background readiness is folded and active owned servers stay visible beside recent commands',()=>{
  const status={seq:2,task:'task',kind:'background_status',payload:{command_id:'a'.repeat(32),profile:'serve',
    state:'running',readiness:{status:'ready',last_ready_at:123,last_check:'ready'}}};
  const rows=[event(1,'server log'),status,...Array.from({length:4},(_,i)=>event(1,'later',{command_id:String(i).repeat(32)}))];
  const groups=commandGroups(rows,tasks);
  assert.equal(groups.length,4);
  assert.equal(groups[0].background.readiness.status,'ready');
  assert.equal(groups[0].background.readiness.last_ready_at,123);
  const stopped={...status,payload:{...status.payload,state:'stopped',readiness:{status:'stopped',last_ready_at:123}}};
  assert.equal(commandGroups([...rows,stopped],tasks).length,3);
});
