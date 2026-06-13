# Golden image for running untrusted Node.js submissions.
#
# Build:  docker build -f node.Dockerfile -t sandbench/node:golden .
#
# Hardening is applied by the runner at `docker run` time (see §6):
#   --network none --read-only --tmpfs /work --user 10001
#   --cap-drop ALL --security-opt no-new-privileges
#   --security-opt seccomp=seccomp.json
#   --memory --cpus --pids-limit  + a wall-clock timeout that kills it
#
# Every run gets a FRESH container from this image and is destroyed after.
FROM node:20-slim

# `node` user (uid 1000) ships with the base image; we add a dedicated one
# so the uid lines up with the python image and the runner's --user flag.
RUN groupadd --gid 10001 sandbox \
 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin sandbox

WORKDIR /work
RUN chown 10001:10001 /work

USER 10001

# Default is a no-op; the runner overrides CMD with the task entrypoint.
CMD ["node", "-e", "console.log('sandbench node golden image ready')"]
