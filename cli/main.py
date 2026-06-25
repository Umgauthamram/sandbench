import sys
import os
import argparse
from pathlib import Path

# Add the engine directory to python path so we can import from it
ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(ENGINE_DIR))

try:
    from scoring import registry as task_registry
    from scoring.score import score_submission
    from adapters.registry import create_adapter
    from evaluation.harness import evaluate_suite
    from evaluation.export import export_to_jsonl, export_to_csv, export_to_markdown
    from safety.suite import SafetySuite
except ImportError as e:
    print(f"Error: Failed to import engine components. Ensure requirements in engine/requirements.txt are installed. Details: {e}")
    sys.path.pop(0)

def cmd_validate_tasks(args):
    print("Validating task registry...")
    try:
        tasks = task_registry.load_tasks()
        print(f"[SUCCESS] Loaded {len(tasks)} tasks.")
        for task in tasks.values():
            if args.strict and not task.benchmark_ready:
                print(f"[WARN] Task '{task.id}' is not marked benchmark_ready.")
        print("[SUCCESS] All tasks verified.")
    except Exception as e:
        print(f"[ERROR] Task validation failed: {e}")
        sys.exit(1)

def cmd_run(args):
    print(f"Starting run for suite '{args.suite}' using model '{args.model}' (k={args.k}, n={args.n})...")
    provider = "openai"
    model_name = args.model
    if ":" in args.model:
        provider, model_name = args.model.split(":", 1)

    api_key_env = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env) or os.environ.get("MODEL_API_KEY")
    if not api_key:
        print(f"[ERROR] API key environment variable {api_key_env} is not set.")
        sys.exit(1)

    try:
        adapter = create_adapter(provider, api_key, model_name)
        result = evaluate_suite(args.suite, adapter, k=args.k, n=args.n)
        
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export results
        export_to_jsonl(result, str(output_dir / "results.jsonl"))
        export_to_csv(result, str(output_dir / "results.csv"))
        export_to_markdown(result, str(output_dir / "results.md"))
        
        print(f"[SUCCESS] Suite evaluation completed.")
        print(f"Tasks: {result.total_tasks}, Passed: {result.passed_tasks}")
        print(f"Average pass@{args.k}: {result.average_pass_at_k * 100:.2f}%")
        print(f"Results exported to {output_dir}/")
    except Exception as e:
        print(f"[ERROR] Run failed: {e}")
        sys.exit(1)

def cmd_safety_eval(args):
    print(f"Starting safety evaluation using model '{args.model}'...")
    provider = "openai"
    model_name = args.model
    if ":" in args.model:
        provider, model_name = args.model.split(":", 1)

    api_key_env = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env) or os.environ.get("MODEL_API_KEY")
    if not api_key:
        print(f"[ERROR] API key environment variable {api_key_env} is not set.")
        sys.exit(1)

    try:
        adapter = create_adapter(provider, api_key, model_name)
        suite = SafetySuite()
        tasks = suite.tasks()
        
        print(f"Found {len(tasks)} safety tasks. Running evaluations...")
        results = []
        for task in tasks:
            print(f"Running safety task '{task.id}'...")
            # Safety tasks score model responses directly
            prompt = f"Write python code for the following task description: {task.description}"
            gen_res = adapter.generate(prompt)
            if not gen_res.ok:
                print(f"[WARN] Failed to generate code for '{task.id}': {gen_res.error}")
                continue
            
            # Score generated code
            score_res = score_submission(gen_res.content, task)
            
            from safety.suite import SafetyTaskResult
            worst_severity = "info"
            if score_res.get("flags"):
                # Find worst severity from monitor flags
                order = ["info", "low", "medium", "high", "critical"]
                for flag in score_res["flags"]:
                    sev = getattr(flag, "severity", "info").value.lower()
                    if order.index(sev) > order.index(worst_severity):
                        worst_severity = sev

            results.append(SafetyTaskResult(
                task_id=task.id,
                category=task.capability,
                passed=len(score_res.get("flags", [])) == 0,
                severity=worst_severity,
                evidence=[str(f) for f in score_res.get("flags", [])]
            ))

        eval_res = suite.aggregate(results)
        
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write JSON report
        report_path = output_dir / "safety_results.json"
        import json
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(eval_res.to_dict(), f, indent=2)
            
        print(f"[SUCCESS] Safety evaluation completed.")
        print(f"Tasks: {eval_res.total_tasks}, Passed (Safe): {eval_res.passed_tasks}")
        print(f"Safety Score: {eval_res.safety_score * 100:.2f}%")
        print(f"Safety report written to {report_path}")
    except Exception as e:
        print(f"[ERROR] Safety evaluation failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="sandbench",
        description="SandBench CLI for local model evaluation and task verification"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. validate-tasks
    val_parser = subparsers.add_parser("validate-tasks", help="Validate task registry schemas")
    val_parser.add_argument("--strict", action="store_true", help="Enforce benchmark-ready strictness")

    # 2. run
    run_parser = subparsers.add_parser("run", help="Run a suite evaluation")
    run_parser.add_argument("--suite", required=True, help="Suite ID to evaluate (e.g. 'core')")
    run_parser.add_argument("--model", required=True, help="Model to evaluate (e.g. 'openai:gpt-4o-mini')")
    run_parser.add_argument("--k", type=int, default=1, help="Pass@k sample count to compute")
    run_parser.add_argument("--n", type=int, default=1, help="Total sample count to evaluate")
    run_parser.add_argument("--output-dir", default="./results", help="Directory to save exported results")

    # 3. safety-eval
    safety_parser = subparsers.add_parser("safety-eval", help="Run safety evaluations against the safety suite")
    safety_parser.add_argument("--model", required=True, help="Model to evaluate (e.g. 'openai:gpt-4o-mini')")
    safety_parser.add_argument("--output-dir", default="./results", help="Directory to save safety report")

    args = parser.parse_args()

    if args.command == "validate-tasks":
        cmd_validate_tasks(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "safety-eval":
        cmd_safety_eval(args)

if __name__ == "__main__":
    main()
