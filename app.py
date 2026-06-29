import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide", page_title="BJT 시뮬레이터")

st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 250px; max-width: 250px; }
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.2rem !important;
    }
    [data-testid="stSidebar"] h3 { font-size: 0.95rem !important; margin-bottom: 5px !important; margin-top: 5px !important; }
    [data-testid="stSidebar"] hr { margin: 6px 0 !important; }
    [data-testid="stSidebar"] .stSlider { margin-top: -15px !important; margin-bottom: -5px !important; }
    [data-testid="stSidebar"] .stNumberInput input { height: 26px !important; padding: 1px 4px !important; font-size: 0.75rem !important; }
    [data-testid="stSidebar"] .stTextArea textarea { font-size: 0.78rem !important; padding: 5px !important; }
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 4px !important; }
    .stat-card { background: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #eaeaea; box-shadow: 0px 4px 10px rgba(0,0,0,0.04); height: 100%; }
    .stat-title { font-size: 0.8rem; color: #7f8c8d; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .stat-label { font-size: 0.72rem; color: #95a5a6; font-weight: 600; }
    .stat-value { font-size: 1.15rem; font-weight: 700; color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── 사이드바 ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔌 BJT 시뮬레이터")
    bjt_type = st.radio("소자 타입", ["NPN", "PNP"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<span style='font-size:0.78rem; font-weight:700;'>접합 전압 인가</span>", unsafe_allow_html=True)

    if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.75
    if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -2.0

    def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
    def update_be_num():    st.session_state.be_num   = st.session_state.v_be_val
    def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
    def update_bc_num():    st.session_state.bc_num   = st.session_state.v_bc_val

    label_be = "V_BE (V)" if bjt_type == "NPN" else "V_EB (V)"
    st.markdown(f"<span style='font-size:0.75rem; font-weight:600; color:#cbd5e1;'>{label_be}</span>", unsafe_allow_html=True)
    V_be = st.slider(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                     key="v_be_val", on_change=update_be_num, label_visibility="collapsed")
    st.number_input(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                    key="be_num", on_change=update_be_slider,
                    value=st.session_state.v_be_val, label_visibility="collapsed")

    label_bc = "V_BC (V)" if bjt_type == "NPN" else "V_CB (V)"
    st.markdown(f"<span style='font-size:0.75rem; font-weight:600; color:#cbd5e1; margin-top:2px; display:block;'>{label_bc}</span>", unsafe_allow_html=True)
    V_bc = st.slider(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                     key="v_bc_val", on_change=update_bc_num, label_visibility="collapsed")
    st.number_input(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                    key="bc_num", on_change=update_bc_slider,
                    value=st.session_state.v_bc_val, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<span style='font-size:0.78rem; font-weight:700;'>💬 AI 질문</span>", unsafe_allow_html=True)
    user_question = st.text_area("질문 입력", height=50, label_visibility="collapsed",
                                 value="현재 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
                                 placeholder="e.g. 현재 바이어스 상태를 물리적으로 설명해줘.")
    ai_btn = st.button("🚀 Gemini 분석 요청", use_container_width=True)

# ── 회로/물리 파라미터 ───────────────────────────────────────────────
V_CC    = 5.0
R_C     = 800.0
beta    = 150
V_AF    = 100.0
early_k = 1.0 / V_AF

# 동작 모드 판정 (6주차 교안 16p 표 2-2)
be_fwd = V_be > 0
bc_fwd = V_bc > 0

if be_fwd and not bc_fwd:
    mode       = "순방향 활성 영역"
    mode_en    = "forward_active"
    mode_color = "#f39c12"
elif be_fwd and bc_fwd:
    mode       = "포화 영역"
    mode_en    = "saturation"
    mode_color = "#28a745"
else:
    mode       = "차단 영역"
    mode_en    = "cutoff"
    mode_color = "#dc3545"

mode_full = f"{mode} ({'Forward Active' if mode_en=='forward_active' else 'Saturation' if mode_en=='saturation' else 'Cutoff'})"

# Q점 계산
R_B_eff = 30000.0
I_B_A   = max(0.0, V_be / R_B_eff) if be_fwd else 0.0

if mode_en == "forward_active":
    I_C_ideal = beta * I_B_A
    I_C_max   = (V_CC - 0.2) / R_C
    q_ic_A    = max(0.0, min(I_C_ideal, I_C_max))
    q_vce     = max(0.2, V_CC - q_ic_A * R_C)
elif mode_en == "saturation":
    q_vce  = 0.2
    q_ic_A = (V_CC - q_vce) / R_C
else:
    q_vce  = V_CC
    q_ic_A = 0.0

q_ic_mA = q_ic_A * 1000

# ── 상단 헤더 ───────────────────────────────────────────────────────
st.markdown("<h3 style='margin-bottom:2px; margin-top:0px;'>📟 BJT 물리 & 특성 시뮬레이터</h3>", unsafe_allow_html=True)
st.markdown("<hr style='margin:2px 0 10px 0;'>", unsafe_allow_html=True)

top_col1, top_col2 = st.columns([0.45, 0.55])

with top_col1:
    st.markdown(f"""
    <div class='stat-card'>
        <div class='stat-title'>Operating Region</div>
        <div style='font-size:1.5rem; font-weight:800; color:{mode_color}; margin-bottom:12px;'>
            {mode} <span style='font-size:1.1rem; font-weight:600;'>({mode_full.split("(")[1].replace(")","") if "(" in mode_full else ""})</span>
        </div>
        <div style='display:grid; grid-template-columns: 1fr 1fr; gap:12px;'>
            <div><div class='stat-label'>인가전압 V_CE</div><div class='stat-value'>{V_be - V_bc:.2f} V</div></div>
            <div><div class='stat-label'>컬렉터전류 I_C</div><div class='stat-value'>{q_ic_mA:.2f} mA</div></div>
            <div><div class='stat-label'>베이스전류 I_B</div><div class='stat-value'>{I_B_A*1e6:.1f} μA</div></div>
            <div><div class='stat-label'>Q점 V_CEQ</div><div class='stat-value'>{q_vce:.2f} V</div></div>
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
                    <div style='background:#f8f9fa; padding:14px; border-radius:12px; border:1px solid #eaeaea;
                                font-size:0.82rem; height:155px; overflow-y:auto; line-height:1.4;'>
                        <strong>💡 AI 실시간 물리적 해설</strong><br>{resp.text}
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"오류: {e}")
        else:
            st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    else:
        st.markdown("""
        <div style='background:#f8f9fa; padding:14px; border-radius:12px; border:1px solid #eaeaea;
                    font-size:0.85rem; height:155px; color:#95a5a6;
                    display:flex; align-items:center; justify-content:center; text-align:center;'>
            사이드바 하단의 '🚀 Gemini 분석 요청' 버튼을 누르면<br>
            이 자리에 물리 밴드 관점의 상세 해설이 실시간 매핑됩니다.
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

# ── 탭 (에너지 밴드 / I-V 곡선 / 캐리어 애니메이션) ────────────────
tab1, tab2, tab3 = st.tabs(["🔋 에너지 밴드 다이어그램", "📈 I_C–V_CE 특성 곡선", "⚡ 캐리어 이동 애니메이션"])

# ════════════════════════════════════════════════════════════════════
#  TAB 1: 에너지 밴드 다이어그램
# ════════════════════════════════════════════════════════════════════
with tab1:
    fig_band = go.Figure()
    E_g = 1.12

    x_all = np.linspace(0, 8.0, 400)
    ec_all = np.zeros_like(x_all)

    v_be_eff = float(np.clip(V_be, -5.0, 0.75))
    v_bc_eff = float(np.clip(V_bc, -5.0, 0.75))

    if bjt_type == "NPN":
        E_F_Base      = 0.0
        E_V_Base      = -0.1
        E_C_Base      = E_V_Base + E_g
        E_F_Emitter   = E_F_Base + v_be_eff
        E_F_Collector = E_F_Base + v_bc_eff
        E_C_Emitter   = E_F_Emitter - 0.05
        E_C_Collector = E_F_Collector - 0.15
    else:
        E_F_Base      = 0.0
        E_C_Base      = 0.1
        E_V_Base      = E_C_Base - E_g
        E_F_Emitter   = E_F_Base - v_be_eff
        E_F_Collector = E_F_Base - v_bc_eff
        E_V_Emitter   = E_F_Emitter + 0.05
        E_V_Collector = E_F_Collector + 0.15
        E_C_Emitter   = E_V_Emitter + E_g
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

    fig_band.add_trace(go.Scatter(x=[0, 2.4],   y=[E_F_Emitter,   E_F_Emitter],   mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (E)'))
    fig_band.add_trace(go.Scatter(x=[3.2, 4.8], y=[E_F_Base,      E_F_Base],      mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (B)'))
    fig_band.add_trace(go.Scatter(x=[5.6, 8.0], y=[E_F_Collector, E_F_Collector], mode='lines', line=dict(color='blue', width=2, dash='dash'), name='E_F (C)'))

    fig_band.add_annotation(x=8.15, y=ec_all[-1]+0.05, text="<b>E_C</b>", showarrow=False, font=dict(size=12))
    fig_band.add_annotation(x=8.15, y=ev_all[-1]-0.05, text="<b>E_V</b>", showarrow=False, font=dict(size=12))

    e_lbl = "EMITTER (N⁺)" if bjt_type=="NPN" else "EMITTER (P⁺)"
    b_lbl = "BASE (P)"      if bjt_type=="NPN" else "BASE (N)"
    c_lbl = "COLLECTOR (N)" if bjt_type=="NPN" else "COLLECTOR (P)"
    fig_band.add_annotation(x=1.4, y=max(ec_all)+0.55, text=f"<b>{e_lbl}</b>", showarrow=False, font=dict(size=11, color='#1565C0'))
    fig_band.add_annotation(x=4.0, y=max(ec_all)+0.55, text=f"<b>{b_lbl}</b>", showarrow=False, font=dict(size=11, color='#B71C1C'))
    fig_band.add_annotation(x=6.6, y=max(ec_all)+0.55, text=f"<b>{c_lbl}</b>", showarrow=False, font=dict(size=11, color='#1B5E20'))

    np.random.seed(42)
    if bjt_type == "NPN":
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.2, 16), y=E_C_Emitter   + np.random.uniform(0.02, 0.15, 16), mode='markers', marker=dict(color='#1565C0', size=9,  line=dict(color='#0D47A1', width=1.5)), name='전자 (e⁻)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.4, 4.6, 10), y=E_V_Base      - np.random.uniform(0.02, 0.15, 10), mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), name='정공 (h⁺)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(5.8, 7.8, 12), y=E_C_Collector + np.random.uniform(0.02, 0.15, 12), mode='markers', marker=dict(color='#1565C0', size=9,  line=dict(color='#0D47A1', width=1.5)), showlegend=False))
    else:
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.2, 16), y=E_V_Emitter   - np.random.uniform(0.02, 0.15, 16), mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), name='정공 (h⁺)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.4, 4.6, 10), y=E_C_Base      + np.random.uniform(0.02, 0.15, 10), mode='markers', marker=dict(color='#1565C0', size=9,  line=dict(color='#0D47A1', width=1.5)), name='전자 (e⁻)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(5.8, 7.8, 12), y=E_V_Collector - np.random.uniform(0.02, 0.15, 12), mode='markers', marker=dict(color='#C62828', size=10, line=dict(color='#7B1818', width=1.5)), showlegend=False))

    fig_band.add_vline(x=2.8, line=dict(color='gray', width=1, dash='dot'))
    fig_band.add_vline(x=5.2, line=dict(color='gray', width=1, dash='dot'))

    fig_band.update_layout(
        xaxis=dict(visible=False, range=[-0.2, 8.6]),
        yaxis=dict(visible=False, range=[min(ev_all)-0.4, max(ec_all)+0.9]),
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        legend=dict(x=0.01, y=0.02, bgcolor='rgba(255,255,255,0.85)',
                    bordercolor='lightgray', borderwidth=1, font=dict(size=10), orientation='h'),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
#  TAB 2: I_C - V_CE 특성 곡선
# ════════════════════════════════════════════════════════════════════
with tab2:
    fig_iv = go.Figure()

    sign       = 1 if bjt_type == "NPN" else -1
    v_max      = V_CC + 0.8
    v_arr      = np.linspace(0, v_max, 300)
    ib_list    = [10, 20, 30, 40, 50]
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

        ic_end = sign * ic_sat * (1 + early_k * v_max)
        fig_iv.add_annotation(
            x=sign * v_max + sign * 0.1, y=ic_end,
            text=f"I_B={ib_uA}μA", showarrow=False,
            font=dict(size=9, color='gray'),
            xanchor='left' if bjt_type=="NPN" else 'right')

    sat_ic_mag = (V_CC / R_C) * 1000
    fig_iv.add_trace(go.Scatter(
        x=[0.0, sign * V_CC], y=[sign * sat_ic_mag, 0.0],
        mode='lines', line=dict(color='black', width=2.8), name='직류 부하선'))

    fig_iv.add_vline(x=sign * 0.2, line=dict(color='purple', width=1.2, dash='dot'))
    fig_iv.add_annotation(x=sign*0.22, y=sign*sat_ic_mag*0.55,
                           text="V_CE,sat", showarrow=False,
                           font=dict(size=9, color='purple'), textangle=-90)

    fig_iv.add_annotation(x=sign*0.15, y=sign*(sat_ic_mag+0.3),
                           text="<b>포화점</b>", showarrow=True,
                           ax=sign*0.6, ay=sign*(sat_ic_mag-0.5),
                           arrowhead=2, arrowcolor='black', font=dict(size=11))
    fig_iv.add_annotation(x=sign*(V_CC-0.1), y=sign*0.4,
                           text="<b>차단점</b>", showarrow=True,
                           ax=sign*(V_CC-0.8), ay=sign*1.0,
                           arrowhead=2, arrowcolor='black', font=dict(size=11))

    q_x, q_y = sign * q_vce, sign * q_ic_mA
    fig_iv.add_trace(go.Scatter(
        x=[q_x], y=[q_y], mode='markers',
        marker=dict(color='red', size=13, symbol='circle', line=dict(color='white', width=2)),
        name=f"Q점 ({q_x:.2f}V, {q_y:.2f}mA)"))
    fig_iv.add_annotation(x=q_x, y=q_y + sign*0.45,
                           text=f"<b>Q ({q_x:.2f}V, {q_y:.2f}mA)</b>",
                           showarrow=False, font=dict(color='red', size=11))
    fig_iv.add_shape(type='line', x0=q_x, x1=q_x, y0=0, y1=q_y, line=dict(color='red', width=1, dash='dash'))
    fig_iv.add_shape(type='line', x0=0,   x1=q_x, y0=q_y, y1=q_y, line=dict(color='red', width=1, dash='dash'))
    fig_iv.add_annotation(x=sign*(-0.08), y=q_y, text="I_CQ", showarrow=False,
                           font=dict(size=9, color='red'), xanchor='right' if bjt_type=="NPN" else 'left')
    fig_iv.add_annotation(x=q_x, y=sign*(-0.3), text="V_CEQ", showarrow=False,
                           font=dict(size=9, color='red'))

    x_range = [-0.15, V_CC+1.3]       if bjt_type=="NPN" else [-(V_CC+1.3), 0.15]
    y_range = [-0.4, sat_ic_mag+1.5]  if bjt_type=="NPN" else [-(sat_ic_mag+1.5), 0.4]

    fig_iv.update_layout(
        xaxis_title="V_CE [V]", yaxis_title="I_C [mA]",
        xaxis=dict(range=x_range, showgrid=True, gridcolor='#EEEEEE',
                   zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        yaxis=dict(range=y_range, showgrid=True, gridcolor='#EEEEEE',
                   zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        height=380, margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
        legend=dict(x=0.55 if bjt_type=="NPN" else 0.01,
                    y=0.98 if bjt_type=="NPN" else 0.15,
                    bgcolor='rgba(255,255,255,0.85)', bordercolor='lightgray',
                    borderwidth=1, font=dict(size=10)),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
#  TAB 3: 캐리어 이동 애니메이션
#  - 동작 모드별 속도/방향/확산도 정의
#  - 주 캐리어(NPN→전자, PNP→정공)와 소수 캐리어 동시 표현
#  - 베이스 재결합 시각화 (순방향 활성 모드)
#  - 모드별 안내 텍스트 + 물리 설명
# ════════════════════════════════════════════════════════════════════
with tab3:
    # 모드별 파라미터
    carrier_color  = "#00E6FF" if bjt_type == "NPN" else "#FF7043"
    carrier_label  = "전자 (Electron)" if bjt_type == "NPN" else "정공 (Hole)"
    minority_color = "#FF7043" if bjt_type == "NPN" else "#00E6FF"  # 소수 캐리어 (베이스)
    minority_label = "정공 (Hole)"     if bjt_type == "NPN" else "전자 (Electron)"

    anim_params = {
        "cutoff": {
            "speed": 0, "dir": 1, "scatter": 0.0,
            "desc": "⛔ 차단 모드: B-E, B-C 모두 역방향 바이어스<br>전위장벽↑ → 캐리어 이동 없음 → 개방 스위치"
        },
        "forward_active": {
            "speed": 4, "dir": 1, "scatter": 0.15,
            "desc": "✅ 순방향 활성: B-E 순방향(장벽↓) + B-C 역방향(전계↑)<br>전자: 이미터→확산→베이스→표류→컬렉터 / 베이스서 일부 재결합"
        },
        "saturation": {
            "speed": 2, "dir": 1, "scatter": 1.2,
            "desc": "⚡ 포화 모드: B-E, B-C 모두 순방향 바이어스<br>캐리어 과잉 주입 → 방향성 약해짐 → 닫힌 스위치 (V_CE ≈ 0.2V)"
        },
    }

    ap    = anim_params[mode_en]
    speed = ap["speed"]
    dire  = ap["dir"] if bjt_type == "NPN" else -ap["dir"]   # PNP는 반대
    sc    = ap["scatter"]
    desc  = ap["desc"]

    # 물리 설명 박스
    st.markdown(f"""
    <div style='background:#1e1e2e; color:#cdd6f4; padding:12px 16px; border-radius:10px;
                font-size:0.85rem; line-height:1.6; margin-bottom:12px; border-left:4px solid {mode_color};'>
        {desc}
    </div>""", unsafe_allow_html=True)

    # Canvas HTML 생성
    canvas_html = f"""
<div style="display:flex; flex-direction:column; align-items:flex-start; gap:6px;">
<canvas id="bjtCanvas" width="720" height="200"
        style="background:#1a1a2e; border-radius:10px; border:1px solid #333; display:block;"></canvas>
<div style="display:flex; gap:18px; font-size:0.78rem; color:#aaa; padding-left:4px;">
    <span>주 캐리어: <span style="color:{carrier_color}; font-weight:700;">● {carrier_label}</span></span>
    <span>소수 캐리어 (Base): <span style="color:{minority_color}; font-weight:700;">● {minority_label}</span></span>
    <span style="color:#888;">| 모드: <span style="color:{mode_color}; font-weight:700;">{mode}</span></span>
</div>
</div>

<script>
(function() {{
    // ── 기존 캔버스 인스턴스 정리 (Streamlit 재렌더링 대응) ──
    const canvas = document.getElementById('bjtCanvas');
    if (!canvas) return;
    if (canvas._animId) cancelAnimationFrame(canvas._animId);
    const ctx = canvas.getContext('2d');

    const W = canvas.width, H = canvas.height;
    const SPEED   = {speed};
    const DIR     = {dire};
    const SCATTER = {sc};
    const MODE    = '{mode_en}';
    const BJT     = '{bjt_type}';

    // 영역 경계 (픽셀)
    const X_BE = 240;   // B-E 경계
    const X_BC = 480;   // B-C 경계
    const Y_MID = H / 2;

    // ── 파티클 초기화 ──────────────────────────────────────────
    const N_MAIN = 40;   // 주 캐리어 (이미터/컬렉터 전도대)
    const N_MIN  = 12;   // 소수 캐리어 (베이스)

    // 주 캐리어: 이미터(0~X_BE) + 컬렉터(X_BC~W) 에 분산
    let mainParticles = Array.from({{length: N_MAIN}}, (_, i) => {{
        const inEmitter = i < N_MAIN * 0.55;
        return {{
            x: inEmitter ? Math.random() * (X_BE - 20) + 10
                         : Math.random() * (W - X_BC - 20) + X_BC + 10,
            y: Y_MID - 20 + Math.random() * 40,
            r: 4.5,
            inEmitter: inEmitter,
            crossing: false,
            alpha: 1.0
        }};
    }});

    // 소수 캐리어: 베이스(X_BE~X_BC) 에 분산
    let minParticles = Array.from({{length: N_MIN}}, () => ({{
        x: Math.random() * (X_BC - X_BE - 20) + X_BE + 10,
        y: Y_MID + 15 + Math.random() * 30,
        r: 4,
        recombining: false,
        recombTimer: 0
    }}));

    // ── 드로우 루프 ────────────────────────────────────────────
    function draw() {{
        ctx.clearRect(0, 0, W, H);

        // 배경 영역 색
        ctx.fillStyle = 'rgba(30,100,200,0.08)';  ctx.fillRect(0,      0, X_BE,    H);
        ctx.fillStyle = 'rgba(200,60,60,0.08)';   ctx.fillRect(X_BE,   0, X_BC-X_BE, H);
        ctx.fillStyle = 'rgba(30,160,80,0.08)';   ctx.fillRect(X_BC,   0, W-X_BC,  H);

        // 경계선
        ctx.strokeStyle = 'rgba(150,150,150,0.5)';
        ctx.lineWidth = 1.2; ctx.setLineDash([5,4]);
        ctx.beginPath(); ctx.moveTo(X_BE,0); ctx.lineTo(X_BE,H); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(X_BC,0); ctx.lineTo(X_BC,H); ctx.stroke();
        ctx.setLineDash([]);

        // 영역 라벨
        ctx.fillStyle = '#8ab4f8'; ctx.font = 'bold 12px monospace';
        ctx.fillText(BJT==='NPN' ? 'EMITTER (N⁺)' : 'EMITTER (P⁺)',  14,  20);
        ctx.fillStyle = '#f28b82'; ctx.font = 'bold 12px monospace';
        ctx.fillText(BJT==='NPN' ? 'BASE (P)'      : 'BASE (N)',      X_BE+20, 20);
        ctx.fillStyle = '#81c995'; ctx.font = 'bold 12px monospace';
        ctx.fillText(BJT==='NPN' ? 'COLLECTOR (N)' : 'COLLECTOR (P)', X_BC+14, 20);

        // 모드 안내
        const modeText = {{
            'cutoff':         '⛔ 차단: 전위장벽↑ → 이동 없음',
            'forward_active': '✅ 순방향 활성: 확산 → 재결합 일부 → 표류',
            'saturation':     '⚡ 포화: 양방향 주입 → 과잉 캐리어'
        }}[MODE];
        ctx.fillStyle = '{mode_color}'; ctx.font = '11px sans-serif';
        ctx.fillText(modeText, 14, H - 10);

        // ── 소수 캐리어 (베이스) ────────────────────────────────
        minParticles.forEach(p => {{
            // 재결합 애니메이션 (순방향 활성에서만)
            if (MODE === 'forward_active' && !p.recombining && Math.random() < 0.002) {{
                p.recombining = true;
                p.recombTimer = 30;
            }}
            if (p.recombining) {{
                p.recombTimer--;
                // 재결합 플래시 효과
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r + (30 - p.recombTimer) * 0.3, 0, Math.PI*2);
                ctx.strokeStyle = `rgba(255,200,0,${{p.recombTimer/30}})`;
                ctx.lineWidth = 1.5; ctx.stroke();
                if (p.recombTimer <= 0) {{
                    p.recombining = false;
                    // 재결합 후 위치 리셋
                    p.x = Math.random() * (X_BC - X_BE - 20) + X_BE + 10;
                    p.y = Y_MID + 15 + Math.random() * 30;
                }}
            }}
            // 소수 캐리어 그리기
            ctx.shadowBlur = 5; ctx.shadowColor = '{minority_color}';
            ctx.fillStyle = '{minority_color}';
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI*2); ctx.fill();
            ctx.shadowBlur = 0;

            // 베이스 내 소수 캐리어는 약한 브라운 운동만
            if (SPEED > 0) {{
                p.x += (Math.random()-0.5) * 1.5;
                p.y += (Math.random()-0.5) * 1.5;
                p.x = Math.max(X_BE+5, Math.min(X_BC-5, p.x));
                p.y = Math.max(Y_MID+5, Math.min(H-15, p.y));
            }}
        }});

        // ── 주 캐리어 ───────────────────────────────────────────
        mainParticles.forEach(p => {{
            ctx.shadowBlur = 8; ctx.shadowColor = '{carrier_color}';
            ctx.fillStyle = '{carrier_color}';
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI*2); ctx.fill();
            ctx.shadowBlur = 0;

            if (SPEED === 0) return;  // 차단: 이동 없음

            // 이동
            const vx = DIR * SPEED + (Math.random()-0.5) * SCATTER;
            const vy = (Math.random()-0.5) * SCATTER * 0.4;
            p.x += vx;
            p.y = Math.max(Y_MID-35, Math.min(Y_MID+35, p.y + vy));

            // 경계 처리: 이미터→베이스 진입 (BE 접합 통과)
            if (DIR > 0 && p.inEmitter && p.x > X_BE) {{
                if (MODE === 'forward_active') {{
                    // 순방향 활성: 베이스 통과 후 컬렉터로
                    p.inEmitter = false;
                }} else if (MODE === 'saturation') {{
                    // 포화: 통과 허용 (역방향도 일부 통과)
                    p.inEmitter = false;
                }} else {{
                    // 차단은 위에서 return으로 처리됨
                    p.x = X_BE - 5;
                }}
            }}

            // 경계 처리: 컬렉터 끝에서 리셋
            if (DIR > 0 && p.x > W) {{
                // 이미터 쪽으로 리셋
                p.x = Math.random() * 30 + 5;
                p.y = Y_MID - 20 + Math.random() * 40;
                p.inEmitter = true;
            }}
            if (DIR < 0 && p.x < 0) {{
                p.x = W - Math.random() * 30 - 5;
                p.y = Y_MID - 20 + Math.random() * 40;
                p.inEmitter = false;
            }}
        }});

        canvas._animId = requestAnimationFrame(draw);
    }}

    draw();
}})();
</script>
"""

    st.components.v1.html(canvas_html, height=240)

    # 모드별 추가 물리 정보 테이블
    st.markdown("#### 📋 동작 모드별 물리 비교")
    st.markdown(f"""
| 항목 | 차단 (Cutoff) | **순방향 활성 (FA)** | 포화 (Saturation) |
|------|:---:|:---:|:---:|
| B-E 접합 | 역방향 | **순방향** | 순방향 |
| B-C 접합 | 역방향 | **역방향** | 순방향 |
| 주 캐리어 이동 | ❌ 없음 | **✅ E→B→C** | ⚠️ 과잉 |
| 전류이득 | 0 | **β ≈ {beta}** | < β |
| 응용 | 개방 스위치 | **증폭기** | 닫힌 스위치 |
| 현재 상태 | {'← 현재' if mode_en=='cutoff' else ''} | {'← 현재' if mode_en=='forward_active' else ''} | {'← 현재' if mode_en=='saturation' else ''} |
""")
