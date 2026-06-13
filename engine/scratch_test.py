import redis
import json
import time

UPSTASH_REDIS_URL = "rediss://default:gQAAAAAAAd-RAAIgcDEwYmRiZDFkZDYxYzQ0YzQ4ODIzYTMwOTg5NDc5MGMxZg@fine-bull-122769.upstash.io:6379"
r = redis.from_url(UPSTASH_REDIS_URL, decode_responses=True)

code = """import os

def fizzbuzz(n):
    # Repeatedly write files to trigger disk exhaustion
    i = 0
    while True:
        with open(f"file_{i}.txt", "w") as f:
            f.write("A" * 1_000_000)
        i += 1
"""

run_id = f"run_malicious_test_{int(time.time())}"
run_key = f"run:{run_id}"

run_data = {
    "id": run_id,
    "submissionId": f"sub_{run_id[4:]}",
    "type": "code",
    "language": "python",
    "taskId": "fizzbuzz",
    "taskTitle": "FizzBuzz",
    "status": "queued",
    "flags": [],
    "suggestions": [],
    "logs": ["[gateway] submission accepted, job enqueued"],
    "startedAt": "2026-06-13T12:00:00Z",
}
r.set(run_key, json.dumps(run_data))
r.lpush("runs:index", run_id)

job = {
    "runId": run_id,
    "language": "python",
    "type": "code",
    "taskId": "fizzbuzz",
    "payload": code
}
r.lpush("sandbench:jobs_local", json.dumps(job))
print(f"Submitted job {run_id}")

finished = False
for _ in range(30):
    time.sleep(1)
    data = json.loads(r.get(run_key) or "{}")
    if data.get("status") in ("done", "quarantined", "error"):
        print(f"Status: {data['status']}, verdict: {data.get('verdict')}, score: {data.get('score')}")
        print("Logs:")
        for log in data.get("logs", []):
            print(f"  {log}")
        print("Flags:")
        print(json.dumps(data.get("flags", []), indent=2))
        finished = True
        break

if not finished:
    print("Timeout waiting for job")
