# Architecture Notes

## Purpose

This document explains how the autonomous trading system is structured so reviewers can connect the UI, orchestration logic, and persistence model.

## Major Components

- `app.py` drives the Gradio dashboard, compare mode, and UI refresh behavior
- `trading_floor.py` controls scheduled execution and manual run entrypoints
- `traders.py` and `accounts.py` define trading behavior and account state
- `database.py` persists accounts and logs in SQLite
- `mcp_params.py` wires search, market, and memory MCP services

## State Model

- Seed JSON can bootstrap the runtime database for deterministic demos
- SQLite stores account state and logs
- Per-trader memory databases store longer-lived context through MCP memory tooling
- The UI reads from persisted state rather than inventing synthetic frontend-only values

## Dashboard Model

- Summary cards optimize for quick scanning
- Detail panels optimize for log and transaction inspection
- Compare mode optimizes for side-by-side evaluation instead of reading isolated agent outputs

## Hosting Implications

- The seeded replay path is intended to make hosted demos more predictable
- Manual-run controls make the system inspectable without requiring a permanently running autonomous loop
