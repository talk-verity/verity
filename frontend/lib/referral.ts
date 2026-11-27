export const REFERRAL_COOKIE = "delphi_ref";

const CODE_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export function isValidReferralCode(value: string | null | undefined): value is string {
  return typeof value === "string" && CODE_PATTERN.test(value);
}

export function parseReferralCookie(cookieHeader: string): string | null {
  for (const part of cookieHeader.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === REFERRAL_COOKIE) {
      try {
        const value = decodeURIComponent(rest.join("="));
        return isValidReferralCode(value) ? value : null;
      } catch {
        return null;
      }
    }
  }
  return null;
}

export function getReferralCode(): string | null {
  return typeof document === "undefined" ? null : parseReferralCookie(document.cookie);
}
