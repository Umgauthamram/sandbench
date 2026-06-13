"""Script to run one real code repair rollout using SandbenchRepairEnv."""
import sys
import os

# Ensure engine is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl_env.env import SandbenchRepairEnv
from sandbox import review

# Deliberately partial FizzBuzz solution (missing division by 15 logic)
PARTIAL_FIZZBUZZ = """def fizzbuzz(n):
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


def main():
    print("=== SANDBENCH RL LOOP ROLLOUT DEMO ===")
    
    env = SandbenchRepairEnv()
    
    # 1. Reset env
    print("\n[t=0] Resetting env with partial FizzBuzz solution...")
    obs = env.reset("fizzbuzz", PARTIAL_FIZZBUZZ)
    score_before = obs["score"]
    print(f"Initial score: {score_before * 100:.1f}%")
    print(f"Test output snippet:\n{obs['test_output']}")
    
    cumulative_reward = 0.0
    
    # Print t=0 trace step
    print(f"\nTrace Step 0:")
    print(f"  t: 0")
    print(f"  Action: reset")
    print(f"  Score: {score_before:.2f}")
    print(f"  Reward: 0.00")
    print(f"  Cumulative: 0.00")

    # 2. Call review.review_code to get a real patch from Gemini/local provider
    print("\nRequesting code review and patch from LLM analysis engine...")
    review_res = review.review_code(PARTIAL_FIZZBUZZ, obs["test_output"])
    
    if not review_res.get("ok"):
        print(f"LLM review failed: {review_res.get('review_text')}")
        return
        
    patch = review_res.get("patch", "")
    print(f"\nReceived patch suggestion:\n{patch}")
    
    # 3. Step the environment with submit_patch
    print("\nStepping environment: submit_patch...")
    action = {"type": "submit_patch", "patch": patch}
    new_obs, reward, done, info = env.step(action)
    
    cumulative_reward += reward
    score_after = new_obs["score"]
    
    # Print t=1 trace step
    print(f"\nTrace Step 1:")
    print(f"  t: 1")
    print(f"  Action: submit_patch (method: {info.get('method', 'unknown')})")
    print(f"  Score: {score_after:.2f}")
    print(f"  Reward: {reward:+.2f}")
    print(f"  Cumulative: {cumulative_reward:+.2f}")
    
    print("\nPatched code:")
    print(new_obs["code"])
    print(f"\nRollout finished. Final score: {score_after * 100:.1f}%, Reward: {reward:+.2f}")


if __name__ == "__main__":
    main()
