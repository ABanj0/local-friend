import assert from 'node:assert/strict';
import test from 'node:test';
import {approvalList,approvalPayload,backgroundObservation,commandDelta,record} from '../src/eventPayloads.ts';

test('approval contracts keep envelope ownership, validate details/expiry and reject transient replay',()=>{
  const payload={id:'request',action:'execute_code',details:{argv:['python','-m','unittest']},expires:12345,task:'forged'};
  const valid=approvalPayload({kind:'approval',task:'owned-task',payload});
  assert.equal(valid.task,'owned-task');
  assert.deepEqual(valid.details,payload.details);
  for(const p of [null,[],{...payload,transient:true},{...payload,expires:Infinity},
    {...payload,expires:'tomorrow'},{...payload,details:['arbitrary']},{...payload,id:undefined}]){
    assert.equal(approvalPayload({kind:'approval',task:'owned-task',payload:p}),undefined);
  }
  assert.equal(approvalPayload({kind:'approval',payload}),undefined);
  assert.deepEqual(approvalList([valid,null,{...valid,details:[]}]),[valid]);
  assert.deepEqual(approvalList({}),[]);
});

test('command delta contracts reject malformed counters and keep exit observations distinct from tests',()=>{
  const valid={command_id:'a'.repeat(32),profile:'test',part:1,text:'output',truncated:false,finished:true,reason:'completed',exit_code:0};
  assert.deepEqual(commandDelta(valid),valid);
  assert.ok(!('verification' in commandDelta(valid)));
  for(const p of [null,[],{...valid,part:'1'},{...valid,part:0},{...valid,part:65},
    {...valid,exit_code:'0'},{...valid,finished:'true'},{...valid,text:{}},{...valid,command_id:'other'}])
    assert.equal(commandDelta(p),undefined);
});

test('background contracts accept missing optional observations and reject invalid readiness dates',()=>{
  const valid={command_id:'a'.repeat(32),profile:'serve',state:'running',readiness:{status:'unconfigured'}};
  assert.deepEqual(backgroundObservation(valid).readiness,{status:'unconfigured',last_ready_at:null,last_check:null});
  assert.equal(backgroundObservation({...valid,readiness:{status:'ready',last_ready_at:Infinity}}),undefined);
  assert.equal(backgroundObservation({...valid,readiness:{status:'ready',last_ready_at:-1}}),undefined);
  assert.equal(backgroundObservation({...valid,readiness:{status:{}}}),undefined);
  assert.equal(record([]),undefined);
});
