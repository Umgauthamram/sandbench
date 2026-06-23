import json
import csv
from typing import List
from evaluation.models import EvaluationResult

def export_to_jsonl(result: EvaluationResult, filepath: str) -> None:
    """Export TaskResult objects, one JSON object per line."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for task_id, task_res in result.task_results.items():
            f.write(json.dumps(task_res.model_dump()) + '\n')

def export_to_csv(result: EvaluationResult, filepath: str) -> None:
    """Export flat table with columns: task_id, score, pass@k, tokens, duration."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['task_id', 'score', 'pass_at_k', 'tokens', 'duration'])
        for task_id, task_res in result.task_results.items():
            # Calculate averages for the n runs
            mean_score = sum(task_res.scores) / len(task_res.scores) if task_res.scores else 0.0
            mean_tokens = int(sum(usage.get("total_tokens", 0) for usage in task_res.token_usages) / len(task_res.token_usages)) if task_res.token_usages else 0
            mean_duration = int(sum(task_res.durations_ms) / len(task_res.durations_ms)) if task_res.durations_ms else 0
            
            writer.writerow([
                task_id,
                f"{mean_score:.4f}",
                f"{task_res.pass_at_k:.4f}",
                mean_tokens,
                mean_duration
            ])

def export_to_markdown(result: EvaluationResult, filepath: str) -> None:
    """Export human-readable markdown summary report."""
    lines = []
    lines.append(f"# SandBench Evaluation Report - Suite `{result.suite_id}`")
    lines.append("")
    lines.append(f"**Timestamp**: {result.timestamp}")
    lines.append(f"**Adapter**: `{result.config.adapter_name}` ({result.config.provider})")
    lines.append(f"**Configuration**: k={result.config.k}, n={result.config.n}")
    lines.append("")
    
    lines.append("## Aggregate Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| **Passed Tasks** | {result.passed_tasks} / {result.total_tasks} |")
    lines.append(f"| **Average pass@{result.config.k}** | {result.average_pass_at_k:.2%} |")
    lines.append(f"| **Total Tokens** | {result.total_tokens:,} |")
    lines.append(f"| **Total Cost (Est.)** | ${result.total_cost:.5f} |")
    lines.append(f"| **Total Duration** | {result.duration_ms / 1000.0:.2f}s |")
    lines.append("")
    
    lines.append("## Per-Task Summary")
    lines.append("")
    lines.append("| Task ID | Success (c/n) | pass@k | Mean Score | Mean Duration |")
    lines.append("| --- | --- | --- | --- | --- |")
    for task_id, task_res in result.task_results.items():
        mean_score = sum(task_res.scores) / len(task_res.scores) if task_res.scores else 0.0
        mean_duration = int(sum(task_res.durations_ms) / len(task_res.durations_ms)) if task_res.durations_ms else 0
        success_str = f"{task_res.c} / {task_res.n}"
        lines.append(
            f"| `{task_id}` | {success_str} | {task_res.pass_at_k:.2%} | {mean_score:.1%} | {mean_duration / 1000.0:.2f}s |"
        )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
