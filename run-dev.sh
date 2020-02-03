#!/bin/bash

set -x
# First kill redis if it exists
REDIS_PID=$(ps | grep redis-server | awk '{print $1;}')

if [ ! -z "$REDIS_PID"  ]; then
    echo "First I have to kill redis."
    kill -9 $REDIS_PID
fi

export RASS_DEV_LOGGER="%(message)s"

echo "Starting redis-server..."
redis-server&
sleep 1
echo "Redis started in background..."

echo "Starting worker in background..."
python task_worker.py&
sleep 1
echo "Worker started in background..."

set +x 

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export FLASK_APP=rass.py
export FLASK_DEBUG=1
mkdir -p $DIR/processing
python -m flask run --host=0.0.0.0 

