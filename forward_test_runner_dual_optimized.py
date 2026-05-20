"""
NEXUS v2.0 - LONG-only Momentum Trading with Telegram Notifications
Single data fetch, shared P1 processing
"""

import sys
sys.path.insert(0, '/home/nexus/nexus_bot')

import time
import logging
from datetime import datetime
import pandas as pd

from config.strategy_config import NexusConfig, TopGainerMode
from core.top_gainer_scanner import TopGainerScanner
from core.paper_trader import PaperTrader
from core.p1_analyst import build_indicator_manager
from core.p2_supervisor.scoring_engine import ScoringEngine
from core.p3_manager.strategy_logic import StrategyLogic
from core.p4_auditor.trade_logger import TradeLogger
from execution.binance_client import BinanceClientWrapper
from execution.telegram_notifier import TelegramNotifier

import logging.handlers as _lh
import os as _os2
_os2.makedirs('logs', exist_ok=True)
_rfh = _lh.RotatingFileHandler(
    'logs/nexus_dual_mode.log', maxBytes=10*1024*1024, backupCount=5
)
_rfh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), _rfh]
)

logger = logging.getLogger(__name__)

class NexusRunner:
    """
    OPTIMIZED: Single data fetch, shared P1 processing
    """
    
    def __init__(self):
        self.config = NexusConfig()
        self.tg_config = TopGainerMode()
        
        self.client = BinanceClientWrapper(testnet=self.config.trading.api_testnet)
        self.telegram = TelegramNotifier(enabled=True, mode_prefix="[NEXUS]")
        self.p1 = build_indicator_manager()
        self.p2 = ScoringEngine(self.config)
        self.p3 = StrategyLogic(self.config)
        self.p4_log = TradeLogger()
        
        # Stable symbols (feature disabled)
        # Stable trading disabled (zero trades in 68+ trades)
# [LEGACY]         self.stable_symbols = []  # Stable trading disabled (zero activity)
        
        # Top gainer symbols
        self.tg_scanner = TopGainerScanner()
        self.tg_symbols = []
        self.tg_last_refresh = None
        # Separate traders for fair A/B comparison
# [LEGACY]         self.stable_trader = None  # Stable trading disabled
        self.tg_trader = PaperTrader(initial_balance=1000)      # Top Gainers: Top gainers
        
        self.cycle_count = 0
        self.last_hourly_check = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.last_daily_check = datetime.now().date()
        
        logger.info("="*80)
        logger.info("NEXUS NEXUS v2.0 INITIALIZED (OPTIMIZED)")
        logger.info("="*80)
# [LEGACY]         logger.info(f"Stable: {len(self.stable_symbols)} stable coins")
        logger.info(f"Top Gainers: Top {self.tg_config.top_n} gainers (paper)")
        logger.info("="*80)
        
        # Send startup notification
        self.telegram.send(
            "🚀 *NEXUS NEXUS v2.0 STARTED*\n\n"
# [LEGACY]             f"Stable: {len(self.stable_symbols)} stable coins (shadow)\n"
            f"Top Gainers: Top {self.tg_config.top_n} gainers (paper)\n"
            f"Cycle: Every 15 minutes\n"
            f"Deployed: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}"
        )
    
    def _fetch_df(self, symbol, interval="15m", limit=100):
        """Fetch and convert klines to DataFrame"""
        klines = self.client.get_futures_candles(symbol, interval, limit)
        
        rows = [
            {
                "timestamp": pd.to_datetime(k[0], unit="ms"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            }
            for k in klines
        ]
        
        df = pd.DataFrame(rows).set_index("timestamp")
        return df
    
    def refresh_top_gainers(self):
        """Refresh near-high list every cycle (15 min)
        Near-high = dynamic! Must check frequently!
        A coin can make new high anytime!
        """
        should_refresh = (
            self.tg_last_refresh is None or
            (datetime.now() - self.tg_last_refresh
             ).total_seconds() >= 900  # 15 min = every cycle!
        )
        
        if should_refresh:
            logger.info("🔄 Refreshing top gainers...")
            self.tg_symbols = self.tg_scanner.get_top_gainers(
                top_n=self.tg_config.top_n,
                min_change=self.tg_config.min_24h_change,
                max_change=self.tg_config.max_24h_change,
                min_volume_usd=self.tg_config.min_volume_usd
            )
            self.tg_last_refresh = datetime.now()

            # NEAR-HIGH GATE: skip if too few candidates!
            # Data: 8 candidates = poor quality = losses!
            # Need minimum 10 for good signal quality!
            if len(self.tg_symbols) < 5:
                logger.warning(
                    f"⚠️ Only {len(self.tg_symbols)} candidates "
                    f"= market too weak! Skip this cycle!")
                self.tg_symbols = []  # No trades this cycle!
            elif len(self.tg_symbols) < 8:
                logger.warning(
                    f"⚠️ Low candidates ({len(self.tg_symbols)}) "
                    f"= cautious mode!")

            logger.info(f"✓ {len(self.tg_symbols)} top gainers found")
    
    def run_cycle(self):
        """
        OPTIMIZED CYCLE:
        1. Get unique symbols (stable + top gainers)
        2. Fetch data ONCE per symbol
        3. P1 analyze ONCE per symbol
        4. Route to Stable and/or Top Gainers
        """
        self.cycle_count += 1
        
        logger.info("")
        logger.info("="*80)
        self._exited_this_cycle = set()  # Reset per cycle
        
        # DATA COLLECTION (not filters yet - need 50+ trades first!)
        self._first_seen = {}    # {symbol: first_seen_timestamp}
        self._sl_exits = {}      # {symbol: last_sl_exit_timestamp}
        logger.info(f"CYCLE {self.cycle_count} | {datetime.now().strftime('%H:%M:%S WIB')}")
        logger.info("="*80)
        
        # Refresh top gainers if needed
        self.refresh_top_gainers()
        
        # === OPTIMIZATION: Get unique symbols ===
        all_symbols = set(self.tg_symbols)  # Top Gainers only
# [LEGACY]         logger.info(f"📊 Scanning {len(all_symbols)} unique symbols (stable={len(self.stable_symbols)}, tg={len(self.tg_symbols)}, overlap={len(self.stable_symbols)+len(self.tg_symbols)-len(all_symbols)})")
        
        # Counters
        stable_signals = 0
        tg_signals = 0
        
        # Check exits for BOTH traders
        # Stable: Stable symbols
        # Stable exit check disabled
        
        # Top Gainers: Top gainers
        if self.tg_trader.open_positions:
            # Build current_prices from SCANNER
            # (kline close = may be stale!)
            current_prices = {}
            for sym in self.tg_trader.open_positions.keys():
                try:
                    klines = self.client.get_futures_candles(sym, "15m", 1)
                    if klines:
                        current_prices[sym] = float(klines[-1][4])
                except:
                    pass
            # Run exits - capture closed symbols for re-entry block
            closed_before = set(t['symbol'] 
                for t in self.tg_trader.closed_trades)

            # CRITICAL FIX: Fetch REAL-TIME prices
            # for open positions before SL/TP check!
            # kline[-1][4] = stale (up to 15min old!)
            # Real-time = prevent SL miss!
            try:
                import requests as _rt_req
                _open_syms = list(
                    self.tg_trader.open_positions.keys())
                if _open_syms:
                    _rt_r = _rt_req.get(
                        'https://fapi.binance.com/fapi/v1/ticker/price',
                        timeout=5)
                    _rt_prices = {
                        t['symbol']: float(t['price'])
                        for t in _rt_r.json()
                        if t['symbol'] in _open_syms
                    }
                    # Override with real-time!
                    current_prices.update(_rt_prices)
                    logger.debug(
                        f'📡 RT prices fetched for '
                        f'{len(_rt_prices)} positions')
            except Exception as _rt_e:
                logger.warning(
                    f'⚠️ RT price fetch failed: {_rt_e}')
                # Fallback: kline price
                # = Better than nothing!

            self.tg_trader.check_exits(current_prices, max_hold_hours=48)
            closed_after = set(t['symbol'] 
                for t in self.tg_trader.closed_trades)
            
            # Add newly closed symbols to exited_this_cycle
            newly_closed = closed_after - closed_before
            if newly_closed:
                self._exited_this_cycle.update(newly_closed)
                for sym in newly_closed:
                    logger.info(f"🚫 {sym} closed this cycle - blocked from re-entry")
        
        # === SINGLE LOOP: Fetch + Process ONCE per symbol ===
        for symbol in all_symbols:
            try:
                # 1. Fetch data ONCE
                df = self._fetch_df(symbol, "15m", 100)

                # ================================================
                # H1 STRUCTURE FILTER
                # Top gainer confirmed → Check H1 alignment
                # Only trade if H1 structure is BULLISH!
                # ================================================
                try:
                    df_h1 = self._fetch_df(symbol, "1h", 50)
                    if df_h1 is not None and len(df_h1) >= 10:
                        # Simple H1 check using HA + trend
                        # HA direction from last 3 H1 candles
                        h1_close = df_h1['close'].values
                        h1_open = df_h1['open'].values
                        
                        # Heiken Ashi H1
                        ha_close = (h1_open[-1] + df_h1['high'].values[-1] +
                                   df_h1['low'].values[-1] + h1_close[-1]) / 4
                        ha_open = (h1_open[-2] + h1_close[-2]) / 2
                        
                        h1_bullish = ha_close > ha_open
                        
                        # Also check H1 trend: price above MA20
                        if len(h1_close) >= 20:
                            h1_ma20 = sum(h1_close[-20:]) / 20
                            h1_above_ma = h1_close[-1] > h1_ma20
                        else:
                            h1_above_ma = True  # Default allow
                        
                        # H1 aligned = HA bullish AND above MA20
                        h1_aligned = h1_bullish and h1_above_ma
                        
                        if not h1_aligned:
                            logger.info(
                                f"📊 H1 FILTER: {symbol} rejected "
                                f"(H1 HA={'BULL' if h1_bullish else 'BEAR'} "
                                f"MA={'above' if h1_above_ma else 'below'})")
                            continue
                        else:
                            logger.debug(
                                f"📊 H1 FILTER: {symbol} aligned ✅ "
                                f"(HA={'BULL'} MA={'above' if h1_above_ma else 'below'})")
                except Exception as e:
                    logger.warning(f"H1 filter error {symbol}: {e}")
                    # On error: allow through (don't block on H1 failure)
                
                # 2. Set context for orderflow modules
                # (CVD, Funding, OI, Orderbook need client + symbol!)
                for module in self.p1._modules:
                    if hasattr(module, 'set_context'):
                        module.set_context(symbol, self.client)

                # 3. P1 analyze ONCE (expensive!)
                p1_rep = self.p1.run_all(df, self.config, symbol=symbol)
                # Inject symbol for P2 context
                # 3. P2 score ONCE
                ctx = self.p2.score(p1_rep.get("modules", p1_rep))
                
                # 4. P3 evaluate ONCE
                dec = self.p3.evaluate(ctx, circuit_breaker_active=False)
                
                # Extract common data

                # === LONG-ONLY MODE (Strategic Decision) ===
                # Skip BEARISH signals (SHORT not aligned with top gainer momentum)
                # See STRATEGY_CLARITY.md for rationale
                if ctx.get("bias") == "BEARISH":
                    logger.info(f"⏭️  {symbol} SHORT skipped (LONG-only momentum strategy)")
                    continue

                action = dec.get('action', 'NO_TRADE')
                score = ctx.get('score', 0)
                grade = ctx.get('grade', 'NO_TRADE')
                current_price = float(df.iloc[-1]['close'])
                
                # === Stable: If symbol in stable list ===

                # === SHADOW LOGGING FOR ML ===
                self.p4_log.log_shadow(
                    symbol=symbol,
                    direction=action if action != 'WAIT' else 'N/A',
                    potential_entry=current_price,
                    potential_sl=0,
                    potential_tp=0,
                    potential_lot=0,
                    score=score,
                    grade=grade,
                    bias=ctx.get('bias', 'NEUTRAL'),
                    reject_reason=dec.get('reason', 'NO_TRADE') if action == 'WAIT' else '',
                    p1_snapshot=ctx.get('p1_snapshot', {}),
                    ml_features={
                        'regime': ctx.get('regime', 'UNKNOWN'),
                        'threshold_used': ctx.get('threshold_used', 0),
                        'score_t0': ctx.get('tier_breakdown', {}).get('t0', 0),
                        'score_t1': ctx.get('tier_breakdown', {}).get('t1', 0),
                        'score_t2': ctx.get('tier_breakdown', {}).get('t2', 0),
                    },
                    score_breakdown=ctx.get('tier_breakdown', {}),
                    bias_reason={}
                )

                # Stable entry logic disabled
                if symbol in self.tg_symbols:
                    
                    # DATA COLLECTION: Track freshness
                    # (Not used as filter yet - collecting data!)
                    if symbol not in self._first_seen:
                        self._first_seen[symbol] = datetime.now()
                        logger.info(
                            f"🆕 FIRST_SEEN: {symbol} "
                            f"@ {datetime.now().strftime('%H:%M')}")

                    # Skip if symbol exited this cycle (no re-entry!)
                    if symbol in getattr(self, '_exited_this_cycle', set()):
                        logger.info(f"⏭️  {symbol} exited this cycle - skip re-entry")
                        continue

                    # Skip if position already open
                    if symbol in self.tg_trader.open_positions:
                        continue

                    # Max positions = 3 (data: max3 WR22% vs max5 WR20%!)
                    if len(self.tg_trader.open_positions) >= 3:
                        logger.info(f"⛔ Max 3 positions - skip {symbol}")
                        continue


                    # ============================================
                    # ENTRY QUALITY FILTERS (Traffic Lights!)
                    # Must pass ALL before entry!
                    # ============================================
                    if action in ['LONG', 'SHORT']:
                        p1_mod = p1_rep.get('modules', {})
                        _basic = p1_mod.get('basic_indicators', {})
                        _ha = p1_mod.get('heiken_ashi', {})
                        
                        _vol = float(_basic.get('volume_ratio', 0) or 0)
                        _rsi = float(_basic.get('rsi_value', 50) or 50)
                        _ha_str = str(_ha.get('ha_strength', '') or '')
                        
                        _reject = None
                        
                        # 🔴 FILTER 1: Volume >= 0.5x
                        if _vol > 0 and _vol < 0.5:
                            _reject = f"Vol:{_vol:.2f}x < 0.5x (weak)"
                        
                        # RSI filter REMOVED by data:
                        # WIN RSI 72.5 vs LOSS RSI 70.2 = not decisive!
                        # RSI>80 in crypto = STRONG MOMENTUM, not reversal!
                        # Live test: RSI>80 coins = 62.5% continuation!
                        # AIAUSDT RSI 88.6% = +59.8% 24h = trending!
                        # = Keeping RSI filter blocks best entries!
                        # elif _rsi > 80:  # REMOVED - not crypto-appropriate
                        #     _reject = f"RSI:{_rsi:.0f} > 80 (overbought)" 
                        
                        # HA WEAK filter REMOVED by data:
                        # HA WEAK avg gain +16.9% vs STRONG +9.8%!
                        # WEAK outperforms STRONG in top gainers!
                        # Reason: Pump candles = small HA body = normal!
                        # Top gainers = volatile = HA WEAK expected!
                        # = Filter was blocking valid pump entries!
                        # elif _ha_str == 'WEAK':  # REMOVED
                        #     _reject = "HA:WEAK"  # not crypto-appropriate
                        
                        if _reject:
                            logger.info(
                                f"🔴 ENTRY FILTER: {symbol} "
                                f"rejected | {_reject}")
                            continue
                        else:
                            logger.debug(
                                f"🟢 ENTRY FILTER: {symbol} passed "
                                f"Vol:{_vol:.2f}x RSI:{_rsi:.0f} "
                                f"HA:{_ha_str}")
                    
                        tg_signals += 1
                        
                        # Calculate SL/TP
                        # Define leverage before SL/TP calculation!
                        leverage = 3 if score >= 70 else (2 if score >= 65 else 1)

                        sl_pct = self.tg_config.stop_loss_pct / 100
                        tp_pct = self.tg_config.take_profit_pct / 100
                        
                        if action == 'LONG':
                            sl = current_price * (1 - sl_pct / leverage)
                            tp = current_price * (1 + tp_pct / leverage)
                            bias = 'LONG'
                        else:
                            sl = current_price * (1 + sl_pct / leverage)
                            tp = current_price * (1 - tp_pct / leverage)
                            bias = 'SHORT'
                        
                        # Open paper position
                        signal = {
                            'symbol': symbol,
                            'bias': bias,
                            'current_price': current_price,
                            'sl_price': sl,
                            'tp_price': tp,
                            # === ADAPTIVE POSITION SIZING ===
                            # Conservative: 5% of balance, inverse leverage
                            'current_balance': self.tg_trader.balance,
                            'target_position_pct': 0.05,
                            'target_position': self.tg_trader.balance * 0.05,
                            'adaptive_leverage': 3 if score >= 70 else (2 if score >= 65 else 1),
                            'position_size': (
                                self.tg_trader.balance * 0.10
                                if score >= 70
                                else self.tg_trader.balance * 0.05
                            ),
                            'leverage': 3 if score >= 70 else (2 if score >= 65 else 1),
                            'p1_snapshot': p1_rep.get('modules',
                                p1_rep if isinstance(p1_rep, dict)
                                else {}),
                            'score': score,
                            'grade': grade,
                        }
                        
                        signal_result = self.tg_trader.open_position(signal)
                        
                        # LOG P1 details at entry
                        if signal_result:
                            p1_mod = p1_rep.get('modules', {})
                            basic = p1_mod.get('basic_indicators',{})
                            ha = p1_mod.get('heiken_ashi',{})
                            mom = p1_mod.get('momentum_classifier',{})
                            pd_zone = p1_mod.get('premium_discount',{})
                            
                            rsi = basic.get('rsi_value', 0)
                            vol = basic.get('volume_ratio', 0)
                            ha_dir = ha.get('ha_direction','?')
                            ha_str = ha.get('ha_strength','?')
                            momentum = mom.get('momentum','?')
                            zone = pd_zone.get('price_zone','?')
                            fresh_h = (
                                datetime.now() - 
                                self._first_seen.get(symbol, datetime.now())
                            ).total_seconds()/3600
                            
                            logger.info(
                                f"📊 ENTRY_DATA | {symbol} | "
                                f"RSI:{rsi:.0f} "
                                f"Vol:{vol:.2f}x "
                                f"HA:{ha_dir}/{ha_str} "
                                f"Zone:{zone} "
                                f"Mom:{momentum} "
                                f"Fresh:{fresh_h:.1f}h "
                                f"Score:{score:.0f}")

                            # M15 STRUCTURE LOG (data collection only!)
                            try:
                                _vols = df['volume'].tolist()
                                _lows = df['low'].tolist()
                                _bodies = []
                                for _si in range(
                                    max(0,len(df)-5), len(df)):
                                    _o = df['open'].iloc[_si]
                                    _c = df['close'].iloc[_si]
                                    _h = df['high'].iloc[_si]
                                    _l = df['low'].iloc[_si]
                                    _rng = _h - _l
                                    _b = abs(_c - _o)
                                    _bodies.append(
                                        _b/_rng if _rng>0 else 0)

                                _b_trend = 'INC'                                     if len(_bodies)>=2 and                                     _bodies[-1] > _bodies[0]                                     else 'DEC'

                                _avg_vol_prev = sum(
                                    _vols[-10:-5])/5                                     if len(_vols)>=10 else 1
                                _avg_vol_curr = sum(
                                    _vols[-5:])/5                                     if len(_vols)>=5 else 1
                                _v_trend = 'INC'                                     if _avg_vol_curr >                                     _avg_vol_prev else 'DEC'

                                _sl = []
                                for _si in range(2, len(_lows)-2):
                                    if all(_lows[_si]<=_lows[_si-j]
                                           for j in range(1,3)) and                                       all(_lows[_si]<=_lows[_si+j]
                                           for j in range(1,3)):
                                        _sl.append(_lows[_si])
                                _hl = len(_sl)>=2 and                                       _sl[-1] > _sl[-2]

                                _avg_b = sum(_bodies)/len(_bodies)                                         if _bodies else 0

                                logger.info(
                                    f"📊 M15_STRUCT | {symbol} |"
                                    f" Body:{_b_trend}"
                                    f" Vol:{_v_trend}"
                                    f" HL:{_hl}"
                                    f" AvgBody:{_avg_b:.2f}"
                                    f" SwingLows:{len(_sl)}")
                            except Exception as _me:
                                logger.debug(
                                    f"M15 struct error: {_me}")
                        
                        # ENTRY notification
                        sl_dist_pct = abs(current_price - sl) / current_price * 100
                        tp_dist_pct = abs(tp - current_price) / current_price * 100
                        rr = tp_dist_pct / sl_dist_pct if sl_dist_pct > 0 else 0
                        size = signal.get('position_size', 0)
                        lev = signal.get('leverage', 2)
                        if signal_result:
                            self.telegram.send(
                                f"🟢 *ENTRY*\n\n"
                                f"Symbol:  {symbol}\n"
                                f"Side:    {bias} | Score: {score:.0f} {grade}\n\n"
                                f"Entry:   ${current_price:.6f}\n"
                                f"SL:      ${sl:.6f} (-{sl_dist_pct:.2f}% price)\n"
                                f"TP:      ${tp:.6f} (+{tp_dist_pct:.2f}% price)\n\n"
                                f"Size:    ${size:.2f} | Lev: {lev}x | R:R 1:{rr:.2f}\n"
                                f"Time:    {datetime.now().strftime('%d %b %H:%M WIB')}\n"
                                f"Balance: ${self.tg_trader.balance:.2f}"
                            )
            
            except Exception as e:
                import traceback
                logger.error(f"Error processing {symbol}: {e}")
                logger.error(traceback.format_exc())
                continue
        
        # Stats
        # stable_stats disabled
        tg_stats = self.tg_trader.get_stats()
        
        logger.info("")
        logger.info(f"✓ Cycle {self.cycle_count} complete:")
        logger.info(f"  📊 TRADES: {tg_signals} new | Open={len(self.tg_trader.open_positions)} Closed={tg_stats['total_trades']} WR={tg_stats['win_rate']:.1f}% PnL=${tg_stats['total_pnl']:+.2f}")

        # LOG: Open position health every cycle
        if self.tg_trader.open_positions:
            import requests as _req
            for _sym, _pos in self.tg_trader.open_positions.items():
                try:
                    _r = _req.get(
                        f"https://fapi.binance.com/fapi/v1/ticker/price"
                        f"?symbol={_sym}", timeout=3)
                    _curr = float(_r.json()['price'])
                    _entry = float(_pos['entry_price'])
                    _lev = float(_pos.get('leverage', 2))
                    _size = float(_pos.get('size_usd', 50))
                    _pnl_pct = (_curr-_entry)/_entry*100*_lev
                    _pnl_usd = _size*(_pnl_pct/100)
                    _hold = (datetime.now() -
                            _pos['entry_time']).total_seconds()/3600
                    _sl = float(_pos['stop_loss'])
                    _sl_tag = "🔒" if _sl >= _entry*0.999 else "📍"
                    logger.info(
                        f"  ⏳ MONITOR | {_sym} | "
                        f"Hold:{_hold:.1f}h | "
                        f"PnL:${_pnl_usd:+.2f}({_pnl_pct:+.1f}%) | "
                        f"SL:{_sl_tag}${_sl:.5f}")
                except Exception as _e:
                    logger.debug(f"Monitor error {_sym}: {_e}")

        logger.info("="*80)
        
        # Hourly summary via Telegram
    

    def send_daily_report(self):
        """Send daily report at 07:00 WIB"""
        import pandas as pd
        
        tg_stats = self.tg_trader.get_stats()
        current_date = datetime.now().date()
        
        try:
            df = pd.read_csv('data/paper_trades_top_gainers.csv')
            df['entry_time'] = pd.to_datetime(df['entry_time'], format='mixed')
            yesterday = current_date - pd.Timedelta(days=1)
            yesterday_trades = df[df['entry_time'].dt.date == yesterday]
            yesterday_closed = yesterday_trades[yesterday_trades['outcome'].notna()]
            
            if len(yesterday_closed) > 0:
                y_wins = len(yesterday_closed[yesterday_closed['outcome']=='WIN'])
                y_wr = (y_wins/len(yesterday_closed))*100
                y_pnl = yesterday_closed['pnl_usd'].sum()
                yesterday_summary = f"📅 Yesterday: {len(yesterday_closed)} trades | WR {y_wr:.1f}% | PnL ${y_pnl:+.2f}\n\n"
            else:
                yesterday_summary = "📅 Yesterday: No closed trades\n\n"
        except:
            yesterday_summary = ""
        
        # Calculate WIN/LOSS breakdown
        wins = [t for t in self.tg_trader.closed_trades if t['outcome'] == 'WIN']
        losses = [t for t in self.tg_trader.closed_trades if t['outcome'] == 'LOSS']
        
        # Today's best/worst
        best_trade = ""
        worst_trade = ""
        today_summary = ""
        try:
            df_today = pd.read_csv('data/paper_trades_top_gainers.csv')
            df_today['entry_time'] = pd.to_datetime(
                df_today['entry_time'], format='mixed')
            today_closed = df_today[
                (df_today['entry_time'].dt.date == current_date) &
                (df_today['outcome'].notna())
            ]
            if len(today_closed) > 0:
                t_wins = len(today_closed[today_closed['outcome']=='WIN'])
                t_wr = t_wins/len(today_closed)*100
                t_pnl = today_closed['pnl_usd'].sum()
                today_summary = (
                    f"📅 *Today: {len(today_closed)} trades | "
                    f"WR {t_wr:.1f}% | ${t_pnl:+.2f}*\n\n"
                )
                best = today_closed.loc[today_closed['pnl_usd'].idxmax()]
                worst = today_closed.loc[today_closed['pnl_usd'].idxmin()]
                best_trade = (
                    f"\n💎 Best:  {best['symbol']} "
                    f"${best['pnl_usd']:+.2f} "
                    f"({best['hold_hours']:.1f}h, "
                    f"Score {best['p2_score']:.0f})"
                )
                worst_trade = (
                    f"\n💀 Worst: {worst['symbol']} "
                    f"${worst['pnl_usd']:+.2f} "
                    f"({worst['hold_hours']:.1f}h, "
                    f"Score {worst['p2_score']:.0f})"
                )
        except Exception as e:
            logger.warning(f"Daily stats error: {e}")

        bal = self.tg_trader.balance
        total_pct = (bal - 1000.0) / 1000.0 * 100

        self.telegram.send(
            f"☀️ *Daily Report - "
            f"{datetime.now().strftime('%d %b %Y')}*\n\n"
            f"💰 Balance: ${bal:.2f} ({total_pct:+.1f}%)\n\n"
            f"{today_summary}"
            f"{yesterday_summary}"
            f"📊 *Overall*\n"
            f"  Total: {tg_stats['total_trades']} | "
            f"WIN: {len(wins)} | LOSS: {len(losses)}\n"
            f"  WR: {tg_stats['win_rate']:.1f}% | "
            f"PnL: ${tg_stats['total_pnl']:+.2f}\n"
            f"  Avg W: ${tg_stats['avg_win']:+.2f} | "
            f"Avg L: ${tg_stats['avg_loss']:+.2f}"
            f"{best_trade}"
            f"{worst_trade}"
        )
        logger.info("📰 Daily report sent")

    def send_hourly_report(self):
        """Send hourly report at top of hour"""
        tg_stats = self.tg_trader.get_stats()
        
        # Calculate WIN/LOSS breakdown
        wins = [t for t in self.tg_trader.closed_trades if t['outcome'] == 'WIN']
        losses = [t for t in self.tg_trader.closed_trades if t['outcome'] == 'LOSS']
        
        # Open positions detail
        open_lines = ""
        for sym, pos in list(self.tg_trader.open_positions.items())[:5]:
            try:
                entry_t = pos.get('entry_time')
                if isinstance(entry_t, str):
                    from datetime import datetime as dt2
                    entry_t = dt2.fromisoformat(entry_t)
                hold_h = (datetime.now() - entry_t).total_seconds()/3600
                sc = pos.get('p2_score', pos.get('score', 0))
                open_lines += f"  ⏳ {sym} Score:{sc:.0f} {hold_h:.1f}h\n"
            except:
                open_lines += f"  ⏳ {sym}\n"

        # Recent closes
        recent_lines = ""
        recent = sorted(
            self.tg_trader.closed_trades,
            key=lambda x: x.get('exit_time',''), reverse=True
        )[:3]
        for t in recent:
            emoji = "✅" if t['outcome']=='WIN' else "❌"
            recent_lines += (
                f"  {emoji} {t['symbol']} "
                f"{t.get('exit_reason','')} "
                f"${t.get('pnl_usd',0):+.2f} "
                f"({t.get('hold_hours',0):.1f}h)\n"
            )

        bal = self.tg_trader.balance
        session_pct = (bal - 1000.0) / 1000.0 * 100

        msg = (
            f"📈 *Hourly Summary*\n\n"
            f"🕐 {datetime.now().strftime('%H:%M WIB')} | sched: {datetime.now().replace(minute=0,second=0).strftime('%H:00 WIB')}" 
            f" | {datetime.now().strftime('%d %b %Y')}\n\n"
            f"(hour: {datetime.now().strftime('%H:00')}) | "
            f"{datetime.now().strftime('%d %b %Y')}\n\n"
            f"💰 Balance: ${bal:.2f} ({session_pct:+.1f}%)\n\n"
            f"📊 Overall: {tg_stats['total_trades']} trades | "
            f"WR {tg_stats['win_rate']:.1f}% | "
            f"${tg_stats['total_pnl']:+.2f}\n"
            f"   WIN: {len(wins)} | LOSS: {len(losses)}\n"
            f"   Avg W: ${tg_stats['avg_win']:+.2f} | "
            f"Avg L: ${tg_stats['avg_loss']:+.2f}\n"
        )
        if recent_lines:
            msg += f"\n🕐 Recent:\n{recent_lines}"
        if open_lines:
            msg += f"\n🔄 Open ({len(self.tg_trader.open_positions)}):\n{open_lines}"
        else:
            msg += f"\n🔄 Open: 0"

        self.telegram.send(msg)
        logger.info("📊 Hourly report sent")

    def run(self):
        """Main loop"""
        logger.info("🚀 Starting NEXUS NEXUS (OPTIMIZED)...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        try:
            while True:
                self.run_cycle()

                # Check hourly BEFORE sleep
                now = datetime.now()
                current_hour = now.replace(
                    minute=0, second=0, microsecond=0)
                if current_hour > self.last_hourly_check:
                    self.last_hourly_check = current_hour
                    self.send_hourly_report()

                # Check daily BEFORE sleep
                current_date = now.date()
                if current_date > self.last_daily_check and                    now.hour >= 7:
                    self.last_daily_check = current_date
                    self.send_daily_report()

                # Smart sleep: until next 15-min boundary
                # Ensures hourly fires EXACTLY on the hour!
                # e.g. 20:59 → sleep 1min → 21:00 → hourly! ✅
                minutes = now.minute
                seconds = now.second
                next_mark = ((minutes // 15) + 1) * 15
                sleep_secs = max(
                    30,
                    min((next_mark - minutes)*60 - seconds, 900)
                )
                # Display label: :60 means :00 next hour
                display = next_mark if next_mark < 60 else 0
                logger.info(
                    f"⏳ Sleeping {sleep_secs}s "
                    f"(next cycle at :{display:02d})")
                time.sleep(sleep_secs)

        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("="*80)
            logger.info("STOPPING NEXUS v2.0")
            logger.info("="*80)
            
            stats = self.paper_trader.get_stats()
            logger.info(f"Paper Trading Results:")
            logger.info(f"  Total trades: {stats['total_trades']}")
            logger.info(f"  Win rate: {stats['win_rate']:.1f}%")
            logger.info(f"  Total PnL: ${stats['total_pnl']:+.2f}")
            logger.info(f"  ROI: {stats['roi']:+.1f}%")
            logger.info("="*80)
            
            # Final telegram notification
            self.telegram.send(
                f"🛑 *NEXUS NEXUS v2.0 STOPPED*\n\n"
                f"Paper Trading Final Results:\n"
                f"Total trades: {stats['total_trades']}\n"
                f"Win rate: {stats['win_rate']:.1f}%\n"
                f"PnL: ${stats['total_pnl']:+.2f}\n"
                f"ROI: {stats['roi']:+.1f}%\n\n"
                f"Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}"
            )
        
        except Exception as e:
            logger.error(f"FATAL ERROR: {e}", exc_info=True)
            
            # Error notification
            self.telegram.send(
                f"❌ *NEXUS NEXUS v2.0 CRASHED*\n\n"
                f"Error: {str(e)[:200]}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}\n\n"
                f"⚠️ Check logs immediately!"
            )
            raise

if __name__ == '__main__':
    runner = NexusRunner()
    runner.run()
