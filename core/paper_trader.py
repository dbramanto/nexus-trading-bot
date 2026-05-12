"""
NEXUS v2.0 - Paper Trading Engine
Simulates trade execution without real capital
"""

import logging
from execution.telegram_notifier import TelegramNotifier
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

class PaperTrader:
    """
    Paper trading engine for risk-free testing
    Tracks positions, calculates PnL, logs all trades
    """
    
    def __init__(self, initial_balance: float = 1000, csv_path: str = 'data/paper_trades_top_gainers.csv'):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.open_positions = {}
        self.closed_trades = []
        self.csv_path_init = csv_path
        
        # Load open positions from CSV on startup (prevents data loss on restart)
        self._load_open_positions_from_csv(csv_path)
    
    def open_position(self, signal: Dict) -> Optional[Dict]:
        """
        Open a paper position
        
        Args:
            signal: Signal dict with symbol, bias, price, sl, tp, etc.
        
        Returns:
            Trade dict or None if already open
        """
        
        symbol = signal['symbol']
        
        # Check if position already open
        if symbol in self.open_positions:
            logger.warning(f"📄 Position already open on {symbol}, skipping")
            return None
        
        trade = {
            'symbol': symbol,
            'side': signal['bias'],
            'entry_price': signal['current_price'],
            'entry_time': datetime.now(),
            'size_usd': signal.get('position_size', 100),
            'leverage': signal.get('leverage', 2),
            'stop_loss': signal['sl_price'],
            'take_profit': signal['tp_price'],
            
            # P1/P2 data for analysis
            'p1_snapshot': signal.get('p1_snapshot', {}),
            'p2_score': signal.get('score', 0),
            'p2_grade': signal.get('grade', 'UNKNOWN'),
            
            # Outcome (filled on close)
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'pnl_usd': None,
            'pnl_pct': None,
            'outcome': None,
        }
        
        self.open_positions[symbol] = trade
        
        # Send entry notification
        try:
            notifier = TelegramNotifier()
            msg = (
                f"🟢 *ENTRY*\n\n"
                f"Symbol: {symbol}\n"
                f"Side: {trade['side']}\n"
                f"Entry: ${trade['entry_price']:.4f}\n"
                f"TP: ${trade['take_profit']:.4f}\n"
                f"SL: ${trade['stop_loss']:.4f}\n"
                f"Score: {trade['p2_score']:.1f}"
            )
            notifier.send(msg)
        except Exception as e:
            logger.warning(f"Entry notification failed: {e}")
        
        logger.info(
            f"📄 OPEN {trade['side']} {symbol} @ ${trade['entry_price']:.4f} | "
            f"SL: ${trade['stop_loss']:.4f} | TP: ${trade['take_profit']:.4f} | "
            f"Score: {trade['p2_score']:.1f}"
        )
        
        return trade
    
    def check_exits(self, current_prices: Dict[str, float], max_hold_hours: int = 4):
        """
        Check exit conditions for all open positions
        
        Args:
            current_prices: Dict of symbol -> current price
            max_hold_hours: Maximum hold time before force exit
        """
        
        symbols_to_close = []
        
        for symbol, trade in self.open_positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Check SL
            if trade['side'] == 'LONG':
                if current_price <= trade['stop_loss']:
                    symbols_to_close.append((symbol, current_price, 'SL_HIT'))
                elif current_price >= trade['take_profit']:
                    symbols_to_close.append((symbol, current_price, 'TP_HIT'))
            else:  # SHORT
                if current_price >= trade['stop_loss']:
                    symbols_to_close.append((symbol, current_price, 'SL_HIT'))
                elif current_price <= trade['take_profit']:
                    symbols_to_close.append((symbol, current_price, 'TP_HIT'))
            
            # Check max hold time (CONDITIONAL)
            # Handle both datetime and pd.Timestamp
            entry_time = trade["entry_time"]
            if hasattr(entry_time, 'to_pydatetime'):
                entry_time = entry_time.to_pydatetime()
            if hasattr(entry_time, 'tzinfo') and entry_time.tzinfo is not None:
                entry_time = entry_time.replace(tzinfo=None)
            duration = (datetime.now() - entry_time).total_seconds() / 3600
            
            # Calculate current P&L
            if trade["side"] == "LONG":
                pnl_pct = ((current_price - trade["entry_price"]) / trade["entry_price"]) * 100 * trade["leverage"]
            else:  # SHORT
                pnl_pct = ((trade["entry_price"] - current_price) / trade["entry_price"]) * 100 * trade["leverage"]
            
            # CONDITIONAL TIME EXIT:
            # If in profit: No time limit (let run to TP)
            # If not in profit: Apply time limit (cut losers)
            # Only add if not already scheduled to close (prevent duplicate!)
            already_closing = any(s[0] == symbol for s in symbols_to_close)
            # Conditional MAX_HOLD:
            # Losing position: exit after 8h (momentum dead!)
            # Winning position: hold up to 48h (let it run!)
            max_hold_dynamic = 8 if pnl_pct <= 0 else max_hold_hours
            if not already_closing and duration >= max_hold_dynamic:
                symbols_to_close.append((symbol, current_price, "MAX_HOLD"))
        
        # Close positions (deduplicate first)
        seen_symbols = set()
        unique_closes = []
        for item in symbols_to_close:
            if item[0] not in seen_symbols:
                seen_symbols.add(item[0])
                unique_closes.append(item)
            else:
                logger.warning(f"⚠️ Duplicate close request for {item[0]} ({item[2]}) - skipping")
        
        for symbol, exit_price, reason in unique_closes:
            self.close_position(symbol, exit_price, reason)
    
    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict:
        """
        Close a position and calculate PnL
        
        Args:
            symbol: Symbol to close
            exit_price: Exit price
            reason: Exit reason (SL_HIT, TP_HIT, MAX_HOLD)
        
        Returns:
            Closed trade dict
        """

        # Guard: Prevent KeyError if position already closed
        if symbol not in self.open_positions:
            logger.warning(f"⚠️ {symbol} not in open_positions - skipping close")
            return {}

        
        trade = self.open_positions.pop(symbol)
        
        # Calculate PnL
        entry = trade['entry_price']
        
        if trade['side'] == 'LONG':
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:  # SHORT
            pnl_pct = ((entry - exit_price) / entry) * 100
        
        # Apply leverage
        pnl_pct *= trade['leverage']
        
        # Calculate USD PnL
        pnl_usd = trade['size_usd'] * (pnl_pct / 100)
        
        # Update balance
        self.balance += pnl_usd
        
        # Fill outcome fields
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now()
        trade['exit_reason'] = reason
        trade['pnl_usd'] = pnl_usd
        trade['pnl_pct'] = pnl_pct
        trade['outcome'] = 'WIN' if pnl_usd > 0 else 'LOSS'
        
        # Hold duration
        duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600
        trade['hold_hours'] = duration
        
        self.closed_trades.append(trade)
        
        # Send exit notification
        try:
            notifier = TelegramNotifier()
            emoji = "✅" if trade['outcome'] == "WIN" else "❌"
            msg = (
                f"{emoji} *EXIT*\n\n"
                f"Symbol: {symbol}\n"
                f"PnL: ${trade['pnl_usd']:+.2f}\n"
                f"Outcome: {trade['outcome']}\n"
                f"Reason: {reason}"
            )
            notifier.send(msg)
        except Exception as e:
            logger.warning(f"Exit notification failed: {e}")
        
        # Log
        emoji = "✅" if pnl_usd > 0 else "❌"
        logger.info(
            f"📄 {emoji} CLOSE {symbol} @ ${exit_price:.4f} | {reason} | "
            f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%)"
        )
        
        self._save_to_csv()  # Auto-save before return
        return trade
    


    def _load_open_positions_from_csv(self, csv_path: str = 'data/paper_trades_top_gainers.csv'):
        """Load open AND closed positions from CSV on startup."""
        import pandas as pd
        import os

        if not os.path.exists(csv_path):
            logger.info("No CSV found, starting fresh")
            return

        try:
            df = pd.read_csv(csv_path)

            if df.empty:
                return

            # ---- LOAD OPEN POSITIONS ----
            open_trades = df[df['outcome'].isna()].copy()
            open_trades = open_trades.drop_duplicates(
                subset=['symbol', 'entry_time'], keep='last'
            )

            loaded_open = 0
            for _, row in open_trades.iterrows():
                symbol = row['symbol']

                if symbol in self.open_positions:
                    continue

                try:
                    entry_time = pd.to_datetime(row['entry_time']).to_pydatetime()
                    if entry_time.tzinfo is not None:
                        entry_time = entry_time.replace(tzinfo=None)
                except:
                    entry_time = datetime.now()

                self.open_positions[symbol] = {
                    'symbol': symbol,
                    'side': row.get('side', 'LONG'),
                    'entry_price': float(row['entry_price']),
                    'entry_time': entry_time,
                    'size_usd': float(row.get('size_usd', 100)),
                    'leverage': float(row.get('leverage', 1)),
                    'stop_loss': float(row['stop_loss']),
                    'take_profit': float(row['take_profit']),
                    'p2_score': float(row.get('p2_score', 0)),
                    'p2_grade': row.get('p2_grade', 'VALID'),
                }
                loaded_open += 1

            logger.info(f"📂 Restored {loaded_open} open positions from CSV")

            # ---- LOAD CLOSED TRADES ----
            closed_df = df[df['outcome'].notna()].copy()
            closed_df = closed_df.drop_duplicates(
                subset=['symbol', 'entry_time'], keep='last'
            )

            loaded_closed = 0
            total_pnl = 0.0

            for _, row in closed_df.iterrows():
                try:
                    trade = {}

                    # String fields
                    for key in ['symbol', 'side', 'outcome', 'exit_reason', 'p2_grade']:
                        trade[key] = row.get(key, '')

                    # Float fields
                    for key in ['entry_price', 'exit_price', 'pnl_usd', 'pnl_pct',
                                'size_usd', 'leverage', 'stop_loss', 'take_profit',
                                'hold_hours', 'p2_score']:
                        try:
                            val = row.get(key)
                            trade[key] = float(val) if val is not None and str(val) != 'nan' else 0.0
                        except:
                            trade[key] = 0.0

                    # Datetime fields
                    for key in ['entry_time', 'exit_time']:
                        try:
                            t = pd.to_datetime(row.get(key))
                            if hasattr(t, 'to_pydatetime'):
                                t = t.to_pydatetime()
                            if hasattr(t, 'tzinfo') and t.tzinfo is not None:
                                t = t.replace(tzinfo=None)
                            trade[key] = t
                        except:
                            trade[key] = None

                    self.closed_trades.append(trade)
                    total_pnl += trade.get('pnl_usd', 0) or 0
                    loaded_closed += 1

                except Exception as e:
                    logger.warning(f"Could not load closed trade row: {e}")

            logger.info(f"📂 Restored {loaded_closed} closed trades from CSV")

            # ---- RESTORE BALANCE ----
            if loaded_closed > 0:
                self.balance = self.initial_balance + total_pnl
                logger.info(f"💰 Balance restored: ${self.balance:,.2f}")

        except Exception as e:
            logger.error(f"Failed to load from CSV: {e}")


    def _save_to_csv(self):
        """Save current trades to CSV file.
        
        SOURCE OF TRUTH:
          - Open positions: self.open_positions (memory)
          - Closed trades: self.closed_trades (memory, loaded from CSV on startup)
          
        NO need to read CSV during save - memory IS the state!
        """
        import pandas as pd

        try:
            csv_path = 'data/paper_trades_top_gainers.csv'
            all_trades = []

            # 1. Add CLOSED trades from MEMORY
            # (These are loaded from CSV on startup + new closes this session)
            for ct in self.closed_trades:
                ct_copy = ct.copy()
                for key in ['entry_time', 'exit_time']:
                    if key in ct_copy and ct_copy[key] is not None:
                        if hasattr(ct_copy[key], 'strftime'):
                            ct_copy[key] = ct_copy[key].strftime('%Y-%m-%d %H:%M:%S.%f')
                all_trades.append(ct_copy)

            # 2. Add OPEN positions from MEMORY
            for symbol, pos in self.open_positions.items():
                all_trades.append({
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side', 'LONG'),
                    'entry_price': pos.get('entry_price'),
                    'exit_price': None,
                    'entry_time': pos.get('entry_time'),
                    'exit_time': None,
                    'exit_reason': None,
                    'size_usd': pos.get('size_usd'),
                    'leverage': pos.get('leverage'),
                    'stop_loss': pos.get('stop_loss'),
                    'take_profit': pos.get('take_profit'),
                    'pnl_usd': None,
                    'pnl_pct': None,
                    'outcome': None,
                    'hold_hours': None,
                    'p2_score': pos.get('p2_score'),
                    'p2_grade': pos.get('p2_grade')
                })

            # NOTE: Do NOT read from CSV here!
            # Memory (closed_trades + open_positions) IS the complete state
            # Reading CSV would cause duplicates since closed_trades = CSV data

            # 3. Convert to DataFrame and save
            df = pd.DataFrame(all_trades)

            # Safety dedup (should not be needed, but defensive)
            if not df.empty and 'symbol' in df.columns and 'entry_time' in df.columns:
                before = len(df)
                df = df.drop_duplicates(subset=['symbol', 'entry_time'], keep='last')
                after = len(df)
                if before != after:
                    logger.warning(f'Removed {before-after} unexpected duplicates')

            df.to_csv(csv_path, index=False)
            logger.info(f"💾 Saved {len(df)} trades to CSV "
                       f"(open: {len(self.open_positions)}, "
                       f"closed: {len(self.closed_trades)})")

        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")


    def get_stats(self) -> Dict:
        """Get trading statistics from memory (loaded from CSV on startup)."""
        import pandas as pd
        import os

        # Primary: use self.closed_trades (loaded from CSV on startup)
        trades = self.closed_trades

        # Fallback: read directly from CSV if memory is empty
        if not trades:
            csv_path = 'data/paper_trades_top_gainers.csv'
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    closed_df = df[df['outcome'].notna()]
                    if not closed_df.empty:
                        trades = closed_df.to_dict('records')
                        logger.info(f"get_stats: Read {len(trades)} trades from CSV (fallback)")
                except Exception as e:
                    logger.warning(f"get_stats CSV fallback failed: {e}")

        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }

        wins = [t for t in trades if t.get('outcome') == 'WIN']
        losses = [t for t in trades if t.get('outcome') == 'LOSS']

        def safe_float(val):
            try:
                return float(val) if val is not None and str(val) != 'nan' else 0.0
            except:
                return 0.0

        total_pnl = sum(safe_float(t.get('pnl_usd')) for t in trades)
        avg_win = sum(safe_float(t.get('pnl_usd')) for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(safe_float(t.get('pnl_usd')) for t in losses) / len(losses) if losses else 0.0

        return {
            'total_trades': len(trades),
            'win_rate': (len(wins) / len(trades)) * 100,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }

