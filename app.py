import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="BJT 시뮬레이터")

st.markdown("""
<style>
    [data-testid="stSidebar"] {
        min-width: 250px;
        max-width: 250px;
    }
    [data-testid="stSidebar"] .stWidgetFormSubmitButton,
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.2rem !important;
    }
    [data-testid="stSidebar"] h3 {
        font-size: 0.95rem !important;
        margin-bottom: 5px !important;
        margin-top: 5px !important;
    }
    [data-testid="stSidebar"] hr {
        margin: 6px 0 !important;
    }
    [data-testid="stSidebar"] .stSlider {
        margin-top: -15px !important;
        margin-bottom: -5px !important;
    }
    [data-testid="stSidebar"] .stNumberInput div[data-baseweb="input"],
    [data-testid="stSidebar"] .stNumberInput div[data-baseweb="base-input"] {
        background-color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stNumberInput input {
        height: 26px !important;
        padding: 1px 4px !important;
        font-size: 0.75rem !important;
        color: #2c3e50 !important;
        background-color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stTextArea textarea {
        font-size: 0.78rem !important;
        padding: 5px !important;
        color: #2c3e50 !important;
    }
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 4px !important; }

    .stat-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #eaeaea;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.04);
        height: 100%;
    }
    .stat-title { font-size: 0.8rem; color: #7f8c8d; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .stat-label { font-size: 0.72rem; color: #95a5a6; font-weight: 600; }
    .stat-value { font-size: 1.15rem; font-weight: 700; color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    st.markdown("### 🔌 BJT 시뮬레이터")
    bjt_type = st.radio("소자 타입", ["NPN", "PNP"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<span style='font-size:0.8rem; font-weight:700; color:#1e293b;'>접합 전압 인가</span>", unsafe_allow_html=True)

    if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.75
    if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -2.0

    def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
    def update_be_num():    st.session_state.be_num   = st.session_state.v_be_val
    def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
    def update_bc_num():    st.session_state.bc_num   = st.session_state.v_bc_val

    label_be = "V_BE (V)" if bjt_type == "NPN" else "V_EB (V)"
    st.markdown(f"<span style='font-size:0.75rem; font-weight:700; color:#2c3e50;'>{label_be}</span>", unsafe_allow_html=True)
    V_be = st.slider(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                     key="v_be_val", on_change=update_be_num, label_visibility="collapsed")
    st.number_input(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                    key="be_num", on_change=update_be_slider,
                    value=st.session_state.v_be_val, label_visibility="collapsed")

    label_bc = "V_BC (V)" if bjt_type == "NPN" else "V_CB (V)"
    st.markdown(f"<span style='font-size:0.75rem; font-weight:700; color:#2c3e50; margin-top:2px; display:block;'>{label_bc}</span>", unsafe_allow_html=True)
    V_bc = st.slider(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                     key="v_bc_val", on_change=update_bc_num, label_visibility="collapsed")
    st.number_input(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                    key="bc_num", on_change=update_bc_slider,
                    value=st.session_state.v_bc_val, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<span style='font-size:0.8rem; font-weight:700; color:#1e293b;'>💬 AI 질문</span>", unsafe_allow_html=True)
    user_question = st.text_area("질문 입력", height=50, label_visibility="collapsed",
                                 value="현재 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
                                 placeholder="e.g. 현재 바이어스 상태를 물리적으로 설명해줘.")
    ai_btn = st.button("🚀 Gemini 분석 요청", use_container_width=True)

V_CC   = 5.0
R_C    = 800.0
beta   = 150
V_AF   = 100.0
early_k = 1.0 / V_AF

be_fwd = V_be > 0
bc_fwd = V_bc > 0

if be_fwd and not bc_fwd:
    mode       = "순방향 활성 영역"
    mode_en    = "Forward Active"
    mode_color = "#f39c12"
    anim_key   = "forward_active"
elif be_fwd and bc_fwd:
    mode       = "포화 영역"
    mode_en    = "Saturation"
    mode_color = "#28a745"
    anim_key   = "saturation"
elif not be_fwd and bc_fwd:
    mode       = "역방향 활성 영역"
    mode_en    = "Reverse Active"
    mode_color = "#9b59b6"
    anim_key   = "reverse_active"
else:
    mode       = "차단 영역"
    mode_en    = "Cutoff"
    mode_color = "#dc3545"
    anim_key   = "cutoff"

mode_full = f"{mode} ({mode_en})"

R_B_eff = 30000.0
I_B_A = max(0.0, V_be / R_B_eff) if be_fwd else 0.0

if mode_en == "Forward Active":
    I_C_ideal = beta * I_B_A
    I_C_max   = (V_CC - 0.2) / R_C
    q_ic_A    = max(0.0, min(I_C_ideal, I_C_max))
    q_vce     = max(0.2, V_CC - q_ic_A * R_C)
elif mode_en == "Saturation":
    q_vce  = 0.2
    q_ic_A = (V_CC - q_vce) / R_C
else:
    q_vce  = V_CC
    q_ic_A = 0.0

q_ic_mA = q_ic_A * 1000

# ── 모드별 색상 및 설명 (Python 단에서 미리 계산)
mode_color_map = {
    "forward_active": "#f39c12",
    "saturation":     "#28a745",
    "reverse_active": "#9b59b6",
    "cutoff":         "#dc3545",
}
mode_desc_map = {
    "forward_active": "순방향 활성: 다수 캐리어의 연속적인 흐름 및 소수 캐리어 확산",
    "saturation":     "포화: 양쪽 장벽 소실로 캐리어가 양방향으로 막힘없이 범람(Flooding)함",
    "reverse_active": "역방향 활성: 흐름의 역전 (Collector → Emitter 방향 표류)",
    "cutoff":         "차단: 거대한 장벽에 막혀 이동 불가 (단순 열진동 상태)",
}
desc_color  = mode_color_map[anim_key]
desc_text   = mode_desc_map[anim_key]

# ── BJT 구조 SVG (NPN/PNP)
if bjt_type == "NPN":
    e_fill, e_stroke, e_label = "#1a3a5c", "#3a7abf", "N⁺"
    b_fill, b_stroke, b_label, b_tcolor = "#4a1a3a", "#bf3a8a", "P", "#f9c"
    c_fill, c_stroke, c_label = "#1a3a1a", "#3abf3a", "N"
    vbe_label, vbc_label = f"V_BE={V_be:.2f}V", f"V_BC={V_bc:.2f}V"
    vbe_color, vbc_color = "#7ac", "#7ca"
else:
    e_fill, e_stroke, e_label = "#5c1a1a", "#bf3a3a", "P⁺"
    b_fill, b_stroke, b_label, b_tcolor = "#1a3a2a", "#3abf6a", "N", "#9fc"
    c_fill, c_stroke, c_label = "#3a2a1a", "#bf8a3a", "P"
    vbe_label, vbc_label = f"V_EB={V_be:.2f}V", f"V_CB={V_bc:.2f}V"
    vbe_color, vbc_color = "#ca7", "#a7c"

bjt_svg = f"""
<svg width="530" height="95" style="display:block;">
  <defs>
    <marker id="arrE" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#aaa" stroke-width="1.5"/>
    </marker>
  </defs>

  <!-- Emitter 블록 -->
  <rect x="60" y="22" width="110" height="52" rx="4"
        fill="{e_fill}" stroke="{e_stroke}" stroke-width="1.5"/>
  <text x="115" y="44" text-anchor="middle"
        fill="#cde" font-size="13" font-family="monospace" font-weight="bold">{e_label}</text>
  <text x="115" y="62" text-anchor="middle"
        fill="#9ab" font-size="10" font-family="monospace">Emitter</text>

  <!-- Base 블록 -->
  <rect x="195" y="22" width="80" height="52" rx="0"
        fill="{b_fill}" stroke="{b_stroke}" stroke-width="1.5"/>
  <text x="235" y="44" text-anchor="middle"
        fill="{b_tcolor}" font-size="13" font-family="monospace" font-weight="bold">{b_label}</text>
  <text x="235" y="62" text-anchor="middle"
        fill="#9ab" font-size="10" font-family="monospace">Base</text>

  <!-- Collector 블록 -->
  <rect x="300" y="22" width="110" height="52" rx="4"
        fill="{c_fill}" stroke="{c_stroke}" stroke-width="1.5"/>
  <text x="355" y="44" text-anchor="middle"
        fill="#cec" font-size="13" font-family="monospace" font-weight="bold">{c_label}</text>
  <text x="355" y="62" text-anchor="middle"
        fill="#9ab" font-size="10" font-family="monospace">Collector</text>

  <!-- E 단자 -->
  <line x1="20" y1="48" x2="58" y2="48" stroke="#aaa" stroke-width="1.5" marker-end="url(#arrE)"/>
  <text x="10" y="52" text-anchor="middle" fill="#ddd"
        font-size="13" font-family="monospace" font-weight="bold">E</text>

  <!-- B 단자 (아래로) -->
  <line x1="235" y1="74" x2="235" y2="85" stroke="#aaa" stroke-width="1.5"/>
  <text x="235" y="94" text-anchor="middle" fill="#ddd"
        font-size="13" font-family="monospace" font-weight="bold">B</text>

  <!-- C 단자 -->
  <line x1="410" y1="48" x2="450" y2="48" stroke="#aaa" stroke-width="1.5"/>
  <text x="462" y="52" text-anchor="middle" fill="#ddd"
        font-size="13" font-family="monospace" font-weight="bold">C</text>

  <!-- V_BE / V_BC 수치 표시 -->
  <text x="148" y="15" text-anchor="middle"
        fill="{vbe_color}" font-size="10" font-family="monospace">{vbe_label}</text>
  <text x="323" y="15" text-anchor="middle"
        fill="{vbc_color}" font-size="10" font-family="monospace">{vbc_label}</text>

  <!-- BJT 타입 라벨 -->
  <text x="478" y="38" fill="#ccc" font-size="13" font-family="monospace" font-weight="bold">{bjt_type}</text>
  <text x="478" y="54" fill="#888" font-size="10" font-family="monospace">BJT</text>
</svg>
"""

st.markdown(f"<h3 style='margin-bottom:2px; margin-top:0px;'>📟 BJT 물리 & 특성 시뮬레이터</h3>", unsafe_allow_html=True)
st.markdown("<hr style='margin:2px 0 10px 0;'>", unsafe_allow_html=True)

top_col1, top_col2 = st.columns([0.45, 0.55])

with top_col1:
    st.markdown(f"""
    <div class='stat-card'>
        <div class='stat-title'>Operating Region</div>
        <div style='font-size:1.5rem; font-weight:800; color:{mode_color}; margin-bottom:12px;'>
            {mode} <span style='font-size:1.1rem; font-weight:600;'>({mode_en})</span>
        </div>
        <div style='display:grid; grid-template-columns: 1fr 1fr; gap:12px;'>
            <div>
                <div class='stat-label'>인가전압 |V_CE|</div>
                <div class='stat-value'>{abs(V_be - V_bc):.2f} V</div>
            </div>
            <div>
                <div class='stat-label'>컬렉터전류 |I_C|</div>
                <div class='stat-value'>{q_ic_mA:.2f} mA</div>
            </div>
            <div>
                <div class='stat-label'>베이스전류 |I_B|</div>
                <div class='stat-value'>{I_B_A*1e6:.1f} μA</div>
            </div>
            <div>
                <div class='stat-label'>Q점 V_CEQ</div>
                <div class='stat-value'>{q_vce:.2f} V</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_col2:
    if ai_btn:
        system_instruction = f"""
당신은 반도체 소자 물리학 및 증폭 회로 설계 전문가입니다.
인삿말 없이 바로 수치 분석부터 시작하세요.
현재 설정: BJT={bjt_type}, V_BE={V_be:.2f}V, V_BC={V_bc:.2f}V
모드={mode_full}, I_B={I_B_A*1e6:.2f}μA, I_C={q_ic_mA:.2f}mA, Q점 V_CE={q_vce:.2f}V
6주차 에너지 밴드 교안과 7주차 바이어스 교안을 연결하여 한국어 마크다운으로 답변하세요.
질문: "{user_question}"
"""
        if "GEMINI_API_KEY" in st.secrets:
            with st.spinner("물리적 특성 실시간 해석 중..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    resp  = model.generate_content(system_instruction)
                    st.markdown(f"""
                    <div style='background:#f8f9fa; padding:14px; border-radius:12px; border:1px solid #eaeaea; font-size:0.82rem; height:155px; overflow-y:auto; line-height:1.4;'>
                        <strong>💡 AI 실시간 물리적 해설</strong><br>{resp.text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"오류 발생: {e}")
        else:
            st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    else:
        st.markdown("""
        <div style='background:#f8f9fa; padding:14px; border-radius:12px; border:1px solid #eaeaea; font-size:0.85rem; height:155px; color:#64748b; display:flex; align-items:center; justify-content:center; text-align:center;'>
            사이드바 하단의 '🚀 Gemini 분석 요청' 버튼을 누르면<br>이 자리에 물리 밴드 관점의 상세 해설이 실시간 매핑됩니다.
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔋 에너지 밴드 다이어그램", "📈 I_C–V_CE 특성 곡선", "🏃 캐리어 거동 애니메이션"])

with tab1:
    fig_band = go.Figure()

    E_g = 1.12
    x_all = np.linspace(0, 8.0, 400)
    ec_all = np.zeros_like(x_all)

    v_be_eff = float(np.clip(V_be, -5.0, 0.75))
    v_bc_eff = float(np.clip(V_bc, -5.0, 0.75))

    if bjt_type == "NPN":
        E_F_Base = 0.0
        E_V_Base = -0.1
        E_C_Base = E_V_Base + E_g

        E_F_Emitter = E_F_Base + v_be_eff
        E_F_Collector = E_F_Base + v_bc_eff

        E_C_Emitter = E_F_Emitter - 0.05
        E_C_Collector = E_F_Collector - 0.15
    else:
        E_F_Base = 0.0
        E_C_Base = 0.1
        E_V_Base = E_C_Base - E_g

        E_F_Emitter = E_F_Base - v_be_eff
        E_F_Collector = E_F_Base - v_bc_eff

        E_V_Emitter = E_F_Emitter + 0.05
        E_V_Collector = E_F_Collector + 0.15
        E_C_Emitter = E_V_Emitter + E_g
        E_C_Collector = E_V_Collector + E_g

    for i, x in enumerate(x_all):
        if x <= 2.4:
            ec_all[i] = E_C_Emitter
        elif x >= 5.6:
            ec_all[i] = E_C_Collector
        elif 3.2 <= x <= 4.8:
            ec_all[i] = E_C_Base
        elif 2.4 < x < 3.2:
            t = (x - 2.4) / 0.8 * np.pi
            ec_all[i] = E_C_Emitter + (E_C_Base - E_C_Emitter) * (1 - np.cos(t)) / 2
        elif 4.8 < x < 5.6:
            t = (x - 4.8) / 0.8 * np.pi
            ec_all[i] = E_C_Base + (E_C_Collector - E_C_Base) * (1 - np.cos(t)) / 2

    ev_all = ec_all - E_g

    fig_band.add_vrect(x0=0,   x1=2.8, fillcolor="rgba(173,216,230,0.25)", line_width=0)
    fig_band.add_vrect(x0=2.8, x1=5.2, fillcolor="rgba(255,182,193,0.25)", line_width=0)
    fig_band.add_vrect(x0=5.2, x1=8.0, fillcolor="rgba(144,238,144,0.25)", line_width=0)

    fig_band.add_trace(go.Scatter(x=x_all, y=ec_all, mode='lines', line=dict(color='black', width=2.5), name='E_c'))
    fig_band.add_trace(go.Scatter(x=x_all, y=ev_all, mode='lines', line=dict(color='black', width=2.5), name='E_v'))

    fig_band.add_trace(go.Scatter(x=[0, 2.4], y=[E_F_Emitter, E_F_Emitter], mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (Emitter)'))
    fig_band.add_trace(go.Scatter(x=[3.2, 4.8], y=[E_F_Base, E_F_Base], mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (Base)'))
    fig_band.add_trace(go.Scatter(x=[5.6, 8.0], y=[E_F_Collector, E_F_Collector], mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (Collector)'))

    fig_band.add_annotation(x=8.15, y=ec_all[-1]+0.05, text="<b>E_C</b>", showarrow=False, font=dict(size=12, color='black'))
    fig_band.add_annotation(x=8.15, y=ev_all[-1]-0.05, text="<b>E_V</b>", showarrow=False, font=dict(size=12, color='black'))

    e_lbl = "EMITTER (N⁺)" if bjt_type=="NPN" else "EMITTER (P⁺)"
    b_lbl = "BASE (P)"     if bjt_type=="NPN" else "BASE (N)"
    c_lbl = "COLLECTOR (N)"if bjt_type=="NPN" else "COLLECTOR (P)"

    fig_band.add_annotation(x=1.4, y=max(ec_all)+0.55, text=f"<b>{e_lbl}</b>", showarrow=False, font=dict(size=11, color='#1565C0'))
    fig_band.add_annotation(x=4.0, y=max(ec_all)+0.55, text=f"<b>{b_lbl}</b>", showarrow=False, font=dict(size=11, color='#B71C1C'))
    fig_band.add_annotation(x=6.6, y=max(ec_all)+0.55, text=f"<b>{c_lbl}</b>", showarrow=False, font=dict(size=11, color='#1B5E20'))

    np.random.seed(42)
    if bjt_type == "NPN":
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.2, 16), y=E_C_Emitter + np.random.uniform(0.02, 0.15, 16),
            mode='markers', marker=dict(color='#1565C0', size=9, line=dict(color='#0D47A1', width=1.5)), name='전자 (e⁻)'))
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.4, 4.6, 10), y=E_V_Base - np.random.uniform(0.02, 0.15, 10),
            mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), name='정공 (h⁺)'))
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(5.8, 7.8, 12), y=E_C_Collector + np.random.uniform(0.02, 0.15, 12),
            mode='markers', marker=dict(color='#1565C0', size=9, line=dict(color='#0D47A1', width=1.5)), showlegend=False))
    else:
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.2, 16), y=E_V_Emitter - np.random.uniform(0.02, 0.15, 16),
            mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), name='정공 (h⁺)'))
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.4, 4.6, 10), y=E_C_Base + np.random.uniform(0.02, 0.15, 10),
            mode='markers', marker=dict(color='#1565C0', size=9, line=dict(color='#0D47A1', width=1.5)), name='전자 (e⁻)'))
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(5.8, 7.8, 12), y=E_V_Collector - np.random.uniform(0.02, 0.15, 12),
            mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), showlegend=False))

    fig_band.add_vline(x=2.8, line=dict(color='gray', width=1, dash='dot'))
    fig_band.add_vline(x=5.2, line=dict(color='gray', width=1, dash='dot'))

    y_bot = min(ev_all) - 0.4
    y_top = max(ec_all) + 0.9

    fig_band.update_layout(
        xaxis=dict(visible=False, range=[-0.2, 8.6]),
        yaxis=dict(visible=False, range=[y_bot, y_top]),
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        legend=dict(x=0.01, y=0.02, bgcolor='rgba(255,255,255,0.85)', bordercolor='lightgray', borderwidth=1, font=dict(size=10), orientation='h'),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

with tab2:
    fig_iv = go.Figure()

    sign    = 1 if bjt_type == "NPN" else -1
    v_max   = V_CC + 0.8
    v_arr   = np.linspace(0, v_max, 300)
    ib_list = [10, 20, 30, 40, 50]
    base_color = (255, 127, 14) if bjt_type == "NPN" else (148, 103, 189)

    for idx, ib_uA in enumerate(ib_list):
        ib_A   = ib_uA * 1e-6
        ic_sat = beta * ib_A * 1000
        alpha  = 0.4 + 0.12 * idx
        color  = f"rgba({base_color[0]},{base_color[1]},{base_color[2]},{alpha:.2f})"

        ic_curve = [max(0.0, ic_sat * np.tanh(v / 0.12) * (1 + early_k * v)) for v in v_arr]

        fig_iv.add_trace(go.Scatter(
            x=[sign * v for v in v_arr], y=[sign * ic for ic in ic_curve],
            mode='lines', line=dict(color=color, width=2.2), showlegend=False))

    sat_ic_mag = (V_CC / R_C) * 1000
    fig_iv.add_trace(go.Scatter(
        x=[0.0, sign * V_CC], y=[sign * sat_ic_mag, 0.0],
        mode='lines', line=dict(color='black', width=2.8), name='직류 부하선'))

    fig_iv.add_vline(x=sign*0.2, line=dict(color='purple', width=1.2, dash='dot'))

    q_x, q_y = sign * q_vce, sign * q_ic_mA
    fig_iv.add_trace(go.Scatter(
        x=[q_x], y=[q_y], mode='markers', marker=dict(color='red', size=13, symbol='circle', line=dict(color='white', width=2)), name="Q점"))
    fig_iv.add_shape(type='line', x0=q_x, x1=q_x, y0=0, y1=q_y, line=dict(color='red', width=1, dash='dash'))
    fig_iv.add_shape(type='line', x0=0, x1=q_x, y0=q_y, y1=q_y, line=dict(color='red', width=1, dash='dash'))

    x_range = [-0.15, V_CC+1.3] if bjt_type=="NPN" else [-(V_CC+1.3), 0.15]
    y_range = [-0.4, sat_ic_mag+1.5] if bjt_type=="NPN" else [-(sat_ic_mag+1.5), 0.4]

    fig_iv.update_layout(
        xaxis_title="V_CE [V]", yaxis_title="I_C [mA]",
        xaxis=dict(range=x_range, showgrid=True, gridcolor='#EEEEEE', zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        yaxis=dict(range=y_range, showgrid=True, gridcolor='#EEEEEE', zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        height=380, margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
        legend=dict(x=0.55 if bjt_type=="NPN" else 0.01, y=0.98 if bjt_type=="NPN" else 0.15, bgcolor='rgba(255,255,255,0.85)', bordercolor='lightgray', borderwidth=1, font=dict(size=10)),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_iv, use_container_width=True)

with tab3:
    canvas_html = f"""
    <div style="display:flex; flex-direction:column; align-items:center; gap:12px; padding-top:15px;">

        <!-- BJT 구조 그림 -->
        {bjt_svg}

        <!-- 캐리어 거동 애니메이션 캔버스 -->
        <canvas id="bjtCanvas" width="530" height="160"
                style="background:#2d2d2d; border-radius:8px; display:block;
                       box-shadow:0px 4px 10px rgba(0,0,0,0.15);"></canvas>

        <!-- 범례 -->
        <p style="color:#aaa; font-size:0.82rem; margin:0; font-family:sans-serif; text-align:center;">
            <span style="color:#00E6FF; font-weight:bold;">● 전자 (Electron)</span>
            &nbsp;&nbsp;&nbsp;&nbsp;
            <span style="color:#FF7043; font-weight:bold;">● 정공 (Hole)</span>
        </p>

        <!-- 동작 설명 (캔버스 밖, 별도 박스) -->
        <div style="
            width:530px;
            background:#1e1e1e;
            border-radius:8px;
            padding:10px 16px;
            border-left:4px solid {desc_color};
            font-family:sans-serif;
            font-size:0.83rem;
            color:{desc_color};
            line-height:1.5;
        ">
            {desc_text}
        </div>

    </div>

    <script>
    (function() {{
        const canvas = document.getElementById('bjtCanvas');
        const ctx    = canvas.getContext('2d');
        const MODE     = '{anim_key}';
        const BJT_TYPE = '{bjt_type}';

        const N_e = 40, N_h = 40;
        let particles = [];

        for (let i = 0; i < N_e; i++) {{
            particles.push({{
                x: Math.random() * canvas.width,
                y: 45 + Math.random() * 70,
                r: 3.5, type: 'electron',
                dir: Math.random() < 0.5 ? 1 : -1
            }});
        }}
        for (let i = 0; i < N_h; i++) {{
            particles.push({{
                x: Math.random() * canvas.width,
                y: 45 + Math.random() * 70,
                r: 3.5, type: 'hole',
                dir: Math.random() < 0.5 ? 1 : -1
            }});
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 접합면 점선
            [160, 360].forEach(x => {{
                ctx.strokeStyle = '#555'; ctx.lineWidth = 1.5;
                ctx.setLineDash([4, 4]);
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
                ctx.setLineDash([]);
            }});

            // 영역 라벨
            ctx.fillStyle = '#bbb'; ctx.font = '13px monospace';
            const labels = {{
                'NPN': ['Emitter (N+)', 'Base (P)',  'Collector (N)'],
                'PNP': ['Emitter (P+)', 'Base (N)', 'Collector (P)']
            }}[BJT_TYPE];
            ctx.fillText(labels[0],  20, 25);
            ctx.fillText(labels[1], 195, 25);
            ctx.fillText(labels[2], 380, 25);

            // 입자 그리기 및 이동
            particles.forEach(p => {{
                ctx.fillStyle   = p.type === 'electron' ? '#00E6FF' : '#FF7043';
                ctx.shadowBlur  = 4;
                ctx.shadowColor = ctx.fillStyle;
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
                ctx.shadowBlur  = 0;

                let vx = 0, scatterX = 0.2;

                if (MODE === 'forward_active') {{
                    if (BJT_TYPE === 'NPN') {{
                        if (p.type === 'electron') {{ vx = 3.5;  if (p.x > canvas.width) p.x = 0; }}
                        else                       {{ vx = -1.5; if (p.x < 0) p.x = 360; }}
                    }} else {{
                        if (p.type === 'hole')     {{ vx = 3.5;  if (p.x > canvas.width) p.x = 0; }}
                        else                       {{ vx = -1.5; if (p.x < 0) p.x = 360; }}
                    }}
                }} else if (MODE === 'saturation') {{
                    if (BJT_TYPE === 'NPN') {{
                        if (p.type === 'electron') {{
                            vx = p.dir * 3.0;
                            if (vx > 0 && p.x > canvas.width) p.x = 0;
                            if (vx < 0 && p.x < 0) p.x = canvas.width;
                        }} else {{
                            vx = p.dir * 1.5;
                            if (vx > 0 && p.x > canvas.width) p.x = 260;
                            if (vx < 0 && p.x < 0) p.x = 260;
                        }}
                    }} else {{
                        if (p.type === 'hole') {{
                            vx = p.dir * 3.0;
                            if (vx > 0 && p.x > canvas.width) p.x = 0;
                            if (vx < 0 && p.x < 0) p.x = canvas.width;
                        }} else {{
                            vx = p.dir * 1.5;
                            if (vx > 0 && p.x > canvas.width) p.x = 260;
                            if (vx < 0 && p.x < 0) p.x = 260;
                        }}
                    }}
                }} else if (MODE === 'reverse_active') {{
                    if (BJT_TYPE === 'NPN') {{
                        if (p.type === 'electron') {{ vx = -3.5; if (p.x < 0) p.x = canvas.width; }}
                        else                       {{ vx = 1.5;  if (p.x > canvas.width) p.x = 160; }}
                    }} else {{
                        if (p.type === 'hole')     {{ vx = -3.5; if (p.x < 0) p.x = canvas.width; }}
                        else                       {{ vx = 1.5;  if (p.x > canvas.width) p.x = 160; }}
                    }}
                }} else {{  // cutoff
                    vx = 0; scatterX = 0.5;
                }}

                p.x += vx + (Math.random() - 0.5) * scatterX;
                p.y += (Math.random() - 0.5) * 0.5;
                if (p.y < 35)  p.y = 135;
                if (p.y > 135) p.y = 35;
            }});

            requestAnimationFrame(draw);
        }}
        draw();
    }})();
    </script>
    """

    components.html(canvas_html, height=430)
