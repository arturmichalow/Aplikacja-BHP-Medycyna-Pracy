from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
LOGIN_BG = BASE_DIR / "assets" / "login_bg.png"


def inject_css():
    logo = base64.b64encode(LOGIN_BG.read_bytes()).decode("utf-8") if LOGIN_BG.exists() else ""

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: #eef2f7;
        }}

        .top-banner {{
            background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 55%, #22a6e3 100%);
            color: white;
            padding: 26px 22px;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,.12);
            margin-bottom: 14px;
        }}

        .top-banner h1 {{
            margin: 0;
            font-size: 32px;
            font-weight: 800;
        }}

        .badge-row {{
            margin-top: 10px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .badge {{
            background: rgba(255,255,255,.92);
            color: #334155;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 13px;
            display: inline-block;
        }}

        .metric-card {{
            background: white;
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 6px 18px rgba(15,23,42,.05);
            border: 1px solid #e5e7eb;
        }}

        .section-card {{
            background: white;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 6px 18px rgba(15,23,42,.05);
            border: 1px solid #e5e7eb;
        }}

        .status-overdue {{
            background: #fbe2e2;
            padding: 4px 8px;
            border-radius: 8px;
            color: #8a1c1c;
            font-weight: 600;
        }}

        .status-soon {{
            background: #f7ebd1;
            padding: 4px 8px;
            border-radius: 8px;
            color: #8a5a0a;
            font-weight: 600;
        }}

        .status-ok {{
            background: #dff3e5;
            padding: 4px 8px;
            border-radius: 8px;
            color: #11632c;
            font-weight: 600;
        }}

        .status-none {{
            background: #eceff3;
            padding: 4px 8px;
            border-radius: 8px;
            color: #475569;
            font-weight: 600;
        }}

        /* LOGIN */
        .login-wrap {{
            margin: -1rem;
            padding: 0;
            background: #eef2f7;
        }}

        .login-logo-bar {{
            width: 100%;
            height: 128px;
            background: #102a3b;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding-left: 150px;
            box-shadow: 0 8px 20px rgba(0,0,0,.10);
            margin-bottom: 0;
        }}

        .login-logo {{
            width: 210px;
            height: 64px;
            background-image: url('data:image/png;base64,{logo}');
            background-repeat: no-repeat;
            background-position: left center;
            background-size: contain;
        }}

        .login-card {{
            width: 100%;
            margin: 0;
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 22px 20px 18px 20px;
            box-shadow: none;
        }}

        .small-muted {{
            color: #64748b;
            font-size: 13px;
        }}

        .action-btn button {{
            background: #ff5a3c !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
        }}

        .secondary-btn button {{
            border-radius: 12px;
        }}

        /* SIDEBAR MENU */
        [data-testid="stSidebar"] .stButton > button {{
            width: 100% !important;
            border-radius: 10px !important;
            border: 1px solid #c8d0da !important;
            background: #ffffff !important;
            color: #1f2937 !important;
            padding: 10px 14px !important;
            text-align: left !important;
            transition: all 0.15s ease-in-out !important;
            box-shadow: none !important;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            background: #ff5a3c !important;
            color: #ffffff !important;
            border-color: #ff5a3c !important;
        }}

        [data-testid="stSidebar"] .stButton > button:focus {{
            border-color: #ff5a3c !important;
            box-shadow: 0 0 0 0.15rem rgba(255, 90, 60, 0.25) !important;
        }}

        .menu-active button {{
            background: #ff5a3c !important;
            color: white !important;
            border-color: #ff5a3c !important;
        }}

        .menu-active button:hover {{
            background: #ff5a3c !important;
            color: white !important;
            border-color: #ff5a3c !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_banner(user: dict, workers: int, referrals: int):
    st.markdown(
        f"""
        <div class='top-banner'>
            <h1>Aplikacja BHP / medycyna pracy</h1>
            <div style='margin-top:8px;font-weight:600;'>
                Import LMP poprawiony, PDF z zagrożeniami w sekcjach I-V, druga strona ze wzoru.
            </div>
            <div class='badge-row'>
                <span class='badge'>Użytkownik: {user.get('full_name', '')}</span>
                <span class='badge'>Rola: {user.get('role', '')}</span>
                <span class='badge'>Pracownicy: {workers}</span>
                <span class='badge'>Skierowania: {referrals}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    s = (status or "").upper()
    if "PO TERMINIE" in s:
        cls = "status-overdue"
    elif "30" in s:
        cls = "status-soon"
    elif "OK" in s:
        cls = "status-ok"
    else:
        cls = "status-none"
    return f"<span class='{cls}'>{status}</span>"