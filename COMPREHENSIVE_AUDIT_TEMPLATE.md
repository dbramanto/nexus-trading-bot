# COMPREHENSIVE AUDIT TEMPLATE
**Created:** May 2, 2026
**Lesson:** Class rename caused crash
**Proven:** Audit saves time + eliminates risk

## WHY IT MATTERS
Without: 20min, 2 commits, crash, rework
With: 15min, 1 commit, works first time
NET: Saves 5min + zero risk

## CHECKLIST
1. IDENTIFY: What changes
2. FIND: grep -rn Pattern
3. CATEGORIZE: Each reference
4. IMPACT: What breaks
5. FIX ALL: Atomically
6. VERIFY: grep = 0 results

## EXAMPLE
WRONG: Change one thing, commit, crash
RIGHT: grep ALL, fix ALL, verify 0, commit

## PRINCIPLES
1. grep mandatory
2. Fix atomically
3. Verify zero
4. Test before commit

**Status:** ACTIVE for all work