#!/bin/bash
# Launch the bulk agent in detached mode that survives docker exec exit
cd /app
nohup setsid python3 -u scripts/bulk_agent.py "${1:-1500}" "${2:-5}" \
    > /tmp/agent_bulk2.log 2>&1 < /dev/null &
disown
echo "launched PID=$!"
