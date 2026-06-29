"""
Custom CSS Theme — Premium Dark Glassmorphism
"""

import streamlit as st


def inject_custom_css():
    """Inject the premium dark theme CSS."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Base Theme */
    :root {
        --bg-primary: #0f1117;
        --bg-secondary: #1a1d29;
        --bg-card: rgba(26, 29, 41, 0.8);
        --bg-glass: rgba(255, 255, 255, 0.03);
        --border: rgba(255, 255, 255, 0.08);
        --text-primary: #e4e6f0;
        --text-secondary: #8b8fa3;
        --accent-1: #667eea;
        --accent-2: #764ba2;
        --accent-3: #f093fb;
        --success: #4ade80;
        --warning: #fbbf24;
        --danger: #f87171;
        --info: #60a5fa;
    }

    /* Global */
    .main .block-container {
        max-width: 1400px;
        padding-top: 2rem;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Glass Cards */
    .glass-card {
        background: var(--bg-glass);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(102, 126, 234, 0.3);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1);
        transform: translateY(-2px);
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.3rem 0;
    }

    .metric-label {
        color: var(--text-secondary);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Score Badges */
    .score-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .score-high {
        background: rgba(74, 222, 128, 0.15);
        color: #4ade80;
        border: 1px solid rgba(74, 222, 128, 0.3);
    }

    .score-medium {
        background: rgba(251, 191, 36, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }

    .score-low {
        background: rgba(248, 113, 113, 0.15);
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.3);
    }

    /* Candidate Card */
    .candidate-card {
        background: var(--bg-glass);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: all 0.3s ease;
    }

    .candidate-card:hover {
        border-color: rgba(102, 126, 234, 0.4);
        background: rgba(102, 126, 234, 0.05);
    }

    .rank-badge {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        flex-shrink: 0;
    }

    .candidate-info {
        flex-grow: 1;
    }

    .candidate-name {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.2rem;
    }

    .candidate-title {
        color: var(--text-secondary);
        font-size: 0.85rem;
    }

    /* Progress Bar */
    .progress-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 2px;
        margin: 0.5rem 0;
    }

    .progress-bar {
        height: 8px;
        border-radius: 8px;
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        transition: width 0.5s ease;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid transparent;
        border-image: linear-gradient(90deg, #667eea, transparent) 1;
    }

    /* Pipeline Stage */
    .pipeline-stage {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid transparent;
    }

    .pipeline-stage.active {
        background: rgba(102, 126, 234, 0.1);
        border-left-color: #667eea;
    }

    .pipeline-stage.complete {
        border-left-color: #4ade80;
    }

    /* Animated gradient text */
    .gradient-text {
        background: linear-gradient(135deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-size: 200% 200%;
        animation: gradient-shift 3s ease infinite;
    }

    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Pulse animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    .pulse { animation: pulse 2s ease-in-out infinite; }

    /* Hide Streamlit defaults */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Streamlit elements customization */
    .stRadio > label { display: none; }

    .stRadio > div {
        gap: 0.3rem;
    }

    .stRadio > div > label {
        padding: 0.6rem 1rem !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }

    .stRadio > div > label:hover {
        background: rgba(102, 126, 234, 0.1) !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, icon: str = "📊"):
    """Render a custom metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 1.5rem;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_score_badge(score: float, label: str = ""):
    """Render a colored score badge."""
    if score >= 0.7:
        css_class = "score-high"
    elif score >= 0.4:
        css_class = "score-medium"
    else:
        css_class = "score-low"

    text = f"{label}: {score:.0%}" if label else f"{score:.0%}"
    return f'<span class="score-badge {css_class}">{text}</span>'


def render_candidate_card(rank: int, name: str, title: str, score: float, exp: float):
    """Render a candidate card."""
    badge = render_score_badge(score)
    st.markdown(f"""
    <div class="candidate-card">
        <div class="rank-badge">{rank}</div>
        <div class="candidate-info">
            <div class="candidate-name">{name}</div>
            <div class="candidate-title">{title} · {exp:.0f}y experience</div>
        </div>
        <div>{badge}</div>
    </div>
    """, unsafe_allow_html=True)
