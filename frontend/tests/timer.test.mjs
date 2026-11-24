import test from 'node:test';
import assert from 'node:assert/strict';

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function calcRemaining(startMs, nowMs, limitSeconds = 300) {
  const elapsed = Math.floor((nowMs - startMs) / 1000);
  return Math.max(0, limitSeconds - elapsed);
}

test('formatTime renders MM:SS properly across critical boundary values', () => {
  assert.equal(formatTime(300), '5:00');
  assert.equal(formatTime(299), '4:59');
  assert.equal(formatTime(125), '2:05');
  assert.equal(formatTime(60), '1:00');
  assert.equal(formatTime(59), '0:59');
  assert.equal(formatTime(9), '0:09');
  assert.equal(formatTime(0), '0:00');
});

test('calcRemaining computes remaining seconds from created_at timestamp', () => {
  const start = 1700000000000;
  assert.equal(calcRemaining(start, start), 300);
  assert.equal(calcRemaining(start, start + 60000), 240);
  assert.equal(calcRemaining(start, start + 240000), 60);
  assert.equal(calcRemaining(start, start + 300000), 0);
  assert.equal(calcRemaining(start, start + 350000), 0);
});
