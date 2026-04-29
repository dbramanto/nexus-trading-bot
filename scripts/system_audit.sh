#!/bin/bash
# NEXUS Complete System Audit
# Run this BEFORE any troubleshooting!

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           NEXUS COMPLETE SYSTEM AUDIT                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "1️⃣  ALL RUNNING PROCESSES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ps aux | grep -E "nexus|forward_test|dual" | grep python | grep -v grep
echo ""

echo "2️⃣  SYSTEMD SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl list-units --all | grep nexus
echo ""

echo "3️⃣  ALL LOG FILES (with size & timestamp)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lht logs/*.log 2>/dev/null
echo ""

echo "4️⃣  CONFIG FILES TIMELINE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lh config/strategy_config.py core/p3_manager/strategy_logic.py
echo ""

echo "5️⃣  PROCESS START TIMES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ps aux | grep -E "forward_test|dual" | grep python | grep -v grep | while read line; do
    pid=$(echo $line | awk '{print $2}')
    echo "PID $pid:"
    ps -p $pid -o lstart= 2>/dev/null
done
echo ""

echo "6️⃣  CONFIGURATION SYNC CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CONFIG_TIME=$(stat -c %Y config/strategy_config.py 2>/dev/null)
echo "Config last modified: $(date -d @$CONFIG_TIME 2>/dev/null)"
echo ""
ps aux | grep -E "forward_test|dual" | grep python | grep -v grep | while read line; do
    pid=$(echo $line | awk '{print $2}')
    START_TIME=$(stat -c %Y /proc/$pid 2>/dev/null)
    if [ -n "$START_TIME" ] && [ -n "$CONFIG_TIME" ]; then
        if [ $START_TIME -lt $CONFIG_TIME ]; then
            echo "⚠️  PID $pid: STARTED BEFORE CONFIG CHANGE - RESTART NEEDED!"
        else
            echo "✅ PID $pid: Using current config"
        fi
    fi
done
echo ""

echo "7️⃣  RECENT ACTIVITY (last 5 lines per log)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for log in logs/*.log; do
    if [ -f "$log" ]; then
        echo "--- $(basename $log) ---"
        tail -5 "$log" 2>/dev/null
        echo ""
    fi
done

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    AUDIT COMPLETE                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
