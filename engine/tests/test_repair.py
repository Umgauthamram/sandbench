"""Integration and unit tests for the repair loop and Gymnasium environment.

Run with: pytest -v tests/test_repair.py
"""
import pytest
from analysis import patch_apply
from rl_env.env import SandbenchRepairEnv

ORIGINAL_CODE = """def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(i)
    return out
"""

PATCH = """--- a/solution.py
+++ b/solution.py
@@ -1,8 +1,10 @@
 def fizzbuzz(n):
     out = []
     for i in range(1, n + 1):
-        if i % 3 == 0:
+        if i % 15 == 0:
+            out.append("FizzBuzz")
+        elif i % 3 == 0:
             out.append("Fizz")
         elif i % 5 == 0:
             out.append("Buzz")
         else:
             out.append(i)
     return out
"""


def test_apply_patch_library():
    # Test application via patch-ng
    patched, method = patch_apply.apply_patch(ORIGINAL_CODE, PATCH)
    assert method == "patch-ng"
    assert patched is not None
    assert 'out.append("FizzBuzz")' in patched


def test_fallback_apply():
    # Test fallback application manually
    patched = patch_apply.fallback_apply(ORIGINAL_CODE, PATCH)
    assert patched is not None
    assert 'out.append("FizzBuzz")' in patched


def test_apply_patch_empty():
    patched, reason = patch_apply.apply_patch(ORIGINAL_CODE, "")
    assert patched is None
    assert reason == "empty patch"


def test_apply_patch_invalid():
    bad_patch = "this is not a unified diff"
    patched, reason = patch_apply.apply_patch(ORIGINAL_CODE, bad_patch)
    assert patched is None
    assert reason == "patch did not apply"


@pytest.mark.integration
def test_repair_env_workflow():
    env = SandbenchRepairEnv()
    obs = env.reset("fizzbuzz", ORIGINAL_CODE)
    assert obs["task_id"] == "fizzbuzz"
    assert obs["score"] == 0.60
    
    # Run tests action
    new_obs, reward, done, info = env.step({"type": "run_tests"})
    assert reward == -0.01
    assert done is False
    assert new_obs["score"] == 0.60
    
    # Submit patch action
    new_obs2, reward2, done2, info2 = env.step({"type": "submit_patch", "patch": PATCH})
    assert done2 is True
    assert new_obs2["score"] == 1.00
    assert reward2 == pytest.approx(0.40)
    assert info2["method"] == "patch-ng"
