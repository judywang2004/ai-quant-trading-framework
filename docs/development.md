Module          One responsibility
Strategy        Should I trade?
RiskManager     How much should I trade?
Executor        Execute the trade
Trade           Record what happened

The Strategy should never calculate position size.

The RiskManager should never decide BUY or SELL.

The Executor should never know why the trade exists.
