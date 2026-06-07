#!/bin/bash
export HERMES_HOME=/home/sesveria/.hermes
set -a
source /home/sesveria/.hermes/.env
set +a
cd /home/sesveria/hermes_workspace/story_tool
exec /home/sesveria/.hermes/hermes-agent/venv/bin/python3 web_app.py
