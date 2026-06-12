# Golden image for running untrusted Python submissions.
#
# Build:  docker build -f python.Dockerfile -t sandbench/python:golden .
#
# This image is intentionally minimal. The real hardening is applied by the
# runner at `docker run` time (see backend/sandbox/runner.py and §6 of the
# build guide):
#   --network none --read-only --tmpfs /work --user 10001
#   --cap-drop ALL --security-opt no-new-privileges
#   --security-opt seccomp=seccomp.json
#   --memory --cpus --pids-limit  + a wall-clock timeout that kills it
#
# Every run gets a FRESH container from this image and is destroyed after.
FROM python:3.11-slim

# Test/eval tooling the scorer needs, baked in so runs need no network.
RUN pip install --no-cache-dir pytest==8.* \
 && rm -rf /root/.cache/pip

# Non-root user; the runner also passes --user but we set a safe default.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin sandbox

# Submissions and the task harness are copied in here at run time.
# The runner mounts this as a writable tmpfs; the rest of the FS is read-only.
WORKDIR /work
RUN chown 10001:10001 /work

USER 10001

# Default is a no-op; the runner overrides CMD with the task entrypoint.
CMD ["python", "-c", "print('sandbench python golden image ready')"]
