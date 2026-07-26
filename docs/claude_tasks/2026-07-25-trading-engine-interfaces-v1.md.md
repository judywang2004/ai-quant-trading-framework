Implement the trading engine interfaces, not the High Base logic yet.

具体包括：

1. core/opportunity.py
    * OpportunityType
    * PatternState
    * Opportunity dataclass
2. risk/position_sizer.py
    * Fixed fractional position sizing
    * Risk % → lot size
3. execution/order_request.py
    * Broker-independent order description
    * No MT4 API calls yet
4. Keep everything independent of MT4/MT5 so it can be reused by backtests and future live execution.