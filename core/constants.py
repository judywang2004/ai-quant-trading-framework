"""Framework-wide default constants.

These are defaults only. Components that use them (e.g.
DailyTrendAssessment) accept the same values as constructor arguments so
callers can override them per instrument without editing this file.
"""

# --- Daily Bias / DailyTrendAssessment -------------------------------

DAILY_EMA_FAST_PERIOD = 20
DAILY_EMA_SLOW_PERIOD = 50

# Number of completed daily candles fetched before evaluating the trend.
# Must be large enough for the slow EMA to warm up.
DAILY_TREND_HISTORY_LOOKBACK = 100

# Minimum number of completed daily candles required before a trend can
# be assessed at all.
DAILY_TREND_MIN_HISTORY = 50

# Number of completed daily candles used to measure the EMA20 slope.
DAILY_TREND_SLOPE_LOOKBACK = 5

# EMA20 slope is expressed as a fraction of EMA20's own value (percent
# change per candle), not raw price units, so the same threshold is
# meaningful across instruments with very different price scales (e.g.
# USDJPY ~150 vs EURUSD ~1.1). A slope whose magnitude is <= this
# threshold is classified as FLAT rather than RISING/FALLING. Defaults
# to 0.0 (only an exactly-zero slope counts as flat) until a real value
# has been chosen and verified against TradingView.
DAILY_TREND_FLAT_SLOPE_THRESHOLD_PCT = 0.0

# Minimum EMA20/EMA50 separation required to accept a trend as tradeable,
# expressed as a fraction of EMA50 (percent of price) rather than raw
# price units, for the same instrument-independence reason as above.
# Defaults to 0.0 (no minimum) so the rule never rejects a trend until a
# real threshold has been chosen and verified against TradingView.
DAILY_TREND_MIN_EMA_SEPARATION_PCT = 0.0

# Number of completed daily candles a future Market Structure (HH/HL)
# rule would look back over. Not used yet - evaluate_market_structure()
# is a placeholder - but reserved here so that rule can be configured
# the same way as the others once implemented.
DAILY_MARKET_STRUCTURE_LOOKBACK = 20
