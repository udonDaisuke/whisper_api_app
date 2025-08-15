// Recorder.js
export class Recorder {
  constructor({ sampleRate = 16000, frameMs = 50, workletUrl = '/recorder.worklet.js' } = {}) {
    this.targetRate = sampleRate;
    this.frameSamples = Math.round(sampleRate * frameMs / 1000);
    this.workletUrl = workletUrl;

    this.ctx = null;
    this.stream = null;
    this.source = null;
    this.node = null;
    this.gain = null; // ミュート用
    this._onFrame = () => {};
  }

  static isSupported() {
    return !!(window.AudioWorkletNode && window.isSecureContext);
  }

  onFrame(fn) { this._onFrame = fn || (() => {}); }

  async start() {
    // マイク取得
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // AudioContext を作成（レートは実機依存。Worklet内でリサンプルするのでOK）
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();

    // Worklet モジュールをロード（同一オリジンで配信されている必要あり）
    await this.ctx.audioWorklet.addModule(this.workletUrl);

    // Worklet ノードを作成
    this.node = new AudioWorkletNode(this.ctx, 'recorder-processor', {
      processorOptions: { targetRate: this.targetRate, frameSamples: this.frameSamples },
    });

    // フレーム受領
    this.node.port.onmessage = (e) => {
      const buf = e.data; // ArrayBuffer (PCM16)
      this._onFrame(buf);
    };

    // 音声グラフ
    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.gain = this.ctx.createGain();
    this.gain.gain.value = 0; // ミュート（音は出さない）

    this.source.connect(this.node).connect(this.gain).connect(this.ctx.destination);
  }

  async stop() {
    try {
      this.node?.disconnect();
      this.gain?.disconnect();
      this.source?.disconnect();
      await this.ctx?.close?.();
      this.stream?.getTracks().forEach(t => t.stop());
    } finally {
      this.ctx = this.stream = this.source = this.node = this.gain = null;
    }
  }
}
