from enum import Enum

css = """
.trader-grid-summary {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    align-items: stretch !important;
    gap: 10px;
}
.trader-grid-summary > * {
    min-width: 0 !important;
}
.summary-card-shell {
    min-width: 0 !important;
}
.summary-card {
    height: 100%;
    background: linear-gradient(180deg, #11131a, #0b0d12) !important;
    border: 1px solid #202533 !important;
    border-radius: 10px !important;
    padding: 10px !important;
}
.summary-card-controls {
    align-items: center !important;
    gap: 8px;
}
.summary-card-controls .gradio-checkbox {
    margin-top: 0 !important;
}
.summary-card-title-wrap {
    min-height: 68px;
    text-align: center;
    border: 1px solid #202533;
    border-radius: 8px;
    padding: 8px 6px 6px;
    background: #121620;
}
.summary-card-title-wrap.is-selected {
    border-color: #3ea0ff;
    box-shadow: 0 0 0 1px rgba(62,160,255,0.25) inset;
}
.summary-card-title-wrap.is-compared {
    background: #141a24;
}
.summary-title-main {
    font-size: 2rem;
    line-height: 1.05;
    font-weight: 700;
    white-space: nowrap;
}
.summary-title-sub {
    font-size: 1rem;
    color: #c8cbd4;
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.summary-badges {
    min-height: 20px;
    margin-top: 4px;
}
.summary-badge {
    display: inline-block;
    font-size: 0.72rem;
    line-height: 1;
    border-radius: 999px;
    padding: 4px 7px;
    margin: 0 3px;
    border: 1px solid transparent;
}
.summary-badge-active {
    background: rgba(62,160,255,0.15);
    border-color: rgba(62,160,255,0.35);
    color: #91c7ff;
}
.summary-badge-compare {
    background: rgba(0,221,170,0.12);
    border-color: rgba(0,221,170,0.3);
    color: #78f4d3;
}
.summary-pnl-strip {
    margin-top: 8px;
    border-radius: 8px;
    text-align: center;
    padding: 8px 6px;
}
.summary-pnl-value {
    font-size: 1.15rem;
    font-weight: 700;
    color: #fff;
    margin-right: 10px;
}
.summary-pnl-change {
    font-size: 0.95rem;
    font-weight: 700;
    color: #fff;
}
.summary-meta {
    min-height: 68px;
    margin-top: 8px;
    border-radius: 8px;
    padding: 8px;
    background: #0e1219;
    border: 1px solid #1b2230;
    font-size: 0.8rem;
    line-height: 1.35;
    color: #c8d2e3;
    overflow: hidden;
}
.summary-meta-log {
    color: #99b6d8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.workspace-controls {
    margin-top: 10px;
    border: 1px solid #1b2230 !important;
    border-radius: 10px !important;
    padding: 8px !important;
    background: #0f1218 !important;
}
.workspace-panel {
    margin-top: 10px;
    border: 1px solid #1b2230;
    border-radius: 12px;
    padding: 10px;
    background: #0c1016;
}
.detail-header {
    border-radius: 10px;
    border: 1px solid #1f2836;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #121722;
}
.detail-header-main {
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.15;
}
.detail-header-sub {
    margin-top: 4px;
    font-size: 0.9rem;
    color: #b7bfd0;
}
.detail-scroll-table .table-wrap {
    height: 260px !important;
    min-height: 260px !important;
    max-height: 260px !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
}
.compare-scroll-table .table-wrap {
    height: 320px !important;
    min-height: 320px !important;
    max-height: 320px !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
}
.compare-helper {
    border-radius: 10px;
    border: 1px solid #1f2836;
    padding: 10px 12px;
    margin-bottom: 10px;
    background: #121722;
    color: #d0d8e7;
}
.compare-helper.muted {
    color: #a9b5c7;
}
.compare-helper.warning {
    border-color: rgba(255, 196, 61, 0.35);
    background: rgba(255, 196, 61, 0.06);
}
.compare-helper.success {
    border-color: rgba(0, 221, 170, 0.30);
    background: rgba(0, 221, 170, 0.06);
}
.compare-explorer-group {
    margin-top: 10px;
    border-top: 1px solid #1b2230;
    padding-top: 8px;
}
.compare-trader-panel-header {
    border-radius: 10px;
    border: 1px solid #1f2836;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #121722;
}
.compare-trader-panel-title {
    font-size: 1.05rem;
    font-weight: 700;
}
.compare-trader-panel-sub {
    margin-top: 4px;
    font-size: 0.85rem;
    color: #b7bfd0;
}
.compare-trader-panel-status {
    margin-top: 6px;
}
.compare-trader-grid {
    align-items: start !important;
    gap: 10px;
}
.compare-trader-tx-table .table-wrap {
    height: 520px !important;
    min-height: 520px !important;
    max-height: 520px !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
}
@media (max-width: 1700px) {
    .summary-title-main {
        font-size: 1.65rem;
    }
    .summary-title-sub {
        font-size: 0.9rem;
    }
    .summary-meta {
        font-size: 0.75rem;
    }
}
.positive-pnl {
    color: green !important;
    font-weight: bold;
}
.positive-bg {
    background-color: green !important;
    font-weight: bold;
}
.negative-bg {
    background-color: red !important;
    font-weight: bold;
}
.negative-pnl {
    color: red !important;
    font-weight: bold;
}
footer{display:none !important}
"""


js = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

class Color(Enum):
    RED = "#dd0000"
    GREEN = "#00dd00"
    YELLOW = "#dddd00"
    BLUE = "#0000ee"
    MAGENTA = "#aa00dd"
    CYAN = "#00dddd"
    WHITE = "#87CEEB"
