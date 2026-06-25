import json

from artifacts.bundler import create_artifact_bundle
from artifacts.storage import LocalArtifactStorage


def test_artifact_bundle_writes_expected_files(tmp_path):
    storage = LocalArtifactStorage(root=str(tmp_path), signing_secret="test-secret")
    bundle = create_artifact_bundle(
        run_id="run_test",
        manifest={"run_id": "run_test", "score": 1.0},
        submitted_files={"/workspace/solution.py": "print('ok')"},
        stdout="ok",
        stderr="",
        score_breakdown={"passed": 1, "total": 1, "score": 1.0},
        flags=[],
        repair_patch="--- a/solution.py\n+++ b/solution.py\n",
        storage=storage,
    )

    bundle_dir = tmp_path / "run_test"
    assert (bundle_dir / "manifest.json").is_file()
    assert (bundle_dir / "submitted_code" / "solution.py").is_file()
    assert (bundle_dir / "repair_patch.diff").is_file()
    assert bundle.bundle_hash
    assert "manifest.json" in bundle.artifact_hashes
    assert bundle.signed_urls["manifest"].startswith("local-artifact://")

    bundle_json = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
    assert bundle_json["bundle_hash"] == bundle.bundle_hash


def test_artifact_bundle_redacts_secret_text(tmp_path):
    storage = LocalArtifactStorage(root=str(tmp_path), signing_secret="test-secret")
    create_artifact_bundle(
        run_id="run_secret",
        manifest={"review": "Authorization: Bearer abc.def.secret"},
        stdout="OPENAI_API_KEY=sk-abcdefghijklmnop",
        storage=storage,
    )

    manifest_text = (tmp_path / "run_secret" / "manifest.json").read_text(encoding="utf-8")
    stdout_text = (tmp_path / "run_secret" / "stdout.txt").read_text(encoding="utf-8")
    assert "abc.def.secret" not in manifest_text
    assert "sk-abcdefghijklmnop" not in stdout_text
