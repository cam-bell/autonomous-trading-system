from dataclasses import dataclass
from datetime import datetime, timezone

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from accounts import Account, INITIAL_BALANCE
from database import read_log
from trading_floor import lastnames, names, short_model_names
from util import Color, css, js

TRANSACTION_COLUMNS = ["Timestamp", "Symbol", "Quantity", "Price", "Rationale"]
HOLDINGS_COLUMNS = ["Symbol", "Quantity"]
COMPARE_METRICS_COLUMNS = [
    "Trader",
    "Strategy",
    "Portfolio Value",
    "PnL",
    "PnL %",
    "Holdings",
    "Transactions",
    "Last Tx (UTC)",
]
COMPARE_TX_COLUMNS = ["Trader"] + TRANSACTION_COLUMNS
COMPARE_TX_LIMIT_OPTIONS = [10, 25, 50]

mapper = {
    "trace": Color.WHITE,
    "agent": Color.CYAN,
    "function": Color.GREEN,
    "generation": Color.YELLOW,
    "response": Color.MAGENTA,
    "account": Color.RED,
}


def _empty_plot(message: str, height: int = 220):
    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="#111",
        plot_bgcolor="#111",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#bbb", size=14),
            )
        ],
    )
    return fig


def _format_timestamp_for_demo(value, include_seconds: bool = False) -> str:
    if value is None:
        return ""
    raw = str(value)
    ts = pd.to_datetime(raw, errors="coerce", utc=True)
    if pd.isna(ts):
        return raw
    now_utc_date = datetime.now(timezone.utc).date()
    if ts.date() == now_utc_date:
        return ts.strftime("%H:%M:%S UTC" if include_seconds else "%H:%M UTC")
    return ts.strftime("%d %b %H:%M:%S UTC" if include_seconds else "%d %b %H:%M UTC")


def _normalize_selection(selection: list[str] | None, valid_names: list[str]) -> list[str]:
    if selection is None:
        return []
    valid = set(valid_names)
    return [name for name in valid_names if name in set(selection) and name in valid]


class Trader:
    def __init__(self, name: str, lastname: str, model_name: str):
        self.name = name
        self.lastname = lastname
        self.model_name = model_name
        self.account = Account.get(name)

    def reload(self):
        self.account = Account.get(self.name)

    def get_title(self) -> str:
        return (
            "<div class='trader-title'>"
            f"<div class='trader-title-main'>{self.name}</div>"
            f"<div class='trader-title-sub'>({self.model_name}) - {self.lastname}</div>"
            "</div>"
        )

    def get_portfolio_value_df(self) -> pd.DataFrame:
        series = self.account.portfolio_value_time_series or []
        if not series:
            return pd.DataFrame(columns=["datetime", "value"])
        df = pd.DataFrame(series, columns=["datetime", "value"])
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["datetime", "value"]).sort_values("datetime")
        return df

    def get_portfolio_value_chart(self, height: int = 300, compact: bool = False):
        df = self.get_portfolio_value_df()
        if df.empty:
            return _empty_plot("No portfolio history yet", height=height)

        fig = px.line(df, x="datetime", y="value")
        if compact:
            fig.update_layout(
                height=height,
                margin=dict(l=8, r=8, t=8, b=8),
                paper_bgcolor="#17181f",
                plot_bgcolor="#17181f",
            )
            fig.update_traces(line=dict(width=2, color="#5b6dff"))
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
        else:
            fig.update_layout(
                height=height,
                margin=dict(l=40, r=20, t=20, b=40),
                xaxis_title="Time (UTC)",
                yaxis_title="Portfolio Value ($)",
                paper_bgcolor="#bbb",
                plot_bgcolor="#dde",
            )
            fig.update_xaxes(tickformat="%H:%M", tickangle=45, tickfont=dict(size=8))
            fig.update_yaxes(tickfont=dict(size=8), tickformat=",.0f")
        return fig

    def get_holdings_df(self) -> pd.DataFrame:
        holdings = self.account.get_holdings() or {}
        if not holdings:
            return pd.DataFrame(columns=HOLDINGS_COLUMNS)
        df = pd.DataFrame(
            [{"Symbol": symbol, "Quantity": quantity} for symbol, quantity in holdings.items()]
        )
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
        return df[HOLDINGS_COLUMNS].sort_values("Symbol").reset_index(drop=True)

    def get_transactions_df(self) -> pd.DataFrame:
        transactions = self.account.list_transactions() or []
        if not transactions:
            return pd.DataFrame(columns=TRANSACTION_COLUMNS)

        df = pd.DataFrame(transactions).rename(
            columns={
                "timestamp": "Timestamp",
                "symbol": "Symbol",
                "quantity": "Quantity",
                "price": "Price",
                "rationale": "Rationale",
            }
        )
        for col in TRANSACTION_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[TRANSACTION_COLUMNS].copy()
        original_timestamp = df["Timestamp"].astype(str).fillna("")
        parsed_ts = pd.to_datetime(df["Timestamp"], errors="coerce", utc=True)
        df["_sort_ts"] = parsed_ts
        df = df.sort_values("_sort_ts", ascending=False, na_position="last")
        df["Timestamp"] = [
            _format_timestamp_for_demo(parsed_ts.loc[idx], include_seconds=False)
            if pd.notna(parsed_ts.loc[idx])
            else original_timestamp.loc[idx]
            for idx in df.index
        ]
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.drop(columns=["_sort_ts"]).reset_index(drop=True)
        return df

    def get_summary_snapshot(self) -> dict:
        portfolio_value = self.account.calculate_portfolio_value() or 0.0
        pnl = self.account.calculate_profit_loss(portfolio_value) or 0.0
        holdings_df = self.get_holdings_df()
        tx_df = self.get_transactions_df()
        last_tx = tx_df.iloc[0]["Timestamp"] if not tx_df.empty else None
        logs = list(read_log(self.name, last_n=1))
        latest_log_preview = None
        if logs:
            _, log_type, message = logs[-1]
            latest_log_preview = f"[{log_type}] {message}"
            if len(latest_log_preview) > 72:
                latest_log_preview = latest_log_preview[:69] + "..."
        baseline = INITIAL_BALANCE or 10_000.0
        pnl_pct = (pnl / baseline * 100.0) if baseline else 0.0
        return {
            "name": self.name,
            "lastname": self.lastname,
            "model_name": self.model_name,
            "strategy": self.account.strategy or self.lastname,
            "portfolio_value": portfolio_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "holdings_count": int(len(holdings_df.index)),
            "transaction_count": int(len(tx_df.index)),
            "last_transaction_timestamp": last_tx,
            "latest_log_preview": latest_log_preview,
        }

    def get_portfolio_value(self) -> str:
        portfolio_value = self.account.calculate_portfolio_value() or 0.0
        pnl = self.account.calculate_profit_loss(portfolio_value) or 0.0
        color = "green" if pnl >= 0 else "red"
        emoji = "⬆" if pnl >= 0 else "⬇"
        return (
            f"<div style='text-align:center;background-color:{color};'>"
            f"<span style='font-size:32px'>${portfolio_value:,.0f}</span>"
            f"<span style='font-size:24px'>&nbsp;&nbsp;&nbsp;{emoji}&nbsp;${pnl:,.0f}</span></div>"
        )

    def get_logs_html(self, previous=None, max_lines: int | None = 13, height: int = 250) -> str:
        logs = list(read_log(self.name, last_n=max_lines))
        response = ""
        for timestamp, type_name, message in logs:
            color = mapper.get(type_name, Color.WHITE).value
            response += (
                f"<span style='color:{color}'>{_format_timestamp_for_demo(timestamp, include_seconds=True)} : [{type_name}] {message}</span><br/>"
            )
        title = "All Logs (UTC)" if max_lines is None else f"Recent Logs (UTC, last {max_lines})"
        response = (
            f"<div><div style='margin-bottom:6px;color:#c7d1e1;font-weight:600'>{title}</div>"
            f"<div style='height:{height}px; overflow-y:auto;'>{response}</div></div>"
        )
        if response != previous:
            return response
        return gr.update()

    def get_logs(self, previous=None) -> str:
        return self.get_logs_html(previous=previous)


def build_compare_metrics_df(traders_by_name: dict[str, Trader], selected_names: list[str]) -> pd.DataFrame:
    rows = []
    for name in selected_names:
        trader = traders_by_name[name]
        snapshot = trader.get_summary_snapshot()
        rows.append(
            {
                "Trader": snapshot["name"],
                "Strategy": snapshot["strategy"],
                "Portfolio Value": round(snapshot["portfolio_value"], 2),
                "PnL": round(snapshot["pnl"], 2),
                "PnL %": round(snapshot["pnl_pct"], 2),
                "Holdings": snapshot["holdings_count"],
                "Transactions": snapshot["transaction_count"],
                "Last Tx (UTC)": snapshot["last_transaction_timestamp"] or "-",
            }
        )
    if not rows:
        return pd.DataFrame(columns=COMPARE_METRICS_COLUMNS)
    df = pd.DataFrame(rows)[COMPARE_METRICS_COLUMNS]
    return df.sort_values("Portfolio Value", ascending=False).reset_index(drop=True)


def build_compare_portfolio_df(
    traders_by_name: dict[str, Trader], selected_names: list[str], normalized: bool
) -> pd.DataFrame:
    frames = []
    for name in selected_names:
        trader = traders_by_name[name]
        df = trader.get_portfolio_value_df().copy()
        if df.empty:
            continue
        df["trader"] = name
        if normalized:
            base = df["value"].iloc[0]
            if base and pd.notna(base):
                df["plot_value"] = (df["value"] / base) * 100.0
            else:
                df["plot_value"] = df["value"]
        else:
            df["plot_value"] = df["value"]
        frames.append(df[["datetime", "value", "trader", "plot_value"]])
    if not frames:
        return pd.DataFrame(columns=["datetime", "value", "trader", "plot_value"])
    return pd.concat(frames, ignore_index=True).sort_values(["datetime", "trader"])


def build_merged_transactions_df(
    traders_by_name: dict[str, Trader], selected_names: list[str], limit: int
) -> pd.DataFrame:
    frames = []
    for name in selected_names:
        df = traders_by_name[name].get_transactions_df().copy()
        if df.empty:
            continue
        df.insert(0, "Trader", name)
        frames.append(df[COMPARE_TX_COLUMNS])
    if not frames:
        return pd.DataFrame(columns=COMPARE_TX_COLUMNS)
    merged = pd.concat(frames, ignore_index=True)
    merged["_sort_ts"] = pd.to_datetime(merged["Timestamp"], errors="coerce")
    merged = merged.sort_values("_sort_ts", ascending=False, na_position="last").drop(
        columns=["_sort_ts"]
    )
    if limit:
        merged = merged.head(limit)
    return merged.reset_index(drop=True)


def build_compare_chart(
    traders_by_name: dict[str, Trader], selected_names: list[str], chart_mode: str
):
    normalized = chart_mode.lower().startswith("norm")
    df = build_compare_portfolio_df(traders_by_name, selected_names, normalized=normalized)
    if df.empty:
        return _empty_plot("No portfolio history available for comparison", height=320)

    y_col = "plot_value"
    fig = px.line(df, x="datetime", y=y_col, color="trader")
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Time (UTC)",
        yaxis_title=None,
        paper_bgcolor="#14161e",
        plot_bgcolor="#1b1f2a",
        legend_title_text="Trader",
    )
    fig.update_xaxes(tickformat="%H:%M", tickangle=45, tickfont=dict(size=9), gridcolor="#39445a")
    if normalized:
        fig.update_yaxes(title=None, tickfont=dict(size=9), tickformat=".1f", gridcolor="#39445a")
    else:
        fig.update_yaxes(title=None, tickfont=dict(size=9), tickformat=",.0f", gridcolor="#39445a")
    return fig


def default_ui_state(trader_names: list[str]) -> dict:
    return {
        "active_trader": trader_names[0] if trader_names else "",
        "compare_enabled": False,
        "compare_selected": list(trader_names),
        "compare_chart_mode": "Normalized",
        "compare_tx_limit": 25,
        "view_all_logs": False,
    }


def sanitize_state(state: dict | None, trader_names: list[str]) -> dict:
    state = dict(state or {})
    valid_names = list(trader_names)
    state.setdefault("active_trader", valid_names[0] if valid_names else "")
    if state["active_trader"] not in valid_names and valid_names:
        state["active_trader"] = valid_names[0]
    state["compare_enabled"] = bool(state.get("compare_enabled", False))
    state["compare_selected"] = _normalize_selection(state.get("compare_selected"), valid_names)
    chart_mode = str(state.get("compare_chart_mode", "Normalized"))
    state["compare_chart_mode"] = "Absolute" if chart_mode.lower().startswith("abs") else "Normalized"
    tx_limit = state.get("compare_tx_limit", 25)
    state["compare_tx_limit"] = int(tx_limit) if str(tx_limit).isdigit() else 25
    if state["compare_tx_limit"] not in COMPARE_TX_LIMIT_OPTIONS:
        state["compare_tx_limit"] = 25
    state["view_all_logs"] = bool(state.get("view_all_logs", False))
    return state


def set_active_trader(state: dict, trader_name: str, trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    if trader_name in trader_names:
        state["active_trader"] = trader_name
    return state


def toggle_compare_trader(
    state: dict, trader_name: str, checked: bool, trader_names: list[str]
) -> dict:
    state = sanitize_state(state, trader_names)
    selected = set(state["compare_selected"])
    if checked:
        selected.add(trader_name)
    else:
        selected.discard(trader_name)
    state["compare_selected"] = [name for name in trader_names if name in selected]
    return state


def set_compare_mode(state: dict, enabled: bool, trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    state["compare_enabled"] = bool(enabled)
    if state["compare_enabled"] and not state["compare_selected"]:
        state["compare_selected"] = list(trader_names)
    return state


def update_compare_selection(state: dict, selected_names: list[str], trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    normalized = _normalize_selection(selected_names, trader_names)
    state["compare_selected"] = normalized
    return state


def set_compare_chart_mode(state: dict, mode: str, trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    state["compare_chart_mode"] = "Absolute" if str(mode).lower().startswith("abs") else "Normalized"
    return state


def set_compare_tx_limit(state: dict, limit: int, trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 25
    if parsed not in COMPARE_TX_LIMIT_OPTIONS:
        parsed = 25
    state["compare_tx_limit"] = parsed
    return state


def set_view_all_logs(state: dict, enabled: bool, trader_names: list[str]) -> dict:
    state = sanitize_state(state, trader_names)
    state["view_all_logs"] = bool(enabled)
    return state


def _summary_title_html(snapshot: dict, selected: bool, compared: bool) -> str:
    classes = ["summary-card-title-wrap"]
    if selected:
        classes.append("is-selected")
    if compared:
        classes.append("is-compared")
    badges = []
    if selected:
        badges.append("<span class='summary-badge summary-badge-active'>Active</span>")
    if compared:
        badges.append("<span class='summary-badge summary-badge-compare'>Compare</span>")
    badges_html = "".join(badges)
    return (
        f"<div class='{' '.join(classes)}'>"
        f"<div class='summary-title-main'>{snapshot['name']}</div>"
        f"<div class='summary-title-sub'>({snapshot['model_name']}) - {snapshot['strategy']}</div>"
        f"<div class='summary-badges'>{badges_html}</div>"
        "</div>"
    )


def _summary_value_html(snapshot: dict) -> str:
    pnl = snapshot["pnl"]
    value = snapshot["portfolio_value"]
    color = "#0b9f17" if pnl >= 0 else "#f91414"
    arrow = "⬆" if pnl >= 0 else "⬇"
    return (
        f"<div class='summary-pnl-strip' style='background:{color};'>"
        f"<span class='summary-pnl-value'>${value:,.0f}</span>"
        f"<span class='summary-pnl-change'>{arrow} ${pnl:,.0f}</span>"
        "</div>"
    )


def _summary_meta_html(snapshot: dict) -> str:
    last_tx = snapshot["last_transaction_timestamp"] or "No transactions"
    log_preview = snapshot["latest_log_preview"] or "No recent logs"
    return (
        "<div class='summary-meta'>"
        f"<div><strong>Holdings:</strong> {snapshot['holdings_count']} &nbsp; "
        f"<strong>Tx:</strong> {snapshot['transaction_count']} &nbsp; "
        f"<strong>PnL%:</strong> {snapshot['pnl_pct']:.2f}%</div>"
        f"<div><strong>Last Tx:</strong> {last_tx}</div>"
        f"<div class='summary-meta-log'>{log_preview}</div>"
        "</div>"
    )


def _detail_header_html(snapshot: dict) -> str:
    return (
        "<div class='detail-header'>"
        f"<div class='detail-header-main'>{snapshot['name']} — {snapshot['strategy']}</div>"
        f"<div class='detail-header-sub'>"
        f"{snapshot['model_name']} | Portfolio ${snapshot['portfolio_value']:,.0f} | "
        f"PnL ${snapshot['pnl']:,.0f} ({snapshot['pnl_pct']:.2f}%)"
        "</div>"
        "</div>"
    )


def _compare_helper_html(compare_enabled: bool, selected_count: int) -> str:
    if not compare_enabled:
        return (
            "<div class='compare-helper muted'>Compare mode is off. "
            "Enable Compare Mode and select 2-4 traders.</div>"
        )
    if selected_count < 2:
        return (
            "<div class='compare-helper warning'>Select at least 2 traders to compare. "
            "Single-trader detail remains visible until then.</div>"
        )
    return (
        f"<div class='compare-helper success'>Comparing {selected_count} traders. "
        "Use the controls to switch normalized vs absolute chart view.</div>"
    )


def _compare_trader_panel_header_html(snapshot: dict, selected: bool) -> str:
    status = (
        "<span class='summary-badge summary-badge-compare'>Included in Compare</span>"
        if selected
        else "<span class='summary-badge'>Not Selected</span>"
    )
    return (
        "<div class='compare-trader-panel-header'>"
        f"<div class='compare-trader-panel-title'>{snapshot['name']} — {snapshot['strategy']}</div>"
        f"<div class='compare-trader-panel-sub'>"
        f"Portfolio ${snapshot['portfolio_value']:,.0f} | "
        f"PnL ${snapshot['pnl']:,.0f} ({snapshot['pnl_pct']:.2f}%) | "
        f"Holdings {snapshot['holdings_count']} | Tx {snapshot['transaction_count']}</div>"
        f"<div class='compare-trader-panel-status'>{status}</div>"
        "</div>"
    )


@dataclass
class SummaryCardComponents:
    name: str
    title: gr.HTML
    value: gr.HTML
    chart: gr.Plot
    meta: gr.HTML
    select_button: gr.Button
    compare_checkbox: gr.Checkbox


@dataclass
class CompareTraderPanelComponents:
    name: str
    header: gr.HTML
    log: gr.HTML
    holdings: gr.Dataframe
    transactions: gr.Dataframe


@dataclass
class DashboardRefs:
    state: gr.State
    active_trader_control: gr.Radio
    compare_mode_control: gr.Checkbox
    compare_selection_control: gr.CheckboxGroup
    compare_chart_mode_control: gr.Radio
    compare_tx_limit_control: gr.Dropdown
    view_all_logs_control: gr.Checkbox
    summary_cards: list[SummaryCardComponents]
    compare_trader_panels: list[CompareTraderPanelComponents]
    detail_header: gr.HTML
    detail_chart: gr.Plot
    detail_log: gr.HTML
    detail_holdings: gr.Dataframe
    detail_transactions: gr.Dataframe
    compare_helper: gr.HTML
    compare_metrics: gr.Dataframe
    compare_chart: gr.Plot
    compare_transactions: gr.Dataframe


class DashboardController:
    def __init__(self, traders: list[Trader]):
        self.traders = traders
        self.traders_by_name = {t.name: t for t in traders}
        self.trader_names = [t.name for t in traders]

    def reload_all(self):
        for trader in self.traders:
            trader.reload()

    def _sanitize(self, state: dict | None) -> dict:
        return sanitize_state(state, self.trader_names)

    def _summary_card_payload(self, state: dict, trader_name: str):
        trader = self.traders_by_name[trader_name]
        snapshot = trader.get_summary_snapshot()
        selected = state["active_trader"] == trader_name
        compared = trader_name in state["compare_selected"]
        return (
            _summary_title_html(snapshot, selected=selected, compared=compared),
            _summary_value_html(snapshot),
            trader.get_portfolio_value_chart(height=155, compact=True),
            _summary_meta_html(snapshot),
            bool(compared),
            gr.update(variant="primary" if selected else "secondary"),
        )

    def _detail_payload(self, state: dict):
        trader = self.traders_by_name[state["active_trader"]]
        snapshot = trader.get_summary_snapshot()
        max_lines = None if state.get("view_all_logs") else 18
        return (
            _detail_header_html(snapshot),
            trader.get_portfolio_value_chart(height=350, compact=False),
            trader.get_logs_html(max_lines=max_lines, height=270),
            trader.get_holdings_df(),
            trader.get_transactions_df(),
        )

    def _compare_payload(self, state: dict):
        compare_enabled = bool(state["compare_enabled"])
        selected_names = state["compare_selected"]
        selected_count = len(selected_names)

        helper_html = _compare_helper_html(compare_enabled, selected_count)
        compare_visuals_visible = compare_enabled and selected_count >= 2

        if compare_visuals_visible:
            metrics_df = build_compare_metrics_df(self.traders_by_name, selected_names)
            compare_fig = build_compare_chart(
                self.traders_by_name, selected_names, state["compare_chart_mode"]
            )
            merged_tx_df = build_merged_transactions_df(
                self.traders_by_name, selected_names, state["compare_tx_limit"]
            )
        else:
            metrics_df = pd.DataFrame(columns=COMPARE_METRICS_COLUMNS)
            compare_fig = _empty_plot("Select at least 2 traders to compare", height=320)
            merged_tx_df = pd.DataFrame(columns=COMPARE_TX_COLUMNS)

        return (
            helper_html,
            gr.update(value=metrics_df, visible=compare_visuals_visible),
            gr.update(value=compare_fig, visible=compare_visuals_visible),
            gr.update(value=merged_tx_df, visible=compare_visuals_visible),
        )

    def _compare_trader_panels_payload(self, state: dict):
        compare_enabled = bool(state["compare_enabled"])
        outputs: list = []
        selected = set(state["compare_selected"])
        for trader_name in self.trader_names:
            trader = self.traders_by_name[trader_name]
            if compare_enabled:
                snapshot = trader.get_summary_snapshot()
                max_lines = None if state.get("view_all_logs") else 14
                outputs.extend(
                    [
                        gr.update(
                            value=_compare_trader_panel_header_html(
                                snapshot, selected=trader_name in selected
                            ),
                            visible=True,
                        ),
                        gr.update(value=trader.get_logs_html(max_lines=max_lines, height=220), visible=True),
                        gr.update(value=trader.get_holdings_df(), visible=True),
                        gr.update(value=trader.get_transactions_df(), visible=True),
                    ]
                )
            else:
                outputs.extend(
                    [
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                    ]
                )
        return tuple(outputs)

    def render_dashboard(self, state: dict | None, reload_data: bool = False):
        if reload_data:
            self.reload_all()
        state = self._sanitize(state)

        outputs: list = [
            state,
            state["active_trader"],
            state["compare_enabled"],
            state["compare_selected"],
            state["compare_chart_mode"],
            state["compare_tx_limit"],
            state["view_all_logs"],
        ]

        for trader_name in self.trader_names:
            outputs.extend(self._summary_card_payload(state, trader_name))

        outputs.extend(self._compare_payload(state))
        outputs.extend(self._compare_trader_panels_payload(state))
        outputs.extend(self._detail_payload(state))
        return tuple(outputs)

    def refresh_active_log(self, state: dict | None, previous: str | None = None):
        state = self._sanitize(state)
        trader = self.traders_by_name[state["active_trader"]]
        trader.reload()
        max_lines = None if state.get("view_all_logs") else 18
        return trader.get_logs_html(previous=previous, max_lines=max_lines, height=270)


def _all_dashboard_outputs(refs: DashboardRefs):
    outputs = [
        refs.state,
        refs.active_trader_control,
        refs.compare_mode_control,
        refs.compare_selection_control,
        refs.compare_chart_mode_control,
        refs.compare_tx_limit_control,
        refs.view_all_logs_control,
    ]
    for card in refs.summary_cards:
        outputs.extend(
            [
                card.title,
                card.value,
                card.chart,
                card.meta,
                card.compare_checkbox,
                card.select_button,
            ]
        )
    outputs.extend(
        [
            refs.compare_helper,
            refs.compare_metrics,
            refs.compare_chart,
            refs.compare_transactions,
        ]
    )
    for panel in refs.compare_trader_panels:
        outputs.extend([panel.header, panel.log, panel.holdings, panel.transactions])
    outputs.extend(
        [
            refs.detail_header,
            refs.detail_chart,
            refs.detail_log,
            refs.detail_holdings,
            refs.detail_transactions,
        ]
    )
    return outputs


def create_ui():
    traders = [
        Trader(trader_name, lastname, model_name)
        for trader_name, lastname, model_name in zip(names, lastnames, short_model_names)
    ]
    controller = DashboardController(traders)
    initial_state = default_ui_state(controller.trader_names)

    with gr.Blocks(
        title="Traders", css=css, js=js, theme=gr.themes.Default(primary_hue="sky"), fill_width=True
    ) as ui:
        state = gr.State(initial_state)

        summary_cards: list[SummaryCardComponents] = []
        with gr.Row(elem_classes=["trader-grid-summary"]):
            for trader in traders:
                with gr.Column(scale=1, min_width=0, elem_classes=["summary-card-shell"]):
                    with gr.Group(elem_classes=["summary-card"]):
                        title = gr.HTML()
                        value = gr.HTML()
                        chart = gr.Plot(show_label=False, container=True)
                        meta = gr.HTML()
                        with gr.Row(elem_classes=["summary-card-controls"]):
                            select_button = gr.Button("Select", size="sm", variant="secondary")
                            compare_checkbox = gr.Checkbox(label="Compare", value=True)
                    summary_cards.append(
                        SummaryCardComponents(
                            name=trader.name,
                            title=title,
                            value=value,
                            chart=chart,
                            meta=meta,
                            select_button=select_button,
                            compare_checkbox=compare_checkbox,
                        )
                    )

        with gr.Group(elem_classes=["workspace-controls"]):
            with gr.Row():
                active_trader_control = gr.Radio(
                    controller.trader_names, value=controller.trader_names[0], label="Active Trader"
                )
                compare_mode_control = gr.Checkbox(value=False, label="Compare Mode")
                compare_chart_mode_control = gr.Radio(
                    ["Normalized", "Absolute"],
                    value="Normalized",
                    label="Compare Chart",
                )
                compare_tx_limit_control = gr.Dropdown(
                    choices=COMPARE_TX_LIMIT_OPTIONS,
                    value=25,
                    label="Merged Tx Rows",
                )
                view_all_logs_control = gr.Checkbox(value=False, label="View all logs")
            compare_selection_control = gr.CheckboxGroup(
                choices=controller.trader_names,
                value=list(controller.trader_names),
                label="Compare Traders (2-4 recommended)",
            )

        with gr.Column(visible=True, elem_classes=["workspace-panel"]) as single_detail_container:
            detail_header = gr.HTML()
            detail_chart = gr.Plot(show_label=False, container=True)
            with gr.Row(variant="panel"):
                detail_log = gr.HTML()
            detail_holdings = gr.Dataframe(
                label="Holdings",
                headers=HOLDINGS_COLUMNS,
                row_count=(5, "dynamic"),
                col_count=2,
                elem_classes=["detail-scroll-table"],
                interactive=False,
            )
            detail_transactions = gr.Dataframe(
                label="Recent Transactions (UTC)",
                headers=TRANSACTION_COLUMNS,
                row_count=(5, "dynamic"),
                col_count=5,
                elem_classes=["detail-scroll-table"],
                interactive=False,
            )

        with gr.Column(visible=True, elem_classes=["workspace-panel"]) as compare_container:
            compare_helper = gr.HTML()
            with gr.Group(visible=True) as compare_visual_group:
                compare_metrics = gr.Dataframe(
                    label="Compare Metrics",
                    headers=COMPARE_METRICS_COLUMNS,
                    row_count=(4, "dynamic"),
                    col_count=len(COMPARE_METRICS_COLUMNS),
                    interactive=False,
                    visible=False,
                )
                compare_chart = gr.Plot(show_label=False, container=True, visible=False)
                compare_transactions = gr.Dataframe(
                    label="Merged Recent Transactions (UTC)",
                    headers=COMPARE_TX_COLUMNS,
                    row_count=(10, "dynamic"),
                    col_count=len(COMPARE_TX_COLUMNS),
                    elem_classes=["compare-scroll-table"],
                    interactive=False,
                    visible=False,
                )
            compare_trader_panels: list[CompareTraderPanelComponents] = []
            with gr.Group(visible=True, elem_classes=["compare-explorer-group"]) as compare_explorer_group:
                gr.Markdown("### Per-Trader Data Explorer")
                with gr.Tabs():
                    for trader in traders:
                        with gr.Tab(label=trader.name):
                            panel_header = gr.HTML(visible=False)
                            with gr.Row(elem_classes=["compare-trader-grid"]):
                                with gr.Column(scale=1, min_width=0):
                                    panel_log = gr.HTML(visible=False)
                                    panel_holdings = gr.Dataframe(
                                        label="Holdings",
                                        headers=HOLDINGS_COLUMNS,
                                        row_count=(5, "dynamic"),
                                        col_count=2,
                                        elem_classes=["detail-scroll-table"],
                                        interactive=False,
                                        visible=False,
                                    )
                                with gr.Column(scale=1, min_width=0):
                                    panel_transactions = gr.Dataframe(
                                        label="Recent Transactions (UTC)",
                                        headers=TRANSACTION_COLUMNS,
                                        row_count=(8, "dynamic"),
                                        col_count=5,
                                        elem_classes=["compare-trader-tx-table"],
                                        interactive=False,
                                        visible=False,
                                    )
                            compare_trader_panels.append(
                                CompareTraderPanelComponents(
                                    name=trader.name,
                                    header=panel_header,
                                    log=panel_log,
                                    holdings=panel_holdings,
                                    transactions=panel_transactions,
                                )
                            )

        refs = DashboardRefs(
            state=state,
            active_trader_control=active_trader_control,
            compare_mode_control=compare_mode_control,
            compare_selection_control=compare_selection_control,
            compare_chart_mode_control=compare_chart_mode_control,
            compare_tx_limit_control=compare_tx_limit_control,
            view_all_logs_control=view_all_logs_control,
            summary_cards=summary_cards,
            compare_trader_panels=compare_trader_panels,
            detail_header=detail_header,
            detail_chart=detail_chart,
            detail_log=detail_log,
            detail_holdings=detail_holdings,
            detail_transactions=detail_transactions,
            compare_helper=compare_helper,
            compare_metrics=compare_metrics,
            compare_chart=compare_chart,
            compare_transactions=compare_transactions,
        )
        dashboard_outputs = _all_dashboard_outputs(refs)

        def render_from_state(current_state):
            return controller.render_dashboard(current_state, reload_data=False)

        def select_from_card(current_state, trader_name):
            next_state = set_active_trader(current_state, trader_name, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def toggle_card_compare(checked, current_state, trader_name):
            next_state = toggle_compare_trader(
                current_state, trader_name, checked, controller.trader_names
            )
            return controller.render_dashboard(next_state, reload_data=False)

        def on_active_control_change(active_name, current_state):
            next_state = set_active_trader(current_state, active_name, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def on_compare_mode_change(enabled, current_state):
            next_state = set_compare_mode(current_state, enabled, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def on_compare_selection_change(selected_names, current_state):
            next_state = update_compare_selection(current_state, selected_names, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def on_compare_chart_mode_change(mode, current_state):
            next_state = set_compare_chart_mode(current_state, mode, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def on_compare_tx_limit_change(limit, current_state):
            next_state = set_compare_tx_limit(current_state, limit, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        def on_view_all_logs_change(enabled, current_state):
            next_state = set_view_all_logs(current_state, enabled, controller.trader_names)
            return controller.render_dashboard(next_state, reload_data=False)

        for card in summary_cards:
            card.select_button.click(
                fn=lambda current_state, trader_name=card.name: select_from_card(
                    current_state, trader_name
                ),
                inputs=[state],
                outputs=dashboard_outputs,
                show_progress="hidden",
                queue=False,
            )
            card.compare_checkbox.change(
                fn=lambda checked, current_state, trader_name=card.name: toggle_card_compare(
                    checked, current_state, trader_name
                ),
                inputs=[card.compare_checkbox, state],
                outputs=dashboard_outputs,
                show_progress="hidden",
                queue=False,
            )

        active_trader_control.change(
            fn=on_active_control_change,
            inputs=[active_trader_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )
        compare_mode_control.change(
            fn=on_compare_mode_change,
            inputs=[compare_mode_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )
        compare_selection_control.change(
            fn=on_compare_selection_change,
            inputs=[compare_selection_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )
        compare_chart_mode_control.change(
            fn=on_compare_chart_mode_change,
            inputs=[compare_chart_mode_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )
        compare_tx_limit_control.change(
            fn=on_compare_tx_limit_change,
            inputs=[compare_tx_limit_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )
        view_all_logs_control.change(
            fn=on_view_all_logs_change,
            inputs=[view_all_logs_control, state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )

        ui.load(
            fn=render_from_state,
            inputs=[state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )

        data_timer = gr.Timer(value=120)
        data_timer.tick(
            fn=lambda current_state: controller.render_dashboard(current_state, reload_data=True),
            inputs=[state],
            outputs=dashboard_outputs,
            show_progress="hidden",
            queue=False,
        )

        log_timer = gr.Timer(value=0.5)
        log_timer.tick(
            fn=controller.refresh_active_log,
            inputs=[state, detail_log],
            outputs=[detail_log],
            show_progress="hidden",
            queue=False,
        )

    return ui


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(inbrowser=True)
