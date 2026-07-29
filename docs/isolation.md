# Isolation model

SandBench's verdict is only worth as much as the boundary that produced it. This
document states exactly what that boundary is, what it does not protect against,
and how to strengthen it.

## The ladder

There are three meaningfully different places the boundary can sit.

| Level | Who services the submission's syscalls | Escape means | Needs |
|---|---|---|---|
| `runc` (default) | The **host kernel**, directly | Host compromise | nothing |
| **`runsc` (gVisor)** | A **userspace kernel** (the Sentry), which forwards a small filtered set to the host | Break the Sentry *first*, then the host kernel | Linux, no hardware virt |
| microVM (Firecracker / Kata) | A real guest kernel in a VM | Break the hypervisor | `/dev/kvm`, bare metal or nested virt |

SandBench supports the first two today. The third is future work.

### Why runc alone is not enough

The hardening SandBench applies on runc is real and worth having:

- `--network none` — no outbound traffic is possible at all
- read-only root filesystem, single 16 MB `/tmp` tmpfs as the only writable path
- `--cap-drop ALL` and `no-new-privileges`
- runs as `nobody` (65534)
- memory, CPU and PID caps; container destroyed after every run
- a custom seccomp profile narrowing the syscall surface

But all of that constrains *what the code is allowed to ask for*. It does not
change *who answers*. On runc, every permitted syscall is implemented by the
same kernel your host is running. A kernel-level vulnerability reachable through
the allowed syscall set is a host compromise, and seccomp cannot fix that — it
only shrinks the target.

### What gVisor changes

gVisor's `runsc` runtime starts a sandboxed process called the Sentry that
implements the Linux syscall interface in Go, in userspace. The container talks
to the Sentry; the Sentry talks to the host kernel through a deliberately narrow,
seccomp-filtered interface. An attacker now has to defeat the Sentry *and then*
the host kernel.

The reason this matters commercially: **gVisor needs no hardware
virtualisation.** It runs on an ordinary VPS, a shared cloud instance, or a
developer laptop — exactly the hosts where Firecracker and Kata are unavailable.
It is the only hardening step on this ladder that most SandBench deployments can
actually take.

The cost is syscall latency. Syscall-heavy workloads slow down measurably;
compute-bound ones barely notice. For test suites in the 1–20 second range the
overhead is acceptable, and correctness of the boundary is worth more than the
milliseconds.

## Configuration

Two environment variables, read in `engine/config.py`:

| Variable | Default | Meaning |
|---|---|---|
| `SANDBOX_RUNTIME` | `auto` | `auto` uses gVisor when the daemon has it and falls back to runc. `runc` forces shared-kernel. Any other value is treated as a literal runtime name and must be registered with the daemon. |
| `SANDBOX_REQUIRE_HARDENED` | `0` | When `1`, a run is **refused** rather than executed on runc. |

`auto` is deliberately the default so that cloning the repo and running the demo
works on a laptop with nothing installed. `SANDBOX_REQUIRE_HARDENED=1` is the
correct setting for any worker that evaluates code it did not write, and should
be set on every production host.

Recommended `engine/.env` for a real worker:

```env
SANDBOX_RUNTIME=auto
SANDBOX_REQUIRE_HARDENED=1
```

## Install

```bash
sudo bash scripts/install-gvisor.sh
python cli/main.py doctor
```

`doctor` reports what the host will actually do, not what it was configured to
do:

```
  Configured (SANDBOX_RUNTIME) : auto
  Daemon runtimes              : runc, runsc
  gVisor available             : yes (runsc)
  Effective runtime            : runsc
  Isolation level              : gVisor — userspace kernel (Sentry) between code and host
```

## The audit-profile exception

Safety-suite tasks (`is_safety_task=True`) use the audit seccomp profile: instead
of blocking dangerous syscalls, it **logs** them, so the monitor can cite
evidence that a submission genuinely attempted to open a socket or write outside
`/work`. That evidence is a host-kernel seccomp audit record.

Under gVisor the Sentry services those syscalls itself, so the host kernel never
sees them and never logs them. The evidence silently disappears — the run would
still pass, but the safety verdict would be based on nothing.

So **audit runs stay on runc even when gVisor is available**, and the reason is
recorded in the run's `isolation_note`. This is a considered trade-off, not an
oversight: safety tasks are SandBench's own curated adversarial samples, not
arbitrary untrusted user code, so the risk profile is different. To override:

```env
SANDBOX_RUNTIME=runsc   # pins gVisor for audit runs too, losing syscall evidence
```

Making gVisor's own Sentry-level logs a first-class evidence source — which
would remove this trade-off entirely — is the right long-term fix.

## What travels with the verdict

Every `RunResult` now carries `runtime`, `isolation` and `isolation_note`, and
`score_submission()` surfaces them under `result["isolation"]`. Containers are
labelled `sandbench.isolation=<level>`. A leaderboard row produced on
shared-kernel runc is not the same claim as one produced under gVisor, and the
data now says which it was.

## macOS and Windows

gVisor cannot be installed on Docker Desktop. It does not need to be: Docker
Desktop already runs all containers inside a Linux VM, so a container escape
lands in that disposable VM rather than on your machine. Your weakest case is a
**native Linux host**, which is exactly where the worker runs in production and
exactly where gVisor should be installed.

## Not yet covered

- **microVM isolation** (Firecracker / Kata) for hosts with `/dev/kvm`. The
  runtime plumbing added here is generic — `SANDBOX_RUNTIME=io.containerd.kata.v2`
  will already be passed through — but it is untested, and the
  copy-payload-before-start trick in `runner.py` may need revisiting.
- **Sentry-level monitoring** as an evidence source, which would let audit runs
  use gVisor.
- **Side channels.** Neither runc nor gVisor claims to stop timing or
  microarchitectural side channels between the sandbox and the host.
