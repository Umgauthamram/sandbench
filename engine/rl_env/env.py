"""Gymnasium-style environment wrapper for SandBench code repair.

Exposes the sandbox scoring and patching loops as an environment.
"""
import logging
from typing import Tuple, Dict, Any

from scoring import registry as task_registry
from scoring import score as scorer
from analysis import patch_apply

logger = logging.getLogger(__name__)


class SandbenchRepairEnv:
    """A minimal Gymnasium-style environment for code repair rollouts.

    Wraps the existing runner, scorer, and review mechanisms to express
    the repair loop as obs -> action -> reward.
    """

    def __init__(self):
        self.task_id = None
        self.task = None
        self.code = ""
        self.score_before = 0.0
        self.current_score = 0.0
        self.test_output = ""

    def reset(self, task_id: str, code: str) -> Dict[str, Any]:
        """Reset the environment to a new task and submission code.

        Returns observation dict.
        """
        self.task_id = task_id
        self.task = task_registry.get_task(task_id)
        if not self.task:
            raise ValueError(f"Unknown task: {task_id}")

        self.code = code
        res = scorer.score_submission(self.code, self.task)
        self.score_before = res["score"]
        self.current_score = self.score_before
        self.test_output = res["raw_output"]

        return self._get_obs()

    def _get_obs(self) -> Dict[str, Any]:
        """Return the current observation state."""
        return {
            "task_id": self.task_id,
            "code": self.code,
            "score": self.current_score,
            "test_output": self.test_output,
        }

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Step the environment with an action.

        Actions:
          - {"type": "run_tests"}: Re-run tests on current code, step cost -0.01.
          - {"type": "submit_patch", "patch": "..."}: Apply patch, score, done=True.

        Returns (observation, reward, done, info).
        """
        action_type = action.get("type")
        info = {}

        if action_type == "run_tests":
            res = scorer.score_submission(self.code, self.task)
            self.current_score = res["score"]
            self.test_output = res["raw_output"]
            reward = -0.01
            done = False
            return self._get_obs(), reward, done, info

        elif action_type == "submit_patch":
            patch = action.get("patch", "")
            patched_code, method = patch_apply.apply_patch(self.code, patch)
            
            if patched_code is None:
                info["error"] = f"Patch failed to apply: {method}"
                reward = 0.0
                done = True
                return self._get_obs(), reward, done, info
            
            self.code = patched_code
            res = scorer.score_submission(self.code, self.task)
            score_after = res["score"]
            self.current_score = score_after
            self.test_output = res["raw_output"]
            
            reward = score_after - self.score_before
            done = True
            info["method"] = method
            return self._get_obs(), reward, done, info

        else:
            return self._get_obs(), 0.0, True, {"error": f"Unknown action type: {action_type}"}
