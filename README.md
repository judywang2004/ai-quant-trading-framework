# ai-quant-trading-framework
Professional AI-assisted quantitative trading framework for research, backtesting, machine learning and automated execution.


## Features

- MT5 Expert Advisors
- TradingView Pine Script
- Python Backtesting
- Risk Management
- Machine Learning
- Automated Execution

## Project Status

🚧 Under Development

## Objective
Build a consistently profitable, systematic trading framework that can eventually trade real money with controlled risk.

The GitHub repository should support this goal by making the research reproducible, the code maintainable, and skills visible—but we should never optimize the project for appearances at the expense of developing profitable strategies.

our priorities:

1. Develop profitable trading strategies 💰
2. Build a robust quantitative research framework 🧠
3. Create a professional GitHub portfolio 📚

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

After that, all examples and tests can be run directly.

Examples:

```bash
python3 examples/demo_daily_bias.py
python3 -m unittest discover -s tests
```