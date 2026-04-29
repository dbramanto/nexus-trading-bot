#!/bin/bash
# Periodic Progress Monitor

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           NEXUS PERIODIC PROGRESS MONITOR                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "🕐 $(date '+%Y-%m-%d %H:%M:%S WIB')"
echo ""

echo "1️⃣  SERVICE STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl is-active nexus-dual.service && echo "Dual Mode: ✅ Running" || echo "Dual Mode: ❌ Stopped"
systemctl is-active nexus.service && echo "Original:  ✅ Running" || echo "Original:  ❌ Stopped"
echo ""

echo "2️⃣  RECENT CYCLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Dual Mode:"
grep "Cycle.*complete" logs/nexus_dual_mode.log | tail -3 | sed 's/.*INFO]/  /'
echo ""
echo "Original:"
grep "Cycle.*Scanned" logs/nexus_v2.log | tail -3 | sed 's/.*INFO] NEXUS:/  /'
echo ""

echo "3️⃣  P2 SCORING ACTIVITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
P2_COUNT=$(grep -c "P2 SCORE" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null)
if [ "$P2_COUNT" -gt 0 ]; then
    echo "✅ P2 Logging Active ($P2_COUNT entries)"
    echo "Last 3 P2 scores:"
    grep "P2 SCORE" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null | tail -3 | sed 's/.*INFO]/  /'
else
    echo "⏳ No P2 logs yet (waiting for next cycle...)"
fi
echo ""

echo "4️⃣  P3 DECISIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
P3_ACCEPT=$(grep -c "P3 ACCEPT" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null)
P3_REJECT=$(grep -c "P3 REJECT" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null)

if [ "$P3_ACCEPT" -gt 0 ] || [ "$P3_REJECT" -gt 0 ]; then
    echo "✅ P3 Logging Active"
    echo "  Accepts: $P3_ACCEPT"
    echo "  Rejects: $P3_REJECT"
    echo ""
    if [ "$P3_REJECT" -gt 0 ]; then
        echo "Top rejection reasons:"
        grep "P3 REJECT" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null | \
            sed 's/.*Reason: //' | sed 's/ | Score.*//' | \
            sort | uniq -c | sort -rn | head -5 | sed 's/^/  /'
    fi
    if [ "$P3_ACCEPT" -gt 0 ]; then
        echo ""
        echo "Recent accepts:"
        grep "P3 ACCEPT" logs/nexus_dual_mode.log logs/nexus_v2.log 2>/dev/null | tail -3 | sed 's/.*INFO]/  /'
    fi
else
    echo "⏳ No P3 logs yet (waiting for next cycle...)"
fi
echo ""

echo "5️⃣  SIGNALS GENERATED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DUAL_SIGNALS=$(grep "MODE A (stable):" logs/nexus_dual_mode.log | tail -1 | grep -o "[0-9]* signals" || echo "0 signals")
ORIG_SIGNALS=$(grep "Signal=" logs/nexus_v2.log | tail -1 | grep -o "Signal=[0-9]*" | cut -d= -f2 || echo "0")

echo "Dual Mode: $DUAL_SIGNALS"
echo "Original:  $ORIG_SIGNALS signals"
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  MONITOR COMPLETE                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
