"""Training-data trace capture for SandBench analysis engine.

Appends structured code review traces to a JSONL file for future model fine-tuning.
"""
import os
import json
import logging
from config import TRACE_LOG_PATH

logger = logging.getLogger(__name__)


def log_trace(trace: dict) -> None:
    """Append a structured LLM review trace to the traces log file.

    This function is completely isolated and will never propagate exceptions.
    """
    try:
        path = TRACE_LOG_PATH
        if not os.path.isabs(path):
            # Resolve relative to the engine directory (parent of this file's parent)
            current_dir = os.path.dirname(os.path.abspath(__file__))  # engine/analysis
            engine_dir = os.path.dirname(current_dir)  # engine
            path = os.path.join(engine_dir, path)

        # Ensure target directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace) + "\n")
            f.flush()
    except Exception as e:
        logger.exception("Failed to log training trace: %s", e)
