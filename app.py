import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide")
st.title("📟 AI 반도체 소자 직관 보조 툴: BJT 전자/물리 구조 매퍼")

if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API 키가 Secrets에 등록되지 않아 AI 인사이트 기능이 제한됩니다.")

st.sidebar.header("🎛️ BJT 소자 및 바이어스 조절")
bjt_type = st.sidebar.radio("소자 타입 선택 (Type)", ["NPN", "PNP"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 접합 전압 인가 (Bias)")

if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.8
if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -1.7

def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
def update_be_num(): st.session_state.be_num = st.session_state.v_be_val
def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
def update_bc_num(): st.session_state.bc_num = st.session_state.v_bc_val

label_be = "베이스-이미터 전압 (V_BE) [V]" if bjt_type == "NPN" else "이미터-베이스 전압 (V_EB) [V]"
st.sidebar.number_input(label_be, min_value=-1.0, max_value=1.5, step=0.05, key="be_num", on_change=update_be_slider, value=st.session_state.v_be_val)
V_be = st.sidebar.slider(label_be, min_value=-1.0, max_value=1.5, step=0.05, key="v_be_val", on_change=update_be_num, label_visibility="collapsed")

label_bc = "베이스-컬렉터 전압 (V_BC) [V]" if bjt_type == "NPN" else "컬렉터-베이스 전압 (V_CB) [V]"
st.sidebar.number_input(label_bc, min_value=-5.0, max_value=5.0, step=0.1, key="bc_num", on_change=update_bc_slider, value=st.session_state.v_bc_val)
V_bc = st.sidebar.slider(label_bc, min_value=-5.0, max_value=5.0, step=0.1, key="v_bc_val", on_change=update_bc_num, label_visibility="collapsed")

V_CE = V_be - V_bc

st.sidebar.markdown("---")
st.sidebar.header("💬 AI에게 질문하기")
user_question = st.sidebar.text_area(
    "궁금한 점을 입력하세요:",
    value="현재 접합 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
    height=100
)

# ── 동작 모드 판정 (PN 접합 턴온 임계값 통일: 0.65V) ──────────────────────────
VT_ON = 0.65  # PN 접합 턴온 전압 (V_BE, V_BC 동일 기준)
be_forward = V_be > VT_ON
bc_forward = V_bc > VT_ON

V_CC = 5.0
R_C  = 800
max_ic_mA = (V_CC / R_C) * 1000  # 6.25 mA

if be_forward and not bc_forward:
    mode = "순방향 활성 모드 (Forward Active)"
    description = "B-E 순방향, B-C 역방향 바이어스 상태입니다. 캐리어 증폭 작용이 일어납니다."
    ideal_vce = max(0.2, min(V_CC, V_CE))
    ideal_ic  = 3.6 * (1 - np.exp(-ideal_vce / 0.25)) + 0.03 * ideal_vce
    load_ic   = (-(1 / R_C) * ideal_vce + (V_CC / R_C)) * 1000
    q_ic_point  = max(0.0, min(load_ic, ideal_ic))
    q_vce_point = V_CC - (q_ic_point / 1000) * R_C
elif be_forward and bc_forward:
    mode = "포화 모드 (Saturation)"
    description = "B-E 순방향, B-C 순방향 바이어스 상태입니다. 스위치가 닫힌(Closed) 것처럼 동작합니다."
    q_vce_point = max(0.12, min(0.3, V_CE if V_CE > 0 else 0.2))
    q_ic_point  = (-(1 / R_C) * q_vce_point + (V_CC / R_C)) * 1000
else:
    mode = "차단 모드 (Cut-off)"
    description = "B-E 역방향 바이어스 상태입니다. 전류가 흐르지 않는 개방 스위치 상태입니다."
    q_vce_point = V_CC
    q_ic_point  = 0.0

col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("📊 실시간 BJT 물리 상태 시각화")
    st.info(f"**판정 모드:** {bjt_type} {mode}  \n**실시간 계산값:** V_CE = {V_CE:.2f}V, I_C = {q_ic_point:.2f}mA")

    # ══════════════════════════════════════════════════════════════════
    #  에너지 밴드 다이어그램
    #  핵심 수정:
    #   1) 각 영역(E/B/C)의 E_F를 물리적으로 올바르게 분리
    #      - 열평형: E_F 전체 수평
    #      - 순방향 활성: E_F_E > E_F_B > E_F_C (qV_BE, qV_BC 만큼 분리)
    #      - 포화:  E_F_E > E_F_B, E_F_C > E_F_B (두 접합 모두 순방향)
    #      - 차단:  E_F 전체 수평 (열평형과 동일)
    #   2) E_c 밴드 모양: 순방향 바이어스 → 전위장벽 낮아짐 / 역방향 → 높아짐
    #      전위장벽 높이 = 기준값 ± 바이어스 전압 비례
    # ══════════════════════════════════════════════════════════════════
    fig_band = go.Figure()

    # ── 좌표축 정의 ──────────────────────────────────────────────────
    x_e = np.linspace(0, 2.8, 40)   # 이미터 영역
    x_b = np.linspace(2.8, 5.2, 30) # 베이스 영역
    x_c = np.linspace(5.2, 8.0, 40) # 컬렉터 영역
    x_all = np.concatenate([x_e, x_b, x_c])

    # ── E_c 기준 레벨 (이미터 = 0 기준, 1.5eV 오프셋) ───────────────
    E_c_E_level = 1.5   # 이미터 E_c
    E_g = 1.12          # 실리콘 밴드갭
    phi0 = 0.7          # 열평형 내장 전위 (eV 단위 근사)

    # 바이어스에 의한 전위장벽 변화량 (eV 단위, 전압 직접 대입)
    # B-E 접합 장벽: 순방향 인가 시 낮아짐 → phi0 - V_be
    # B-C 접합 장벽: 역방향 인가 시 높아짐 → phi0 + |V_bc| (역방향이면 V_bc < 0)
    be_barrier = phi0 - max(-phi0, min(phi0, V_be))   # 클램프: 0 ~ 2*phi0
    bc_barrier = phi0 - max(-phi0, min(phi0, V_bc))   # V_bc < 0 → barrier 증가

    # E_c 프로파일 구성
    # 이미터: 수평
    y_ec_e = np.full_like(x_e, E_c_E_level)

    # B-E 접합 부근: 장벽 전이 (이미터 → 베이스 방향, 장벽 높이 = be_barrier)
    # 베이스 측 E_c 레벨 = 이미터 E_c - (phi0 - be_barrier) = E_c_E_level - V_be (근사)
    E_c_B_level = E_c_E_level - V_be * 0.8   # 순방향 시 베이스 E_c가 낮아짐
    E_c_B_level = max(E_c_E_level - 1.2, min(E_c_E_level + 1.2, E_c_B_level))

    # 베이스 내부: 수평 (얇은 베이스 가정 → E_c ≈ 일정, 약간 기울기)
    y_ec_b = np.linspace(E_c_B_level, E_c_B_level, len(x_b))

    # B-C 접합 부근: 컬렉터 측 E_c 레벨
    # 역방향 바이어스 시 컬렉터 E_c가 높아짐 (E_c_C > E_c_B)
    E_c_C_level = E_c_B_level + bc_barrier * 0.8
    E_c_C_level = max(E_c_B_level - 0.5, min(E_c_B_level + 2.0, E_c_C_level))

    # 컬렉터: 접합부에서 전위 전이 후 수평
    transition_len = 15  # 전이 구간 포인트 수
    y_ec_c_trans = np.linspace(E_c_B_level, E_c_C_level, transition_len)
    y_ec_c_flat  = np.full(len(x_c) - transition_len, E_c_C_level)
    y_ec_c = np.concatenate([y_ec_c_trans, y_ec_c_flat])

    y_ec = np.concatenate([y_ec_e, y_ec_b, y_ec_c])
    y_ev = y_ec - E_g   # E_v = E_c - E_g (일정한 밴드갭 가정)

    # ── E_F (준페르미 준위) ───────────────────────────────────────────
    # 물리적 원칙:
    #   열평형 & 차단: E_F 전 영역 동일 수평선
    #   순방향 활성:   E_F_E = E_F_ref + q*V_BE/2
    #                  E_F_B = E_F_ref (기준)
    #                  E_F_C = E_F_ref - q*|V_BC|/2  (역방향 → 낮아짐)
    #   포화:          E_F_E > E_F_B, E_F_C > E_F_B

    # 페르미 준위 기준 (도핑에 따라 다르나, NPN 기준 E_c - 0.9 근사)
    E_F_base_ref = E_c_B_level - 0.45  # 베이스 페르미 준위 (P형: E_c - 0.7 ~ E_c - 0.5)

    if mode == "차단 모드 (Cut-off)":
        # 열평형과 유사: 전 영역 동일 E_F
        E_F_E_val = E_F_base_ref
        E_F_B_val = E_F_base_ref
        E_F_C_val = E_F_base_ref
    elif mode == "순방향 활성 모드 (Forward Active)":
        # V_BE > 0 → 이미터 준페르미 준위 상승 (qV_BE 분리)
        # V_BC < 0 → 컬렉터 준페르미 준위 하강 (qV_BC 분리)
        E_F_E_val = E_F_base_ref + V_be * 0.5
        E_F_B_val = E_F_base_ref
        E_F_C_val = E_F_base_ref + V_bc * 0.5   # V_bc<0 → 값이 낮아짐
    else:  # 포화
        E_F_E_val = E_F_base_ref + V_be * 0.5
        E_F_B_val = E_F_base_ref
        E_F_C_val = E_F_base_ref + V_bc * 0.5   # V_bc>0 → 상승

    # 각 영역 E_F 배열 생성 (영역 내부는 수평, 접합부에서 계단 전이)
    y_ef_e = np.full_like(x_e, E_F_E_val)
    y_ef_b = np.full_like(x_b, E_F_B_val)
    y_ef_c = np.full_like(x_c, E_F_C_val)
    y_ef   = np.concatenate([y_ef_e, y_ef_b, y_ef_c])

    # ── 배경 색상 구분 ────────────────────────────────────────────────
    fig_band.add_vrect(x0=0,   x1=2.8, fillcolor="rgba(230,242,255,0.45)", line_width=0)
    fig_band.add_vrect(x0=2.8, x1=5.2, fillcolor="rgba(255,240,245,0.45)", line_width=0)
    fig_band.add_vrect(x0=5.2, x1=8.0, fillcolor="rgba(245,245,220,0.45)", line_width=0)

    # ── E_c, E_v 밴드 ────────────────────────────────────────────────
    fig_band.add_trace(go.Scatter(x=x_all, y=y_ec, mode='lines',
                                  line=dict(color='black', width=3), name='E_c'))
    fig_band.add_trace(go.Scatter(x=x_all, y=y_ev, mode='lines',
                                  line=dict(color='black', width=3), name='E_v'))

    # ── E_F: 영역별 분리 표시 (물리적 핵심) ──────────────────────────
    # 이미터 E_F
    fig_band.add_trace(go.Scatter(x=x_e, y=y_ef_e, mode='lines',
                                  line=dict(color='blue', width=2, dash='dash'), showlegend=False))
    # 베이스 E_F
    fig_band.add_trace(go.Scatter(x=x_b, y=y_ef_b, mode='lines',
                                  line=dict(color='blue', width=2, dash='dash'), showlegend=False))
    # 컬렉터 E_F
    fig_band.add_trace(go.Scatter(x=x_c, y=y_ef_c, mode='lines',
                                  line=dict(color='blue', width=2, dash='dash'), showlegend=False))

    # ── 라벨: 영역별 E_F 값 명시 ─────────────────────────────────────
    fig_band.add_annotation(x=1.4, y=E_F_E_val + 0.18,
                             text=f"<b>E_F(E)</b>", showarrow=False,
                             font=dict(size=10, color="blue"))
    fig_band.add_annotation(x=4.0, y=E_F_B_val + 0.18,
                             text=f"<b>E_F(B)</b>", showarrow=False,
                             font=dict(size=10, color="blue"))
    fig_band.add_annotation(x=6.8, y=E_F_C_val + 0.18,
                             text=f"<b>E_F(C)</b>", showarrow=False,
                             font=dict(size=10, color="blue"))

    # ── E_c, E_v 라벨 ────────────────────────────────────────────────
    fig_band.add_annotation(x=7.85, y=y_ec[-1] + 0.15, text="<b>E_C</b>",
                             showarrow=False, font=dict(size=12, color="black"))
    fig_band.add_annotation(x=7.85, y=y_ev[-1] - 0.18, text="<b>E_V</b>",
                             showarrow=False, font=dict(size=12, color="black"))

    # ── 캐리어 및 메커니즘 (NPN 순방향 활성) ──────────────────────────
    if bjt_type == "NPN":
        # 이미터: 전도대 근처에 전자 (E_c 위)
        np.random.seed(42)
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.6, 20),
            y=y_ec_e[0] + np.random.uniform(0.05, 0.25, 20),
            mode='markers', marker=dict(color='#1f77b4', size=9, line=dict(color='#003380', width=1.5)),
            name='전자(e⁻)', showlegend=False))

        # 베이스: E_v 근처에 정공
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.0, 5.0, 10),
            y=y_ev[40:70:3][:10] + np.random.uniform(-0.1, 0.0, 10),
            mode='markers', marker=dict(color='#d62728', size=10, symbol='circle', line=dict(color='#8b0000', width=1.5)),
            name='정공(h⁺)', showlegend=False))

        if mode == "순방향 활성 모드 (Forward Active)":
            # 확산: 이미터 → 베이스 (전자가 장벽 넘어 이동)
            fig_band.add_annotation(x=3.5, y=E_c_B_level + 0.5,
                                     text="<b>확산(Diffusion) →</b>",
                                     showarrow=False, font=dict(color="#ff7f0e", size=11))
            # 재결합 화살표 (베이스 중간)
            fig_band.add_annotation(x=4.1, y=E_c_B_level - 0.2,
                                     ax=4.1, ay=E_c_B_level - 0.7,
                                     text="재결합", showarrow=True,
                                     arrowhead=2, arrowcolor="red",
                                     font=dict(color="red", size=9))
            # 표류: 베이스 → 컬렉터
            fig_band.add_annotation(x=6.2, y=E_c_C_level + 0.4,
                                     text="<b>← 표류(Drift)</b>",
                                     showarrow=False, font=dict(color="red", size=11))

        elif mode == "차단 모드 (Cut-off)":
            fig_band.add_annotation(x=4.0, y=E_c_B_level + 0.7,
                                     text="전위장벽이 높아 캐리어 이동 없음 (개방 스위치)",
                                     showarrow=False, font=dict(color="gray", size=10))

        elif mode == "포화 모드 (Saturation)":
            fig_band.add_annotation(x=4.0, y=E_c_B_level + 0.7,
                                     text="양쪽 접합 순방향: 닫힌 스위치 (V_CE ≈ V_CE,sat)",
                                     showarrow=False, font=dict(color="purple", size=10))

    else:  # PNP
        np.random.seed(42)
        # 이미터: E_v 근처에 정공
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.6, 20),
            y=y_ev[:40:2][:20] + np.random.uniform(-0.1, 0.05, 20),
            mode='markers', marker=dict(color='#d62728', size=10, symbol='circle', line=dict(color='#8b0000', width=1.5)),
            showlegend=False))
        # 베이스: E_c 근처에 전자
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.0, 5.0, 10),
            y=y_ec[40:70:3][:10] + np.random.uniform(0.0, 0.15, 10),
            mode='markers', marker=dict(color='#1f77b4', size=9, line=dict(color='#003380', width=1.5)),
            showlegend=False))
        if mode == "순방향 활성 모드 (Forward Active)":
            fig_band.add_annotation(x=3.5, y=E_c_B_level + 0.5,
                                     text="<b>← 정공 확산(Diffusion)</b>",
                                     showarrow=False, font=dict(color="#ff7f0e", size=11))
            fig_band.add_annotation(x=6.2, y=E_c_C_level + 0.4,
                                     text="<b>정공 표류(Drift) →</b>",
                                     showarrow=False, font=dict(color="red", size=11))

    # ── 영역 라벨 ─────────────────────────────────────────────────────
    fig_band.add_annotation(x=1.4, y=3.6,
                             text="<b>EMITTER (N⁺)</b>" if bjt_type=="NPN" else "<b>EMITTER (P⁺)</b>",
                             showarrow=False, font=dict(size=12, color="#1f77b4"))
    fig_band.add_annotation(x=4.0, y=3.6,
                             text="<b>BASE (P)</b>" if bjt_type=="NPN" else "<b>BASE (N)</b>",
                             showarrow=False, font=dict(size=12, color="#ff7f0e"))
    fig_band.add_annotation(x=6.5, y=3.6,
                             text="<b>COLLECTOR (N)</b>" if bjt_type=="NPN" else "<b>COLLECTOR (P)</b>",
                             showarrow=False, font=dict(size=12, color="#2ca02c"))

    # ── 범례: 전자/정공 수동 추가 (교안 스타일) ──────────────────────
    fig_band.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(color='#1f77b4', size=9, line=dict(color='#003380', width=1.5)),
        name='전자 (e⁻)'))
    fig_band.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(color='#d62728', size=10, symbol='circle',
                    line=dict(color='#8b0000', width=1.5)),
        name='정공 (h⁺)'))
    fig_band.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color='blue', width=2, dash='dash'),
        name='준페르미 준위 (E_F)'))

    fig_band.update_layout(
        title="<b>🔋 동적 에너지 밴드 다이어그램 (E_F 영역별 분리 고증)</b>",
        xaxis=dict(visible=False, range=[-0.2, 8.6]),
        yaxis=dict(visible=False, range=[-2.0, 4.8]),
        height=340, margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True,
        legend=dict(x=0.01, y=0.01, bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='lightgray', borderwidth=1,
                    font=dict(size=10)),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════
    #  I_C - V_CE 특성 곡선
    #  핵심 수정:
    #   1) 각 I_B 커브에 라벨 추가 (기존: 마지막 커브만 라벨)
    #   2) Early effect 계수 2N3904 datasheet 기반값으로 수정
    #      (V_AF ≈ 100V → 계수 = 1/V_AF ≈ 0.01, 기존 0.038은 과도)
    #   3) β = 150 (2N3904 typ.), 기존 130은 min spec
    #   4) 포화영역 knee 전압 V_CE,sat ≈ 0.2V 표시선 추가
    # ══════════════════════════════════════════════════════════════════
    v_mesh   = np.linspace(0, V_CC + 1.0, 200)
    fig_iv   = go.Figure()

    beta     = 150        # 2N3904 typ. DC 전류이득
    V_AF     = 100.0      # Early voltage (V), 2N3904 ≈ 100V
    early_k  = 1.0 / V_AF  # 0.01 (기존 코드의 0.038은 V_AF≈26V에 해당 → 과도)

    ib_list_uA = [10, 20, 30, 40, 50]
    colors_npn = ['rgba(255,127,14,0.5)', 'rgba(255,127,14,0.6)',
                  'rgba(255,127,14,0.7)', 'rgba(255,127,14,0.85)', 'rgba(255,127,14,1.0)']
    colors_pnp = ['rgba(148,103,189,0.5)', 'rgba(148,103,189,0.6)',
                  'rgba(148,103,189,0.7)', 'rgba(148,103,189,0.85)', 'rgba(148,103,189,1.0)']
    curve_colors = colors_npn if bjt_type == "NPN" else colors_pnp

    for idx, ib_uA in enumerate(ib_list_uA):
        ic_sat = (ib_uA * 1e-6) * beta * 1000  # mA
        curves_mA = []
        for v in v_mesh:
            # Ebers-Moll 근사: I_C = β·I_B·(1-exp(-V_CE/V_T))·(1 + V_CE/V_AF)
            # V_T = 0.026V (실온), 포화영역 knee 포함
            # V_knee ≈ 0.3V: 실제 특성 곡선처럼 완만하게 포화
            ic = ic_sat * (1 - np.exp(-v / 0.3)) * (1 + early_k * v)
            ic = max(0.0, ic)
            curves_mA.append(ic)
        fig_iv.add_trace(go.Scatter(
            x=v_mesh, y=curves_mA, mode='lines',
            line=dict(color=curve_colors[idx], width=2),
            showlegend=False))
        # ── 각 커브마다 라벨 (기존: 마지막만) ──────────────────────
        x_label = V_CC + 0.55
        y_label = ic_sat * (1 + early_k * x_label)
        fig_iv.add_annotation(
            x=x_label, y=y_label,
            text=f"I_B={ib_uA}μA",
            showarrow=False, font=dict(size=9, color="gray"),
            xanchor='left')

    # 직류 부하선
    v_load = np.linspace(0, V_CC, 100)
    i_load = (V_CC / R_C - v_load / R_C) * 1000
    fig_iv.add_trace(go.Scatter(x=v_load, y=i_load, mode='lines',
                                line=dict(color='black', width=2.5), showlegend=False))

    # V_CE,sat 표시선 (≈ 0.2V)
    fig_iv.add_vline(x=0.2, line=dict(color='purple', width=1.2, dash='dot'))
    fig_iv.add_annotation(x=0.2, y=max_ic_mA * 0.5,
                           text="V_CE,sat≈0.2V", showarrow=False,
                           font=dict(size=9, color='purple'), textangle=-90)

    # Q점
    fig_iv.add_trace(go.Scatter(
        x=[q_vce_point], y=[q_ic_point], mode='markers',
        marker=dict(color='red', size=14, symbol='circle',
                    line=dict(color='white', width=1.5)),
        name='동작점 Q'))
    fig_iv.add_annotation(
        x=q_vce_point, y=q_ic_point + 0.45,
        text=f"<b>Q ({q_vce_point:.2f}V, {q_ic_point:.2f}mA)</b>",
        showarrow=False, font=dict(color="red", size=11))

    # 포화점 / 차단점 라벨
    fig_iv.add_annotation(x=0.35, y=max_ic_mA - 0.3,
                           text="<b>포화점</b>", showarrow=True,
                           arrowhead=1, arrowcolor="black")
    fig_iv.add_annotation(x=V_CC, y=0.3,
                           text="<b>차단점</b>", showarrow=True,
                           arrowhead=1, arrowcolor="black")

    fig_iv.update_layout(
        title="<b>📈 BJT I_C–V_CE 특성 곡선 패밀리 & 직류 부하선</b>",
        xaxis_title="컬렉터-이미터 전압 V_CE [V]",
        yaxis_title="컬렉터 전류 I_C [mA]",
        xaxis=dict(range=[-0.1, V_CC + 1.2], showgrid=True, gridcolor='#E5E5E5'),
        yaxis=dict(range=[-0.3, max_ic_mA + 1.8], showgrid=True, gridcolor='#E5E5E5'),
        height=340, margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False, plot_bgcolor='white')
    st.plotly_chart(fig_iv, use_container_width=True)

with col2:
    st.subheader("🤖 AI 반도체 엔지니어 아키텍트 분석")
    st.caption(f"시스템 타겟 파라미터 상태: {bjt_type} / {mode}")

    system_instruction = f"""
    당신은 전 세계 반도체 소자 물리학 및 증폭 회로 설계 부문의 최고 권위자 엔지니어 교수입니다.
    **[Strict Rule] 인삿말이나 서론은 절대 하지 말고 본론 수치 분석부터 출력하세요.**

    현재 사용자가 시뮬레이터에서 설정한 조건:
    - BJT 종류: {bjt_type}형 트랜지스터
    - 인가 바이어스 조건: V_BE = {V_be}V, V_BC = {V_bc}V
    - 판정된 결과적 물리 모드: {mode}

    [미션]
    6주차 에너지 밴드 교안(열적 평형, 순방향 장벽 하강, 캐리어 확산/표류 메커니즘)과
    7주차 바이어스 회로 교안(직류 부하선 상의 Q-point 설계 마진, 차단/포화 파형 잘림 왜곡 방지)을
    융합하여, 수치적/물리적으로 예리한 솔루션을 한국어 경어체 마크다운으로 답변하세요.

    사용자 질문: "{user_question}"
    """

    if st.button("🚀 Gemini 아키텍트 교수님께 연산 요청하기"):
        if "GEMINI_API_KEY" in st.secrets:
            with st.spinner("BJT 내부 물리 거동 및 부하선 동작 한계점 연산 중..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(system_instruction)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"연산 엔진 내부 오류 발생: {e}")
        else:
            st.error("Secrets 금고에 GEMINI_API_KEY가 올바르게 세팅되어 있지 않습니다.")
