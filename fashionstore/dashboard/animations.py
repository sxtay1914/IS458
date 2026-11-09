"""FashionStore — Architecture Failure & Recovery Visualizer.

Creates responsive animated architecture diagrams with:
- Default auto-play sequence (Step 1: Normal -> Step 2: Fault ❌ -> Step 3: Safety 🛡️ -> Step 4: Self-Healing ✅)
- Step navigation buttons (◀ Prev Step / Next Step ▶) with auto-play toggle
- Live link severing animations, glowing fault pulses, and green recovery flows
- Synchronized stage narratives
"""
import json


def _build_interactive_container(
    anim_id: str,
    title: str,
    steps_data: list[dict],
    svg_content: str,
    update_svg_js: str,
    width: int = 760,
    height: int = 220,
) -> str:
    """Builds an unclipped, auto-playing HTML/JS/CSS animation card with Prev/Next step controls."""
    steps_json = json.dumps(steps_data)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}
    body {{
        background: transparent;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #e2e8f0;
        padding: 4px;
        user-select: none;
    }}
    .anim-card {{
        background: linear-gradient(145deg, #0b1120 0%, #0f172a 100%);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
    }}
    .anim-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .anim-title {{
        font-size: 15px;
        font-weight: 700;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .step-nav {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 8px;
        padding: 3px 6px;
        flex-shrink: 0;
    }}
    .nav-btn {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(148, 163, 184, 0.25);
        color: #f1f5f9;
        padding: 4px 10px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        transition: all 0.15s ease;
    }}
    .nav-btn:hover {{
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff;
        border-color: rgba(255, 255, 255, 0.4);
    }}
    .nav-btn:active {{
        transform: scale(0.96);
    }}
    .step-indicator {{
        font-size: 11px;
        font-weight: 700;
        color: #94a3b8;
        padding: 0 6px;
        min-width: 72px;
        text-align: center;
        letter-spacing: 0.3px;
    }}
    .auto-btn {{
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #34d399;
        padding: 4px 10px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }}
    .auto-btn:hover {{
        background: rgba(16, 185, 129, 0.3);
        color: #ffffff;
    }}
    .auto-btn.is-paused {{
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.4);
        color: #60a5fa;
    }}
    .auto-btn.is-paused:hover {{
        background: rgba(59, 130, 246, 0.3);
        color: #ffffff;
    }}
    .pulse-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        animation: statusPulse 1.6s infinite ease-in-out;
    }}
    @keyframes statusPulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}
    .progress-bar-track {{
        width: 100%;
        height: 3px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 2px;
        margin-bottom: 12px;
        overflow: hidden;
    }}
    .progress-bar-fill {{
        height: 100%;
        width: 25%;
        background: #3b82f6;
        transition: width 0.35s ease, background-color 0.35s ease;
    }}
    .svg-wrapper {{
        width: 100%;
        background: #060913;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 8px;
        overflow: hidden;
    }}
    .narrative-box {{
        background: rgba(15, 23, 42, 0.85);
        border-left: 4px solid #3b82f6;
        border-radius: 4px;
        padding: 9px 14px;
        margin-top: 10px;
        font-size: 13px;
        line-height: 1.45;
        color: #e2e8f0;
        min-height: 44px;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
        transition: all 0.3s ease;
    }}
    .narrative-badge {{
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        margin-right: 10px;
        flex-shrink: 0;
    }}
    .badge-normal {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }}
    .badge-fault {{ background: rgba(239, 68, 68, 0.22); color: #f87171; border: 1px solid rgba(239,68,68,0.45); }}
    .badge-safety {{ background: rgba(245, 158, 11, 0.22); color: #fbbf24; border: 1px solid rgba(245,158,11,0.45); }}
    .badge-recovery {{ background: rgba(16, 185, 129, 0.22); color: #34d399; border: 1px solid rgba(16,185,129,0.45); }}

    @keyframes packetFlow {{
        from {{ stroke-dashoffset: 40; }}
        to {{ stroke-dashoffset: 0; }}
    }}
    @keyframes flashCross {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 6px #ef4444); }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 14px #ef4444); }}
    }}
    @keyframes pulseRedHalo {{
        0%, 100% {{ stroke: #ef4444; stroke-width: 2.5; filter: drop-shadow(0 0 8px rgba(239,68,68,0.8)); }}
        50% {{ stroke: #7f1d1d; stroke-width: 1.5; filter: drop-shadow(0 0 2px rgba(239,68,68,0.2)); }}
    }}
    @keyframes pulseGreenHalo {{
        0%, 100% {{ stroke: #10b981; stroke-width: 2.5; filter: drop-shadow(0 0 8px rgba(16,185,129,0.8)); }}
        50% {{ stroke: #064e3b; stroke-width: 1.5; filter: drop-shadow(0 0 2px rgba(16,185,129,0.2)); }}
    }}
    @keyframes shakeNode {{
        0%, 100% {{ transform: translateX(0); }}
        20%, 60% {{ transform: translateX(-3px); }}
        40%, 80% {{ transform: translateX(3px); }}
    }}

    .flow-line {{
        stroke-dasharray: 6 6;
        animation: packetFlow 1.1s linear infinite;
    }}
    .flow-fast {{
        stroke-dasharray: 5 5;
        animation: packetFlow 0.6s linear infinite;
    }}
    .cross-icon {{
        animation: flashCross 1.2s infinite ease-in-out;
        transform-origin: center;
    }}
</style>
</head>
<body>
<div class="anim-card">
    <div class="anim-header">
        <div class="anim-title">
            <span>⚡</span>
            <span>{title}</span>
        </div>
        <div class="step-nav">
            <button class="nav-btn" id="prevBtn_{anim_id}" onclick="prevStep_{anim_id}()">◀ Prev</button>
            <span class="step-indicator" id="stepIndicator_{anim_id}">Step 1 of 4</span>
            <button class="nav-btn" id="nextBtn_{anim_id}" onclick="nextStep_{anim_id}()">Next ▶</button>
            <button class="auto-btn is-paused" id="autoBtn_{anim_id}" onclick="toggleAuto_{anim_id}()">
                <span>▶ Auto-Play</span>
            </button>
        </div>
    </div>

    <div class="progress-bar-track">
        <div class="progress-bar-fill" id="progress_{anim_id}"></div>
    </div>

    <div class="svg-wrapper">
        <svg viewBox="0 0 {width} {height}" style="width: 100%; height: auto; display: block;" xmlns="http://www.w3.org/2000/svg">
            {svg_content}
        </svg>
    </div>

    <div class="narrative-box" id="narrative_{anim_id}"></div>
</div>

<script>
(function() {{
    {update_svg_js}

    const steps = {steps_json};
    let currentStep = 1;
    let isAuto = false;
    let timer = null;

    function applyStep(stepNum) {{
        currentStep = stepNum;
        const data = steps[stepNum - 1];

        // Update step indicator
        const ind = document.getElementById("stepIndicator_{anim_id}");
        if (ind) ind.textContent = "Step " + stepNum + " of 4";

        // Update progress bar
        const prog = document.getElementById("progress_{anim_id}");
        if (prog) {{
            prog.style.width = (stepNum * 25) + "%";
            prog.style.backgroundColor = data.color;
        }}

        // Update narrative caption
        const nar = document.getElementById("narrative_{anim_id}");
        if (nar) {{
            nar.style.borderLeftColor = data.color;
            nar.innerHTML = `<span class="narrative-badge ${{data.badgeClass}}">${{data.badge}}</span> <span>${{data.text}}</span>`;
        }}

        // Trigger SVG visual updates
        if (typeof window["updateSvg_{anim_id}"] === "function") {{
            try {{
                window["updateSvg_{anim_id}"](stepNum);
            }} catch (err) {{
                console.error("SVG update error:", err);
            }}
        }}
    }}

    function updateAutoButtonUI() {{
        const btn = document.getElementById("autoBtn_{anim_id}");
        if (!btn) return;
        if (isAuto) {{
            btn.className = "auto-btn";
            btn.innerHTML = '<span class="pulse-dot"></span> <span>Auto-Play: ON</span>';
        }} else {{
            btn.className = "auto-btn is-paused";
            btn.innerHTML = '<span>▶ Auto-Play</span>';
        }}
    }}

    window["prevStep_{anim_id}"] = function() {{
        isAuto = false;
        clearInterval(timer);
        updateAutoButtonUI();
        let prev = currentStep - 1;
        if (prev < 1) prev = 4;
        applyStep(prev);
    }};

    window["nextStep_{anim_id}"] = function() {{
        isAuto = false;
        clearInterval(timer);
        updateAutoButtonUI();
        let next = (currentStep % 4) + 1;
        applyStep(next);
    }};

    window["toggleAuto_{anim_id}"] = function() {{
        isAuto = !isAuto;
        updateAutoButtonUI();
        if (isAuto) {{
            startTimer();
        }} else {{
            clearInterval(timer);
        }}
    }};

    function startTimer() {{
        clearInterval(timer);
        timer = setInterval(function() {{
            if (!isAuto) return;
            let next = (currentStep % 4) + 1;
            applyStep(next);
        }}, 3500);
    }}

    // Start at Step 1 with auto-play paused by default
    applyStep(1);
    updateAutoButtonUI();
}})();
</script>
</body>
</html>
"""


def render_payment_outage_animation() -> str:
    """Interactive architecture animation for Payment Outage Drill."""
    steps_data = [
        {
            "badge": "Step 1: Normal Traffic",
            "badgeClass": "badge-normal",
            "color": "#3b82f6",
            "text": "Shoppers place checkouts (HTTP 202). Messages enter SQS. Worker successfully calls payment-api Lambda to authorize charges.",
        },
        {
            "badge": "Step 2: Fault Injected",
            "badgeClass": "badge-fault",
            "color": "#ef4444",
            "text": "<code>payment-api</code> concurrency set to 0. Direct link is severed with a red ❌! Invocations throw 429 Throttles.",
        },
        {
            "badge": "Step 3: Safety Circuit",
            "badgeClass": "badge-safety",
            "color": "#f59e0b",
            "text": "SQS Visibility Timeout (180s) protects the order! The message is NOT dropped; it is safely retained in the queue for automated retry.",
        },
        {
            "badge": "Step 4: Self-Healing",
            "badgeClass": "badge-recovery",
            "color": "#10b981",
            "text": "Payment capacity restored. SQS redelivers the message, payment completes, and the order transitions to CONFIRMED in MySQL!",
        },
    ]

    svg_content = """
    <defs>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
        <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#fbbf24"/>
        </marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/>
        </marker>
    </defs>

    <!-- Node 1: Shopper -->
    <rect x="20" y="30" width="105" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="72" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">🛒 Shopper</text>
    <text x="72" y="68" fill="#94a3b8" font-size="10" text-anchor="middle">HTTP 202</text>

    <!-- Path 1 -> 2 -->
    <line x1="125" y1="55" x2="165" y2="55" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 2: EKS store-api -->
    <rect x="170" y="30" width="115" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="227" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">☸️ store-api</text>
    <text x="227" y="68" fill="#94a3b8" font-size="10" text-anchor="middle">Sends to SQS</text>

    <!-- Path 2 -> 3 -->
    <line x1="285" y1="55" x2="325" y2="55" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 3: SQS Queue -->
    <rect x="330" y="30" width="115" height="50" rx="8" id="sqsBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="387" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">📬 SQS Queue</text>
    <text x="387" y="68" fill="#94a3b8" font-size="10" id="sqsSub" text-anchor="middle">Buffers Requests</text>

    <!-- Path 3 -> 4 -->
    <line x1="445" y1="55" x2="485" y2="55" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 4: Worker Lambda -->
    <rect x="490" y="30" width="125" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="552" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">λ process-checkout</text>
    <text x="552" y="68" fill="#94a3b8" font-size="10" text-anchor="middle">Worker Consumer</text>

    <!-- Path 4 -> 5 (Worker to Payment) -->
    <g id="paymentLinkGroup">
        <line id="paymentLine" x1="552" y1="80" x2="552" y2="135" stroke="#38bdf8" stroke-width="2.5" class="flow-line" marker-end="url(#arr-blue)"/>
        <!-- Red Cross Element -->
        <g id="paymentCross" style="display: none;">
            <circle cx="552" cy="108" r="14" fill="#ef4444" fill-opacity="0.25" stroke="#ef4444" stroke-width="2" class="cross-icon"/>
            <text x="552" y="113" fill="#fca5a5" font-size="13" font-weight="bold" text-anchor="middle">❌</text>
        </g>
    </g>

    <!-- Node 5: payment-api Lambda -->
    <g id="paymentNodeGroup" transform="translate(480, 140)">
        <rect x="0" y="0" width="145" height="55" rx="8" id="paymentBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="72" y="25" fill="#f8fafc" font-size="12" font-weight="600" id="paymentTitle" text-anchor="middle">💳 payment-api</text>
        <text x="72" y="42" fill="#94a3b8" font-size="10" id="paymentSub" text-anchor="middle">Active Gateway</text>
    </g>

    <!-- Safety Loop: 180s SQS Visibility Retry Arc -->
    <g id="retryLoopGroup" style="display: none;">
        <path d="M 490 65 Q 435 118 390 85" fill="none" stroke="#fbbf24" stroke-width="2.5" class="flow-line" marker-end="url(#arr-amber)"/>
        <rect x="365" y="102" width="145" height="20" rx="4" fill="#0f172a" stroke="#f59e0b" stroke-width="1"/>
        <text x="437" y="116" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="bold" text-anchor="middle">🛡️ 180s Visibility Retry</text>
    </g>

    <!-- Node 6: MySQL Database -->
    <g id="mysqlNodeGroup" transform="translate(170, 140)">
        <rect x="0" y="0" width="160" height="55" rx="8" id="mysqlBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="80" y="25" fill="#f8fafc" font-size="12" font-weight="600" id="mysqlTitle" text-anchor="middle">🗄️ MySQL Database</text>
        <text x="80" y="42" fill="#38bdf8" font-size="10" id="mysqlSub" text-anchor="middle">Order Confirmed</text>
    </g>

    <!-- Outgoing Link: payment-api -> MySQL (Strictly within canvas bounds) -->
    <g id="mysqlLinkGroup">
        <line id="mysqlLine" x1="480" y1="167" x2="338" y2="167" stroke="#38bdf8" stroke-width="2.5" class="flow-line" marker-end="url(#arr-blue)"/>
        <g id="mysqlBadgeGroup">
            <rect x="375" y="156" width="65" height="22" rx="4" id="mysqlBadgeBox" fill="#0f172a" stroke="#38bdf8" stroke-width="1"/>
            <text x="407" y="171" id="mysqlBadgeText" fill="#38bdf8" font-size="10" font-weight="bold" text-anchor="middle">200 OK</text>
        </g>
    </g>
    """

    update_svg_js = """
    window["updateSvg_payment"] = function(step) {
        const pLine = document.getElementById("paymentLine");
        const pCross = document.getElementById("paymentCross");
        const pBox = document.getElementById("paymentBox");
        const pTitle = document.getElementById("paymentTitle");
        const pSub = document.getElementById("paymentSub");
        const retryLoop = document.getElementById("retryLoopGroup");
        const sqsBox = document.getElementById("sqsBox");
        const sqsSub = document.getElementById("sqsSub");
        const mLine = document.getElementById("mysqlLine");
        const mBadge = document.getElementById("mysqlBadgeGroup");
        const mBadgeBox = document.getElementById("mysqlBadgeBox");
        const mBadgeText = document.getElementById("mysqlBadgeText");
        const mBox = document.getElementById("mysqlBox");
        const mTitle = document.getElementById("mysqlTitle");
        const mSub = document.getElementById("mysqlSub");

        if (!pLine || !pCross || !pBox) return;

        if (step === 1) { // Normal
            pLine.setAttribute("stroke", "#38bdf8");
            pLine.setAttribute("marker-end", "url(#arr-blue)");
            pCross.style.display = "none";
            pBox.style.animation = "none";
            pBox.setAttribute("stroke", "#334155");
            pBox.setAttribute("fill", "#1e293b");
            pTitle.textContent = "💳 payment-api";
            pTitle.setAttribute("fill", "#f8fafc");
            pSub.textContent = "Active Gateway";
            pSub.setAttribute("fill", "#94a3b8");
            retryLoop.style.display = "none";
            sqsBox.setAttribute("stroke", "#334155");
            sqsBox.setAttribute("fill", "#1e293b");
            sqsSub.textContent = "Buffers Requests";

            if (mLine) { mLine.style.display = "block"; mLine.setAttribute("stroke", "#38bdf8"); mLine.setAttribute("marker-end", "url(#arr-blue)"); mLine.setAttribute("class", "flow-line"); }
            if (mBadge) mBadge.style.display = "block";
            if (mBadgeBox) { mBadgeBox.setAttribute("stroke", "#38bdf8"); mBadgeBox.setAttribute("fill", "#0f172a"); }
            if (mBadgeText) { mBadgeText.textContent = "200 OK"; mBadgeText.setAttribute("fill", "#38bdf8"); }
            if (mBox) { mBox.style.animation = "none"; mBox.setAttribute("stroke", "#334155"); mBox.setAttribute("fill", "#1e293b"); }
            if (mTitle) { mTitle.textContent = "🗄️ MySQL Database"; mTitle.setAttribute("fill", "#f8fafc"); }
            if (mSub) { mSub.textContent = "Order Confirmed"; mSub.setAttribute("fill", "#38bdf8"); }

        } else if (step === 2) { // Fault Injected
            pLine.setAttribute("stroke", "#ef4444");
            pLine.removeAttribute("marker-end");
            pCross.style.display = "block";
            pBox.style.animation = "pulseRedHalo 1.5s infinite ease-in-out, shakeNode 0.5s ease";
            pBox.setAttribute("stroke", "#ef4444");
            pBox.setAttribute("fill", "rgba(239, 68, 68, 0.12)");
            pTitle.textContent = "💥 payment-api";
            pTitle.setAttribute("fill", "#ef4444");
            pSub.textContent = "Concurrency = 0 (Throttled)";
            pSub.setAttribute("fill", "#fca5a5");
            retryLoop.style.display = "none";
            sqsBox.setAttribute("stroke", "#334155");
            sqsBox.setAttribute("fill", "#1e293b");

            if (mLine) mLine.style.display = "none";
            if (mBadge) mBadge.style.display = "none";
            if (mBox) { mBox.style.animation = "none"; mBox.setAttribute("stroke", "#334155"); mBox.setAttribute("fill", "#1e293b"); }
            if (mTitle) { mTitle.textContent = "🗄️ MySQL Database"; mTitle.setAttribute("fill", "#64748b"); }
            if (mSub) { mSub.textContent = "Awaiting Payment"; mSub.setAttribute("fill", "#64748b"); }

        } else if (step === 3) { // Safety Circuit
            pLine.setAttribute("stroke", "#ef4444");
            pLine.removeAttribute("marker-end");
            pCross.style.display = "block";
            retryLoop.style.display = "block";
            sqsBox.setAttribute("stroke", "#f59e0b");
            sqsBox.setAttribute("fill", "rgba(245, 158, 11, 0.1)");
            sqsSub.textContent = "Oldest Age (s) Rising";

            if (mLine) mLine.style.display = "none";
            if (mBadge) mBadge.style.display = "none";
            if (mBox) { mBox.style.animation = "none"; mBox.setAttribute("stroke", "#334155"); mBox.setAttribute("fill", "#1e293b"); }
            if (mTitle) { mTitle.textContent = "🗄️ MySQL Database"; mTitle.setAttribute("fill", "#94a3b8"); }
            if (mSub) { mSub.textContent = "Retrying in 180s..."; mSub.setAttribute("fill", "#fbbf24"); }

        } else if (step === 4) { // Recovery
            pLine.setAttribute("stroke", "#34d399");
            pLine.setAttribute("marker-end", "url(#arr-green)");
            pCross.style.display = "none";
            pBox.style.animation = "pulseGreenHalo 2s infinite ease-in-out";
            pBox.setAttribute("stroke", "#10b981");
            pBox.setAttribute("fill", "rgba(16, 185, 129, 0.12)");
            pTitle.textContent = "✅ payment-api";
            pTitle.setAttribute("fill", "#34d399");
            pSub.textContent = "Concurrency Restored";
            pSub.setAttribute("fill", "#a7f3d0");
            retryLoop.style.display = "none";
            sqsBox.setAttribute("stroke", "#10b981");
            sqsBox.setAttribute("fill", "#1e293b");
            sqsSub.textContent = "Queue Drained to 0";

            if (mLine) { mLine.style.display = "block"; mLine.setAttribute("stroke", "#34d399"); mLine.setAttribute("marker-end", "url(#arr-green)"); mLine.setAttribute("class", "flow-fast"); }
            if (mBadge) mBadge.style.display = "block";
            if (mBadgeBox) { mBadgeBox.setAttribute("stroke", "#10b981"); mBadgeBox.setAttribute("fill", "#064e3b"); }
            if (mBadgeText) { mBadgeText.textContent = "Paid 200"; mBadgeText.setAttribute("fill", "#34d399"); }
            if (mBox) { mBox.style.animation = "pulseGreenHalo 2s infinite ease-in-out"; mBox.setAttribute("stroke", "#10b981"); mBox.setAttribute("fill", "rgba(16, 185, 129, 0.15)"); }
            if (mTitle) { mTitle.textContent = "✅ MySQL & Confirmed"; mTitle.setAttribute("fill", "#34d399"); }
            if (mSub) { mSub.textContent = "Zero Orders Lost"; mSub.setAttribute("fill", "#6ee7b7"); }
        }
    };
    """

    return _build_interactive_container("payment", "Payment Gateway Outage & SQS Retry Drill", steps_data, svg_content, update_svg_js)


def render_dlq_redrive_animation() -> str:
    """Interactive architecture animation for DLQ Redrive & Order Recovery Drill."""
    steps_data = [
        {
            "badge": "Step 1: Normal Operations",
            "badgeClass": "badge-normal",
            "color": "#3b82f6",
            "text": "Valid checkout requests enter the SQS main queue and are confirmed normally by the Lambda worker.",
        },
        {
            "badge": "Step 2: Failed Payload",
            "badgeClass": "badge-fault",
            "color": "#ef4444",
            "text": "Order fails processing repeatedly (Retrying 1/5 ➔ 5/5) without confirming.",
        },
        {
            "badge": "Step 3: DLQ Quarantine",
            "badgeClass": "badge-safety",
            "color": "#f59e0b",
            "text": "SQS maxReceiveCount (5) trips! The failed message is isolated into DLQ to protect normal traffic.",
        },
        {
            "badge": "Step 4: Redrive Recovery",
            "badgeClass": "badge-recovery",
            "color": "#10b981",
            "text": "Operator executes <code>start_message_move_task</code>. Message redrives to main queue, confirms, and alarm clears!",
        },
    ]

    svg_content = """
    <defs>
        <marker id="arr-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#f87171"/>
        </marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/>
        </marker>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
    </defs>

    <!-- Node 1: Main Queue -->
    <rect x="25" y="30" width="145" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="97" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">📬 Main Queue</text>
    <text x="97" y="68" fill="#94a3b8" font-size="10" text-anchor="middle">checkout-requests</text>

    <!-- Path 1 -> 2 -->
    <line x1="170" y1="55" x2="215" y2="55" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 2: Worker -->
    <rect x="220" y="30" width="145" height="50" rx="8" id="dlqWorkerBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="292" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">λ process-checkout</text>
    <text x="292" y="68" fill="#94a3b8" font-size="10" id="dlqWorkerSub" text-anchor="middle">Active Consumer</text>

    <!-- Path to Confirmed Order -->
    <line id="dlqSuccessLine" x1="365" y1="55" x2="425" y2="55" stroke="#34d399" stroke-width="2" class="flow-line" marker-end="url(#arr-green)"/>
    <g id="dlqCross" style="display: none;">
        <circle cx="395" cy="55" r="14" fill="#ef4444" fill-opacity="0.3" stroke="#ef4444" stroke-width="2" class="cross-icon"/>
        <text x="395" y="60" fill="#fca5a5" font-size="13" font-weight="bold" text-anchor="middle">❌</text>
    </g>

    <rect x="430" y="30" width="135" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="497" y="52" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">✅ Confirmed Order</text>
    <text x="497" y="68" fill="#94a3b8" font-size="10" text-anchor="middle">MySQL & SNS</text>

    <!-- Path to DLQ -->
    <g id="dlqDropPathGroup" style="display: none;">
        <path d="M 292 80 L 292 135" fill="none" stroke="#ef4444" stroke-width="2.5" class="flow-line" marker-end="url(#arr-red)"/>
        <rect x="300" y="98" width="115" height="20" rx="3" fill="#1e293b" stroke="#ef4444" stroke-width="1"/>
        <text x="357" y="112" fill="#f87171" font-size="10" font-family="monospace" text-anchor="middle">5x Retries Exceeded</text>
    </g>

    <!-- Node 3: Dead-Letter Queue -->
    <g id="dlqNodeGroup" transform="translate(220, 140)">
        <rect x="0" y="0" width="145" height="55" rx="8" id="dlqBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="72" y="25" fill="#f8fafc" font-size="12" font-weight="600" id="dlqTitle" text-anchor="middle">☠️ Dead-Letter Queue</text>
        <text x="72" y="42" fill="#94a3b8" font-size="10" id="dlqSub" text-anchor="middle">checkout-dlq (Depth: 0)</text>
    </g>

    <!-- Node 4: CloudWatch Alarm -->
    <g id="alarmGroup" transform="translate(430, 140)">
        <rect x="0" y="0" width="160" height="55" rx="8" id="alarmBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="80" y="25" fill="#f8fafc" font-size="12" font-weight="600" id="alarmTitle" text-anchor="middle">🚨 CloudWatch Alarm</text>
        <text x="80" y="42" fill="#34d399" font-size="10" id="alarmSub" text-anchor="middle">dlq-not-empty (OK)</text>
    </g>

    <!-- Redrive Arc from DLQ back to Main Queue -->
    <g id="redriveArcGroup" style="display: none;">
        <path d="M 220 165 C 120 190 50 130 75 90" fill="none" stroke="#34d399" stroke-width="2.5" class="flow-line" marker-end="url(#arr-green)"/>
        <rect x="65" y="145" width="145" height="22" rx="4" fill="#0f172a" stroke="#10b981" stroke-width="1"/>
        <text x="137" y="160" fill="#34d399" font-size="10" font-family="monospace" font-weight="bold" text-anchor="middle">♻️ SQS Redrive Move Task</text>
    </g>
    """

    update_svg_js = """
    window["updateSvg_dlq"] = function(step) {
        const workerBox = document.getElementById("dlqWorkerBox");
        const workerSub = document.getElementById("dlqWorkerSub");
        const succLine = document.getElementById("dlqSuccessLine");
        const cross = document.getElementById("dlqCross");
        const dropPath = document.getElementById("dlqDropPathGroup");
        const dlqBox = document.getElementById("dlqBox");
        const dlqTitle = document.getElementById("dlqTitle");
        const dlqSub = document.getElementById("dlqSub");
        const alarmBox = document.getElementById("alarmBox");
        const alarmSub = document.getElementById("alarmSub");
        const redriveArc = document.getElementById("redriveArcGroup");

        if (!workerBox || !cross) return;

        if (step === 1) { // Normal
            workerBox.setAttribute("stroke", "#334155");
            workerSub.textContent = "Active Consumer";
            succLine.setAttribute("stroke", "#34d399");
            cross.style.display = "none";
            dropPath.style.display = "none";
            dlqBox.setAttribute("stroke", "#334155");
            dlqBox.style.animation = "none";
            dlqTitle.setAttribute("fill", "#f8fafc");
            dlqSub.textContent = "Depth: 0 (Empty)";
            alarmBox.setAttribute("stroke", "#334155");
            alarmSub.textContent = "dlq-not-empty (OK)";
            alarmSub.setAttribute("fill", "#34d399");
            redriveArc.style.display = "none";
        } else if (step === 2) { // Poison Message
            workerBox.setAttribute("stroke", "#ef4444");
            workerBox.style.animation = "shakeNode 0.5s ease";
            workerSub.textContent = "Exception! Retrying (5x)";
            succLine.setAttribute("stroke", "#ef4444");
            cross.style.display = "block";
            dropPath.style.display = "none";
            redriveArc.style.display = "none";
        } else if (step === 3) { // DLQ Isolation
            workerBox.setAttribute("stroke", "#334155");
            workerSub.textContent = "Pipeline Unblocked";
            succLine.setAttribute("stroke", "#34d399");
            cross.style.display = "none";
            dropPath.style.display = "block";
            dlqBox.setAttribute("stroke", "#ef4444");
            dlqBox.style.animation = "pulseRedHalo 1.5s infinite ease-in-out";
            dlqTitle.setAttribute("fill", "#ef4444");
            dlqSub.textContent = "Depth: 1 (Quarantined)";
            alarmBox.setAttribute("stroke", "#ef4444");
            alarmSub.textContent = "dlq-not-empty (ALARM)";
            alarmSub.setAttribute("fill", "#ef4444");
            redriveArc.style.display = "none";
        } else if (step === 4) { // Redrive Recovery
            dropPath.style.display = "none";
            redriveArc.style.display = "block";
            dlqBox.setAttribute("stroke", "#10b981");
            dlqBox.style.animation = "pulseGreenHalo 2s infinite ease-in-out";
            dlqTitle.setAttribute("fill", "#34d399");
            dlqSub.textContent = "Depth: 0 (Drained)";
            alarmBox.setAttribute("stroke", "#10b981");
            alarmSub.textContent = "dlq-not-empty (OK)";
            alarmSub.setAttribute("fill", "#34d399");
        }
    };
    """

    return _build_interactive_container("dlq", "Poison Message & DLQ Redrive Drill", steps_data, svg_content, update_svg_js)


def render_pod_kill_animation() -> str:
    """Interactive architecture animation for Abrupt Pod Kill Drill."""
    steps_data = [
        {
            "badge": "Step 1: Multi-Replica",
            "badgeClass": "badge-normal",
            "color": "#3b82f6",
            "text": "ALB load balances incoming /api shopper requests 50/50 between Pod 1 and Pod 2.",
        },
        {
            "badge": "Step 2: Pod Abruptly Killed",
            "badgeClass": "badge-fault",
            "color": "#ef4444",
            "text": "<code>kubectl delete pod --now</code> kills Pod 1. Ingress link to Pod 1 is severed (❌) instantly.",
        },
        {
            "badge": "Step 3: Zero-Downtime Failover",
            "badgeClass": "badge-safety",
            "color": "#10b981",
            "text": "ALB TargetGroupBinding detects pod termination and diverts 100% of live traffic to Pod 2. Zero HTTP 502/504 errors!",
        },
        {
            "badge": "Step 4: Auto-Healing",
            "badgeClass": "badge-recovery",
            "color": "#34d399",
            "text": "Kubernetes ReplicaSet boots replacement Pod 3, registers into the ALB target group, and restores 50/50 balance!",
        },
    ]

    svg_content = """
    <defs>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/>
        </marker>
    </defs>

    <!-- Node 1: Live Shoppers -->
    <rect x="25" y="75" width="120" height="55" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="85" y="98" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">🌐 Shoppers</text>
    <text x="85" y="115" fill="#94a3b8" font-size="10" text-anchor="middle">Continuous HTTP</text>

    <!-- Path to ALB -->
    <line x1="145" y1="102" x2="195" y2="102" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 2: Internal ALB -->
    <rect x="200" y="75" width="130" height="55" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="265" y="98" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">⚖️ Internal ALB</text>
    <text x="265" y="115" fill="#94a3b8" font-size="10" text-anchor="middle">TargetGroupBinding</text>

    <!-- Path ALB -> Pod 1 -->
    <path id="pathPod1" d="M 330 90 C 370 75 390 45 425 45" fill="none" stroke="#38bdf8" stroke-width="2" class="flow-line"/>
    <g id="crossPod1" style="display: none;">
        <circle cx="380" cy="62" r="14" fill="#ef4444" fill-opacity="0.3" stroke="#ef4444" stroke-width="2" class="cross-icon"/>
        <text x="380" y="67" fill="#fca5a5" font-size="13" font-weight="bold" text-anchor="middle">❌</text>
    </g>

    <!-- Node 3: Pod 1 -->
    <g id="pod1Group" transform="translate(430, 20)">
        <rect x="0" y="0" width="150" height="50" rx="8" id="pod1Box" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="75" y="24" fill="#f8fafc" font-size="12" font-weight="600" id="pod1Title" text-anchor="middle">☸️ Pod 1 (store-api)</text>
        <text x="75" y="40" fill="#94a3b8" font-size="10" id="pod1Sub" text-anchor="middle">Target: Healthy</text>
    </g>

    <!-- Path ALB -> Pod 2 -->
    <path id="pathPod2" d="M 330 115 C 370 130 390 160 425 160" fill="none" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 4: Pod 2 -->
    <g id="pod2Group" transform="translate(430, 135)">
        <rect x="0" y="0" width="150" height="50" rx="8" id="pod2Box" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <text x="75" y="24" fill="#f8fafc" font-size="12" font-weight="600" id="pod2Title" text-anchor="middle">☸️ Pod 2 (store-api)</text>
        <text x="75" y="40" fill="#94a3b8" font-size="10" id="pod2Sub" text-anchor="middle">Target: Healthy</text>
    </g>

    <!-- Node 5: Replacement Pod 3 -->
    <g id="pod3Group" style="display: none;" transform="translate(605, 75)">
        <rect x="0" y="0" width="135" height="55" rx="8" fill="rgba(16,185,129,0.12)" stroke="#10b981" stroke-width="2" style="animation: pulseGreenHalo 2s infinite ease-in-out;"/>
        <text x="67" y="25" fill="#34d399" font-size="12" font-weight="600" text-anchor="middle">🌱 Pod 3 (Spawned)</text>
        <text x="67" y="42" fill="#a7f3d0" font-size="10" text-anchor="middle">K8s ReplicaSet Ready</text>
    </g>
    """

    update_svg_js = """
    window["updateSvg_podkill"] = function(step) {
        const path1 = document.getElementById("pathPod1");
        const cross1 = document.getElementById("crossPod1");
        const pod1Box = document.getElementById("pod1Box");
        const pod1Title = document.getElementById("pod1Title");
        const pod1Sub = document.getElementById("pod1Sub");
        const path2 = document.getElementById("pathPod2");
        const pod2Box = document.getElementById("pod2Box");
        const pod2Sub = document.getElementById("pod2Sub");
        const pod3 = document.getElementById("pod3Group");

        if (!path1 || !cross1) return;

        if (step === 1) { // Normal
            path1.setAttribute("stroke", "#38bdf8");
            path1.setAttribute("stroke-width", "2");
            cross1.style.display = "none";
            pod1Box.setAttribute("stroke", "#334155");
            pod1Box.style.animation = "none";
            pod1Title.textContent = "☸️ Pod 1 (store-api)";
            pod1Title.setAttribute("fill", "#f8fafc");
            pod1Sub.textContent = "Healthy (50% Traffic)";
            path2.setAttribute("stroke", "#38bdf8");
            path2.setAttribute("stroke-width", "2");
            pod2Box.setAttribute("stroke", "#334155");
            pod2Sub.textContent = "Healthy (50% Traffic)";
            pod3.style.display = "none";
        } else if (step === 2) { // Pod Killed
            path1.setAttribute("stroke", "#ef4444");
            path1.setAttribute("stroke-width", "1.5");
            cross1.style.display = "block";
            pod1Box.setAttribute("stroke", "#ef4444");
            pod1Box.style.animation = "pulseRedHalo 1.5s infinite ease-in-out, shakeNode 0.5s ease";
            pod1Title.textContent = "💀 Pod 1 (Killed)";
            pod1Title.setAttribute("fill", "#ef4444");
            pod1Sub.textContent = "Deregistering...";
            pod3.style.display = "none";
        } else if (step === 3) { // Zero-Downtime Failover
            cross1.style.display = "block";
            path1.setAttribute("stroke", "transparent");
            path2.setAttribute("stroke", "#10b981");
            path2.setAttribute("stroke-width", "3.5");
            pod2Box.setAttribute("stroke", "#10b981");
            pod2Box.style.animation = "pulseGreenHalo 2s infinite ease-in-out";
            pod2Sub.textContent = "100% Traffic (0 Errors)";
            pod3.style.display = "none";
        } else if (step === 4) { // Auto-Healing
            cross1.style.display = "none";
            pod3.style.display = "block";
            pod2Sub.textContent = "Rebalancing 50/50";
        }
    };
    """

    return _build_interactive_container("podkill", "Abrupt Pod Kill & Zero-Downtime HA Drill", steps_data, svg_content, update_svg_js)


def render_reconciler_animation() -> str:
    """Interactive architecture animation for SQS Partition & Outbox Reconciler Drill."""
    steps_data = [
        {
            "badge": "Step 1: Normal Flow",
            "badgeClass": "badge-normal",
            "color": "#3b82f6",
            "text": "Store-API pod directly pushes checkout messages to AWS SQS without delay.",
        },
        {
            "badge": "Step 2: SQS Severed",
            "badgeClass": "badge-fault",
            "color": "#ef4444",
            "text": "Network partition or bad queue configuration! Connection link is severed with a flashing lightning bolt (⚡).",
        },
        {
            "badge": "Step 3: Outbox Fallback",
            "badgeClass": "badge-safety",
            "color": "#f59e0b",
            "text": "Transactional Outbox Pattern activates! Store-API saves order in MySQL as PENDING and returns 202. Reconciler thread sweeps MySQL.",
        },
        {
            "badge": "Step 4: Auto-Flush",
            "badgeClass": "badge-recovery",
            "color": "#10b981",
            "text": "SQS recovers. Background Reconciler.java flushes all pending orders into SQS with zero order loss!",
        },
    ]

    svg_content = """
    <defs>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/>
        </marker>
        <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#fbbf24"/>
        </marker>
    </defs>

    <!-- Node 1: Shopper -->
    <rect x="25" y="35" width="110" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="80" y="57" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">🛒 Shopper</text>
    <text x="80" y="73" fill="#94a3b8" font-size="10" text-anchor="middle">POST /checkouts</text>

    <!-- Path to API -->
    <line x1="135" y1="60" x2="185" y2="60" stroke="#38bdf8" stroke-width="2" class="flow-line" marker-end="url(#arr-blue)"/>

    <!-- Node 2: Store API -->
    <rect x="190" y="35" width="125" height="50" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="252" y="57" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">☸️ EKS store-api</text>
    <text x="252" y="73" fill="#94a3b8" font-size="10" text-anchor="middle">Returns 202</text>

    <!-- Link API -> SQS -->
    <g id="sqsLinkGroup">
        <line id="sqsLine" x1="315" y1="60" x2="395" y2="60" stroke="#38bdf8" stroke-width="2" class="flow-line"/>
        <g id="sqsBreak" style="display: none;">
            <circle cx="355" cy="60" r="14" fill="#ef4444" fill-opacity="0.25" stroke="#ef4444" stroke-width="1.5" class="cross-icon"/>
            <text x="355" y="65" fill="#ef4444" font-size="13" font-weight="bold" text-anchor="middle">⚡</text>
        </g>
    </g>

    <!-- Node 3: SQS Queue -->
    <rect x="400" y="35" width="125" height="50" rx="8" id="recSqsBox" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="462" y="57" fill="#f8fafc" font-size="12" font-weight="600" id="recSqsTitle" text-anchor="middle">📬 SQS Queue</text>
    <text x="462" y="73" fill="#94a3b8" font-size="10" id="recSqsSub" text-anchor="middle">checkout-requests</text>

    <!-- Node 4: MySQL Outbox -->
    <g id="outboxGroup" style="display: none;" transform="translate(190, 130)">
        <rect x="0" y="0" width="125" height="50" rx="8" fill="#1e293b" stroke="#fbbf24" stroke-width="1.5"/>
        <text x="62" y="24" fill="#fbbf24" font-size="12" font-weight="600" text-anchor="middle">💾 MySQL Outbox</text>
        <text x="62" y="40" fill="#fef3c7" font-size="10" text-anchor="middle">Status = PENDING</text>
        <line x1="62" y1="-45" x2="62" y2="0" stroke="#fbbf24" stroke-width="2" marker-end="url(#arr-amber)"/>
    </g>

    <!-- Node 5: Reconciler Thread -->
    <g id="reconcilerGroup" style="display: none;" transform="translate(370, 130)">
        <rect x="0" y="0" width="155" height="50" rx="8" id="recBox" fill="#1e293b" stroke="#10b981" stroke-width="1.5"/>
        <text x="77" y="24" fill="#34d399" font-size="12" font-weight="600" text-anchor="middle">🔄 Reconciler.java</text>
        <text x="77" y="40" fill="#a7f3d0" font-size="10" text-anchor="middle">Sweeps every 15s</text>
        <line x1="-55" y1="25" x2="0" y2="25" stroke="#34d399" stroke-width="2" class="flow-line" marker-end="url(#arr-green)"/>
    </g>

    <!-- Flush Path: Reconciler -> SQS -->
    <g id="flushArcGroup" style="display: none;">
        <path d="M 525 155 C 585 155 585 60 530 60" fill="none" stroke="#34d399" stroke-width="2.5" class="flow-fast" marker-end="url(#arr-green)"/>
        <rect x="540" y="95" width="140" height="22" rx="4" fill="#0f172a" stroke="#10b981" stroke-width="1"/>
        <text x="610" y="110" fill="#34d399" font-size="10" font-family="monospace" font-weight="bold" text-anchor="middle">🚀 Auto-Flush</text>
    </g>
    """

    update_svg_js = """
    window["updateSvg_reconciler"] = function(step) {
        const sqsLine = document.getElementById("sqsLine");
        const sqsBreak = document.getElementById("sqsBreak");
        const sqsBox = document.getElementById("recSqsBox");
        const sqsTitle = document.getElementById("recSqsTitle");
        const sqsSub = document.getElementById("recSqsSub");
        const outbox = document.getElementById("outboxGroup");
        const rec = document.getElementById("reconcilerGroup");
        const flush = document.getElementById("flushArcGroup");

        if (!sqsLine || !sqsBreak) return;

        if (step === 1) { // Normal
            sqsLine.setAttribute("stroke", "#38bdf8");
            sqsBreak.style.display = "none";
            sqsBox.setAttribute("stroke", "#334155");
            sqsTitle.setAttribute("fill", "#f8fafc");
            sqsSub.textContent = "checkout-requests";
            outbox.style.display = "none";
            rec.style.display = "none";
            flush.style.display = "none";
        } else if (step === 2) { // Broken Link
            sqsLine.setAttribute("stroke", "#ef4444");
            sqsBreak.style.display = "block";
            sqsBox.setAttribute("stroke", "#ef4444");
            sqsTitle.setAttribute("fill", "#ef4444");
            sqsSub.textContent = "Connection Severed";
            outbox.style.display = "none";
            rec.style.display = "none";
            flush.style.display = "none";
        } else if (step === 3) { // Outbox Active
            sqsBreak.style.display = "block";
            outbox.style.display = "block";
            rec.style.display = "block";
            flush.style.display = "none";
        } else if (step === 4) { // Reconnect & Flush
            sqsBreak.style.display = "none";
            sqsLine.setAttribute("stroke", "#34d399");
            sqsBox.setAttribute("stroke", "#10b981");
            sqsTitle.setAttribute("fill", "#34d399");
            sqsSub.textContent = "Receiving Orders";
            outbox.style.display = "block";
            rec.style.display = "block";
            flush.style.display = "block";
        }
    };
    """

    return _build_interactive_container("reconciler", "SQS Partition & Outbox Reconciler Drill", steps_data, svg_content, update_svg_js)


def render_flash_sale_animation() -> str:
    """Interactive architecture animation for Flash Sale Concurrency Drill."""
    steps_data = [
        {
            "badge": "Step 1: Traffic Burst",
            "badgeClass": "badge-normal",
            "color": "#3b82f6",
            "text": "60 concurrent shoppers blast checkout requests at the exact same millisecond for 50 limited items.",
        },
        {
            "badge": "Step 2: SQS Absorption",
            "badgeClass": "badge-safety",
            "color": "#fbbf24",
            "text": "SQS absorbs the burst, preventing database connection exhaustion or gateway timeouts.",
        },
        {
            "badge": "Step 3: Atomic Lock",
            "badgeClass": "badge-safety",
            "color": "#f59e0b",
            "text": "MySQL executes atomic conditional decrements: <code>UPDATE ... WHERE stock >= 1</code> without table locks.",
        },
        {
            "badge": "Step 4: Zero Oversell",
            "badgeClass": "badge-recovery",
            "color": "#10b981",
            "text": "Exactly 50 confirmed orders (Stock 50 ➔ 0), 10 out-of-stock rejections. 0 oversold items guaranteed!",
        },
    ]

    svg_content = """
    <defs>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8"/>
        </marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/>
        </marker>
        <marker id="arr-gray" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#94a3b8"/>
        </marker>
    </defs>

    <!-- Node 1: 60 Shoppers -->
    <rect x="25" y="70" width="125" height="55" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="87" y="94" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">🏎️ 60 Shoppers</text>
    <text x="87" y="110" fill="#94a3b8" font-size="10" text-anchor="middle">Simultaneous Burst</text>

    <!-- Path 1 -> 2 -->
    <line x1="150" y1="97" x2="200" y2="97" stroke="#38bdf8" stroke-width="2.5" class="flow-fast" marker-end="url(#arr-blue)"/>

    <!-- Node 2: SQS Buffer -->
    <rect x="205" y="70" width="120" height="55" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="265" y="94" fill="#f8fafc" font-size="12" font-weight="600" text-anchor="middle">📬 SQS Buffer</text>
    <text x="265" y="110" fill="#94a3b8" font-size="10" text-anchor="middle">Absorbs Spike</text>

    <!-- Path 2 -> 3 -->
    <line x1="325" y1="97" x2="375" y2="97" stroke="#38bdf8" stroke-width="2.5" class="flow-fast" marker-end="url(#arr-blue)"/>

    <!-- Node 3: MySQL Atomic Lock -->
    <g id="mysqlNodeGroup" transform="translate(380, 65)">
        <rect x="0" y="0" width="165" height="65" rx="8" id="mysqlBox" fill="#1e293b" stroke="#fbbf24" stroke-width="1.5"/>
        <text x="82" y="24" fill="#fbbf24" font-size="12" font-weight="600" text-anchor="middle">🔒 MySQL 8.4 Engine</text>
        <text x="82" y="40" fill="#94a3b8" font-size="10" id="mysqlSub" text-anchor="middle">UPDATE ... WHERE stock >= 1</text>
        <text x="82" y="54" fill="#34d399" font-size="9" font-weight="bold" text-anchor="middle">Row-Level Atomic Decrement</text>
    </g>

    <!-- Outputs -->
    <g id="outGroup" style="display: none;">
        <!-- Upper: 50 Confirmed -->
        <path d="M 545 88 C 575 75 585 50 610 50" fill="none" stroke="#34d399" stroke-width="2.5" class="flow-fast" marker-end="url(#arr-green)"/>
        <rect x="615" y="28" width="115" height="46" rx="8" fill="rgba(16,185,129,0.12)" stroke="#10b981" stroke-width="1.5"/>
        <text x="672" y="47" fill="#34d399" font-size="12" font-weight="bold" text-anchor="middle">50 Confirmed</text>
        <text x="672" y="62" fill="#a7f3d0" font-size="10" text-anchor="middle">Stock: 50 → 0</text>

        <!-- Lower: 10 Declined -->
        <path d="M 545 105 C 575 120 585 145 610 145" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 4" marker-end="url(#arr-gray)"/>
        <rect x="615" y="125" width="115" height="46" rx="8" fill="#1e293b" stroke="#475569" stroke-width="1.5"/>
        <text x="672" y="144" fill="#cbd5e1" font-size="12" font-weight="600" text-anchor="middle">10 Declined</text>
        <text x="672" y="159" fill="#94a3b8" font-size="10" text-anchor="middle">OUT_OF_STOCK</text>
    </g>
    """

    update_svg_js = """
    window["updateSvg_flash"] = function(step) {
        const out = document.getElementById("outGroup");
        const mysqlBox = document.getElementById("mysqlBox");
        const mysqlSub = document.getElementById("mysqlSub");

        if (!mysqlBox) return;

        if (step === 1 || step === 2) {
            if (out) out.style.display = "none";
            mysqlBox.setAttribute("stroke", "#fbbf24");
            mysqlSub.textContent = "UPDATE ... WHERE stock >= 1";
        } else if (step === 3) {
            if (out) out.style.display = "none";
            mysqlBox.setAttribute("stroke", "#10b981");
            mysqlBox.style.animation = "pulseGreenHalo 1.5s infinite ease-in-out";
            mysqlSub.textContent = "Locking row FLASH-001";
        } else if (step === 4) {
            if (out) out.style.display = "block";
            mysqlBox.setAttribute("stroke", "#10b981");
            mysqlSub.textContent = "Final Stock: 0";
        }
    };
    """

    return _build_interactive_container("flash", "Flash Sale Atomic Concurrency Drill", steps_data, svg_content, update_svg_js)
