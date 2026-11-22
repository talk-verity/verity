import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

// Execute the real hook with deterministic browser/hook lifecycle adapters.
function mount({ deferred = false } = {}) {
  const effects = [], cleanups = [], calls = [];
  let resolveMedia;
  const track = { stopped: false, stop() { this.stopped = true; } };
  const media = { getTracks: () => [track] };
  class Recorder {
    static last;
    static isTypeSupported() { return true; }
    constructor() { Recorder.last = this; this.state = 'inactive'; this.mimeType = 'audio/webm'; }
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.onstop?.(); }
  }
  class AudioContext {
    constructor() { this.state = 'running'; }
    async resume() {}
    async close() { this.state = 'closed'; }
  }
  const react = { useRef: value => ({current:value}), useState: value => [value, () => {}], useEffect: fn => effects.push(fn) };
  const source = fs.readFileSync(new URL('../hooks/useVoiceRecorder.ts', import.meta.url), 'utf8');
  const code = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const hookModule = { exports: {} };
  const timers = [];
  const execute = new Function('require','exports','navigator','MediaRecorder','AudioContext','setTimeout','clearTimeout', code);
  execute(() => react, hookModule.exports, {mediaDevices:{getUserMedia: () => deferred ? new Promise(resolve => { resolveMedia=resolve; }) : Promise.resolve(media)}}, Recorder, AudioContext, fn => {timers.push(fn);return timers.length;}, () => {});
  const hook = hookModule.exports.useVoiceRecorder(blob => calls.push(blob), error => {throw new Error(error);});
  for (const effect of effects) { const cleanup=effect(); if(cleanup) cleanups.push(cleanup); }
  return { hook, track, Recorder, calls, timers, unmount: () => cleanups.forEach(fn=>fn()), grant: () => resolveMedia(media) };
}
test('unmount releases microphone and does not submit recording', async () => {
  const h=mount(); await h.hook.start(); h.unmount();
  assert.equal(h.track.stopped,true);
  assert.equal(h.Recorder.last.state,'inactive');
  assert.equal(h.calls.length,0);
});
test('late microphone permission after navigation releases acquired tracks', async () => {
  const h=mount({deferred:true}); const pending=h.hook.start();
  await Promise.resolve(); h.unmount(); h.grant(); await pending;
  assert.equal(h.track.stopped,true);
  assert.equal(h.calls.length,0);
});
test('recording limit stops microphone and submits exactly once', async () => {
  const h=mount(); await h.hook.start();
  h.Recorder.last.ondataavailable({data:new Blob(['audio'])});
  h.timers[0]();
  assert.equal(h.track.stopped,true); assert.equal(h.calls.length,1);
  h.unmount(); assert.equal(h.calls.length,1);
});
test('duplicate start while permission pending makes one recording', async () => {
  const h=mount({deferred:true}); const first=h.hook.start();
  await Promise.resolve(); await h.hook.start(); h.grant(); await first;
  h.hook.stop(); assert.equal(h.calls.length,1); h.unmount();
});
