# Design Decisions

## Why Gradio

Gradio is a practical fit for this project because it makes it easy to ship an interactive Python-native dashboard without building a separate frontend stack.

## Why Seeded Replay

The seeded replay path exists because autonomous agent demos are hard to review when every run depends on current runtime state. Seeded JSON provides a repeatable baseline for screenshots, hosted demos, and recruiter review.

## Why Compare Mode

A multi-agent system is more convincing when reviewers can compare behavior directly. Compare mode turns the project from a single-agent UI into a system-evaluation surface.

## Why Manual Runs

Manual runs create a middle ground between static replay and a fully autonomous background scheduler. That is better for demos, cost control, and debugging.

## Why SQLite and Local Memory

SQLite keeps the project simple to run locally, while per-trader MCP-backed memory makes the architecture more realistic than a pure stateless toy demo.
