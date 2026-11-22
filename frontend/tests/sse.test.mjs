import test from 'node:test';
import assert from 'node:assert/strict';
import { SSEParser } from '../lib/sse.ts';
const wire = 'event: transcription\ndata: {"data":"hello"}\n\nevent: audio\ndata: abc\n\nevent: done\ndata: {}\n\n';
const expected = [{event:'transcription',data:'{"data":"hello"}'},{event:'audio',data:'abc'},{event:'done',data:'{}'}];
test('every possible network split preserves all events', () => {
 for(let i=0;i<=wire.length;i++) {
   const parser=new SSEParser();
   assert.deepEqual([...parser.push(wire.slice(0,i)),...parser.push(wire.slice(i))],expected);
 }
});
test('single-byte chunks, CRLF and multiline data', () => {
 const parser=new SSEParser();
 const events=[...': comment\r\nevent: message\r\ndata: first\r\ndata: second\r\n\r\n'].flatMap(c=>parser.push(c));
 assert.deepEqual(events,[{event:'message',data:'first\nsecond'}]);
});
test('incomplete frames are not dispatched', () => {
 const parser=new SSEParser();
 assert.deepEqual(parser.push('event: audio\ndata: abc'),[]);
 assert.deepEqual(parser.push('\n\n'),[{event:'audio',data:'abc'}]);
});
