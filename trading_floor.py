from traders import Trader
from typing import List
import asyncio
from tracers import LogTracer
from agents import add_trace_processor
from market import is_market_open
from dotenv import load_dotenv
import os
import argparse

from ui_config import lastnames, model_names, names

load_dotenv(override=True)

RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "60"))
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower() == "true"
)
DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() == "true"
MAX_MANUAL_RUNS_PER_TRIGGER = max(1, min(3, int(os.getenv("MAX_MANUAL_RUNS_PER_TRIGGER", "1"))))


def create_traders() -> List[Trader]:
    traders = []
    for name, lastname, model_name in zip(names, lastnames, model_names):
        traders.append(Trader(name, lastname, model_name))
    return traders


async def run_every_n_minutes():
    add_trace_processor(LogTracer())
    traders = create_traders()
    while True:
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
            await asyncio.gather(*[trader.run() for trader in traders])
        else:
            print("Market is closed, skipping run")
        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)


async def run_n_cycles(runs: int, run_every_n_minutes: int | None = None):
    add_trace_processor(LogTracer())
    traders = create_traders()
    sleep_minutes = RUN_EVERY_N_MINUTES if run_every_n_minutes is None else run_every_n_minutes

    for idx in range(runs):
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
            await asyncio.gather(*[trader.run() for trader in traders])
        else:
            print("Market is closed, skipping run")

        if idx < runs - 1:
            await asyncio.sleep(max(0, sleep_minutes) * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=0, help="Run a fixed number of cycles then exit")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=None,
        help="Minutes between cycles when --runs is used",
    )
    args = parser.parse_args()

    if args.runs > 0:
        runs = max(1, min(MAX_MANUAL_RUNS_PER_TRIGGER, args.runs))
        print(f"Running {runs} manual cycle(s)")
        asyncio.run(run_n_cycles(runs=runs, run_every_n_minutes=args.interval_minutes))
    else:
        if DEMO_MODE:
            print("DEMO_MODE=true and no manual runs requested; scheduler not started.")
        else:
            print(f"Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
            asyncio.run(run_every_n_minutes())
