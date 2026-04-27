#!/bin/bash

echo "=== NEXUS DUAL MODE DEPLOYMENT SCRIPT ==="
echo ""

echo "STEP 1: Identify all running processes"
ps aux | grep -E "forward_test|dual" | grep python | grep -v grep
echo ""

echo "STEP 2: Count before kill"
COUNT=$(ps aux | grep -E "forward_test|dual" | grep python | grep -v grep | wc -l)
echo "Found: $COUNT processes"
echo ""

echo "STEP 3: Kill all processes"
sudo pkill -9 -f forward_test
sudo pkill -9 -f dual
screen -ls | grep nexus_dual | cut -d. -f1 | awk '{print $1}' | xargs -r kill 2>/dev/null
sleep 3
echo "Killed all processes"
echo ""

echo "STEP 4: Verify clean"
REMAINING=$(ps aux | grep -E "forward_test|dual" | grep python | grep -v grep | wc -l)
echo "Remaining processes: $REMAINING"

if [ $REMAINING -ne 0 ]; then
    echo "ERROR: Still have processes running!"
    ps aux | grep -E "forward_test|dual" | grep python | grep -v grep
    exit 1
fi
echo "Clean slate confirmed"
echo ""

echo "STEP 5: Deploy in screen"
cd /home/nexus/nexus_bot
screen -dmS nexus_dual python3 forward_test_runner_dual_optimized.py
sleep 5
echo "Deployed"
echo ""

echo "STEP 6: Verify exactly 1 running"
DEPLOYED=$(ps aux | grep dual_optimized | grep python | grep -v grep | wc -l)
echo "Running processes: $DEPLOYED"

if [ $DEPLOYED -eq 1 ]; then
    echo "SUCCESS: Exactly 1 instance"
    ps aux | grep dual_optimized | grep python | grep -v grep
else
    echo "ERROR: Found $DEPLOYED instances (expected 1)"
    exit 1
fi
echo ""

echo "STEP 7: Check log"
tail -20 logs/nexus_dual_mode.log
