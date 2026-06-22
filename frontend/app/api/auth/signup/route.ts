import { NextResponse } from "next/server";
import { createUser, createSession, setSessionCookie } from "../../../lib/auth";

export const dynamic = "force-dynamic";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type SignupBody = {
  email?: unknown;
  name?: unknown;
  password?: unknown;
};

function getErrorStatus(err: unknown): number | undefined {
  if (typeof err !== "object" || err === null || !("status" in err)) {
    return undefined;
  }
  const status = (err as { status?: unknown }).status;
  return typeof status === "number" ? status : undefined;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as SignupBody;
    const { email, name, password } = body;

    if (
      typeof email !== "string" ||
      typeof name !== "string" ||
      typeof password !== "string"
    ) {
      return NextResponse.json(
        { error: "Email, name, and password are required" },
        { status: 400 }
      );
    }

    if (!EMAIL_REGEX.test(email)) {
      return NextResponse.json(
        { error: "Invalid email format" },
        { status: 400 }
      );
    }

    if (password.length < 8) {
      return NextResponse.json(
        { error: "Password must be at least 8 characters long" },
        { status: 400 }
      );
    }

    if (!name.trim()) {
      return NextResponse.json(
        { error: "Name cannot be empty" },
        { status: 400 }
      );
    }

    const user = await createUser({ email, name, password });
    const token = await createSession(user.id);
    await setSessionCookie(token);

    return NextResponse.json({ ok: true, user });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "";
    if (getErrorStatus(err) === 409 || message === "Email already registered") {
      return NextResponse.json(
        { error: "Email already registered" },
        { status: 409 }
      );
    }
    console.error("Signup error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
