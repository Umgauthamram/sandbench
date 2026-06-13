import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getCurrentUser, deleteUserAndData, destroySession, clearSessionCookie } from "../../../lib/auth";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const cookieStore = await cookies();
    const token = cookieStore.get("sb_session")?.value;

    // Cascade delete all user information
    await deleteUserAndData(user.id);

    // Destroy the current session key and cookie
    if (token) {
      await destroySession(token);
    }
    await clearSessionCookie();

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Delete user account error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
