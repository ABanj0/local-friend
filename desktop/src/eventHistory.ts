import type { Event } from './api';

export type EventPacket = { delivery: number; kind: 'snapshot'|'replay'|'live'|'ready'; payload: {
  events?: Event[]; after?: number; cursor: number; through?: number; epoch: string;
  store_id?: string; reset?: boolean; live_seq?: number;
  tasks?: import('./api').Task[]; approvals?: import('./api').Approval[]; streams?: Record<string,string>;
} };
const MAX_EVENTS = 10000;
const MAX_BYTES = 16 * 1024 ** 2;
const integer = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0;

/** Durable cursors survive reconnects; transient sequence numbers belong to one backend. */
export class EventHistory {
  cursor = 0;
  storeId: string | undefined;
  epoch = '';
  events: Event[] = [];
  private liveCursor = 0;
  private delivery = 0;
  private sizes: number[] = [];
  private bytes = 0;

  beginConnection() { this.delivery = 0; }
  clear() { this.events = []; this.sizes = []; this.bytes = 0; }

  accept(packet: EventPacket): Event[] | null {
    if (!integer(packet.delivery) || !packet.delivery) throw new Error('Invalid activity delivery');
    if (packet.delivery <= this.delivery) return null;
    if (packet.delivery !== this.delivery + 1) throw new Error('Activity delivery gap; reconnecting');
    const p = packet.payload;
    if (!p || !integer(p.cursor) || typeof p.epoch !== 'string') throw new Error('Invalid activity cursor');
    if (!['snapshot', 'replay', 'live', 'ready'].includes(packet.kind)) throw new Error('Invalid activity packet');
    const snapshot = packet.kind === 'snapshot';
    if (snapshot && (typeof p.store_id !== 'string' || !integer(p.live_seq))) throw new Error('Invalid activity snapshot');
    const reset = snapshot && (p.reset || (this.storeId !== undefined && p.store_id !== this.storeId));
    const start = reset ? 0 : this.cursor;
    if (packet.kind !== 'ready' && (!integer(p.after) || p.after > start || !Array.isArray(p.events))) {
      throw new Error('Activity replay gap; reconnecting');
    }
    if (p.cursor < start || (!snapshot && p.epoch !== this.epoch)) throw new Error('Stale activity packet');
    if (packet.kind !== 'live' && packet.kind !== 'ready' && (!integer(p.through) || p.cursor > p.through)) {
      throw new Error('Invalid activity boundary');
    }
    let previous = p.after ?? start;
    for (const event of p.events ?? []) {
      const seq = event.seq ?? 0;
      if (!integer(seq) || typeof event.kind !== 'string' || !event.payload ||
          (seq && (seq <= previous || seq > p.cursor))) throw new Error('Invalid activity event');
      if (seq) previous = seq;
      if (packet.kind === 'live' && (!integer(event.live_seq) || !event.live_seq)) throw new Error('Invalid live activity');
    }
    // Validate the complete packet before advancing any accepted cursor.
    if (reset) { this.clear(); this.cursor = 0; this.liveCursor = 0; }
    if (snapshot) {
      this.storeId = p.store_id;
      this.epoch = p.epoch;
      this.liveCursor = p.live_seq!;
    }
    const accepted: Event[] = [];
    for (const event of p.events ?? []) {
      const seq = event.seq ?? 0;
      const duplicate = seq ? seq <= this.cursor : (event.live_seq ?? 0) <= this.liveCursor;
      if (packet.kind === 'live') this.liveCursor = Math.max(this.liveCursor, event.live_seq!);
      if (duplicate) continue;
      if (seq) this.cursor = seq;
      accepted.push(event);
      if (event.kind === 'token') continue;
      const retained = ['preview','approval'].includes(event.kind) ? {...event, payload:{transient:true}} : event;
      const size = new TextEncoder().encode(JSON.stringify(retained)).length;
      this.events.push(retained); this.sizes.push(size); this.bytes += size;
      while (this.events.length > MAX_EVENTS || this.bytes > MAX_BYTES) {
        this.events.shift(); this.bytes -= this.sizes.shift()!;
      }
    }
    this.cursor = p.cursor;
    this.delivery = packet.delivery;
    return accepted;
  }
}
