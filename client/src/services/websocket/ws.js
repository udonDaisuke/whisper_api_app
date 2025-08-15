

class WebsocketService{

  constructor(options){
    this.options = {
      pingIntervalMs: 15000,
      queueMaxFrames: 10,
      ownsConnection: true,
      wsCtor: typeof WebSocket !== 'undefined' ? WebSocket : undefined,
      ...options,      
    }

    if (!this.opts.url) throw new Error('url is required');
    if (!this.opts.wsCtor) throw new Error('No WebSocket constructor available');

        // 状態
    this.ws = null;
    this.state = 'IDLE'; // IDLE | CONNECTING | OPEN | CLOSED
    this.seq = 0;        // 送信フレームの連番
    this.pingTimer = null;
    this.readyResolver = null; // startSession() の完了を resolve するコールバック

    this.queue = [];
    this.handlers = new Map(); // event -> Set<fn>
  }
  // ===== イベントシステム（最小） =====
  on(ev, handler) {
    if (!this.handlers.has(ev)) this.handlers.set(ev, new Set());
      this.handlers.get(ev).add(handler);
      return () => this.off(ev, handler);
  };
  off(ev, handler) {
    this.handlers.get(ev)?.delete(handler);
  }
  emit(ev, payload) {
    this.handlers.get(ev)?.forEach(fn => {
      try { fn(payload); } catch (e) { console.error(e); }
    });
  }
    
}