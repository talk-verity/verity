import test from 'node:test';
import assert from 'node:assert/strict';
import { isValidReferralCode, parseReferralCookie, REFERRAL_COOKIE } from '../lib/referral.ts';

test('referral codes are bounded and safe', () => {
  assert.equal(isValidReferralCode('ACME_2026'), true);
  assert.equal(isValidReferralCode(''), false);
  assert.equal(isValidReferralCode('a'.repeat(65)), false);
  assert.equal(isValidReferralCode('bad;code'), false);
  assert.equal(isValidReferralCode(null), false);
});

test('referral cookie is parsed and invalid values are ignored', () => {
  assert.equal(parseReferralCookie(`other=1; ${REFERRAL_COOKIE}=ACME_2026; theme=dark`), 'ACME_2026');
  assert.equal(parseReferralCookie(`${REFERRAL_COOKIE}=bad%3Bcode`), null);
  assert.equal(parseReferralCookie(`${REFERRAL_COOKIE}=%E0%A4%A`), null);
  assert.equal(parseReferralCookie('theme=dark'), null);
});
