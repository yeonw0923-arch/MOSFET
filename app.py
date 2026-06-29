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

# ─────────────────────────────────────────────
#  사이드바: BJT 타입 + 바이어스 슬라이더
# ─────────────────────────────────────────────
st.sidebar.header("🎛️ BJT 소자 및 바이어스 조절")
bjt_type = st.sidebar.radio("소자 타입 선택", ["NPN", "PNP"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 접합 전압 인가 (Bias)")

if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.75
if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -2.0

def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
def update_be_num():    st.session_state.be_num   = st.session_state.v_be_val
def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
def update_bc_num():    st.session_state.bc_num   = st.session_state.v_bc_val

label_be = "V_BE [V]" if bjt_type == "NPN" else "V_EB [V]"
st.sidebar.number_input(label_be, min_value=-1.0, max_value=1.5, step=0.05,
                        key="be_num", on_change=update_be_slider,
                        value=st.session_state.v_be_val)
V_be = st.sidebar.slider(label_be, min_value=-1.0, max_value=1.5, step=0.05,
                         key="v_be_val", on_change=update_be_num,
                         label_visibility="collapsed")

label_bc = "V_BC [V]" if bjt_type == "NPN" else "V_CB [V]"
st.sidebar.number_input(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                        key="bc_num", on_change=update_bc_slider,
                        value=st.session_state.v_bc_val)
V_bc = st.sidebar.slider(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                         key="v_bc_val", on_change=update_bc_num,
                         label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.header("💬 AI에게 질문하기")
user_question = st.sidebar.text_area(
    "궁금한 점을 입력하세요:",
    value="현재 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
    height=100)

# ─────────────────────────────────────────────
#  동작 모드 판정
# ─────────────────────────────────────────────
VT = 0.65   # PN 접합 턴온 전압 (V_BE, V_BC 동일 기준)
be_fwd = V_be >  VT
bc_fwd = V_bc >  VT

# 회로 파라미터 (7주차 예제 기준)
V_CC  = 5.0
R_C   = 800.0   # Ω
beta  = 150     # 2N3904 typ.
V_AF  = 100.0   # Early voltage

if be_fwd and not bc_fwd:
    mode = "순방향 활성 모드 (Forward Active)"
elif be_fwd and bc_fwd:
    mode = "포화 모드 (Saturation)"
else:
    mode = "차단 모드 (Cut-off)"

# ─────────────────────────────────────────────
#  Q점 계산 (슬라이더와 연동)
#
#  V_BE 슬라이더 → I_B 계산 (Shockley 다이오드 방정식 기반)
#  I_C = β * I_B  (순방향 활성),  Early effect 포함
#  V_CE = V_CC - I_C * R_C
# ─────────────────────────────────────────────
V_T   = 0.02585   # 열전압 (실온 300K)
I_S   = 1e-14     # 역포화 전류

# B-E 전류 (Shockley): 베이스 전류 근사
# I_B ≈ I_S / beta * (exp(V_BE/V_T) - 1)
I_B_A = (I_S / beta) * (np.exp(np.clip(V_be, -1, 1.2) / V_T) - 1)
I_B_A = max(0.0, I_B_A)

if mode == "순방향 활성 모드 (Forward Active)":
    # I_C = β * I_B (Early effect 포함은 V_CE 확정 후)
    I_C_ideal = beta * I_B_A          # A
    V_CE_calc = V_CC - I_C_ideal * R_C
    V_CE_calc = max(VT, V_CE_calc)    # 포화점 아래로 내려가지 않도록
    I_C_early = I_C_ideal * (1 + V_CE_calc / V_AF)
    # 부하선 제약: I_C <= (V_CC - V_CE) / R_C
    I_C_load  = (V_CC - V_CE_calc) / R_C
    q_ic_A    = min(I_C_early, I_C_load)
    q_ic_A    = max(0.0, q_ic_A)
    q_vce     = V_CC - q_ic_A * R_C
    q_vce     = max(0.2, q_vce)

elif mode == "포화 모드 (Saturation)":
    q_vce  = 0.2   # V_CE,sat
    q_ic_A = (V_CC - q_vce) / R_C

else:  # Cut-off
    q_vce  = V_CC
    q_ic_A = 0.0

q_ic_mA = q_ic_A * 1000

# ─────────────────────────────────────────────
#  레이아웃
# ─────────────────────────────────────────────
col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("📊 실시간 BJT 물리 상태 시각화")
    st.info(
        f"**판정 모드:** {bjt_type} {mode}  \n"
        f"**V_CE = {V_be - V_bc:.2f}V** (= V_BE - V_BC)   "
        f"**I_B = {I_B_A*1e6:.2f} μA**   "
        f"**I_C = {q_ic_mA:.2f} mA**   "
        f"**Q점: ({q_vce:.2f} V, {q_ic_mA:.2f} mA)**"
    )

    # ══════════════════════════════════════════
    #  에너지 밴드 다이어그램
    #  ─ 6주차 교안 그림 2-5 ~ 2-9 기준 ─
    #
    #  좌표계:
    #    x: 0~3 이미터 / 3~5 베이스 / 5~8 컬렉터
    #    y: E_c, E_v, E_F (eV 단위)
    #
    #  물리 원칙:
    #    E_g(Si) = 1.12 eV → E_v = E_c - 1.12
    #    내장 전위 φ_bi ≈ 0.7 eV (BE, BC 각각)
    #    바이어스 인가 시 접합 전위장벽 = φ_bi - V_bias
    #    역방향 인가 시 전위장벽 = φ_bi + |V_bias|
    #
    #  E_F 영역별 분리:
    #    순방향 활성: E_F(E) > E_F(B) > E_F(C)
    #      - E_F(E) - E_F(B) = q*V_BE
    #      - E_F(B) - E_F(C) = q*|V_BC| (역방향이면 E_F(C) < E_F(B))
    #    포화: E_F(E) > E_F(B), E_F(C) > E_F(B)
    #    차단: 전 영역 수평 (열평형)
    # ══════════════════════════════════════════

    fig_band = go.Figure()
    E_g    = 1.12   # 실리콘 밴드갭 (eV)
    phi_bi = 0.7    # 내장 전위 (eV)

    # ── 이미터 E_c 기준 레벨 ──────────────────
    E_c_E = 2.0

    # ── BE 접합 전위장벽 변화 ─────────────────
    # 순방향(V_be>0): 장벽 낮아짐 → 베이스 E_c 하강
    # 역방향(V_be<0): 장벽 높아짐 → 베이스 E_c 상승
    dE_BE = np.clip(V_be, -1.0, phi_bi)   # 최대 phi_bi까지만 낮아짐
    E_c_B = E_c_E - dE_BE * 0.9           # 베이스 E_c (P형이므로 이미터보다 낮음)

    # ── BC 접합 전위장벽 변화 ─────────────────
    # 역방향(V_bc<0): 컬렉터 E_c 상승 (전위장벽 증가)
    # 순방향(V_bc>0): 컬렉터 E_c 하강
    dE_BC = np.clip(V_bc, -3.0, phi_bi)
    E_c_C = E_c_B - dE_BC * 0.85          # 컬렉터 E_c

    # ── x 좌표 ────────────────────────────────
    x_e  = np.linspace(0,   2.8, 50)
    x_b  = np.linspace(2.8, 5.2, 40)
    x_c  = np.linspace(5.2, 8.0, 50)

    # ── E_c 프로파일 구성 ─────────────────────
    # 이미터: 수평
    ec_e = np.full_like(x_e, E_c_E)

    # BE 접합 전이: sigmoid 함수로 부드럽게
    t_be = np.linspace(-4, 4, len(x_b))
    sig_be = 1 / (1 + np.exp(-t_be))
    ec_b = E_c_E + (E_c_B - E_c_E) * sig_be   # 이미터→베이스 전이

    # 베이스 내부는 E_c_B로 수평 유지 (얇은 베이스 → 거의 수평)
    ec_b_flat = np.full(len(x_b), E_c_B)
    # 접합 부근만 전이, 나머지는 수평
    trans_frac = 0.5
    n_trans = int(len(x_b) * trans_frac)
    ec_b_combined = np.concatenate([
        ec_b[:n_trans],
        np.full(len(x_b) - n_trans, E_c_B)
    ])

    # BC 접합 전이: 베이스→컬렉터
    t_bc = np.linspace(-4, 4, len(x_c))
    sig_bc = 1 / (1 + np.exp(-t_bc))
    ec_c = E_c_B + (E_c_C - E_c_B) * sig_bc

    # 컬렉터 후반부는 수평
    n_trans_c = int(len(x_c) * 0.45)
    ec_c_combined = np.concatenate([
        ec_c[:n_trans_c],
        np.full(len(x_c) - n_trans_c, E_c_C)
    ])

    # ── E_v = E_c - E_g ───────────────────────
    ev_e = ec_e - E_g
    ev_b = ec_b_combined - E_g
    ev_c = ec_c_combined - E_g

    # ── E_F (준페르미 준위) ───────────────────
    # 베이스 E_F 기준: N형(이미터/컬렉터) → E_c - 0.2 근처
    #                  P형(베이스)         → E_v + 0.3 근처
    # 여기서는 표시 편의상 중간값 사용
    E_F_B = (E_c_B + (E_c_B - E_g)) / 2 + 0.1   # 베이스 페르미 준위

    if mode == "차단 모드 (Cut-off)":
        # 열평형과 유사: 전 영역 동일 수평
        E_F_E_val = E_F_B
        E_F_C_val = E_F_B
    elif mode == "순방향 활성 모드 (Forward Active)":
        # E_F(E) - E_F(B) = q*V_BE (순방향이므로 E_F(E) > E_F(B))
        # E_F(B) - E_F(C) = q*|V_BC| (역방향이므로 E_F(C) < E_F(B))
        E_F_E_val = E_F_B + V_be * 0.6
        E_F_C_val = E_F_B + V_bc * 0.6   # V_bc<0 → 낮아짐
    else:  # 포화
        # 양쪽 순방향: E_F(E) > E_F(B), E_F(C) > E_F(B)
        E_F_E_val = E_F_B + V_be * 0.6
        E_F_C_val = E_F_B + V_bc * 0.6   # V_bc>0 → 높아짐

    ef_e = np.full_like(x_e, E_F_E_val)
    ef_b = np.full_like(x_b, E_F_B)
    ef_c = np.full_like(x_c, E_F_C_val)

    # ── 배경 색 ───────────────────────────────
    fig_band.add_vrect(x0=0,   x1=2.8, fillcolor="rgba(173,216,230,0.3)", line_width=0)  # 이미터: 연파랑
    fig_band.add_vrect(x0=2.8, x1=5.2, fillcolor="rgba(255,182,193,0.3)", line_width=0)  # 베이스: 연분홍
    fig_band.add_vrect(x0=5.2, x1=8.0, fillcolor="rgba(144,238,144,0.3)", line_width=0)  # 컬렉터: 연초록

    # ── E_c, E_v 밴드 그리기 ──────────────────
    x_all  = np.concatenate([x_e, x_b, x_c])
    ec_all = np.concatenate([ec_e, ec_b_combined, ec_c_combined])
    ev_all = ec_all - E_g

    fig_band.add_trace(go.Scatter(
        x=x_all, y=ec_all, mode='lines',
        line=dict(color='black', width=3),
        name='E_c', showlegend=True))
    fig_band.add_trace(go.Scatter(
        x=x_all, y=ev_all, mode='lines',
        line=dict(color='black', width=3),
        name='E_v', showlegend=True))

    # ── E_F 영역별 분리 표시 ──────────────────
    fig_band.add_trace(go.Scatter(
        x=x_e, y=ef_e, mode='lines',
        line=dict(color='blue', width=2, dash='dash'),
        name='E_F (준페르미)', showlegend=True))
    fig_band.add_trace(go.Scatter(
        x=x_b, y=ef_b, mode='lines',
        line=dict(color='blue', width=2, dash='dash'),
        showlegend=False))
    fig_band.add_trace(go.Scatter(
        x=x_c, y=ef_c, mode='lines',
        line=dict(color='blue', width=2, dash='dash'),
        showlegend=False))

    # ── E_F 라벨 ──────────────────────────────
    fig_band.add_annotation(x=1.4,  y=E_F_E_val+0.15, text="<b>E_F</b>",
                             showarrow=False, font=dict(size=11, color='blue'))
    fig_band.add_annotation(x=4.0,  y=E_F_B+0.15,     text="<b>E_F</b>",
                             showarrow=False, font=dict(size=11, color='blue'))
    fig_band.add_annotation(x=6.8,  y=E_F_C_val+0.15, text="<b>E_F</b>",
                             showarrow=False, font=dict(size=11, color='blue'))

    # ── E_c / E_v 끝 라벨 ────────────────────
    fig_band.add_annotation(x=8.1, y=ec_c_combined[-1]+0.1,
                             text="<b>E_C</b>", showarrow=False,
                             font=dict(size=13, color='black'))
    fig_band.add_annotation(x=8.1, y=ev_c[-1]-0.15,
                             text="<b>E_V</b>", showarrow=False,
                             font=dict(size=13, color='black'))

    # ── 캐리어 배치 ───────────────────────────
    # 6주차 교안 그림 2-7 기준:
    #  NPN 순방향 활성:
    #   ① 이미터 전자 → E_c 위에 분포 (파란 원)
    #   ② 베이스 정공 → E_v 위에 분포 (빨간 원)
    #   ③ 컬렉터에도 전자 분포 (파란 원) ← 기존 코드에서 누락된 부분
    #   ④ 확산/표류 화살표
    np.random.seed(7)

    if bjt_type == "NPN":
        # ① 이미터: 전자 (E_c 위)
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.6, 18),
            y=ec_e[0] + np.random.uniform(0.08, 0.28, 18),
            mode='markers',
            marker=dict(color='#1565C0', size=10,
                        line=dict(color='#0D47A1', width=1.5)),
            name='전자 (e⁻)', showlegend=True))

        # ② 베이스: 정공 (E_v 위) — 교안 그림처럼 베이스에만 정공 집중
        base_ev_y = E_c_B - E_g   # 베이스 E_v 레벨
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.0, 5.0, 12),
            y=base_ev_y + np.random.uniform(0.0, 0.2, 12),
            mode='markers',
            marker=dict(color='#C62828', size=11,
                        line=dict(color='#7B1818', width=1.5)),
            name='정공 (h⁺)', showlegend=True))

        # ③ 컬렉터: 전자 (E_c 위) — 교안에서 표류로 넘어온 전자
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(5.4, 7.8, 14),
            y=ec_c_combined[-1] + np.random.uniform(0.08, 0.25, 14),
            mode='markers',
            marker=dict(color='#1565C0', size=10,
                        line=dict(color='#0D47A1', width=1.5)),
            showlegend=False))

        # ── 메커니즘 화살표/텍스트 (순방향 활성만) ──
        if mode == "순방향 활성 모드 (Forward Active)":
            # 확산: 이미터→베이스 (전자가 BE 장벽 넘어)
            fig_band.add_annotation(
                x=3.5, y=E_c_B + 0.55,
                text="<b>① 확산 →</b>",
                showarrow=False, font=dict(color='#FF6F00', size=12))
            # 재결합: 베이스에서 일부 소멸
            fig_band.add_annotation(
                x=4.0, y=base_ev_y + 0.55,
                ax=4.0, ay=base_ev_y + 0.1,
                text="③ 재결합", showarrow=True,
                arrowhead=2, arrowsize=1, arrowcolor='red',
                font=dict(color='red', size=10))
            # 표류: 베이스→컬렉터 (BC 역방향 전계)
            fig_band.add_annotation(
                x=6.5, y=ec_c_combined[-1] + 0.55,
                text="<b>② 표류 →</b>",
                showarrow=False, font=dict(color='red', size=12))

        elif mode == "차단 모드 (Cut-off)":
            fig_band.add_annotation(
                x=4.0, y=E_c_B + 0.7,
                text="⛔ 전위장벽↑ → 캐리어 이동 없음 (개방 스위치)",
                showarrow=False, font=dict(color='gray', size=10))

        elif mode == "포화 모드 (Saturation)":
            fig_band.add_annotation(
                x=4.0, y=E_c_B + 0.7,
                text="⚡ 양쪽 장벽↓ → 닫힌 스위치 (V_CE ≈ 0.2V)",
                showarrow=False, font=dict(color='purple', size=10))

    else:  # PNP
        # 이미터: 정공 (E_v 위)
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(0.2, 2.6, 18),
            y=ev_e[0] + np.random.uniform(0.0, 0.2, 18),
            mode='markers',
            marker=dict(color='#C62828', size=11,
                        line=dict(color='#7B1818', width=1.5)),
            name='정공 (h⁺)', showlegend=True))
        # 베이스: 전자 (E_c 위)
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(3.0, 5.0, 10),
            y=ec_b_combined[int(len(ec_b_combined)*0.3):int(len(ec_b_combined)*0.7):4][:10] + 0.1,
            mode='markers',
            marker=dict(color='#1565C0', size=10,
                        line=dict(color='#0D47A1', width=1.5)),
            name='전자 (e⁻)', showlegend=True))
        # 컬렉터: 정공 (E_v 위)
        fig_band.add_trace(go.Scatter(
            x=np.random.uniform(5.4, 7.8, 14),
            y=ev_c[-1] + np.random.uniform(0.0, 0.2, 14),
            mode='markers',
            marker=dict(color='#C62828', size=11,
                        line=dict(color='#7B1818', width=1.5)),
            showlegend=False))

        if mode == "순방향 활성 모드 (Forward Active)":
            fig_band.add_annotation(x=3.5, y=E_c_B+0.5,
                                     text="<b>← 정공 확산</b>", showarrow=False,
                                     font=dict(color='#FF6F00', size=12))
            fig_band.add_annotation(x=6.5, y=E_c_C+0.5,
                                     text="<b>← 정공 표류</b>", showarrow=False,
                                     font=dict(color='red', size=12))

    # ── 영역 라벨 ─────────────────────────────
    e_label = "EMITTER (N⁺)" if bjt_type=="NPN" else "EMITTER (P⁺)"
    b_label = "BASE (P)"     if bjt_type=="NPN" else "BASE (N)"
    c_label = "COLLECTOR (N)"if bjt_type=="NPN" else "COLLECTOR (P)"

    fig_band.add_annotation(x=1.4, y=ec_e[0]+0.65,  text=f"<b>{e_label}</b>",
                             showarrow=False, font=dict(size=12, color='#1565C0'))
    fig_band.add_annotation(x=4.0, y=E_c_B+0.65,    text=f"<b>{b_label}</b>",
                             showarrow=False, font=dict(size=12, color='#B71C1C'))
    fig_band.add_annotation(x=6.5, y=ec_c_combined[-1]+0.65, text=f"<b>{c_label}</b>",
                             showarrow=False, font=dict(size=12, color='#1B5E20'))

    # ── 접합 경계선 ───────────────────────────
    fig_band.add_vline(x=2.8, line=dict(color='gray', width=1, dash='dot'))
    fig_band.add_vline(x=5.2, line=dict(color='gray', width=1, dash='dot'))

    y_range_bot = min(ev_e[0], ev_c[-1], E_F_C_val) - 0.5
    y_range_top = max(ec_e[0], ec_c_combined[-1], E_F_E_val) + 0.9

    fig_band.update_layout(
        title="<b>🔋 에너지 밴드 다이어그램 (6주차 교안 기준)</b>",
        xaxis=dict(visible=False, range=[-0.2, 8.5]),
        yaxis=dict(visible=False, range=[y_range_bot, y_range_top]),
        height=360,
        margin=dict(l=10, r=10, t=45, b=10),
        showlegend=True,
        legend=dict(x=0.01, y=0.02, bgcolor='rgba(255,255,255,0.85)',
                    bordercolor='lightgray', borderwidth=1,
                    font=dict(size=10), orientation='h'),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

    # ══════════════════════════════════════════
    #  I_C - V_CE 특성 곡선 + 직류 부하선
    #  ─ 7주차 교안 그림 2-14 기준 ─
    #
    #  - 특성 곡선 패밀리: I_B = 10~50 μA (5개)
    #  - 직류 부하선: 기울기 -1/R_C, x절편 V_CC, y절편 V_CC/R_C
    #  - Q점: 슬라이더 V_BE → I_B 계산 → 부하선 위 실제 좌표
    #  - 포화점(y절편), 차단점(x절편) 표시
    # ══════════════════════════════════════════
    fig_iv = go.Figure()

    # ── NPN / PNP 부호 처리 ───────────────────────────────────────────
    # NPN: V_CE > 0, I_C > 0  → 1사분면
    # PNP: V_EC > 0 (= V_CE < 0), I_C < 0 → 3사분면 (교안 그림 5-2)
    #      x축: V_CE (음수), y축: I_C (음수)
    sign     = 1 if bjt_type == "NPN" else -1
    v_max    = V_CC + 0.8
    v_arr    = np.linspace(0, v_max, 300)
    ib_list  = [10, 20, 30, 40, 50]   # μA
    early_k  = 1.0 / V_AF

    base_color = (255, 127, 14) if bjt_type == "NPN" else (148, 103, 189)

    for idx, ib_uA in enumerate(ib_list):
        ib_A   = ib_uA * 1e-6
        ic_sat = beta * ib_A * 1000   # mA (양수 기준)
        alpha  = 0.4 + 0.12 * idx
        color  = f"rgba({base_color[0]},{base_color[1]},{base_color[2]},{alpha:.2f})"

        ic_curve = []
        for v in v_arr:
            ic = ic_sat * (1 - np.exp(-v / 0.3)) * (1 + early_k * v)
            ic_curve.append(max(0.0, ic))

        # PNP: x, y 모두 부호 반전
        x_plot = [sign * v for v in v_arr]
        y_plot = [sign * ic for ic in ic_curve]

        fig_iv.add_trace(go.Scatter(
            x=x_plot, y=y_plot, mode='lines',
            line=dict(color=color, width=2.2),
            showlegend=False))

        # 커브 끝 라벨
        ic_end = sign * ic_sat * (1 + early_k * v_max)
        label_x = sign * v_max + sign * 0.1
        fig_iv.add_annotation(
            x=label_x, y=ic_end,
            text=f"I_B={ib_uA}μA",
            showarrow=False, font=dict(size=9, color='gray'),
            xanchor='left' if bjt_type=="NPN" else 'right')

    # ── 직류 부하선 ────────────────────────────
    # NPN: (0, V_CC/R_C) ~ (V_CC, 0)
    # PNP: (0, -V_CC/R_C) ~ (-V_CC, 0)
    sat_ic_mag = (V_CC / R_C) * 1000   # 절대값 mA
    v_load = np.array([0.0, sign * V_CC])
    i_load = np.array([sign * sat_ic_mag, 0.0])

    fig_iv.add_trace(go.Scatter(
        x=v_load, y=i_load, mode='lines',
        line=dict(color='black', width=2.8),
        name='직류 부하선', showlegend=True))

    # 포화점 / 차단점
    sat_x = sign * 0.15
    sat_y = sign * (sat_ic_mag + 0.3)
    cut_x = sign * (V_CC - 0.1)
    cut_y = sign * 0.4

    fig_iv.add_annotation(x=sat_x, y=sat_y,
                           text="<b>포화점</b>",
                           showarrow=True,
                           ax=sign*0.6, ay=sign*(sat_ic_mag-0.5),
                           arrowhead=2, arrowcolor='black',
                           font=dict(size=11))
    fig_iv.add_annotation(x=cut_x, y=cut_y,
                           text="<b>차단점</b>",
                           showarrow=True,
                           ax=sign*(V_CC-0.8), ay=sign*1.0,
                           arrowhead=2, arrowcolor='black',
                           font=dict(size=11))

    # V_CE,sat 기준선
    fig_iv.add_vline(x=sign * 0.2,
                     line=dict(color='purple', width=1.2, dash='dot'))
    fig_iv.add_annotation(x=sign*0.22, y=sign*sat_ic_mag*0.55,
                           text="V_CE,sat", showarrow=False,
                           font=dict(size=9, color='purple'), textangle=-90)

    # ── Q점 ────────────────────────────────────
    q_x = sign * q_vce
    q_y = sign * q_ic_mA

    fig_iv.add_trace(go.Scatter(
        x=[q_x], y=[q_y],
        mode='markers',
        marker=dict(color='red', size=14, symbol='circle',
                    line=dict(color='white', width=2)),
        name=f"Q점"))

    fig_iv.add_annotation(
        x=q_x, y=q_y + sign*0.5,
        text=f"<b>Q ({q_x:.2f}V, {q_y:.2f}mA)</b>",
        showarrow=False, font=dict(color='red', size=11))

    # Q점 수직/수평 점선
    fig_iv.add_shape(type='line',
                     x0=q_x, x1=q_x, y0=0, y1=q_y,
                     line=dict(color='red', width=1, dash='dash'))
    fig_iv.add_shape(type='line',
                     x0=0, x1=q_x, y0=q_y, y1=q_y,
                     line=dict(color='red', width=1, dash='dash'))

    fig_iv.add_annotation(x=sign*(-0.08), y=q_y,
                           text="I_CQ", showarrow=False,
                           font=dict(size=9, color='red'),
                           xanchor='right' if bjt_type=="NPN" else 'left')
    fig_iv.add_annotation(x=q_x, y=sign*(-0.28),
                           text="V_CEQ", showarrow=False,
                           font=dict(size=9, color='red'))

    # ── 축 범위 ────────────────────────────────
    x_range = [-0.15, V_CC+1.3] if bjt_type=="NPN" else [-(V_CC+1.3), 0.15]
    y_range = [-0.4, sat_ic_mag+1.5] if bjt_type=="NPN" else [-(sat_ic_mag+1.5), 0.4]

    fig_iv.update_layout(
        title="<b>📈 I_C–V_CE 특성 곡선 & 직류 부하선 (7주차 교안 기준)</b>",
        xaxis_title="V_CE [V]",
        yaxis_title="I_C [mA]",
        xaxis=dict(range=x_range, showgrid=True, gridcolor='#EEEEEE',
                   zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        yaxis=dict(range=y_range, showgrid=True, gridcolor='#EEEEEE',
                   zeroline=True, zerolinecolor='black', zerolinewidth=1.5),
        height=360,
        margin=dict(l=10, r=10, t=45, b=10),
        showlegend=True,
        legend=dict(x=0.55 if bjt_type=="NPN" else 0.01,
                    y=0.98 if bjt_type=="NPN" else 0.15,
                    bgcolor='rgba(255,255,255,0.85)',
                    bordercolor='lightgray', borderwidth=1,
                    font=dict(size=10)),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# ─────────────────────────────────────────────
#  AI 분석
# ─────────────────────────────────────────────
with col2:
    st.subheader("🤖 AI 반도체 엔지니어 아키텍트 분석")
    st.caption(f"상태: {bjt_type} / {mode}")

    system_instruction = f"""
당신은 반도체 소자 물리학 및 증폭 회로 설계 전문가입니다.
[규칙] 인삿말 없이 바로 수치 분석부터 시작하세요.

현재 설정 조건:
- BJT 종류: {bjt_type}
- V_BE = {V_be:.2f}V, V_BC = {V_bc:.2f}V
- 판정 모드: {mode}
- I_B = {I_B_A*1e6:.2f} μA, I_C = {q_ic_mA:.2f} mA, Q점: V_CE = {q_vce:.2f}V

[미션]
6주차 에너지 밴드 교안(열적 평형, 순방향 장벽 하강, 캐리어 확산/표류)과
7주차 바이어스 교안(직류 부하선, Q점 설계 마진, 왜곡 방지)을 연결하여
사용자 질문에 수치적/물리적으로 명확한 한국어 마크다운 답변을 하세요.

사용자 질문: "{user_question}"
"""

    if st.button("🚀 Gemini 교수님께 분석 요청"):
        if "GEMINI_API_KEY" in st.secrets:
            with st.spinner("분석 중..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    resp  = model.generate_content(system_instruction)
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"오류: {e}")
        else:
            st.error("GEMINI_API_KEY가 Secrets에 없습니다.")
