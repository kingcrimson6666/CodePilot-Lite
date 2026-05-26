#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$PWD:$PWD/frameworks/HelloAgents"
exec python3 app/cli.py "$@"
