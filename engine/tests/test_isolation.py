"""Tests for isolation runtime resolution.

These are pure unit tests: they patch the daemon runtime list rather than
requiring gVisor to be installed, so they run anywhere including CI.
"""
import pytest

from sandbox import runner


@pytest.fixture(autouse=True)
def _reset_runtime_state(monkeypatch):
    """Clear the runtime cache and restore defaults around every test."""
    monkeypatch.setattr(runner, "_runtimes_cache", None, raising=False)
    monkeypatch.setattr(runner, "_isolation_warned", False, raising=False)
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "auto", raising=False)
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", False, raising=False)
    yield
    monkeypatch.setattr(runner, "_runtimes_cache", None, raising=False)


def _fake_runtimes(monkeypatch, names):
    monkeypatch.setattr(runner, "available_runtimes", lambda *a, **k: list(names))


# --- auto mode ------------------------------------------------------------

def test_auto_prefers_gvisor_when_present(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    rt, level, _ = runner.resolve_runtime()
    assert rt == "runsc"
    assert level == runner.ISOLATION_GVISOR


def test_auto_falls_back_to_runc(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc"])
    rt, level, note = runner.resolve_runtime()
    assert rt is None  # None => daemon default
    assert level == runner.ISOLATION_SHARED_KERNEL
    assert "gVisor not installed" in note


def test_auto_respects_preference_order(monkeypatch):
    """runsc wins over runsc-kvm because it is listed first in GVISOR_RUNTIMES."""
    _fake_runtimes(monkeypatch, ["runc", "runsc-kvm", "runsc"])
    rt, _, _ = runner.resolve_runtime()
    assert rt == "runsc"


# --- explicit pinning -----------------------------------------------------

def test_explicit_runc_is_honoured(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "runc")
    rt, level, _ = runner.resolve_runtime()
    assert rt is None
    assert level == runner.ISOLATION_SHARED_KERNEL


def test_pinned_unknown_runtime_falls_back_with_warning(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "runsc")
    rt, level, note = runner.resolve_runtime()
    assert rt is None
    assert level == runner.ISOLATION_SHARED_KERNEL
    assert "not registered" in note


def test_pinned_non_gvisor_runtime_is_not_claimed_as_gvisor(monkeypatch):
    """An arbitrary runtime must not be labelled as gVisor isolation."""
    _fake_runtimes(monkeypatch, ["runc", "io.containerd.kata.v2"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "io.containerd.kata.v2")
    rt, level, _ = runner.resolve_runtime()
    assert rt == "io.containerd.kata.v2"
    assert level == runner.ISOLATION_SHARED_KERNEL


# --- require-hardened -----------------------------------------------------

def test_require_hardened_raises_without_gvisor(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc"])
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", True)
    with pytest.raises(runner.HardenedRuntimeUnavailable):
        runner.resolve_runtime()


def test_require_hardened_passes_with_gvisor(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", True)
    rt, level, _ = runner.resolve_runtime()
    assert rt == "runsc"
    assert level == runner.ISOLATION_GVISOR


def test_require_hardened_conflicts_with_explicit_runc(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "runc")
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", True)
    with pytest.raises(runner.HardenedRuntimeUnavailable):
        runner.resolve_runtime()


def test_require_hardened_raises_on_missing_pinned_runtime(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "runsc")
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", True)
    with pytest.raises(runner.HardenedRuntimeUnavailable):
        runner.resolve_runtime()


# --- the audit-profile exception -----------------------------------------

def test_audit_runs_stay_on_runc_to_preserve_syscall_evidence(monkeypatch):
    """Safety tasks need host seccomp audit records, which gVisor never produces."""
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    rt, level, note = runner.resolve_runtime(audit=True)
    assert rt is None
    assert level == runner.ISOLATION_SHARED_KERNEL
    assert "evidence" in note.lower()


def test_audit_can_be_forced_onto_gvisor(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    monkeypatch.setattr(runner, "SANDBOX_RUNTIME", "runsc")
    rt, level, _ = runner.resolve_runtime(audit=True)
    assert rt == "runsc"
    assert level == runner.ISOLATION_GVISOR


# --- report ---------------------------------------------------------------

def test_isolation_report_shape(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc", "runsc"])
    report = runner.isolation_report()
    assert report["gvisor_available"] is True
    assert report["gvisor_runtime"] == "runsc"
    assert report["effective_runtime"] == "runsc"
    assert report["isolation"] == runner.ISOLATION_GVISOR
    assert report["error"] is None


def test_isolation_report_surfaces_error_instead_of_raising(monkeypatch):
    _fake_runtimes(monkeypatch, ["runc"])
    monkeypatch.setattr(runner, "SANDBOX_REQUIRE_HARDENED", True)
    report = runner.isolation_report()
    assert report["error"]
    assert report["gvisor_available"] is False


def test_run_result_defaults_to_shared_kernel():
    """A RunResult that nobody annotated must not claim hardened isolation."""
    res = runner.RunResult(
        exit_code=0, stdout="", stderr="", duration_ms=1,
        oom_killed=False, timed_out=False,
    )
    assert res.isolation == runner.ISOLATION_SHARED_KERNEL
    assert res.runtime == "runc"
