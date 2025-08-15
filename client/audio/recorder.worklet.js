// recorder.worklet.js
// AudioWorklet: 入力Float32(実サンプリング) → 16kHz/mono に線形補間でリサンプル
// frameSamples ごとに PCM16 (ArrayBuffer) を port.postMessage で送る

class RecorderProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const p = options.processorOptions || {};
    this.targetRate   = p.targetRate   || 16000;
    this.frameSamples = p.frameSamples || Math.round(this.targetRate * 0.05); // 50ms
    this.ratio  = sampleRate / this.targetRate; // AudioContextの実レート→目標レート
    this.cursor = 0;                            // 浮動小数の読み位置
    this.src    = new Float32Array(0);          // 入力の残り
    this.pcm    = new Int16Array(0);            // 出力PCMの残り
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const ch = input[0]; // mono

    // 前回残り + 今回を連結
    const src = new Float32Array(this.src.length + ch.length);
    src.set(this.src, 0);
    src.set(ch, this.src.length);

    // 線形補間で targetRate にリサンプル
    const outCount = Math.floor((src.length - 1 - this.cursor) / this.ratio);
    if (outCount > 0) {
      const out = new Float32Array(outCount);
      let cur = this.cursor;
      for (let i = 0; i < outCount; i++) {
        const idx = Math.floor(cur);
        const frac = cur - idx;
        const s0 = src[idx], s1 = src[idx + 1];
        out[i] = s0 + (s1 - s0) * frac;
        cur += this.ratio;
      }
      // 消費分を除去
      const consumed = Math.floor(cur);
      this.src = src.slice(consumed);
      this.cursor = cur - consumed;

      // Float32 → Int16
      const pcmChunk = new Int16Array(out.length);
      for (let i = 0; i < out.length; i++) {
        let s = out[i];
        if (s > 1) s = 1; else if (s < -1) s = -1;
        pcmChunk[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }

      // 既存と結合
      const merged = new Int16Array(this.pcm.length + pcmChunk.length);
      merged.set(this.pcm, 0);
      merged.set(pcmChunk, this.pcm.length);
      this.pcm = merged;

      // frameSamples ごとに送り出し（transferable でゼロコピー）
      while (this.pcm.length >= this.frameSamples) {
        const frame = this.pcm.subarray(0, this.frameSamples);
        const buf = new ArrayBuffer(this.frameSamples * 2);
        new Int16Array(buf).set(frame);
        this.port.postMessage(buf, [buf]);
        this.pcm = this.pcm.slice(this.frameSamples);
      }
    } else {
      this.src = src;
    }

    return true; // 継続
  }
}

registerProcessor('recorder-processor', RecorderProcessor);
