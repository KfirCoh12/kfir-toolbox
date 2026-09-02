"""Shared visual language for the Streamlit electrical-engineering tools.

The theme is deliberately restrained and information-first: dark control-room surfaces,
clear visual hierarchy, compact engineering typography, and semantic status colors.
"""
from html import escape

import streamlit as st


_THEME_CSS = r"""
<style>
:root {
  --bg: #07101d;
  --bg-elevated: #0b1626;
  --surface: #0f1c2e;
  --surface-2: #132238;
  --surface-3: #172a43;
  --line: #253a56;
  --line-soft: #1b2d46;
  --text: #eef5ff;
  --text-2: #b6c5d8;
  --text-3: #7f93ad;
  --accent: #36a7ff;
  --accent-soft: rgba(54, 167, 255, .14);
  --good: #39d98a;
  --good-soft: rgba(57, 217, 138, .12);
  --warn: #f7bf4f;
  --warn-soft: rgba(247, 191, 79, .13);
  --bad: #ff6874;
  --bad-soft: rgba(255, 104, 116, .12);
  --neutral: #8ca0b9;
  --radius: 10px;
  --radius-lg: 14px;
}

html, body, [class*="css"] {font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
.stApp {background: linear-gradient(180deg, #07101d 0%, #081321 100%); color: var(--text);}
.block-container {max-width: 1640px; padding: 1.35rem 2.25rem 3rem 2.25rem;}

/* Top-level page typography */
h1, h2, h3, h4 {color: var(--text); letter-spacing: -.025em;}
h1 {font-size: 2rem !important; font-weight: 720 !important; line-height: 1.15 !important;}
h2 {font-size: 1.38rem !important; font-weight: 680 !important; margin-top: 1.5rem !important;}
h3 {font-size: 1.08rem !important; font-weight: 650 !important; margin-top: 1.15rem !important;}
h4 {font-size: .95rem !important; font-weight: 650 !important;}
p, label, .stCaption {font-size: .88rem;}
small {color: var(--text-3);}

.hmi-page-header {display:flex; align-items:flex-start; justify-content:space-between; gap:1.5rem; padding:.35rem 0 1rem 0; border-bottom:1px solid var(--line-soft); margin-bottom:1.1rem;}
.hmi-page-title-wrap {max-width: 950px;}
.hmi-eyebrow {font-size:.66rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; color:var(--accent); margin-bottom:.28rem;}
.hmi-page-title {font-size:2rem; font-weight:730; letter-spacing:-.035em; line-height:1.08; margin:0; color:var(--text);}
.hmi-page-subtitle {font-size:.9rem; color:var(--text-2); line-height:1.5; margin:.45rem 0 0 0; max-width:900px;}
.hmi-context {display:flex; gap:.45rem; flex-wrap:wrap; justify-content:flex-end; padding-top:.25rem;}
.hmi-chip {display:inline-flex; align-items:center; min-height:28px; padding:.28rem .58rem; border:1px solid var(--line); border-radius:999px; color:var(--text-2); background:var(--surface); font-size:.73rem; font-weight:650; white-space:nowrap;}
.hmi-chip.accent {border-color:rgba(54,167,255,.35); background:var(--accent-soft); color:#9ed5ff;}
.hmi-chip.good {border-color:rgba(57,217,138,.35); background:var(--good-soft); color:#8cf0bc;}
.hmi-chip.warn {border-color:rgba(247,191,79,.35); background:var(--warn-soft); color:#ffd782;}
.hmi-chip.bad {border-color:rgba(255,104,116,.35); background:var(--bad-soft); color:#ff9ca5;}

.hmi-section {display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:1.35rem 0 .55rem 0;}
.hmi-section-title {font-size:1rem; font-weight:680; color:var(--text); letter-spacing:-.015em;}
.hmi-section-subtitle {font-size:.77rem; color:var(--text-3); margin-top:.14rem; line-height:1.4;}

/* Controls */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
  border-radius:8px !important;
  border-color:var(--line) !important;
  background:var(--surface) !important;
  min-height:38px;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {color:var(--text-2) !important; font-size:.78rem !important; font-weight:600 !important;}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-baseweb="select"] > div:focus-within {border-color:var(--accent) !important; box-shadow:0 0 0 1px rgba(54,167,255,.25) !important;}

/* Containers / panels */
[data-testid="stVerticalBlockBorderWrapper"] {background:var(--surface) !important; border:1px solid var(--line-soft) !important; border-radius:var(--radius-lg) !important; box-shadow:0 8px 24px rgba(0,0,0,.08);}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1rem 1.05rem !important;}
[data-testid="stExpander"] {background:rgba(15,28,46,.72) !important; border:1px solid var(--line-soft) !important; border-radius:var(--radius) !important; overflow:hidden;}
[data-testid="stExpander"] summary {font-size:.81rem !important; font-weight:650 !important; color:var(--text-2) !important;}

/* Buttons */
div.stButton > button {min-height:38px; border-radius:8px; border:1px solid var(--line); font-size:.8rem; font-weight:680; padding:.45rem .9rem;}
div.stButton > button[kind="primary"] {background:#177fca; border-color:#2699ec;}
div.stButton > button:hover {border-color:#3f6086;}

/* Metrics */
[data-testid="stMetric"] {background:var(--surface); border:1px solid var(--line-soft); border-radius:var(--radius); padding:.72rem .82rem; min-height:92px;}
[data-testid="stMetricLabel"] {font-size:.68rem !important; font-weight:700 !important; color:var(--text-3) !important; text-transform:uppercase; letter-spacing:.055em;}
[data-testid="stMetricValue"] {font-size:1.48rem !important; font-weight:650 !important; color:var(--text) !important;}

/* Data tables / editors */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {border:1px solid var(--line-soft); border-radius:var(--radius); overflow:hidden; background:var(--surface);}
[data-testid="stDataFrame"] [role="columnheader"], [data-testid="stDataEditor"] [role="columnheader"] {background:var(--surface-2) !important; color:var(--text-2) !important; font-weight:700 !important; font-size:.74rem !important;}
[data-testid="stDataFrame"] [role="gridcell"], [data-testid="stDataEditor"] [role="gridcell"] {font-size:.78rem !important;}

/* Alerts */
[data-testid="stAlert"] {border-radius:9px !important; border-width:1px !important; font-size:.8rem;}

/* Radios / tabs */
[data-testid="stRadio"] [role="radiogroup"] {gap:.35rem;}
[data-testid="stRadio"] label {background:var(--surface); border:1px solid var(--line-soft); border-radius:8px; padding:.42rem .68rem;}
[data-testid="stRadio"] label:has(input:checked) {background:var(--accent-soft); border-color:rgba(54,167,255,.45);}

/* Separators / captions */
hr {border-color:var(--line-soft) !important; margin:1.2rem 0 !important;}
.stCaption, [data-testid="stCaptionContainer"] {color:var(--text-3) !important; font-size:.74rem !important;}

/* Reduce Streamlit chrome dominance */
[data-testid="stHeader"] {background:rgba(7,16,29,.88); backdrop-filter:blur(8px);}
[data-testid="stSidebar"] {background:#091523; border-right:1px solid var(--line-soft);}

@media (max-width: 900px) {
  .block-container {padding-left:1rem; padding-right:1rem;}
  .hmi-page-header {display:block;}
  .hmi-context {justify-content:flex-start; margin-top:.75rem;}
}
</style>
"""


def apply_theme() -> None:
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def page_header(*, eyebrow: str, title: str, subtitle: str, chips: tuple[tuple[str, str], ...] = ()) -> None:
    chip_html = "".join(
        f'<span class="hmi-chip {escape(kind)}">{escape(text)}</span>' for text, kind in chips
    )
    st.markdown(
        f"""
        <div class="hmi-page-header">
          <div class="hmi-page-title-wrap">
            <div class="hmi-eyebrow">{escape(eyebrow)}</div>
            <div class="hmi-page-title">{escape(title)}</div>
            <div class="hmi-page-subtitle">{escape(subtitle)}</div>
          </div>
          <div class="hmi-context">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="hmi-section-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="hmi-section"><div><div class="hmi-section-title">{escape(title)}</div>{subtitle_html}</div></div>',
        unsafe_allow_html=True,
    )
