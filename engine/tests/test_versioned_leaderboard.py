import json

from leaderboard.versioned import upsert_versioned_leaderboard


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.lists = {}
        self.zsets = {}
        self.hashes = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value):
        self.kv[key] = value

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    def zscore(self, key, member):
        return self.zsets.get(key, {}).get(member)

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)

    def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def zrevrange(self, key, start, end):
        members = sorted(self.zsets.get(key, {}), key=lambda m: self.zsets[key][m], reverse=True)
        return members[start:] if end == -1 else members[start:end + 1]


def test_versioned_leaderboard_keeps_peak_and_history():
    redis = FakeRedis()

    first = upsert_versioned_leaderboard(
        redis,
        run_id="run_1",
        user="ada",
        user_id="usr_1",
        submission_id="sub_1",
        suite="core",
        task_id="fizzbuzz",
        task_title="FizzBuzz",
        task_version="0.1.0",
        score=0.5,
        verdict="clean",
        created_at="2026-06-25T00:00:00Z",
    )
    second = upsert_versioned_leaderboard(
        redis,
        run_id="run_2",
        user="ada",
        user_id="usr_1",
        submission_id="sub_2",
        suite="core",
        task_id="fizzbuzz",
        task_title="FizzBuzz",
        task_version="0.1.0",
        score=0.4,
        verdict="clean",
        created_at="2026-06-25T00:01:00Z",
    )

    assert first.submission_hash != second.submission_hash
    assert len(redis.lists["sandbench:lb:core:0.1.0:history:usr_1"]) == 2
    assert redis.zsets["sandbench:lb:core:0.1.0:scores"]["usr_1:fizzbuzz"] == 0.5

    latest = json.loads(redis.kv[f"sandbench:submission:{second.submission_hash}"])
    assert latest["previous_hash"] == first.submission_hash
