"""
NEXUS v2.0 - P2 Scoring Engine
T0 max=20, T1 max=50, T2 max=30. Total=100.
Negative penalties: FAKE_BOS=-100, wrong_zone=-50, extreme_funding=-30.
"""
import logging
from typing import Dict, Any, Optional
from config.strategy_config import NexusConfig
logger = logging.getLogger(__name__)

class ScoringEngine:
    def __init__(self, config: NexusConfig):
        self.config = config

    def score(self, p1_reports, circuit_breaker_state=None):
        # === OPTIMIZATION: Early Volume Gate ===
        # 93% of scans have volume <0.5 — reject early to save compute
        bi_check = p1_reports.get("basic_indicators", {})
        vol_check = bi_check.get("volume_ratio", 0) or 0
        if vol_check < 0.5:
            return {
                'score': 0,
                'grade': 'NO_TRADE',
                'bias': 'NEUTRAL',
                'tier_breakdown': {'t0': 0, 't1': 0, 't2': 0},
                'reject_reason': 'Volume <0.5 (early gate - 93% filtered here)',
                'p1_snapshot': p1_reports
            }
        
        modules = p1_reports.get("modules", {})
        bias = self._determine_bias(modules)
        regime = self._determine_regime(modules)
        t0 = min(self._score_t0_context(modules, regime), self.config.scoring.tier_0_max)
        t1 = min(self._score_t1_direction(modules, bias), self.config.scoring.tier_1_max)
        t2 = min(self._score_t2_confirmation(modules, bias), self.config.scoring.tier_2_max)
        pen_total, pen_list = self._apply_penalties(modules, bias)
        bon_total, bon_list = self._apply_bonuses(modules, bias)
        cb_pen = 0
        if circuit_breaker_state:
            cb_pen = circuit_breaker_state.get("symbol_penalty", 0)
            if cb_pen != 0: pen_list.append({"source": "circuit_breaker", "value": cb_pen})
        raw = t0 + t1 + t2 + bon_total + pen_total + cb_pen
        final = max(0, min(100, raw))
        grade = self._assign_grade(final)
        modifier = self._calculate_threshold_modifier(regime)
        threshold = self.config.get_effective_threshold(modifier)
        # Model B — Binary Confidence
        model_b_conf, b_agree, b_total = self._score_model_b(modules, bias)
        model_b_grade = self._assign_grade(model_b_conf)

        # Model C — Hybrid
        model_c_score, c_status, c_reason = self._score_model_c(
            modules, bias, model_b_conf, final
        )
        model_c_grade = self._assign_grade(model_c_score)

        return {
            "score": final, "raw_score": raw, "grade": grade,
            "bias": bias, "regime": regime,
            "threshold_used": threshold, "threshold_modifier": modifier,
            "penalties_applied": pen_list, "bonuses_applied": bon_list,
            "tier_breakdown": {"t0": t0, "t1": t1, "t2": t2},
            "p1_snapshot": self._build_p1_snapshot(modules),
            "model_b": {
                "confidence_pct": model_b_conf,
                "agree": b_agree,
                "total": b_total,
                "grade": model_b_grade,
            },
            "model_c": {
                "score": model_c_score,
                "grade": model_c_grade,
                "status": c_status,
                "reason": c_reason,
            },
        }

    def _determine_bias(self, modules):
        """
        Crypto-native bias detection.
        Priority: MSS > Momentum > OI > Breakout > Funding > Price Action
        Threshold: >= 4 votes untuk declare bias.
        """
        votes = {"BULLISH": 0, "BEARISH": 0}

        # 1. MSS — sinyal terkuat, bobot tertinggi
        mss = modules.get("mss_detector", {})
        choch_dir = mss.get("choch_direction")
        choch_strength = mss.get("choch_strength", "NONE")
        bos_dir = mss.get("bos_direction")
        if choch_dir == "BULLISH" and choch_strength == "STRONG": votes["BULLISH"] += 4
        elif choch_dir == "BULLISH": votes["BULLISH"] += 3
        elif choch_dir == "BEARISH" and choch_strength == "STRONG": votes["BEARISH"] += 4
        elif choch_dir == "BEARISH": votes["BEARISH"] += 3
        if bos_dir == "BULLISH" and not choch_dir: votes["BULLISH"] += 2
        elif bos_dir == "BEARISH" and not choch_dir: votes["BEARISH"] += 2

        # 2. Momentum Classifier — pengganti Ichimoku, lag rendah
        mom = modules.get("momentum_classifier", {})
        mom_dir = mom.get("momentum_direction", "NEUTRAL")
        mom_str = mom.get("momentum_strength", 0)
        rejection = mom.get("rejection_signal")
        if mom_dir == "BULLISH": votes["BULLISH"] += mom_str
        elif mom_dir == "BEARISH": votes["BEARISH"] += mom_str
        if rejection == "BEARISH_REJECTION": votes["BEARISH"] += 1
        elif rejection == "BULLISH_REJECTION": votes["BULLISH"] += 1

        # 3. Open Interest — crypto-native confirmation
        oi = modules.get("open_interest", {})
        oi_bias = oi.get("oi_bias", "NEUTRAL")
        oi_signal = oi.get("oi_signal", "NEUTRAL")
        if oi_signal in ("BULLISH_CONFIRMED", "SHORT_COVERING"): votes["BULLISH"] += 2
        elif oi_signal in ("BEARISH_CONFIRMED", "LONG_UNWINDING"): votes["BEARISH"] += 2

        # 4. Breakout dengan volume — trend acceleration
        brk = modules.get("breakout_detector", {})
        brk_dir = brk.get("breakout_direction")
        brk_vol = brk.get("volume_confirmed", False)
        if brk_dir == "BULLISH" and brk_vol: votes["BULLISH"] += 2
        elif brk_dir == "BEARISH" and brk_vol: votes["BEARISH"] += 2
        elif brk_dir == "BULLISH": votes["BULLISH"] += 1
        elif brk_dir == "BEARISH": votes["BEARISH"] += 1

        # 5. Funding Rate contrarian — crypto-native
        fr = modules.get("funding_rate", {})
        fr_contrarian = fr.get("contrarian_bias", "NEUTRAL")
        fr_extreme = fr.get("is_extreme", False)
        if fr_extreme and fr_contrarian == "BULLISH": votes["BULLISH"] += 2
        elif fr_extreme and fr_contrarian == "BEARISH": votes["BEARISH"] += 2

        # 6. Liquidity sweep — confirmation entry
        sweep = modules.get("liquidity_sweeps", {})
        sweep_dir = sweep.get("sweep_direction")
        if sweep_dir == "BULLISH": votes["BULLISH"] += 1
        elif sweep_dir == "BEARISH": votes["BEARISH"] += 1

        # 7. PDH/PDL sweep + rejection — institutional levels
        dl = modules.get("daily_levels", {})
        if dl.get("pdl_swept") and dl.get("pdl_rejected"): votes["BULLISH"] += 2
        elif dl.get("pdh_swept") and dl.get("pdh_rejected"): votes["BEARISH"] += 2

        # 8. CVD — taker buy vs sell pressure
        cvd = modules.get("cvd_analyzer", {})
        cvd_signal = cvd.get("cvd_signal", "NEUTRAL")
        cvd_div = cvd.get("cvd_divergence", False)
        if cvd_signal == "BULLISH_CONFIRMED": votes["BULLISH"] += 2
        elif cvd_signal == "BEARISH_CONFIRMED": votes["BEARISH"] += 2
        elif cvd_signal == "BULLISH_DIVERGENCE": votes["BULLISH"] += 1
        elif cvd_signal == "BEARISH_DIVERGENCE": votes["BEARISH"] += 1

        # 9. Order Book Imbalance — leading indicator
        ob = modules.get("orderbook_imbalance", {})
        ob_signal = ob.get("ob_signal", "BALANCED")
        if ob_signal == "BID_DOMINANT": votes["BULLISH"] += 1
        elif ob_signal == "ASK_DOMINANT": votes["BEARISH"] += 1

        # 10. Candle Pattern — price action konfirmasi
        cp = modules.get("candle_pattern", {})
        cp_signal = cp.get("pattern_signal", "NEUTRAL")
        cp_strength = cp.get("pattern_strength", "WEAK")
        if cp_signal == "BULLISH" and cp_strength == "STRONG": votes["BULLISH"] += 2
        elif cp_signal == "BULLISH": votes["BULLISH"] += 1
        elif cp_signal == "BEARISH" and cp_strength == "STRONG": votes["BEARISH"] += 2
        elif cp_signal == "BEARISH": votes["BEARISH"] += 1

        # 11. Fear & Greed Index — macro sentiment contrarian
        fng = modules.get("fear_greed_index", {})
        fng_bias = fng.get("fng_bias", "NEUTRAL")
        fng_strength = fng.get("fng_strength", 0)
        if fng_bias == "BULLISH": votes["BULLISH"] += min(fng_strength, 2)
        elif fng_bias == "BEARISH": votes["BEARISH"] += min(fng_strength, 2)

        # Threshold: >= 4 votes untuk declare bias
        if votes["BULLISH"] >= 4: return "BULLISH"
        if votes["BEARISH"] >= 4: return "BEARISH"
        return "NEUTRAL"

    def _determine_regime(self, modules):
        bi = modules.get("basic_indicators", {})
        cons = modules.get("consolidation_detector", {})
        atr_pct = bi.get("atr_percent", 0) or 0
        vol_ratio = bi.get("volume_ratio", 1) or 1
        consolidating = cons.get("consolidating", False)
        if atr_pct > 2.0 and vol_ratio > 1.8: return "VOLATILE"
        if consolidating and atr_pct < 1.0: return "SIDEWAYS"
        ma_dir = bi.get("ma_direction")
        if ma_dir in ("BULLISH", "BEARISH") and bi.get("ma_aligned"): return "TRENDING"
        return "RANGING"

    def _score_t0_context(self, modules, regime):
        score = 0
        bi = modules.get("basic_indicators", {})
        cons = modules.get("consolidation_detector", {})
        fvg = modules.get("fvg_detector", {})
        ob = modules.get("orderblock_detector", {})
        fr = modules.get("funding_rate", {})
        dl = modules.get("daily_levels", {})
        vol_ratio = bi.get("volume_ratio", 0) or 0
        if vol_ratio >= 2.0: score += 6
        elif vol_ratio >= 1.5: score += 4
        elif vol_ratio >= 1.2: score += 2
        consol_q = cons.get("quality", 0) or 0
        score += int((consol_q / 100) * 6)
        has_fvg = fvg.get("fvg_present", False)
        has_ob = ob.get("ob_present", False)
        if has_fvg and has_ob: score += 5
        elif has_fvg or has_ob: score += 2
        fr_extreme = fr.get("is_extreme", False)
        fr_sentiment = fr.get("sentiment", "NEUTRAL")
        if not fr_extreme and fr_sentiment != "NEUTRAL": score += 2
        dl_ctx = dl.get("level_context", "UNKNOWN")
        if dl_ctx in ("ABOVE_PDH", "BELOW_PDL"): score += 1
        return score

    def _score_t1_direction(self, modules, bias):
        if bias == "NEUTRAL": return 0
        score = 0
        bi = modules.get("basic_indicators", {})
        fvg = modules.get("fvg_detector", {})
        ob = modules.get("orderblock_detector", {})
        pd_ = modules.get("premium_discount", {})
        dl = modules.get("daily_levels", {})
        macd = modules.get("macd_indicator", {})
        vwap = modules.get("vwap_calculator", {})
        stoch = modules.get("stochastic_rsi", {})
        sweep = modules.get("liquidity_sweeps", {})
        mss = modules.get("mss_detector", {})
        mom = modules.get("momentum_classifier", {})
        cvd = modules.get("cvd_analyzer", {})
        cp = modules.get("candle_pattern", {})

        # RSI momentum
        rsi = bi.get("rsi_value") or 50
        if bias == "BULLISH" and rsi <= 40: score += 8
        elif bias == "BULLISH" and rsi <= 50: score += 4
        elif bias == "BEARISH" and rsi >= 60: score += 8
        elif bias == "BEARISH" and rsi >= 50: score += 4

        # FVG directional
        fvg_list = fvg.get("fvg_list", [])
        rel_fvg = [f for f in fvg_list if f.get("type") == ("BULLISH" if bias == "BULLISH" else "BEARISH")]
        if rel_fvg:
            q = rel_fvg[0].get("quality", "LOW")
            score += 8 if q == "HIGH" else 5 if q == "MEDIUM" else 3

        # Order Block directional
        ob_list = ob.get("ob_list", [])
        rel_ob = [o for o in ob_list if o.get("type") == ("BULLISH" if bias == "BULLISH" else "BEARISH")]
        if rel_ob: score += 6

        # Premium/Discount zone
        zone = pd_.get("price_zone", "EQUILIBRIUM")
        # TODO: Investigate - data shows -3.8 predictive score for this module
        # Current logic: LONG in DISCOUNT = +7 pts
        # Validate: Does this actually correlate with wins?
        if bias == "BULLISH" and zone == "DISCOUNT": score += 7
        elif bias == "BEARISH" and zone == "PREMIUM": score += 7
        elif zone == "EQUILIBRIUM": score += 2

        # MACD confirmation
        macd_cross = macd.get("cross")
        if bias == "BULLISH" and macd_cross == "BULLISH": score += 3
        elif bias == "BEARISH" and macd_cross == "BEARISH": score += 3

        # VWAP position
        vwap_pos = vwap.get("vwap_position", "")
        if bias == "BULLISH" and vwap_pos in ("ABOVE_VWAP", "ABOVE"): score += 3
        elif bias == "BEARISH" and vwap_pos in ("BELOW_VWAP", "BELOW"): score += 3

        # StochRSI
        stoch_sig = stoch.get("stoch_signal")
        if bias == "BULLISH" and stoch_sig == "OVERSOLD": score += 4
        elif bias == "BEARISH" and stoch_sig == "OVERBOUGHT": score += 4

        # PDH/PDL sweep rejection
        if bias == "BULLISH" and dl.get("pdl_swept") and dl.get("pdl_rejected"): score += 7
        elif bias == "BEARISH" and dl.get("pdh_swept") and dl.get("pdh_rejected"): score += 7

        # Liquidity sweep directional
        sweep_dir = sweep.get("sweep_direction")
        if bias == "BULLISH" and sweep_dir == "BULLISH": score += 4
        elif bias == "BEARISH" and sweep_dir == "BEARISH": score += 4

        # MSS structure alignment
        mss_str = mss.get("mss_structure", "UNDEFINED")
        if bias == "BULLISH" and mss_str == "BULLISH": score += 5
        elif bias == "BEARISH" and mss_str == "BEARISH": score += 5
        choch_dir = mss.get("choch_direction")
        if bias == "BULLISH" and choch_dir == "BULLISH": score += 6
        elif bias == "BEARISH" and choch_dir == "BEARISH": score += 6

        # Momentum classifier
        mom_dir = mom.get("momentum_direction", "NEUTRAL")
        mom_str = mom.get("momentum_strength", 0)
        if bias == "BULLISH" and mom_dir == "BULLISH": score += mom_str * 3  # OPTIMIZED: Tier A (+35.0 score) - boosted from 2x
        elif bias == "BEARISH" and mom_dir == "BEARISH": score += mom_str * 3  # OPTIMIZED: Tier A (+35.0 score) - boosted from 2x

        # CVD — taker order flow
        cvd_signal = cvd.get("cvd_signal", "NEUTRAL")
        if bias == "BULLISH" and cvd_signal == "BULLISH_CONFIRMED": score += 5
        elif bias == "BEARISH" and cvd_signal == "BEARISH_CONFIRMED": score += 5
        elif bias == "BULLISH" and cvd_signal == "BULLISH_DIVERGENCE": score += 3
        elif bias == "BEARISH" and cvd_signal == "BEARISH_DIVERGENCE": score += 3

        # Candle Pattern — price action trigger
        cp_signal = cp.get("pattern_signal", "NEUTRAL")
        cp_strength = cp.get("pattern_strength", "WEAK")
        if bias == "BULLISH" and cp_signal == "BULLISH":
            score += 6 if cp_strength == "STRONG" else 3
        elif bias == "BEARISH" and cp_signal == "BEARISH":
            score += 6 if cp_strength == "STRONG" else 3

        return score

    def _score_t2_confirmation(self, modules, bias):
        if bias == "NEUTRAL": return 0
        score = 0
        bi = modules.get("basic_indicators", {})
        brk = modules.get("breakout_detector", {})
        bb = modules.get("bollinger_bands", {})
        spike = modules.get("spike_classifier", {})
        vp = modules.get("volume_profile", {})
        ma_aligned = bi.get("ma_aligned", False)
        ma_dir = bi.get("ma_direction", "NEUTRAL")
        if ma_aligned and ma_dir == bias: score += 8
        elif ma_aligned: score += 2
        brk_detected = brk.get("breakout_detected", False)
        brk_dir = brk.get("breakout_direction")
        vol_confirmed = brk.get("volume_confirmed", False)
        if brk_detected and brk_dir == bias and vol_confirmed: score += 8
        elif brk_detected and brk_dir == bias: score += 4
        bb_pos = bb.get("bb_position", "")
        bb_squeeze = bb.get("bb_squeeze", False)
        if bias == "BULLISH" and bb_pos == "below_lower": score += 5
        elif bias == "BEARISH" and bb_pos == "above_upper": score += 5
        elif bb_squeeze: score += 3
        spike_cls = spike.get("spike_classification", "NORMAL")
        if bias == "BULLISH" and spike_cls == "BULLISH_SWEEP_REJECTION": score += 6
        elif bias == "BEARISH" and spike_cls == "BEARISH_SWEEP_REJECTION": score += 6
        elif bias == "BULLISH" and spike_cls == "BULLISH_BREAKOUT": score += 4
        elif bias == "BEARISH" and spike_cls == "BEARISH_BREAKOUT": score += 4
        vp_zone = vp.get("price_zone", "")
        if bias == "BULLISH" and vp_zone == "DISCOUNT": score += 3
        elif bias == "BEARISH" and vp_zone == "PREMIUM": score += 3

        # CVD divergence sebagai extra confirmation
        cvd = modules.get("cvd_analyzer", {})
        if bias == "BULLISH" and cvd.get("cvd_divergence"): score += 4
        elif bias == "BEARISH" and cvd.get("cvd_divergence"): score += 4

        # Order Book Imbalance
        ob_imb = modules.get("orderbook_imbalance", {})
        ob_sig = ob_imb.get("ob_signal", "BALANCED")
        if bias == "BULLISH" and ob_sig == "BID_DOMINANT": score += 3
        elif bias == "BEARISH" and ob_sig == "ASK_DOMINANT": score += 3

        # Candle Pattern confirmation
        cp = modules.get("candle_pattern", {})
        cp_signal = cp.get("pattern_signal", "NEUTRAL")
        cp_strength = cp.get("pattern_strength", "WEAK")
        if bias == "BULLISH" and cp_signal == "BULLISH" and cp_strength == "STRONG": score += 8  # OPTIMIZED: Tier S (+54.7)
        elif bias == "BEARISH" and cp_signal == "BEARISH" and cp_strength == "STRONG": score += 8  # OPTIMIZED: Tier S (+54.7)

        return score

    def _apply_penalties(self, modules, bias):
        total = 0
        penalties = []
        fr = modules.get("funding_rate", {})
        pd_ = modules.get("premium_discount", {})
        brk = modules.get("breakout_detector", {})
        dl = modules.get("daily_levels", {})
        if fr.get("is_extreme", False):
            total -= 30
            penalties.append({"source": "extreme_funding", "value": -30})
        zone = pd_.get("price_zone", "EQUILIBRIUM")
        if bias == "BULLISH" and zone == "PREMIUM":
            total -= 50
            penalties.append({"source": "wrong_zone_long_in_premium", "value": -50})
        elif bias == "BEARISH" and zone == "DISCOUNT":
            total -= 50
            penalties.append({"source": "wrong_zone_short_in_discount", "value": -50})
        brk_detected = brk.get("breakout_detected", False)
        brk_dir = brk.get("breakout_direction")
        vol_confirmed = brk.get("volume_confirmed", False)
        if brk_detected and not vol_confirmed and brk_dir and brk_dir != bias:
            total -= 100
            penalties.append({"source": "fake_bos", "value": -100})
        dl_ctx = dl.get("level_context", "UNKNOWN")
        if bias == "BULLISH" and dl.get("approaching_pdh", False):
            total -= 20
            penalties.append({"source": "long_approaching_pdh", "value": -20})
        elif bias == "BEARISH" and dl.get("approaching_pdl", False):
            total -= 20
            penalties.append({"source": "short_approaching_pdl", "value": -20})
        return total, penalties

    def _apply_bonuses(self, modules, bias):
        total = 0
        bonuses = []
        sweep = modules.get("liquidity_sweeps", {})
        fvg = modules.get("fvg_detector", {})
        ob = modules.get("orderblock_detector", {})
        dl = modules.get("daily_levels", {})
        sweep_dir = sweep.get("sweep_direction")
        if bias == "BULLISH" and sweep_dir == "BULLISH":
            total += 20
            bonuses.append({"source": "valid_sweep_bullish", "value": 20})
        elif bias == "BEARISH" and sweep_dir == "BEARISH":
            total += 20
            bonuses.append({"source": "valid_sweep_bearish", "value": 20})
        has_fvg = fvg.get("fvg_present", False)
        has_ob = ob.get("ob_present", False)
        if has_fvg and has_ob and bias != "NEUTRAL":
            total += 15
            bonuses.append({"source": "zone_confluence_fvg_ob", "value": 15})
        # PDH/PDL sweep rejection bonus sudah dihitung di T1 — tidak duplikasi di sini
        return total, bonuses


    def _score_model_b(self, modules, bias):
        """Model B — Binary Confidence: persentase modul yang agree dengan bias."""
        if bias == "NEUTRAL":
            return 0.0, 0, 22

        checks = {
            "rsi": lambda: (
                modules.get("basic_indicators", {}).get("rsi_value", 50) < 40
                if bias == "BULLISH"
                else modules.get("basic_indicators", {}).get("rsi_value", 50) > 60
            ),
            "macd": lambda: (
                modules.get("macd_indicator", {}).get("cross") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("macd_indicator", {}).get("cross") == "BEARISH"
            ),
            "vwap": lambda: (
                modules.get("vwap_calculator", {}).get("vwap_position") == "ABOVE"
                if bias == "BULLISH"
                else modules.get("vwap_calculator", {}).get("vwap_position") == "BELOW"
            ),
            "bb": lambda: (
                modules.get("bollinger_bands", {}).get("bb_position") in ("BELOW_LOWER", "NEAR_LOWER")
                if bias == "BULLISH"
                else modules.get("bollinger_bands", {}).get("bb_position") in ("ABOVE_UPPER", "NEAR_UPPER")
            ),
            "stoch": lambda: (
                modules.get("stochastic_rsi", {}).get("stoch_signal") == "OVERSOLD"
                if bias == "BULLISH"
                else modules.get("stochastic_rsi", {}).get("stoch_signal") == "OVERBOUGHT"
            ),
            "fvg": lambda: modules.get("fvg_detector", {}).get("fvg_present", False),
            "ob": lambda: modules.get("orderblock_detector", {}).get("ob_present", False),
            "zone": lambda: (
                modules.get("premium_discount", {}).get("price_zone") == "DISCOUNT"
                if bias == "BULLISH"
                else modules.get("premium_discount", {}).get("price_zone") == "PREMIUM"
            ),
            "sweep": lambda: modules.get("liquidity_sweeps", {}).get("sweep_detected", False),
            "pdl_swept": lambda: (
                modules.get("daily_levels", {}).get("pdl_swept", False)
                if bias == "BULLISH"
                else modules.get("daily_levels", {}).get("pdh_swept", False)
            ),
            "breakout": lambda: (
                modules.get("breakout_detector", {}).get("breakout_direction") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("breakout_detector", {}).get("breakout_direction") == "BEARISH"
            ),
            "mss": lambda: (
                modules.get("mss_detector", {}).get("mss_structure") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("mss_detector", {}).get("mss_structure") == "BEARISH"
            ),
            "choch": lambda: modules.get("mss_detector", {}).get("choch_detected", False),
            "momentum": lambda: (
                modules.get("momentum_classifier", {}).get("momentum_direction") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("momentum_classifier", {}).get("momentum_direction") == "BEARISH"
            ),
            "candle": lambda: (
                modules.get("candle_pattern", {}).get("primary_pattern", "").startswith("BULLISH")
                if bias == "BULLISH"
                else modules.get("candle_pattern", {}).get("primary_pattern", "").startswith("BEARISH")
            ),
            "cvd": lambda: (
                modules.get("cvd_analyzer", {}).get("cvd_signal") in ("BULLISH_CONFIRMED", "BULLISH_DIVERGENCE")
                if bias == "BULLISH"
                else modules.get("cvd_analyzer", {}).get("cvd_signal") in ("BEARISH_CONFIRMED", "BEARISH_DIVERGENCE")
            ),
            "ob_imb": lambda: (
                modules.get("orderbook_imbalance", {}).get("ob_signal") == "BID_DOMINANT"
                if bias == "BULLISH"
                else modules.get("orderbook_imbalance", {}).get("ob_signal") == "ASK_DOMINANT"
            ),
            "funding": lambda: (
                modules.get("funding_rate", {}).get("sentiment") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("funding_rate", {}).get("sentiment") == "BEARISH"
            ),
            "oi": lambda: (
                modules.get("open_interest", {}).get("oi_signal") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("open_interest", {}).get("oi_signal") == "BEARISH"
            ),
            "fng": lambda: (
                modules.get("fear_greed_index", {}).get("fng_value", 50) < 35
                if bias == "BULLISH"
                else modules.get("fear_greed_index", {}).get("fng_value", 50) > 65
            ),
            "volume": lambda: modules.get("basic_indicators", {}).get("volume_ratio", 0) >= 1.0,
            "ha_direction": lambda: (
                modules.get("heiken_ashi", {}).get("ha_direction") == "BULLISH"
                if bias == "BULLISH"
                else modules.get("heiken_ashi", {}).get("ha_direction") == "BEARISH"
            ),
            "ha_strength": lambda: modules.get("heiken_ashi", {}).get("ha_strength") in ("STRONG", "MODERATE"),
        }

        agree = 0
        total = len(checks)
        for name, fn in checks.items():
            try:
                if fn(): agree += 1
            except Exception:
                pass

        confidence_pct = round(agree / total * 100, 1)
        return confidence_pct, agree, total

    def _score_model_c(self, modules, bias, model_b_confidence, additive_score):
        """Model C — Hybrid: binary filter dulu, lalu additive score."""
        BINARY_THRESHOLD = 45.0
        if model_b_confidence < BINARY_THRESHOLD:
            return 0, "FILTERED", f"Binary confidence {model_b_confidence}% < {BINARY_THRESHOLD}%"
        return additive_score, "PASSED", f"Binary {model_b_confidence}% >= {BINARY_THRESHOLD}%, additive={additive_score}"

    def _assign_grade(self, score):
        if score >= self.config.scoring.premium_threshold: return "PREMIUM"
        elif score >= self.config.scoring.valid_threshold: return "VALID"
        elif score >= self.config.scoring.weak_threshold: return "WEAK"
        return "NO_TRADE"

    def _calculate_threshold_modifier(self, regime):
        if regime == "TRENDING": return -10
        elif regime == "SIDEWAYS": return 15
        elif regime == "VOLATILE": return 20
        return 0

    def _build_p1_snapshot(self, modules):
        snap = {}
        for name, rep in modules.items():
            if rep.get("skipped") or rep.get("error"): continue
            snap[name] = {k: v for k, v in rep.items()
                if k not in ("module","category","is_implemented","error","skipped")
                and not isinstance(v, (list, dict))}
        return snap