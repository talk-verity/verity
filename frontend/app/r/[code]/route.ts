import { NextResponse } from "next/server";
import { isValidReferralCode, REFERRAL_COOKIE } from "@/lib/referral";

export async function GET(_request: Request, { params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const response = new NextResponse(null, {
    status: 307,
    headers: { Location: "/sign-up" },
  });
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
