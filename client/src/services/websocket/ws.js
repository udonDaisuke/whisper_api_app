
class WebsocketService {

  constructor(options) {
    this.options = {
      pingIntervalMs: 30000,
      queueMaxFrames: 10,
      reconnectMaxAttempts: 10,
      reconnectBaseMs: 1000,
      reconnectMaxMs: 30000,
      ownsConnection: true,
      wsCtor: typeof WebSocket !== 'undefined' ? WebSocket : undefined,
      ...options,
    };

    if (!this.options.url) throw new Error('url is required');
    if (!this.options.wsCtor) throw new Error('No WebSocket constructor available');

    // 状態
    this.ws = null;
    this.state = 'IDLE'; // IDLE | CONNECTING | OPEN | CLOSING | CLOSED
    this.seq = 0;        // 送信フレームの連番
    this.sid = null;     // サーバーから受け取ったセッション ID

    // タイマー
    this.pingTimer = null;
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this._intentionalClose = false;

    this.queue = [];
    this.handlers = new Map(); // event -> Set<fn>
  }

  // ===== イベントシステム =====

  on(ev, handler) {
    if (!this.handlers.has(ev)) this.handlers.set(ev, new Set());
    this.handlers.get(ev).add(handler);
    return () => this.off(ev, handler);
  }

  off(ev, handler) {
    this.handlers.get(ev)?.delete(handler);
  }

  emit(ev, payload) {
    this.handlers.get(ev)?.forEach(fn => {
      try { fn(payload); } catch (e) { console.error(e); }
    });
  }

  // ===== 接続管理 =====

  connect() {
    if (this.state === 'CONNECTING' || this.state === 'OPEN') return;
    this._intentionalClose = false;
    this._openConnection();
  }

  disconnect() {
    this._intentionalClose = true;
    this._stopPing();
    this._clearReconnectTimer();
    this.queue = [];
    if (this.ws) {
      this.state = 'CLOSING';
      this.ws.close(1000, 'client disconnect');
      this.ws = null;
    } else {
      this.state = 'CLOSED';
    }
  }

  _openConnection() {
    this.state = 'CONNECTING';
    const ws = new this.options.wsCtor(this.options.url);
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      this.state = 'OPEN';
      this.reconnectAttempts = 0;
      this._startPing();
      this._flushQueue();
      this.emit('open', {});
    };

    ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        console.error('ws: failed to parse message', e);
        return;
      }
      if (msg.sid && !this.sid) this.sid = msg.sid;
      this.emit(msg.type, msg);
    };

    ws.onerror = (event) => {
      this.emit('error', event);
    };

    ws.onclose = (event) => {
      this._stopPing();
      const prevState = this.state;
      this.state = 'CLOSED';
      this.ws = null;
      this.emit('close', { code: event.code, reason: event.reason });
      if (!this._intentionalClose && prevState !== 'CLOSING') {
        this._scheduleReconnect();
      }
    };
  }

  // ===== 再接続（指数バックオフ） =====

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.options.reconnectMaxAttempts) {
      this.emit('reconnect_failed', { attempts: this.reconnectAttempts });
      return;
    }
    const delay = Math.min(
      this.options.reconnectBaseMs * Math.pow(2, this.reconnectAttempts),
      this.options.reconnectMaxMs,
    );
    this.reconnectAttempts++;
    this.emit('reconnecting', { attempt: this.reconnectAttempts, delayMs: delay });
    this.reconnectTimer = setTimeout(() => {
      this._openConnection();
    }, delay);
  }

  _clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ===== ping keepalive =====

  _startPing() {
    this._stopPing();
    this.pingTimer = setInterval(() => {
      if (this.state === 'OPEN') {
        this._sendFrame({ type: 'ping' });
      }
    }, this.options.pingIntervalMs);
  }

  _stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  // ===== 送信 =====

  /**
   * メッセージを送信する。未接続の場合はキューに積む。
   * @param {string} type - メッセージタイプ (start / control 等)
   * @param {object} payload - エンベロープ以外の追加フィールド
   */
  send(type, payload = {}) {
    const frame = { type, ...payload };
    if (this.state === 'OPEN') {
      this._sendFrame(frame);
    } else {
      this._enqueue(frame);
    }
  }

  _sendFrame(frame) {
    if (!this.ws || this.state !== 'OPEN') {
      this._enqueue(frame);
      return;
    }
    const envelope = {
      v: 1,
      type: frame.type,
      seq: ++this.seq,
      ts: Date.now() / 1000,
      sid: this.sid,
      ...frame,
    };
    try {
      this.ws.send(JSON.stringify(envelope));
    } catch (e) {
      console.error('ws: send failed', e);
      this._enqueue(frame);
    }
  }

  // ===== 送信キュー =====

  _enqueue(frame) {
    if (this.queue.length >= this.options.queueMaxFrames) {
      this.queue.shift(); // 上限超過時は最古フレームを破棄
    }
    this.queue.push(frame);
  }

  _flushQueue() {
    while (this.queue.length > 0) {
      const frame = this.queue.shift();
      this._sendFrame(frame);
    }
  }
}
