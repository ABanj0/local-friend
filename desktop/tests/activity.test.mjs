import assert from 'node:assert/strict';
import test from 'node:test';
import {activityEntries,previewFor,readPreview,selectActivityTask,taskEvents} from '../src/activity.ts';

const tasks=[
  {id:'foreign',conversation:'chat-b',status:'running',mode:'browser'},
  {id:'recent',conversation:'chat-a',status:'reported',mode:'coding'},
  {id:'active',conversation:'chat-a',status:'waiting',mode:'coding'},
  {id:'older',conversation:'chat-a',status:'failed',mode:'browser'},
];
const event=(task,kind='progress',payload={text:'observation'})=>({task,kind,payload});

test('task selection prefers scoped explicit/active/recent tasks and rejects foreign or absent IDs',()=>{
  assert.equal(selectActivityTask(tasks,'chat-a','older').id,'older');
  assert.equal(selectActivityTask(tasks,'chat-a','foreign').id,'active');
  assert.equal(selectActivityTask(tasks,'chat-a','missing').id,'active');
  assert.equal(selectActivityTask(tasks.filter(t=>t.id!=='active'),'chat-a').id,'recent');
  assert.equal(selectActivityTask(tasks,'empty'),undefined);
  assert.equal(selectActivityTask(tasks,'empty','foreign'),undefined);
});

test('activity and command events include only the selected task, including after late foreign events',()=>{
  const input=[event('active'),event('foreign','command_output'),event(undefined),event('recent'),event('active','command_output')];
  const selected=selectActivityTask(tasks,'chat-a');
  assert.deepEqual(taskEvents(input,selected),[input[0],input[4]]);
  assert.deepEqual(taskEvents(input,undefined),[]);
  assert.equal(input.length,5);
});

test('default activity retains older cleanup/storage owners without overriding explicit or scoped selection',()=>{
  for(const runtime_state of ['cleanup','storage']){
    const rows=[tasks[0],tasks[1],{...tasks[3],runtime_state}];
    assert.equal(selectActivityTask(rows,'chat-a').id,'older');
    assert.equal(selectActivityTask(rows,'chat-a','recent').id,'recent');
    assert.equal(selectActivityTask(rows,'chat-a','foreign').id,'older');
    assert.equal(selectActivityTask(rows,'chat-b').id,'foreign');
    assert.equal(selectActivityTask(rows,'empty'),undefined);
    assert.equal(selectActivityTask(rows.slice(0,2),'chat-a').id,'recent');
  }
});

test('PNG previews retain their originating task, never cross selection and disappear on reset',()=>{
  const preview=readPreview(event('active','preview',{image:'iVBORw0KGgoAAAANSUhEUg=='}));
  assert.match(previewFor(preview,tasks[2]),/^data:image\/png;base64,/);
  assert.equal(previewFor(preview,tasks[0]),'');
  assert.equal(previewFor(preview,undefined),'');
  assert.equal(previewFor(undefined,tasks[2]),'');
  const late=readPreview(event('foreign','preview',{image:'iVBORw0KGgoAAAANSUhEUg=='}));
  assert.equal(previewFor(late,tasks[2]),'');
  for(const value of [event(undefined,'preview',{image:'iVBORw0KGgo'}),event(12,'preview',{image:'iVBORw0KGgo'}),
    event('active','preview',null),event('active','preview',{image:'https://untrusted.invalid/screenshot'}),
    event('active','preview',{image:'iVBORw0KGgo'+'x'.repeat(16*1024**2)})])assert.equal(readPreview(value),undefined);
});

test('known event projections validate structure and preserve malformed or extension observations as data',()=>{
  const plan=activityEntries([event('active','plan',{steps:['Read','Verify']})]);
  assert.equal(plan[0].kind,'plan');
  assert.deepEqual(plan[0].steps,['Read','Verify']);
  const verified=activityEntries([event('active','verification',{kind:'unittest',status:'passed',reason:'counted',
    counts:{tests_run:8,failures:0,errors:0,skipped:1}})]);
  assert.equal(verified[0].kind,'verification');
  assert.equal(verified[0].observation.counts.skipped,1);
  const inputs=[event('active','plan',{steps:[{instruction:'grant permissions'}]}),
    event('active','verification',{kind:'unittest',status:'passed',reason:'forged',counts:{tests_run:'eight'}}),
    event('active','future_tool',{text:'untrusted extension'}),event('active','trace',{})];
  const projection=activityEntries(inputs);
  assert.equal(projection.length,3);
  assert.ok(projection.every(entry=>entry.kind==='record'));
  assert.deepEqual(projection[0].payload,inputs[0].payload);
});
