import assert from 'node:assert/strict';
import test from 'node:test';
import { EventHistory } from '../src/eventHistory.ts';

const event = (seq, kind='progress', payload={text:`event-${seq}`}, live_seq=seq) => ({seq, kind, payload, live_seq, task:'task'});
const snapshot = (events=[], extra={}) => ({delivery:1, kind:'snapshot', payload:{
  events, after:0, cursor:events.at(-1)?.seq ?? 0, through:events.at(-1)?.seq ?? 0,
  store_id:'store', epoch:'epoch', live_seq:0, tasks:[], approvals:[], streams:{}, ...extra,
}});
const page = (delivery, events, after, cursor=events.at(-1)?.seq ?? after, kind='replay') => ({delivery, kind,
  payload:{events, after, cursor, through:cursor, epoch:'epoch'}});

test('5001 durable events occur once across overlapping replay, reconnect and backend restart', () => {
  const history = new EventHistory();
  history.accept(snapshot(Array.from({length:200}, (_,i)=>event(i+1))));
  history.beginConnection();
  history.accept(snapshot(Array.from({length:200}, (_,i)=>event(i+1)), {after:0}));
  let delivery = 2;
  for (let after=200; after<5001; after+=200) {
    const events=Array.from({length:Math.min(200,5001-after)}, (_,i)=>event(after+i+1));
    const packet=page(delivery++, events, after);
    history.accept(packet);
    assert.equal(history.accept(packet), null);
  }
  assert.deepEqual(history.events.map(e=>e.seq), Array.from({length:5001}, (_,i)=>i+1));
  history.beginConnection();
  history.accept(snapshot([], {after:5001, cursor:5001, through:5001, epoch:'restarted'}));
  assert.equal(history.events.length, 5001);
  history.accept({...page(2,[event(5002)],5001),payload:{...page(2,[event(5002)],5001).payload,epoch:'restarted'}});
  assert.equal(history.events.length, 5002);
});

test('database replacement resets old identity and sequence while deletion holes advance safely', () => {
  const history=new EventHistory(); history.accept(snapshot([event(1),event(9)]));
  history.beginConnection();
  history.accept(snapshot([event(1)], {store_id:'replacement',reset:true}));
  assert.deepEqual(history.events.map(e=>e.seq),[1]);
  history.accept(page(2,[],1,99));
  assert.equal(history.cursor,99);
});

test('tokens stay out of history and sensitive bodies remain transient; duplicate live frames have no effects', () => {
  const history=new EventHistory(); history.accept(snapshot());
  const events=[event(0,'token',{text:'stream'},1),event(1,'approval',{id:'secret-approval'},2),
    event(2,'preview',{image:'private-image'},3)];
  assert.equal(history.accept(page(2,events,0,2,'live')).length,3);
  assert.deepEqual(history.events.map(e=>e.payload),[{transient:true},{transient:true}]);
  assert.deepEqual(history.accept(page(3,events,0,2,'live')),[]);
  assert.ok(!JSON.stringify(history.events).includes('private-image'));
  history.beginConnection();
  history.accept(snapshot([], {after:2,cursor:2,through:2,epoch:'restart'}));
  const packet=page(2,[event(0,'token',{text:'new stream'},1)],2,2,'live');
  packet.payload.epoch='restart';
  assert.equal(history.accept(packet).length,1);
});

test('invalid delivery, epoch, sequence and forward gaps leave the accepted cursor unchanged', () => {
  for (const change of [p=>p.delivery=3,p=>p.payload.after=20,p=>p.payload.cursor=-1,
    p=>p.payload.epoch='other',p=>p.payload.events=[event(8),event(7)],p=>p.payload.events=[event(99)]]) {
    const history=new EventHistory(); history.accept(snapshot([event(1)]));
    const packet=page(2,[event(2)],1); change(packet);
    assert.throws(()=>history.accept(packet));
    assert.equal(history.cursor,1); assert.equal(history.events.length,1);
  }
});

test('RAM gap snapshots replace transient watermark but do not duplicate durable history', () => {
  const history=new EventHistory(); history.accept(snapshot([event(1)]));
  history.accept({...snapshot([event(2)], {after:1,live_seq:5001}),delivery:2});
  assert.equal(history.accept(page(3,[event(0,'token',{text:'old'},5000)],2,2,'live')).length,0);
  assert.equal(history.accept(page(4,[event(0,'token',{text:'new'},5002)],2,2,'live')).length,1);
  assert.deepEqual(history.events.map(e=>e.seq),[1,2]);
});

test('retained count and byte limits do not rewind the durable cursor', () => {
  const history=new EventHistory(); history.accept(snapshot());
  history.accept(page(2,Array.from({length:10001},(_,i)=>event(i+1)),0));
  assert.equal(history.events.length,10000); assert.equal(history.events[0].seq,2);
  history.accept(page(3,[event(10002,'progress',{text:'x'.repeat(9*1024**2)})],10001));
  history.accept(page(4,[event(10003,'progress',{text:'x'.repeat(9*1024**2)})],10002));
  assert.equal(history.events.length,1); assert.equal(history.cursor,10003);
  history.clear(); assert.equal(history.events.length,0); assert.equal(history.cursor,10003);
});
