# SandBench Traces v0

This folder contains generated, redacted training data for a SandBench repair/review model.

Generated files:

- `train.jsonl`: chat-style fine-tuning examples.
- `validation.jsonl`: deterministic validation split.
- `manifest.json`: counts, source path, schema, and task distribution.

Each JSONL row has this shape:

```json
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "Task, verdict, stderr, and submitted code..." },
    { "role": "assistant", "content": "{\"review_text\":\"...\",\"patch\":\"...\"}" }
  ],
  "metadata": {
    "trace_id": "...",
    "task_id": "...",
    "language": "python",
    "verdict": "broken",
    "score_before": 0.2,
    "score_after": 1.0,
    "reward": 0.8
  }
}
```

The builder excludes provider/API error traces and redacts likely API keys, bearer tokens, and secret query parameters. Review the generated files before using them to train a public or shared model.
