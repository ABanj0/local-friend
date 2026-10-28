import assert from 'node:assert/strict';
import test from 'node:test';
import { Recovery } from '../src/recovery.ts';

test('automatic retries back off and stop until an explicit manual reset', () => {
  const recovery = new Recovery();
  assert.deepEqual([recovery.nextDelay(), recovery.nextDelay(), recovery.nextDelay()], [1000, 2000, 4000]);
  for (let i = 0; i < 100; i++) assert.equal(recovery.nextDelay(), null);
  recovery.reset();
  assert.equal(recovery.nextDelay(), 1000);
});
