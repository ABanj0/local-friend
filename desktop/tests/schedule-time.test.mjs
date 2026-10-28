import test from 'node:test';
import assert from 'node:assert/strict';
import {scheduleTime} from '../src/schedule-time.mjs';

test('Toronto spring transition changes offset without a repeated elapsed interval',()=>{
  const first=Date.parse('2026-03-08T06:30:00Z'),second=first+3600000;
  assert.match(scheduleTime(first,'America/Toronto'),/1:30:00.*(?:EST|GMT-5)/);
  assert.match(scheduleTime(second,'America/Toronto'),/3:30:00.*(?:EDT|GMT-4)/);
});
test('Toronto repeated autumn hour is distinguished by its UTC offset',()=>{
  assert.match(scheduleTime(Date.parse('2026-11-01T05:30:00Z'),'America/Toronto'),/1:30:00.*(?:EDT|GMT-4)/);
  assert.match(scheduleTime(Date.parse('2026-11-01T06:30:00Z'),'America/Toronto'),/1:30:00.*(?:EST|GMT-5)/);
});
test('UTC display is explicit and unavailable browser zones fall back visibly',()=>{
  assert.match(scheduleTime(Date.parse('2026-11-01T06:30:00Z'),'UTC'),/6:30:00.*UTC/);
  assert.match(scheduleTime(0,'Unknown/Timezone'),/UTC; display timezone unavailable/);
});
test('malformed saved timestamps render a fixed notice without throwing',()=>{
  for(const value of [NaN,Infinity,2**63,null,true,'PRIVATE-TIMESTAMP-CANARY']){
    assert.equal(scheduleTime(value,'UTC'),'Invalid saved slot; review this schedule');
  }
});
