# AGENTS.md

# AI Quant Trading Framework

This document defines the development philosophy, architecture, coding standards, and workflow for this project.

The purpose of this file is to ensure all AI assistants (Codex, ChatGPT, Codex, etc.) follow the same design principles.

---

# Project Goal

Build a production-quality quantitative trading framework capable of supporting:

- Systematic trading
- Multi-timeframe analysis
- Backtesting
- Risk management
- Automated execution
- Future AI enhancements

The framework must prioritize correctness over complexity.

The first objective is to build one profitable MVP strategy before expanding features.

---

# Development Philosophy

Priority order:

1. Correctness
2. Simplicity
3. Readability
4. Testability
5. Extensibility
6. Performance

Never sacrifice readability for optimization.

Premature optimization is discouraged.

---

# MVP Scope

Current MVP consists of only ONE trading strategy.

Workflow:

Daily Bias

↓

H1 Pullback

↓

M15 Setup

↓

M5 Trigger

↓

BUY

Only bullish trades are supported in MVP.

Bearish strategies will be implemented after bullish strategy has been verified.

Do not introduce additional strategy ideas until the MVP has been validated.

The one-strategy restriction remains in force for the original MVP track.

The separately approved Forex Research Track is an explicit exception.

Do not replace, delete, or modify the original MVP strategy.

---

# Forex Research Track

The existing Daily Bias → H1 Pullback → M15 Setup → M5 Trigger strategy remains the primary MVP and must be preserved. A separate Forex Research Track is authorized to develop research infrastructure and benchmark strategies, beginning with Donchian. This does not authorize replacing or deleting existing strategies.

User-approved decisions: docs/forex/DECISIONS.md

Forex Research Track requirements: docs/forex/FOREX_RESEARCH_TRACK.md

Implementation steps and phase gates: docs/forex/INTEGRATION_PLAN.md

---

## Approved Project Decisions

Before proposing or implementing changes, read docs/forex/DECISIONS.md.

Treat its approved decisions as binding project constraints.

Do not silently override, weaken, or contradict previously approved decisions.

If a requested change conflicts with an approved decision, identify the conflict and request explicit user approval before proceeding.

---

# Strategy Development Process

Every trading rule must follow this workflow.

Step 1

Implement ONE rule.

Step 2

Unit test.

Step 3

Verify against TradingView.

Step 4

Commit.

Step 5

Move to the next rule.

Never implement multiple trading rules before validating the previous one.

---

# Architecture

Framework flow:

MarketData

↓

Strategy

↓

RiskManager

↓

PositionManager

↓

Executor

Responsibilities:

MarketData

- loads market data
- synchronizes multiple timeframes
- provides historical candles

Strategy

- analyzes market
- generates trading signals
- never opens positions
- never manages risk

RiskManager

- determines whether trading is allowed

PositionManager

- manages existing positions
- prevents duplicate entries
- controls scaling

Executor

- executes approved trades

---

# Non-negotiable Design Principles

MarketData owns data retrieval.

Strategies never execute trades.

Strategies never manage positions.

RiskManager decides whether trading is allowed.

One responsibility per class.

One responsibility per function.

Avoid duplicate code.

Favor explicit code over clever code.

---

# Coding Standards

Use Python type hints.

Keep functions small.

Prefer descriptive variable names.

Avoid magic numbers.

Document complex logic.

Use enums instead of strings where appropriate.

Do not optimize unless profiling shows it is necessary.

---

# Logging

Every trading decision should be explainable.

Prefer output such as:

Date

Close

EMA20

EMA50

Decision

Reason

Debug output is encouraged during development.

---

# Current Trading Rules

Daily Bias

EMA20 > EMA50

↓

Bullish

EMA20 < EMA50

↓

Ignored in MVP

Only BUY opportunities are considered.

---

# Current Project Status

Completed

✓ MT4 CSV Loader

✓ MarketData

✓ Multi-timeframe synchronization

✓ Backtest framework

✓ Risk Manager

✓ Daily Bias

In Progress

H1 Pullback

Future

M15 Setup

M5 Trigger

Position Manager

Trade Management

Performance Optimization

Forex Research Track phase status is D10 in docs/forex/DECISIONS.md.

Phase 0: implementation and review completed; commits and PR pending.

Phase 1: scope approved in principle; implementation awaiting final plan approval.

Phase 2: not started.

---

# AI Assistant Guidelines

When modifying this project:

Preserve architecture.

Avoid unnecessary abstraction.

Avoid introducing new frameworks.

Do not rewrite working code without justification.

Suggest improvements incrementally.

Always explain WHY a change is recommended.

Prefer evolutionary improvements over complete rewrites.

---

# Commit Philosophy

Each commit should represent one completed milestone.

Examples:

Add MarketData synchronization

Implement Daily Bias

Validate H1 Pullback

Implement M15 Setup

Never combine unrelated features into one commit.

---

# Long-Term Vision

The long-term objective is to build a professional quantitative trading platform suitable for:

research

backtesting

paper trading

live trading

future AI optimization

The framework should be maintainable for many years.