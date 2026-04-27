#!/bin/bash
# Auto-restart dual mode if it crashes

cd /home/nexus/nexus_bot

while true; do
    echo "$(date): Starting NEXUS Dual Mode..." >> logs/runner_watchdog.log
    
    python3 forward_test_runner_dual_optimized.py >> logs/nexus_dual_mode.log 2>&1
    
    EXIT_CODE=$?
    echo "$(date): Process exited with code $EXIT_CODE" >> logs/runner_watchdog.log
    
    # If exit code 0 (normal Ctrl+C), don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date): Clean exit, stopping watchdog" >> logs/runner_watchdog.log
        break
    fi
    
    # Otherwise, wait 30 seconds and restart
    echo "$(date): Restarting in 30 seconds..." >> logs/runner_watchdog.log
    sleep 30
done
