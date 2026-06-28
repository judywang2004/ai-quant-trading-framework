Folder          Responsibility

config          Global configuration
data            Historical and processed market data
indicators      Technical indicator calculations
models          Core trading domain objects
strategies      Trading logic
risk            Position sizing and risk controls
execution       Execute orders (backtest or live)
backtesting      Replay historical data
analytics       Performance calculations
dashboard       Streamlit UI
ml              AI models
mt5             MT5 integration
pine            Pine Script source
tests           Unit tests

I want  to separate the project into three layers.
Layer 1 — Domain (Pure Trading Logic)
models
strategies
risk
indicators

Layer 2 — Application
backtesting

analytics

dashboard

Layer 3 — Infrastructure
execution

mt5

pine

That means our dependency direction is always:
Infrastructure
        ↓

Application
        ↓

Domain