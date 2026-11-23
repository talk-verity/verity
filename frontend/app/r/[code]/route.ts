import { NextResponse } from "next/server";
import { isValidReferralCode, REFERRAL_COOKIE } from "@/lib/referral";

export async function GET(request: Request, { params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const response = NextResponse.redirect(new URL("/sign-up", request.url));
  if (isValidReferralCode(code)) {
    response.cookies.set(REFERRAL_COOKIE, code, {
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }
  return response;
}
