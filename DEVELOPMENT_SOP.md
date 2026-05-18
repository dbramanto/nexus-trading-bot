# NEXUS DEVELOPMENT SOP

## SETIAP COMMIT = WAJIB RESTART!

```bash
git add .
git commit -m "..."
git push origin master
sudo systemctl restart nexus-dual.service
sleep 8
systemctl is-active nexus-dual.service
tail -5 logs/nexus_dual_mode.log
```

## WHY:
- Old code runs in memory until restart
- Fix committed ≠ Fix active!
- Evidence: P1 empty May 14 15:10-23:30
  because service not restarted after fix!
