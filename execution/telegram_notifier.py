"""
NEXUS v2.0 - Telegram Notifier
"""
import logging, os, requests
from datetime import datetime
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token=None, chat_id=None, enabled=True, mode_prefix="[PAPER]"):
        self.enabled = enabled
        self.mode_prefix = mode_prefix
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if self.enabled and self.bot_token and self.chat_id:
            logger.info("Telegram notifier ready")
        else:
            self.enabled = False

    def send(self, message):
        if not self.enabled:
            logger.info(f"[DISABLED] {message[:80]}")
            return
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=10)
            if not resp.ok:
                logger.error(f"Telegram send failed: {resp.text[:100]}")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S WIB")

    def _msg(self, lines):
        self.send(chr(10).join(lines))

    def notify_trade_open(self, symbol, direction, entry, sl, tp, score, grade, lot):
        self._msg([self.mode_prefix+" TRADE OPEN", "Symbol: "+symbol, "Dir: "+direction, "Entry: "+str(round(entry,4)), "SL: "+str(round(sl,4)), "TP: "+str(round(tp,4)), "Lot: "+str(round(lot,4)), "Score: "+str(score)+"/100 ["+grade+"]", "Time: "+self._ts()])

    def notify_trade_close(self, symbol, direction, pnl, exit_reason, balance):
        sign = "+" if pnl >= 0 else ""
        self._msg([self.mode_prefix+" TRADE CLOSE", "Symbol: "+symbol, "Dir: "+direction, "PnL: "+sign+str(round(pnl,2))+" USDT", "Reason: "+exit_reason, "Balance: "+str(round(balance,2))+" USDT", "Time: "+self._ts()])

    def notify_circuit_breaker(self, symbol, reason):
        self._msg([self.mode_prefix+" CIRCUIT BREAKER", "Symbol: "+symbol, "Reason: "+reason, "Time: "+self._ts()])

    def notify_daily_summary(self, date, pnl, trades, win_rate, balance):
        sign = "+" if pnl >= 0 else ""
        self._msg([self.mode_prefix+" DAILY SUMMARY", "Date: "+str(date), "PnL: "+sign+str(round(pnl,2))+" USDT", "Trades: "+str(trades), "WinRate: "+str(round(win_rate,1))+"%", "Balance: "+str(round(balance,2))+" USDT"])

    def notify_error(self, component, error):
        self._msg([self.mode_prefix+" ERROR", "Component: "+component, "Error: "+str(error)[:200]])

    def notify_scan(self, symbol, score, grade, action):
        self._msg([self.mode_prefix+" SCAN", "Symbol: "+symbol, "Score: "+str(score)+"/100 ["+grade+"]", "Action: "+action, "Time: "+self._ts()])
