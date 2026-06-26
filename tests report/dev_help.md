You can now check any code file synchronously and securely inside the local sandbox without running Redis, a worker process, or a web frontend.

Run:

bash
python cli/main.py check path/to/solution.py
Key Capabilities:
Auto-Detection: The CLI automatically attempts to detect the correct task ID:
By matching task IDs in the file path.
By scanning the first 20 lines of the file for comments like # task: <id> or # id: <id>.
By matching the filename against known task entrypoints in the registry.
You can also explicitly specify it using --task <id> (e.g. --task async-rate-limiter).
Direct Execution: The CLI invokes the Docker sandbox runner and scorer synchronously, bypassing the Redis job queue and database logic entirely.
Optional LLM Repair: You can enable LLM-in-the-loop repair by passing the --repair flag. If the code fails tests or triggers security warnings, it will query your model provider to generate a review and patch, apply the patch, and rescore the repaired version.
Patch Writeback: If you want the CLI to overwrite the solution file with the successful patch, add the --write flag.
Example Run (FizzBuzz Reference):
powershell
G:\projects\sandbench> python cli/main.py check engine/scoring/tasks/fizzbuzz/reference.py
Auto-detected task ID from path: 'fizzbuzz'
Running secure sandbox check for 'fizzbuzz'...
Scoring code against tests inside sandbox...
============================================================
VERDICT: CLEAN
SCORE:   100% (5/5 tests passed)
============================================================






