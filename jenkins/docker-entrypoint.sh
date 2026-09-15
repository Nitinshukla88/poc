#!/bin/bash

set -e

DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

echo "Docker socket GID: $DOCKER_GID"

if ! getent group "$DOCKER_GID" > /dev/null; then
    groupadd -g "$DOCKER_GID" docker-host
fi

DOCKER_GROUP=$(getent group "$DOCKER_GID" | cut -d: -f1)

usermod -aG "$DOCKER_GROUP" jenkins

exec gosu jenkins /usr/local/bin/jenkins.sh
