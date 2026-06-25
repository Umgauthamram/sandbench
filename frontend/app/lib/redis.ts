// Minimal Upstash Redis REST client — no external dependency, just fetch.
// Configure with UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN.
//
// The Python worker connects to the SAME database over the standard rediss://
// protocol and BRPOPs the job queue (see SandBench_Starter_README.md).

let rawUrl = process.env.UPSTASH_REDIS_REST_URL;
if (rawUrl && (rawUrl.startsWith("redis://") || rawUrl.startsWith("rediss://"))) {
  try {
    const withoutProtocol = rawUrl.replace(/^rediss?:\/\//, "");
    const parts = withoutProtocol.split("@");
    const hostPort = parts[parts.length - 1];
    const host = hostPort.split(":")[0];
    rawUrl = `https://${host}`;
  } catch (e) {
    console.error("Failed to parse redis URL into REST URL:", e);
  }
}

const URL = rawUrl;
const TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;

export const redisConfigured = Boolean(URL && TOKEN);

async function command<T = unknown>(args: (string | number)[]): Promise<T> {
  if (!redisConfigured) throw new Error("Upstash Redis is not configured");
  const res = await fetch(URL!, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(args),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Upstash error ${res.status}: ${await res.text()}`);
  }
  const data = (await res.json()) as { result: T };
  return data.result;
}

export const redis = {
  get: (key: string) => command<string | null>(["GET", key]),
  set: (key: string, value: string) => command(["SET", key, value]),
  del: (key: string) => command<number>(["DEL", key]),
  setex: (key: string, seconds: number, value: string) =>
    command(["SET", key, value, "EX", seconds]),
  lpush: (key: string, value: string) => command<number>(["LPUSH", key, value]),
  lrange: (key: string, start: number, stop: number) =>
    command<string[]>(["LRANGE", key, start, stop]),
  lrem: (key: string, count: number, value: string) =>
    command<number>(["LREM", key, count, value]),
  sadd: (key: string, value: string) => command<number>(["SADD", key, value]),
  srem: (key: string, value: string) => command<number>(["SREM", key, value]),
  smembers: (key: string) => command<string[]>(["SMEMBERS", key]),
  zrevrange: (key: string, start: number, stop: number) =>
    command<string[]>(["ZREVRANGE", key, start, stop]),
  hget: (key: string, field: string) => command<string | null>(["HGET", key, field]),
};
