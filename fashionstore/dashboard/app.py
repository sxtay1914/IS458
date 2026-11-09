"""FashionStore — Cloud Resiliency & Test Control Center.

A Streamlit dashboard for IS458 (Cloud Management and Engineering).
Designed for clean aesthetics, executive presentations, and chaos drills.
"""
import os
import sys
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import textwrap

def render_html(raw_html: str):
    """Render raw HTML safely without Markdown parser turning indented lines into code blocks."""
    st.markdown(textwrap.dedent(raw_html).strip(), unsafe_allow_html=True)

# Setup import path
DASHBOARD_DIR = Path(__file__).resolve().parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import importlib
import controller as controller_mod
import animations as animations_mod

# Force dynamic reload of internal modules to prevent stale bytecode in running Streamlit sessions
importlib.reload(controller_mod)
importlib.reload(animations_mod)

from controller import TestController
from animations import (
    render_payment_outage_animation,
    render_dlq_redrive_animation,
    render_pod_kill_animation,
    render_reconciler_animation,
    render_flash_sale_animation,
)

# Page Configuration
st.set_page_config(
    page_title="FashionStore — Cloud Resiliency Control Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Polished, Eye-Friendly CSS (works harmoniously in both Light and Dark themes)
st.markdown("""
<style>
    /* Global layout enhancements */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 1;
    }
    .block-container {
        padding-top: 4.5rem;
        padding-bottom: 2.5rem;
        max-width: 1300px;
    }
    
    /* Header Card */
    .header-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 24px 28px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .header-title {
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin: 0;
    }
    
    /* Status Badges */
    .pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 8px;
        margin-top: 8px;
    }
    .pill-online {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .pill-info {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .pill-neutral {
        background-color: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    .pill-warning {
        background-color: rgba(239, 68, 68, 0.18);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    
    /* Action Cards */
    .test-card {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 18px;
        transition: all 0.2s ease-in-out;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .test-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }
    .card-title {
        font-size: 17px;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .card-desc {
        color: #94a3b8;
        font-size: 13.5px;
        line-height: 1.5;
        margin-bottom: 14px;
    }
    .card-guide {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 13px;
        line-height: 1.5;
        margin-top: 10px;
    }
    .badge-fault {
        display: inline-block;
        background: rgba(239, 68, 68, 0.18);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 4px;
    }
    .badge-safety {
        display: inline-block;
        background: rgba(16, 185, 129, 0.18);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 4px;
    }
    .badge-cw {
        display: inline-block;
        background: rgba(59, 130, 246, 0.18);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 4px;
    }
    
    /* Console & Output Box */
    .console-header {
        font-family: monospace;
        font-size: 13px;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Primary Action Buttons: Crisp Indigo / Executive Blue instead of Streamlit Default Red */
    button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        border: 1px solid #4f46e5 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
        border-color: #4338ca !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
        color: #ffffff !important;
    }
    button[kind="primary"]:active {
        background: #3730a3 !important;
        color: #ffffff !important;
    }
    
    /* Secondary Action Buttons (Update, Reset, Refresh) */
    button[kind="secondary"] {
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Controller (always ensure fresh instance of reloaded class)
if "controller" not in st.session_state or type(st.session_state.controller) is not controller_mod.TestController:
    st.session_state.controller = controller_mod.TestController()
controller = st.session_state.controller

# Fetch live system state
sys_status = controller.get_system_status()
creds = sys_status["credentials"]
is_deployed = sys_status["is_deployed"]
region = sys_status["region"]
site_url = sys_status["storefront_url"]

# Direct AWS Links (with high-res 15-minute window)
cw_link = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards/dashboard/fashionstore-demo-overview?start=PT15M&end=PT0M"
ce_link = "https://console.aws.amazon.com/costmanagement/home#/cost-explorer"
bg_link = "https://console.aws.amazon.com/billing/home#/budgets"

# =============================================================================
# HEADER SECTION
# =============================================================================
account_label = creds["account"] if creds["active"] else "Not Connected"
status_class = "pill-online" if is_deployed else "pill-neutral"
status_text = "● Infrastructure Live" if is_deployed else "○ Stack Idle"

st.markdown(f"""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
            <div class="header-title">⚡ FashionStore Control Center</div>
            <p class="header-subtitle">SMU IS458: Cloud Management and Engineering &nbsp;|&nbsp; Resilience & Chaos Engineering</p>
        </div>
        <div>
            <span class="pill-badge {status_class}">{status_text}</span>
            <span class="pill-badge pill-info">AWS {region}</span>
            <span class="pill-badge pill-neutral">Account {account_label}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Quick Navigation Bar
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1.1, 1.3, 1.1, 0.9])

with nav_col1:
    if site_url and site_url.startswith("http"):
        st.markdown(f"🛍️ [**Open Web UI**]({site_url})")
    else:
        st.markdown("🛍️ **Web UI:** `Not deployed`")

with nav_col2:
    st.markdown(f"📊 [**Open CloudWatch Dashboard**]({cw_link})")

with nav_col3:
    st.markdown(f"💰 [**AWS Cost Explorer**]({ce_link})")

with nav_col4:
    if st.button("🔄 Refresh State", use_container_width=True):
        st.rerun()

st.write("")


# =============================================================================
# LOG STREAMING HELPER
# =============================================================================
def run_action_with_logs(title: str, action_fn):
    st.markdown("---")
    st.markdown(f"#### 📟 Execution: {title}")
    
    log_box = st.empty()
    logs = [f"> Initializing {title}..."]
    log_box.code("\n".join(logs), language="bash")

    def log_callback(msg: str):
        logs.append(msg)
        log_box.code("\n".join(logs[-22:]), language="bash")

    with st.spinner(f"Executing {title}..."):
        success = action_fn(log_callback)

    import datetime
    st.session_state[f"last_exec_{title}"] = {
        "title": title,
        "logs": list(logs),
        "success": success,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    }

    if success:
        st.success(f"🎉 **{title} Passed Successfully!** All health criteria verified.")
    else:
        st.error(f"⚠️ **{title} Completed with Errors.** Inspect terminal output above.")


# =============================================================================
# MAIN INTERACTIVE TABS
# =============================================================================
tab_chaos, tab_load = st.tabs([
    "⚡ Failure & Chaos Drills",
    "🚀 Load & Concurrency (k6)",
])

# -----------------------------------------------------------------------------
# TAB 1: Chaos & Failure Drills
# -----------------------------------------------------------------------------
with tab_chaos:
    st.markdown("### ⚡ Chaos Engineering & Resilience Control")
    st.caption("Select a chaos failure scenario from the dropdown below to review its architecture flow diagram, inspect platform safety defense mechanisms, and trigger live fault injection on AWS.")

    drill_options = [
        "💥 Drill 1: Payment Outage & SQS Retry (Transient Banking Downtime)",
        "☠️ Drill 2: DLQ Redrive & Order Recovery (Failed Message Quarantine)",
        "💀 Drill 3: Abrupt Pod Kill & Zero-Downtime HA (Compute Failover)",
        "🔌 Drill 4: SQS Disconnect & Outbox Reconciler (Network Partition Recovery)",
        "⚡ Drill 5: Flash Sale Atomic Inventory Lock (Zero Oversell Concurrency)",
    ]

    selected_drill_key = st.selectbox(
        "Select Chaos Drill to Inspect & Execute:",
        drill_options,
        index=0,
        key="main_drill_selector",
    )

    drill_data = {
        "💥 Drill 1: Payment Outage & SQS Retry (Transient Banking Downtime)": {
            "title": "💥 Payment Outage & SQS Retry Drill",
            "desc": "Simulates a downstream banking gateway outage by throttling payment worker concurrency to zero.",
            "anim_fn": render_payment_outage_animation,
            "does": "Validates the test shopper and cart, then throttles <code>payment-api</code> Lambda concurrency to 0 and submits a real checkout. Restores the original concurrency after the outage.",
            "safety": "<b>Asynchronous Checkout Recovery</b>: Verifies <code>202 Accepted</code> and <code>PENDING</code> during the outage, then polls for up to 420s after payment is restored. The wait allows for SQS's 180s visibility timeout. Success means this checkout was accepted during the outage and subsequently <code>CONFIRMED</code>; it does not establish whether a worker attempted payment during the outage.",
            "cw_proof": [
                "<i>Payment API Failures</i>: <code>payment-api Throttles</code> rises above 0.",
                "<i>process-checkout</i>: Inspect worker logs for retry failures and the eventual checkout outcome.",
                "<i>Checkout queue</i>: Observe message age while pending and queue drainage after recovery.",
                "<i>DLQ depth</i>: Check for quarantined messages; an empty DLQ alone does not prove checkout recovery.",
            ],
            "target": "Lambda: payment-api (concurrency: 0)",
            "duration": "Up to ~8 minutes for outage/recovery, plus sign-in (180s SQS retry wait)",
            "btn_label": "Run Payment Outage Drill",
            "btn_key": "btn_run_payment",
            "action": lambda cb: controller.run_payment_outage_drill(cb),
        },
        "☠️ Drill 2: DLQ Redrive & Order Recovery (Failed Message Quarantine)": {
            "title": "☠️ DLQ Redrive & Order Recovery Drill",
            "desc": "Quarantines failed order payloads into the Dead-Letter Queue to protect workers, then redrives them to complete processing.",
            "anim_fn": render_dlq_redrive_animation,
            "does": "Parks an unacknowledged order payload in the DLQ, then dispatches an SQS redrive task to move it back to the checkout queue for worker processing.",
            "safety": "<b>Dead-Letter Queue Isolation (maxReceiveCount = 5)</b>: Prevents failing messages from monopolizing workers (head-of-line blocking). Once downstream dependencies recover, operators redrive them via <code>start_message_move_task</code> without losing orders.",
            "cw_proof": [
                "<i>SQS Control Plane</i>: SQS <code>start_message_move_task</code> transitions DLQ depth <b>0 ➔ 1 ➔ 0</b>.",
                "<i>Main Pipeline Consumer</i>: Redriven message is picked up by <code>process-checkout</code> and confirmed.",
                "<i>Alarm Logic</i>: <code>checkout-dlq-not-empty</code> monitors 5-min intervals; sub-minute redrives resolve before breach.",
            ],
            "target": "SQS: checkout-dlq & move_task",
            "duration": "~40 seconds",
            "btn_label": "Run DLQ Redrive Drill",
            "btn_key": "btn_run_dlq",
            "action": lambda cb: controller.run_poison_dlq_drill(cb),
        },
        "💀 Drill 3: Abrupt Pod Kill & Zero-Downtime HA (Compute Failover)": {
            "title": "💀 Abrupt Pod Kill & Zero-Downtime HA Drill",
            "desc": "Instantly kills an active Kubernetes container pod during live shopper browsing to verify failover.",
            "anim_fn": render_pod_kill_animation,
            "does": "Executes an ungraceful termination (<code>kubectl delete pod --now</code>) on a live backend pod while continuous HTTP requests hit the API.",
            "safety": "<b>PodDisruptionBudget (PDB) & ALB TargetGroupBinding</b>: Multi-replica deployment and PDB (<code>minAvailable: 1</code>) ensure surviving pods handle traffic. The ALB stops routing to the dead IP, while Kubernetes ReplicaSet schedules a replacement pod.",
            "cw_proof": [
                "<i>Target 5XX Errors</i>: Stays strictly at <b>0</b> (proves zero 502/504 errors leaked to shoppers during pod kill).",
                "<i>Kubernetes ReplicaSet</i>: Automatically provisions a replacement container in <2 seconds.",
                "<i>ALB Zero-Downtime Routing</i>: Surviving replica absorbs all traffic without dropping connections.",
            ],
            "target": "EKS: pod/store-api-v1-*",
            "duration": "~25 seconds",
            "btn_label": "Run Pod Kill Drill",
            "btn_key": "btn_run_podkill",
            "action": lambda cb: controller.run_pod_kill_drill(cb),
        },
        "🔌 Drill 4: SQS Disconnect & Outbox Reconciler (Network Partition Recovery)": {
            "title": "🔌 SQS Disconnect & Outbox Reconciler Drill",
            "desc": "Breaks network connectivity between Kubernetes pods and SQS, then tests background reconciliation.",
            "anim_fn": render_reconciler_animation,
            "does": "Injects a bogus queue endpoint into EKS deployment environment variables while a customer places an order.",
            "safety": "<b>Transactional Outbox Pattern</b>: When SQS is unreachable, the API persists the order locally in MySQL as <code>PENDING</code> and returns <code>202 Accepted</code>. A background scheduler (<code>Reconciler.java</code>) sweeps MySQL every 15s and pushes delayed checkouts once SQS recovers.",
            "cw_proof": [
                "<i>During partition</i>: <code>Checkout queue</code> receives 0 messages, but HTTP 202 is returned.",
                "<i>After recovery</i>: Delayed messages suddenly arrive in <code>Checkout queue</code> as the reconciler flushes, and <code>process-checkout</code> confirms the order.",
            ],
            "target": "EKS Env: SQS_ENDPOINT override",
            "duration": "~2 minutes",
            "btn_label": "Run SQS Partition Drill",
            "btn_key": "btn_run_reconciler",
            "action": lambda cb: controller.run_pytest("failure/test_dispatch_recovery.py", allow_chaos=True, log_cb=cb),
        },
        "⚡ Drill 5: Flash Sale Atomic Inventory Lock (Zero Oversell Concurrency)": {
            "title": "⚡ Flash Sale Atomic Inventory Lock Drill",
            "desc": "Fires 60 simultaneous checkout requests at the exact same millisecond competing for 50 limited inventory items.",
            "anim_fn": render_flash_sale_animation,
            "does": "Blasts high-concurrency checkouts against a constrained inventory pool to test database row locks.",
            "safety": "<b>Row-Level Atomic Decrement (<code>UPDATE ... WHERE stock >= ?</code>)</b>: MySQL 8.4 executes atomic conditional decrements without full-table locks or deadlocks. Guarantees <b>exactly 50 confirmed orders</b> and 10 clean out-of-stock rejections, with zero negative inventory.",
            "cw_proof": [
                "<i>RDS</i>: Database connections and CPU spike cleanly without saturation.",
                "<i>process-checkout</i>: 50 orders confirm, 10 decline as <code>OUT_OF_STOCK</code>.",
                "<i>Checkout queue</i>: Drains to 0 with DLQ depth staying at 0.",
            ],
            "target": "MySQL 8.4: inventory row-level locks",
            "duration": "~30 seconds",
            "btn_label": "Run Flash Sale Concurrency Drill",
            "btn_key": "btn_run_flash",
            "action": lambda cb: controller.run_k6_test("flash-sale.js", profile="demo", log_cb=cb),
        },
    }

    drill = drill_data[selected_drill_key]

    # 1. Visualization (only if animated component exists for this drill)
    if drill.get("anim_fn"):
        components.html(drill["anim_fn"](), height=490, scrolling=False)

    st.write("")

    # 2. Drill Details and Live AWS Action Panel (Clean 2-Column Split)
    d_col1, d_col2 = st.columns([1.65, 1.35])

    with d_col1:
        cw_proof_html = "<br>".join([f"• {p}" for p in drill["cw_proof"]])
        render_html(f"""
        <div class="test-card" style="margin-bottom: 0px;">
            <div>
                <div class="card-title">{drill['title']}</div>
                <div class="card-desc">{drill['desc']}</div>
                <div class="card-guide">
                    <p style="margin: 0 0 8px 0;"><span class="badge-fault">What Drill Does</span> {drill['does']}</p>
                    <p style="margin: 0 0 8px 0;"><span class="badge-safety">Safety Mechanism</span> {drill['safety']}</p>
                    <p style="margin: 0;"><span class="badge-cw">CloudWatch Proof</span><br>{cw_proof_html} <a href="{cw_link}" target="_blank">View Dashboard ↗</a></p>
                </div>
            </div>
        </div>
        """)

    with d_col2:
        render_html(f"""
        <div class="test-card" style="margin-bottom: 12px;">
            <div class="card-title">⚡ Live Fault Injection</div>
            <div style="font-size: 13px; color: #94a3b8; margin: 10px 0 6px 0; line-height: 1.7;">
                <div>🎯 <b>Target</b>: <code>{drill['target']}</code></div>
                <div>⏱️ <b>Duration</b>: {drill['duration']}</div>
                <div>🌏 <b>Environment</b>: AWS Singapore (<code>ap-southeast-1</code>)</div>
            </div>
        </div>
        """)
        action_clicked = st.button(drill["btn_label"], key=drill["btn_key"], type="primary", use_container_width=True)
        if action_clicked:
            run_action_with_logs(drill["title"], drill["action"])
        elif f"last_exec_{drill['title']}" in st.session_state:
            last = st.session_state[f"last_exec_{drill['title']}"]
            st.markdown(f"**Last Run Output** (Completed at `{last['timestamp']}`):")
            st.code("\n".join(last["logs"][-22:]), language="bash")
            if last["success"]:
                st.success(f"🎉 **{drill['title']} Passed!**")
            else:
                st.error(f"⚠️ **{drill['title']} Completed with Errors.**")

    # 3. Contextual Real-Time CloudWatch Telemetry
    st.write("")
    st.markdown("---")
    t_col_title, t_col_auto, t_col_refresh, t_col_reset = st.columns([2.2, 1.2, 0.9, 1.1])
    with t_col_title:
        st.markdown(f"#### 📊 Real-Time Telemetry & Health")
        st.caption(f"Live telemetry queried from AWS APIs for {drill['title']}.")
    with t_col_auto:
        auto_poll = st.toggle("⏱️ Live Poll (5s)", value=True, key=f"auto_poll_{selected_drill_key}", help="Automatically poll AWS telemetry every 5 seconds hands-free")
    with t_col_refresh:
        if st.button("🔄 Update", key=f"btn_refresh_tel_{selected_drill_key}", use_container_width=True, help="Force refresh right now"):
            st.rerun()
    with t_col_reset:
        if st.button("🧹 Clear Display", key=f"btn_reset_drill_{selected_drill_key}", use_container_width=True, help="Clear saved output and restart the display baseline. AWS resources, queues and inventory are unchanged."):
            controller.reset_drill_state(drill["title"], st.session_state)
            st.toast("✨ Display history cleared and baseline restarted.", icon="🧹")
            time.sleep(0.5)
            st.rerun()

    @st.fragment(run_every=5 if auto_poll else None)
    def render_drill_telemetry_fragment(d_key, d_info):
        baseline_ts = st.session_state.get(f"drill_reset_time_{d_info['title']}")

        if "Drill 1" in d_key:
            tel = controller.get_payment_drill_telemetry(window_minutes=15, since_timestamp=baseline_ts)
            if tel.get("available"):
                s = tel["summary"]

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Payment Gateway",
                    s["concurrency"],
                    delta="Outage Injected" if "Throttled" in s["concurrency"] else "Enabled",
                    delta_color="inverse" if "Throttled" in s["concurrency"] else "normal",
                    help="Configured payment-api concurrency, not a health check. During Drill 1 it drops to 0.",
                )
                m2.metric(
                    "Payment Throttles (429)",
                    f"{s['throttles_15m']}",
                    delta="Fault Spike" if s["throttles_15m"] > 0 else "0 (Clean)",
                    delta_color="inverse" if s["throttles_15m"] > 0 else "normal",
                    help="Throttles recorded in CloudWatch (settles within 1–2m).",
                )
                m3.metric(
                    "Confirmed Orders",
                    f"{s['confirmed_checkouts']}",
                    delta="Recorded confirmations" if s["confirmed_checkouts"] > 0 else None,
                    delta_color="normal",
                    help="Orders confirmed since baseline.",
                )
                m4.metric(
                    "DLQ Depth",
                    f"{s['dlq_depth']}",
                    delta="Empty" if s["dlq_depth"] == 0 else f"{s['dlq_depth']} Quarantined",
                    delta_color="normal" if s["dlq_depth"] == 0 else "inverse",
                    help="Quarantined messages in DLQ. An empty queue does not prove every checkout succeeded.",
                )

                # Recent confirmation records from CloudWatch Logs.
                if s.get("confirmed_records"):
                    st.markdown("##### ⚡ Recent Confirmation Evidence from CloudWatch Logs")
                    records = s["confirmed_records"][-3:]
                    rec_cols = st.columns(len(records))
                    for idx, rec in enumerate(records):
                        with rec_cols[idx]:
                            st.success(f"**Order ID:** `{rec['checkout_id'][:8]}...`\n\n**Status:** `CONFIRMED`\n\n**Processed:** `{rec['time']}`")

                if tel.get("df") is not None and hasattr(tel["df"], "empty") and not tel["df"].empty:
                    st.caption("📈 **CloudWatch Metric History (Past 15 Minutes — 1-Min Interval, SGT):**")
                    st.line_chart(tel["df"], height=230)
                    st.caption("ℹ️ *CloudWatch metrics use 60-second periods. Both metrics and log events can arrive after a delay; the drill checks its checkout outcome through the API.*")

                if tel.get("recent_logs"):
                    with st.expander("📜 Full Lambda Worker Audit Log Stream (process-checkout)", expanded=False):
                        for l in tel["recent_logs"]:
                            st.code(l, language="json")
            else:
                st.warning(f"Telemetry unavailable: {tel.get('error', 'Unknown')}")

        elif "Drill 2" in d_key:
            tel = controller.get_dlq_drill_telemetry(window_minutes=15, since_timestamp=baseline_ts)
            if tel.get("available"):
                s = tel["summary"]

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Quarantined in DLQ",
                    f"{s['dlq_depth']}",
                    delta="0 (Clean)" if s["dlq_depth"] == 0 else f"{s['dlq_depth']} Quarantined",
                    delta_color="normal" if s["dlq_depth"] == 0 else "inverse",
                    help="Corrupted messages held in isolation in checkout-dlq to prevent poison pill crash-loops (0 = healthy baseline).",
                )
                m2.metric(
                    "Main Queue Backlog",
                    f"{s['main_depth']}",
                    delta="0 (Drained)" if s["main_depth"] == 0 else f"{s['main_depth']} Pending",
                    delta_color="normal",
                    help="Active checkout orders waiting in fashionstore-demo-checkout-requests for worker processing.",
                )
                m3.metric(
                    "SQS Redrive Status",
                    s["move_status"],
                    delta="API Dispatched" if s["move_status"] in ["RUNNING", "COMPLETED"] else None,
                    delta_color="normal",
                    help="Status of AWS SQS start_message_move_task control plane task.",
                )
                m4.metric(
                    "Messages Recovered",
                    f"{s['messages_moved']}",
                    delta="Zero Data Loss" if s["messages_moved"] > 0 else None,
                    delta_color="normal",
                    help="Messages moved back from DLQ to checkout queue and confirmed by worker Lambda.",
                )

                # Live Audit Proof Cards from CloudWatch Logs (<300ms)
                if s.get("confirmed_records"):
                    st.markdown("##### ⚡ Instant Audit Evidence (<300ms from CloudWatch Logs)")
                    records = s["confirmed_records"][-3:]
                    rec_cols = st.columns(len(records))
                    for idx, rec in enumerate(records):
                        with rec_cols[idx]:
                            st.success(f"**Order ID:** `{rec['checkout_id'][:8]}...`\n\n**Status:** `CONFIRMED`\n\n**Processed:** `{rec['time']}`")

                if tel.get("df") is not None and hasattr(tel["df"], "empty") and not tel["df"].empty:
                    st.caption("📈 **Queue Quarantine & Backlog History (Past 15 Minutes — 1-Min Interval, SGT):**")
                    st.line_chart(tel["df"], height=230)
                    st.caption("ℹ️ *Note: CloudWatch SQS metrics aggregate every 60s (points settle within 1–2 mins), while audit log events above reflect instantly.*")

                with st.expander("💡 Metric Definitions: What does 'Visible Messages' & 'DLQ Depth' mean?", expanded=False):
                    st.markdown("""
                    - **Quarantined in DLQ (`ApproximateNumberOfMessagesVisible` on DLQ)**: In AWS SQS terminology, a *"visible message"* is a message currently waiting in the queue and available to be fetched. Because a Dead-Letter Queue has **no continuous worker polling it**, visible messages in a DLQ represent **quarantined poison pills** isolated from production traffic to prevent head-of-line blocking. Normal baseline = **`0`**.
                    - **Main Queue Backlog (`ApproximateNumberOfMessagesVisible` on checkout-requests)**: Legitimate customer orders waiting in the primary buffer queue to be ingested by the `process-checkout` Lambda worker.
                    - **AWS SQS Redrive (`start_message_move_task`)**: An AWS native control plane operation that safely drains messages from a DLQ back into the primary queue for reprocessing without bespoke operator scripts.
                    """)

                if tel.get("move_task"):
                    with st.expander("🔍 Latest SQS Message Move Task Details (`list_message_move_tasks`)", expanded=False):
                        st.json(tel["move_task"])

                if tel.get("recent_logs"):
                    with st.expander("📜 Full Lambda Worker Audit Log Stream (process-checkout)", expanded=False):
                        for l in tel["recent_logs"]:
                            st.code(l, language="json")
            else:
                st.warning(f"Telemetry unavailable: {tel.get('error', 'Unknown')}")

        elif "Drill 3" in d_key:
            tel = controller.get_pod_drill_telemetry(window_minutes=15)
            if tel.get("available"):
                s = tel["summary"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("v1 Healthy Targets", f"{s['v1_healthy']} / {s['v1_total']}", help="Active healthy pods registered in ALB v1 target group")
                m2.metric("Target 5XX Errors", f"{s['target_5xx_15m']}", help="HTTP 502/504 errors on ALB (proves zero customer downtime)")
                m3.metric("v2 Canary Targets", f"{s['v2_healthy']} / {s['v2_total']}", help="Canary v2 pods registered in ALB")
                m4.metric("K8s Running Pods", f"{s['running_pods']}", help="Total store-api pods in fashionstore namespace")

                if tel.get("df") is not None and hasattr(tel["df"], "empty") and not tel["df"].empty:
                    st.caption("📈 **ALB Target Group Health & 5XX Errors (Past 15 Minutes — 1-Min Interval, SGT):**")
                    st.line_chart(tel["df"], height=230)
                    st.caption("ℹ️ *Why the healthy host line stays flat: Kubernetes ReplicaSet auto-heals and launches a replacement pod in ~1–2 seconds, which is faster than AWS CloudWatch's 60-second metric aggregation window. The core resilience proof is **Target 5XX Errors remaining strictly at 0**, verifying zero dropped requests during pod failure.*")

                if tel.get("pods"):
                    with st.expander("📦 Active Kubernetes Pod Inventory (`kubectl get pods`)", expanded=False):
                        for p in tel["pods"]:
                            ready_icon = "🟢" if p["ready"] else "🔴"
                            st.write(f"{ready_icon} **`{p['name']}`** — Status: `{p['phase']}` | Ready: `{p['ready']}` | Restarts: `{p['restarts']}`")
            else:
                st.warning(f"Telemetry unavailable: {tel.get('error', 'Unknown')}")

        elif "Drill 5" in d_key:
            tel = controller.get_flash_sale_drill_telemetry(window_minutes=15, since_timestamp=baseline_ts)
            if tel.get("available"):
                s = tel["summary"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Peak RDS CPU", f"{s['rds_cpu_peak']}%", help="Peak CPU utilization on MySQL 8.4")
                m2.metric("Active DB Connections", f"{s['rds_connections_peak']}", help="Concurrent connections to MySQL")
                m3.metric("Recent Confirmed Orders", f"{s['recent_confirmed']}", help="Orders processed since baseline")
                m4.metric("DLQ Depth", f"{s['dlq_depth']}", help="DLQ depth (zero poison pills)")

                if tel.get("df") is not None and hasattr(tel["df"], "empty") and not tel["df"].empty:
                    st.caption("📈 **RDS Database Load (Past 15 Minutes — 1-Min Interval, SGT):**")
                    st.line_chart(tel["df"], height=230)
            else:
                st.warning(f"Telemetry unavailable: {tel.get('error', 'Unknown')}")

        else:
            q_tel = controller.get_queue_telemetry()
            alarms = controller.get_cloudwatch_alarms()
            ok_alarms = sum(1 for a in alarms if a["state"] == "OK")
            alarm_cnt = len(alarms)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Checkout Queue Depth", q_tel.get("checkout_queue_visible", 0))
            m2.metric("DLQ Depth", q_tel.get("dlq_visible", 0))
            m3.metric("In-Flight Messages", q_tel.get("checkout_queue_in_flight", 0))
            m4.metric("CloudWatch Alarms OK", f"{ok_alarms} / {alarm_cnt}")

    render_drill_telemetry_fragment(selected_drill_key, drill)


# -----------------------------------------------------------------------------
# TAB 2: Load & Concurrency (k6)
# -----------------------------------------------------------------------------
with tab_load:
    st.markdown("### 🚀 Full System Load & Concurrency Benchmark")
    st.caption("Benchmark full system scalability, CloudFront CDN edge caching, SQS queue buffering, and database concurrency guarantees under synthetic load.")
    st.caption("Preflight requires distinct loadtest+N@example.com shoppers in this deployment and FS_TEST_PASSWORD. The selected profile determines the number of shoppers; missing or invalid tokens stop the run.")
    st.write("")

    l_col1, l_col2 = st.columns([1.65, 1.35])

    with l_col1:
        render_html(f"""
        <div class="test-card" style="margin-bottom: 0px;">
            <div>
                <div class="card-title">🧪 3-Stage Full System Benchmark Flow</div>
                <div class="card-desc">Executes the complete end-to-end synthetic load test across all architectural tiers sequentially:</div>
                <div class="card-guide">
                    <p style="margin: 0 0 10px 0;"><span class="badge-normal">Stage 1</span> <b>🌐 Catalog Browsing Ramp</b> (<code>tests/load/browse.js</code>)<br><span style="color: #94a3b8; font-size: 12.5px;">Ramps up shoppers browsing listings and categories. Validates CloudFront edge cache hit ratios (>80%) and ALB response times (p95 &lt; 200ms).</span></p>
                    <p style="margin: 0 0 10px 0;"><span class="badge-safety">Stage 2</span> <b>🛒 Asynchronous Checkout Surge</b> (<code>tests/load/checkout.js</code>)<br><span style="color: #94a3b8; font-size: 12.5px;">Sustained stream of authenticated orders. Proves SQS queue absorbs burst traffic while Lambda workers process without dropped orders or timeouts.</span></p>
                    <p style="margin: 0 0 10px 0;"><span class="badge-fault">Stage 3</span> <b>⚡ Flash Sale Atomic Concurrency Race</b> (<code>tests/load/flash-sale.js</code>)<br><span style="color: #94a3b8; font-size: 12.5px;">Buyers competing for limited stock simultaneously. Verifies MySQL row-level atomic locks (zero negative inventory).</span></p>
                    <p style="margin: 0; padding-top: 8px; border-top: 1px solid rgba(148, 163, 184, 0.15);"><span class="badge-cw">CloudWatch Proof</span><br><span style="color: #94a3b8; font-size: 12.5px;">Observe RDS connections/CPU spike, Checkout queue depth absorb bursts, and Target 5XX errors stay strictly at 0.</span> <a href="{cw_link}" target="_blank">View Dashboard ↗</a></p>
                </div>
            </div>
        </div>
        """)

    with l_col2:
        render_html(f"""
        <div class="test-card" style="margin-bottom: 12px;">
            <div class="card-title">⚡ Live Benchmark Execution</div>
            <div style="font-size: 13px; color: #94a3b8; margin: 10px 0 10px 0; line-height: 1.75;">
                <div>🎯 <b>Target</b>: CloudFront CDN & ALB Ingress</div>
                <div>🌏 <b>Environment</b>: AWS Singapore (<code>ap-southeast-1</code>)</div>
            </div>
        </div>
        """)

        bench_profile_choice = st.radio(
            "Benchmark Execution Profile:",
            [
                "⚡ Fast Presentation Demo (~75s) [Recommended]",
                "💨 Smoke Test (~2 mins)",
                "🏋️ Full System Stress (~10 mins)",
            ],
            index=0,
            key="bench_profile_choice",
        )
        selected_profile = "fast-demo" if "Fast Presentation Demo" in bench_profile_choice else ("smoke" if "Smoke Test" in bench_profile_choice else "demo")
        bench_action_title = f"Full System Load Benchmark ({selected_profile.upper()})"

        bench_clicked = st.button(f"🚀 Launch Benchmark ({selected_profile.upper()})", type="primary", use_container_width=True, key="btn_run_full_load")
        if bench_clicked:
            run_action_with_logs(
                bench_action_title,
                lambda cb: controller.run_full_load_suite(selected_profile, cb)
            )
        elif f"last_exec_{bench_action_title}" in st.session_state:
            last_b = st.session_state[f"last_exec_{bench_action_title}"]
            st.markdown(f"**Last Benchmark Output** (Completed at `{last_b['timestamp']}`):")
            st.code("\n".join(last_b["logs"][-22:]), language="bash")
            if last_b["success"]:
                st.success(f"🎉 **{bench_action_title} Passed!**")
            else:
                st.error(f"⚠️ **{bench_action_title} Completed with Warnings.**")

    # Real-Time Benchmark Telemetry
    st.write("")
    st.markdown("---")
    b_col_title, b_col_auto, b_col_refresh, b_col_reset = st.columns([2.2, 1.2, 0.9, 1.1])
    with b_col_title:
        st.markdown("#### 📊 Live Benchmark Telemetry")
        st.caption("Aggregated across CloudFront, ALB, SQS, and RDS MySQL.")
    with b_col_auto:
        auto_poll_b = st.toggle("⏱️ Live Poll (5s)", value=True, key="auto_poll_bench", help="Automatically poll benchmark telemetry every 5 seconds")
    with b_col_refresh:
        if st.button("🔄 Update", key="btn_refresh_bench_tel", use_container_width=True):
            st.rerun()
    with b_col_reset:
        if st.button("🧹 Clear Log", key="btn_reset_bench", use_container_width=True, help="Clear previous benchmark execution logs"):
            st.session_state.pop(f"last_exec_{bench_action_title}", None)
            st.toast("✨ Benchmark log cleared.", icon="🧹")
            st.rerun()

    @st.fragment(run_every=5 if auto_poll_b else None)
    def render_benchmark_telemetry_fragment():
        b_tel = controller.get_load_benchmark_telemetry(window_minutes=15)
        if b_tel.get("available"):
            bs = b_tel["summary"]
            bm1, bm2, bm3, bm4, bm5 = st.columns(5)
            bm1.metric("Total ALB Requests (15m)", f"{bs['total_requests']:,}", help="Total HTTP requests processed by ALB")
            bm2.metric("Target Latency (p95)", f"{bs['p95_latency_ms']} ms", help="ALB p95 response time")
            bm3.metric("Target 5XX Errors", f"{bs['target_5xx']}", help="HTTP 5XX errors on ALB (zero dropped requests)")
            bm4.metric("Store API Pods (HPA)", f"{bs.get('v1_pods', 2)} Pods", help=f"EKS HorizontalPodAutoscaler (Active replicas: {bs.get('v1_pods', 2)}, Range: {bs.get('hpa_range', '2-5')}, Target: 70% CPU)")
            bm5.metric("Peak RDS CPU", f"{bs['peak_cpu']}%", help="Peak MySQL 8.4 CPU utilization during load")

            st.caption("ℹ️ **Autoscaling & Elasticity Proof**: Kubernetes HorizontalPodAutoscaler (HPA) automatically scales `store-api-v1` between **2 and 5 pods** when CPU exceeds **70%**. ALB TargetGroupBinding registers/deregisters pods dynamically with zero dropped connections.")

            bc_col1, bc_col2 = st.columns(2)
            with bc_col1:
                if b_tel.get("df_traffic") is not None and hasattr(b_tel["df_traffic"], "empty") and not b_tel["df_traffic"].empty:
                    st.caption("📈 **ALB Ingress Traffic & Latency (Past 15m, SGT):**")
                    st.line_chart(b_tel["df_traffic"], height=220)
            with bc_col2:
                if b_tel.get("df_backend") is not None and hasattr(b_tel["df_backend"], "empty") and not b_tel["df_backend"].empty:
                    st.caption("📈 **RDS Database Load & Connections (Past 15m, SGT):**")
                    st.line_chart(b_tel["df_backend"], height=220)
        else:
            st.warning(f"Benchmark telemetry unavailable: {b_tel.get('error', 'Unknown')}")

    render_benchmark_telemetry_fragment()

