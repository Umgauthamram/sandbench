import bcrypt from "bcryptjs";
import crypto from "crypto";
import { cookies } from "next/headers";
import { redis, redisConfigured } from "./redis";
import type { User, SafeUser } from "./types";

// ── In-memory fallback (resets on server restart) ──
const memUsers = new Map<string, User>();
const memEmails = new Map<string, string>(); // normalizedEmail -> userId
const memSessions = new Map<string, { userId: string; createdAt: string }>();
const memUserSessions = new Map<string, Set<string>>(); // userId -> Set<token>

class AuthError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "AuthError";
  }
}

type LeaderboardRecord = {
  rank?: number;
  user?: string;
  userId?: string;
};

function toSafeUser(user: User): SafeUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    createdAt: user.createdAt,
  };
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDynamicServerUsageError(err: unknown): boolean {
  return isObjectRecord(err) && err.digest === "DYNAMIC_SERVER_USAGE";
}

function hasRunUserId(value: unknown, userId: string): boolean {
  return isObjectRecord(value) && value.userId === userId;
}

function toLeaderboardRecord(value: unknown): LeaderboardRecord | null {
  if (!isObjectRecord(value)) return null;
  return {
    rank: typeof value.rank === "number" ? value.rank : undefined,
    user: typeof value.user === "string" ? value.user : undefined,
    userId: typeof value.userId === "string" ? value.userId : undefined,
  };
}

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, 12);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}

export async function createUser({
  email,
  name,
  password,
}: {
  email: string;
  name: string;
  password: string;
}): Promise<SafeUser> {
  const normalizedEmail = email.trim().toLowerCase();

  if (!redisConfigured) {
    if (memEmails.has(normalizedEmail)) {
      throw new AuthError("Email already registered", 409);
    }
    const id = `usr_${crypto.randomUUID().replace(/-/g, "")}`;
    const passwordHash = await hashPassword(password);
    const user: User = {
      id,
      email: normalizedEmail,
      name: name.trim(),
      passwordHash,
      createdAt: new Date().toISOString(),
    };
    memUsers.set(id, user);
    memEmails.set(normalizedEmail, id);

    return toSafeUser(user);
  }

  // Redis path
  const existingId = await redis.get(`user:email:${normalizedEmail}`);
  if (existingId) {
    throw new AuthError("Email already registered", 409);
  }

  const id = `usr_${crypto.randomUUID().replace(/-/g, "")}`;
  const passwordHash = await hashPassword(password);
  
  const user: User = {
    id,
    email: normalizedEmail,
    name: name.trim(),
    passwordHash,
    createdAt: new Date().toISOString(),
  };

  await redis.set(`user:${id}`, JSON.stringify(user));
  await redis.set(`user:email:${normalizedEmail}`, id);
  await redis.lpush("users:index", id);

  return toSafeUser(user);
}

export async function getUserByEmail(email: string): Promise<User | null> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!redisConfigured) {
    const id = memEmails.get(normalizedEmail);
    if (!id) return null;
    return memUsers.get(id) ?? null;
  }
  const id = await redis.get(`user:email:${normalizedEmail}`);
  if (!id) return null;
  return getUserById(id);
}

export async function getUserById(id: string): Promise<User | null> {
  if (!redisConfigured) {
    return memUsers.get(id) ?? null;
  }
  const raw = await redis.get(`user:${id}`);
  if (!raw) return null;
  return JSON.parse(raw) as User;
}

export async function createSession(userId: string): Promise<string> {
  const token = crypto.randomUUID();
  const sessionData = {
    userId,
    createdAt: new Date().toISOString(),
  };

  if (!redisConfigured) {
    memSessions.set(token, sessionData);
    if (!memUserSessions.has(userId)) {
      memUserSessions.set(userId, new Set());
    }
    memUserSessions.get(userId)!.add(token);
    return token;
  }

  // Store session with 7 days TTL (604800 seconds)
  await redis.setex(`session:${token}`, 604800, JSON.stringify(sessionData));
  // Record this session for the user
  await redis.sadd(`user:${userId}:sessions`, token);
  return token;
}

export async function getSession(token: string): Promise<{ userId: string; createdAt: string } | null> {
  if (!redisConfigured) {
    return memSessions.get(token) ?? null;
  }
  const raw = await redis.get(`session:${token}`);
  if (!raw) return null;
  return JSON.parse(raw) as { userId: string; createdAt: string };
}

export async function destroySession(token: string): Promise<void> {
  if (!redisConfigured) {
    const session = memSessions.get(token);
    if (session) {
      memUserSessions.get(session.userId)?.delete(token);
    }
    memSessions.delete(token);
    return;
  }

  const session = await getSession(token);
  if (session) {
    await redis.srem(`user:${session.userId}:sessions`, token);
  }
  await redis.del(`session:${token}`);
}

export async function getCurrentUser(): Promise<SafeUser | null> {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("sb_session")?.value;
    if (!token) return null;

    const session = await getSession(token);
    if (!session) return null;

    const user = await getUserById(session.userId);
    if (!user) return null;

    return toSafeUser(user);
  } catch (err) {
    if (isDynamicServerUsageError(err)) {
      throw err;
    }
    console.error("Error in getCurrentUser:", err);
    return null;
  }
}

export async function deleteUserAndData(userId: string): Promise<void> {
  const user = await getUserById(userId);
  if (!user) return;

  if (!redisConfigured) {
    // 1. Delete all active sessions
    const tokens = memUserSessions.get(userId);
    if (tokens) {
      for (const token of tokens) {
        memSessions.delete(token);
      }
    }
    memUserSessions.delete(userId);
    
    // 2. Delete user mapping
    memUsers.delete(userId);
    memEmails.delete(user.email);
    
    // 3. Leaderboard fallback filter
    // Note: Since leaderboard is mock data locally, we could either filter the static array,
    // but we can skip / mock it since it resets anyway.
    return;
  }

  // Redis path
  // 1. Delete all active sessions for this user
  const sessions = await redis.smembers(`user:${userId}:sessions`);
  if (sessions && sessions.length > 0) {
    await Promise.all(sessions.map((token) => redis.del(`session:${token}`)));
  }
  await redis.del(`user:${userId}:sessions`);

  // 2. Delete user index and mapping keys
  await redis.del(`user:${userId}`);
  await redis.del(`user:email:${user.email}`);
  await redis.lrem("users:index", 0, userId);

  // 3. Remove all runs for this user from runs:index and delete run keys
  const runIds = await redis.lrange("runs:index", 0, -1);
  if (runIds && runIds.length > 0) {
    for (const runId of runIds) {
      const runRaw = await redis.get(`run:${runId}`);
      if (runRaw) {
        const run = JSON.parse(runRaw) as unknown;
        if (hasRunUserId(run, userId)) {
          await redis.del(`run:${runId}`);
          await redis.lrem("runs:index", 0, runId);
        }
      }
    }
  }

  // 4. Filter user's entries out of the leaderboard JSON
  const lbRaw = await redis.get("leaderboard");
  if (lbRaw) {
    const lb = JSON.parse(lbRaw) as unknown;
    if (Array.isArray(lb)) {
      const filtered = lb.filter((entry) => {
        const record = toLeaderboardRecord(entry);
        if (!record) return true;
        return record.userId !== userId && record.user !== user.name;
      });
      // Recalculate rank
      filtered.forEach((entry, i) => {
        if (isObjectRecord(entry)) {
          entry.rank = i + 1;
        }
      });
      await redis.set("leaderboard", JSON.stringify(filtered));
    }
  }
}

export async function setSessionCookie(token: string) {
  const cookieStore = await cookies();
  cookieStore.set("sb_session", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 604800, // 7 days
  });
}

export async function clearSessionCookie() {
  const cookieStore = await cookies();
  cookieStore.set("sb_session", "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}
