import streamlit as st
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 레이아웃 설정 (와이드 모드)
st.set_page_config(layout="wide")
st.title("📟 AI 반도체 소자 직관 보조 툴: BJT 전자/물리 구조 매퍼")

# 2. API 키 보안 로드 (Secrets 금고 활용)
if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API 키가 Secrets에 등록되지 않아 AI 인사이트 기능이 제한됩니다.")

# 3. 좌측 사이드바: BJT 타입 및 슬라이더 + 입력창 실시간 동기화 아키텍처
st.sidebar.header("🎛️ BJT 소자 및 바이어스 조절")
bjt_type = st.sidebar.radio("소자 타입 선택 (Type)", ["NPN", "PNP"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 접합 전압 인가 (Bias)")

# 세션 상태(st.session_state)를 이용한 슬라이더 & number_input 쌍방향 실시간 연동 로직
if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.8
if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -1.7

def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
def update_be_num(): st.session_state.be_num = st.session_state.v_be_val
def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
def update_bc_num(): st.session_state.bc_num = st.session_state.v_bc_val

# 🛠️ [범위 수정] V_BE 제어 컴포넌트 (현실적인 -1.0V ~ 1.5V 세팅)
label_be = "베이스-이미터 전압 (V_BE) [V]" if bjt_type == "NPN" else "이미터-베이스 전압 (V_EB) [V]"
st.sidebar.number_input(label_be, min_value=-1.0, max_value=1.5, step=0.05, key="be_num", on_change=update_be_slider, value=st.session_state.v_be_val)
V_be = st.sidebar.slider(label_be, min_value=-1.0, max_value=1.5, step=0.05, key="v_be_val", on_change=update_be_num, label_visibility="collapsed")

# 🛠️ [범위 수정] V_BC 제어 컴포넌트 (부하선 연동형 -5.0V ~ 5.0V 세팅)
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

# 4. 백엔드 알고리즘: 실제 물리 바이어스 기준 동작 모드 정밀 판정 (교안 6p 표 2-2)
be_forward = V_be > 0.65  
bc_forward = V_bc > 0.50

# 7주차 부하선 스펙 가산 연동 (V_CC = 5V, R_C = 800옴)
V_CC = 5.0  
R_C = 800   
max_ic_mA = (V_CC / R_C) * 1000  # 6.25 mA

if be_forward and not bc_forward:
    mode = "순방향 활성 모드 (Forward Active)"
    description = "B-E 순방향, B-C 역방향 바이어스 상태입니다. 캐리어 증폭 작용이 일어납니다."
    # 실제 부하선(Load Line) 방정식과 연동되는 물리 동작점 수치 계산 기법 적용
    ideal_vce = max(0.2, min(V_CC, V_CE))
    ideal_ic = 3.6 * (1 - np.exp(-ideal_vce / 0.25)) + 0.03 * ideal_vce
    load_ic = (-(1 / R_C) * ideal_vce + (V_CC / R_C)) * 1000
    q_ic_point = max(0.0, min(load_ic, ideal_ic))
    q_vce_point = V_CC - (q_ic_point / 1000) * R_C
elif be_forward and bc_forward:
    mode = "포화 모드 (Saturation)"
    description = "B-E 순방향, B-C 순방향 바이어스 상태입니다. 스위치가 닫힌(Closed) 것처럼 동작합니다."
    q_vce_point = max(0.12, min(0.3, V_CE if V_CE > 0 else 0.2)) # Knee 전압 포화 영역 수렴
    q_ic_point = (-(1 / R_C) * q_vce_point + (V_CC / R_C)) * 1000
else:
    mode = "차단 모드 (Cut-off)"
    description = "B-E 역방향, B-C 역방향 바이어스 상태입니다. 전류가 흐르지 않는 개방 스위치 상태입니다."
    q_vce_point = V_CC
    q_ic_point = 0.0

# 5. 화면 분할
col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("📊 실시간 BJT 물리 상태 시각화")
    st.info(f"**판정 모드:** {bjt_type} {mode}  \n**실시간 계산값:** V_CE = {V_CE:.2f}V, I_C = {q_ic_point:.2f}mA")
    
    # ------------------------------------------------------------------
    # [차트 1] 6주차 교안 고증 100%: E_c, E_v, E_f 풀 라벨링 및 캐리어 메커니즘 차트
    # ------------------------------------------------------------------
    fig_band = go.Figure()
    
    v_be_clamped = max(-3.0, min(3.0, V_be))
    v_bc_clamped = max(-3.0, min(3.0, V_bc))
    be_shift = -v_be_clamped * 0.7
    bc_shift = -v_bc_clamped * 0.7
    
    x_e = np.linspace(0, 3, 40)
    x_b = np.linspace(3, 5, 30)
    x_c = np.linspace(5, 8, 40)
    
    y_e_ec = np.zeros_like(x_e) + 1.5
    y_b_peak = 1.5 + (0.8 if bjt_type == "NPN" else -0.8) + be_shift
    y_b_ec = 1.5 + (y_b_peak - 1.5) * np.sin(np.linspace(0, np.pi/2, len(x_b)))
    y_c_base_end = y_b_ec[-1]
    y_c_target = 1.5 + be_shift - bc_shift
    y_c_ec = y_c_target + (y_c_base_end - y_c_target) * np.exp(-3 * np.linspace(0, 1, len(x_c)))
    
    x_total = np.concatenate([x_e, x_b, x_c])
    y_ec = np.concatenate([y_e_ec, y_b_ec, y_c_ec])
    y_ev = y_ec - 1.2  
    
    y_ef = np.zeros_like(x_total) + 0.7
    if mode != "차단 모드 (Cut-off)" and (V_be != 0 or V_bc != 0):
        y_ef[:40] = 0.7
        y_ef[40:] = 0.7 + be_shift
    
    fig_band.add_vrect(x0=0, x1=3, fillcolor="rgba(230, 242, 255, 0.45)", line_width=0)
    fig_band.add_vrect(x0=3, x1=5, fillcolor="rgba(255, 240, 245, 0.45)", line_width=0)
    fig_band.add_vrect(x0=5, x1=8, fillcolor="rgba(245, 245, 220, 0.45)", line_width=0)
    
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ec, mode='lines', line=dict(color='#000000', width=3.5)))
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ev, mode='lines', line=dict(color='#000000', width=3.5)))
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ef, mode='lines', line=dict(color='blue', width=1.5, dash='dash')))
    
    # 준위별 축 텍스트 명시 라벨링 고증
    fig_band.add_annotation(x=7.8, y=y_c_ec[-1]+0.2, text="<b>E_C</b>", showarrow=False, font=dict(size=12, color="black"))
    fig_band.add_annotation(x=7.8, y=y_ef[-1]-0.15, text="<b>E_F</b>", showarrow=False, font=dict(size=12, color="blue"))
    fig_band.add_annotation(x=7.8, y=y_ev[-1]-0.2, text="<b>E_V</b>", showarrow=False, font=dict(size=12, color="black"))
    
    if bjt_type == "NPN":
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 20), y=np.random.uniform(1.55, 1.75, 20), mode='markers', marker=dict(color='#1f77b4', size=6.5, line=dict(color='white', width=0.3)), name='전자'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.2, 4.8, 12), y=np.random.uniform(y_b_peak-1.1, y_b_peak-0.85, 12), mode='markers', marker=dict(color='#d62728', size=6, line=dict(color='white', width=0.3)), name='정공'))
        
        if mode == "순방향 활성 모드 (Forward Active)":
            fig_band.add_trace(go.Scatter(x=[2.9, 3.3, 3.8, 4.4], y=[1.55, y_b_ec[4]+0.06, y_b_ec[12]+0.06, y_b_ec[21]+0.06], mode='markers', marker=dict(color='#1f77b4', size=7, symbol='circle')))
            fig_band.add_annotation(x=3.8, y=y_b_peak+0.3, text="<b>🔥 확산 (Diffusion)</b>", showarrow=False, font=dict(color="#ff7f0e", size=11))
            
            fig_band.add_trace(go.Scatter(x=[4.1, 4.1], y=[y_b_ec[16]+0.05, y_b_peak-0.85], mode='lines+markers', line=dict(color='red', width=1.5, dash='dash'), marker=dict(symbol='triangle-down', size=6)))
            fig_band.add_annotation(x=4.5, y=y_b_peak-0.4, text="재결합<br>(Recombination)", showarrow=False, font=dict(color="red", size=9))
            
            fig_band.add_trace(go.Scatter(x=[5.1, 5.8, 6.8, 7.6], y=[y_c_ec[2]+0.06, y_c_ec[12]+0.06, y_c_ec[25]+0.06, y_c_ec[37]+0.06], mode='markers+lines', line=dict(color='red', width=1, dash='dot'), marker=dict(color='#1f77b4', size=7, symbol='arrow', angleref='previous')))
            fig_band.add_annotation(x=6.4, y=y_c_target+0.4, text="<b>⚡ 표류 (Drift)</b>", showarrow=False, font=dict(color="red", size=11))
    else:
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 20), y=np.random.uniform(0.1, 0.3, 20), mode='markers', marker=dict(color='#d62728', size=6.5, line=dict(color='white', width=0.3))))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.2, 4.8, 12), y=np.random.uniform(y_b_peak+0.85, y_b_peak+1.1, 12), mode='markers', marker=dict(color='#1f77b4', size=6, line=dict(color='white', width=0.3))))
        if mode == "순방향 활성 모드 (Forward Active)":
            fig_band.add_trace(go.Scatter(x=[2.9, 3.5, 4.5, 5.4, 6.8], y=[0.3, y_ev[45]-0.06, y_ev[62]-0.06, y_ev[82]-0.06, y_ev[105]-0.06], mode='markers+lines', line=dict(color='#9467bd', width=1.5, dash='dot'), marker=dict(color='#d62728', size=7, symbol='arrow', angleref='previous')))

    fig_band.add_annotation(x=1.5, y=3.5, text="<b>EMITTER (N+)</b>" if bjt_type=="NPN" else "<b>EMITTER (P+)</b>", showarrow=False, font=dict(size=12, color="#1f77b4"))
    fig_band.add_annotation(x=4.0, y=3.5, text="<b>BASE (P)</b>" if bjt_type=="NPN" else "<b>BASE (N)</b>", showarrow=False, font=dict(size=12, color="#ff7f0e"))
    fig_band.add_annotation(x=6.5, y=3.5, text="<b>COLLECTOR (N)</b>" if bjt_type=="NPN" else "<b>COLLECTOR (P)</b>", showarrow=False, font=dict(size=12, color="#2ca02c"))

    fig_band.update_layout(
        title="<b>🔋 6주차 강의자료 동기화: 동적 에너지 밴드 다이어그램 (풀 고증)</b>",
        xaxis=dict(visible=False, range=[-0.2, 8.4]), yaxis=dict(visible=False, range=[-1.8, 4.2]),
        height=280, margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

    # ------------------------------------------------------------------
    # [차트 2] 수식 교정 완료: 정밀 연동형 직류 부하선 & 특성 곡선 패밀리 (7주차 기반)
    # ------------------------------------------------------------------
    v_mesh = np.linspace(0, V_CC + 1.0, 150)
    fig_iv = go.Figure()
    
    ib_list_uA = [10, 20, 30, 40, 50]
    for idx, ib_each in enumerate(ib_list_uA):
        curves_mA = []
        for v in v_mesh:
            ideal_ic = (ib_each * 130 / 1000) * (1 - np.exp(-v / 0.25)) + 0.038 * v
            curves_mA.append(ideal_ic)
        fig_iv.add_trace(go.Scatter(x=v_mesh, y=curves_mA, mode='lines', line=dict(color='rgba(255, 127, 14, 0.45)' if bjt_type=="NPN" else 'rgba(148, 103, 189, 0.45)', width=2), showlegend=False))
        if idx == len(ib_list_uA) - 1:
            fig_iv.add_annotation(x=V_CC+0.5, y=curves_mA[-1]+0.15, text=f"I_B = {ib_each}uA", showarrow=False, font=dict(size=10, color="gray"))

    v_load_mesh = np.linspace(0, V_CC, 100)
    i_load_mA = (-(1 / R_C) * v_load_mesh + (V_CC / R_C)) * 1000
    fig_iv.add_trace(go.Scatter(x=v_load_mesh, y=i_load_mA, mode='lines', line=dict(color='#000000', width=2.5)))
    
    # 부하선 정렬 고증이 완료된 진짜 Q점 플로팅
    fig_iv.add_trace(go.Scatter(
        x=[q_vce_point], y=[q_ic_point], mode='markers',
        marker=dict(color='red', size=14, symbol='circle', line=dict(color='white', width=1.5)),
        name='동작점 Q'
    ))
    
    fig_iv.add_annotation(x=0.35, y=max_ic_mA-0.2, text="<b>포화점(Saturation)</b>", showarrow=True, arrowhead=1, arrowcolor="black")
    fig_iv.add_annotation(x=V_CC, y=0.25, text="<b>차단점(Cut-off)</b>", showarrow=True, arrowhead=1, arrowcolor="black")
    fig_iv.add_annotation(x=q_vce_point, y=q_ic_point+0.5, text=f"<b>Q ({q_vce_point:.2f}V, {q_ic_point:.2f}mA)</b>", showarrow=False, font=dict(color="red", size=11))
    
    fig_iv.update_layout(
        title=f"📈 <b>7주차 강의자료 동기화: BJT $I_C - V_{{CE}}$ 특성 곡선 패밀리 및 고정 정렬 동작점</b>",
        xaxis_title="컬렉터-이미터 전압 V_CE [V]", yaxis_title="컬렉터 전류 I_C [mA]",
        xaxis=dict(range=[-0.1, V_CC + 0.8], showgrid=True, gridcolor='#E5E5E5'),
        yaxis=dict(range=[-0.5, max_ic_mA + 1.5], showgrid=True, gridcolor='#E5E5E5'),
        height=320, margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor='white'
    )
    st.plotly_chart(fig_iv, use_container_width=True)

with col2:
    st.subheader("🤖 AI 반도체 엔지니어 아키텍트 분석")
    st.caption(f"시스템 타겟 파라미터 상태: {bjt_type} / {mode}")
    
    system_instruction = f"""
    당신은 전 세계 반도체 소자 물리학 및 증폭 회로 설계 부문의 최고 권위자 엔지니어 교수입니다.
    **[Strict Rule] 인삿말("안녕하세요", "반갑습니다")이나 학부생 대상조의 서론은 절대 하지 말고 본론 수치 분석부터 출력하세요.**
    
    현재 사용자가 시뮬레이터에서 설정한 조건:
    - BJT 종류: {bjt_type}형 트랜지스터
    - 인가 바이어스 조건: V_BE = {V_be}V, V_BC = {V_bc}V
    - 판정된 결과적 물리 모드: {mode}
    
    [미션]
    6주차 에너지 밴드 교안(열적 평형, 순방향 장벽 하강, 캐리어 확산/표류 메커니즘)과 7주차 바이어스 회로 교안(직류 부하선 상의 Q-point 설계 마진, 차단/포화 파형 잘림 왜곡 방지)을 기막히게 융합하여, 사용자가 질문에 대해 수치적/물리적으로 예리한 솔루션을 한국어 경어체로 다이렉트 마크다운 답변을 하십시오.
    
    사용자 자연어 질문: "{user_question}"
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
            st.error("Secrets 금고에 GEMINI_API_KEY가 올바르게 세팅되어 있지 않습니다. 스트림릿 관리자 창을 확인해 주세요.")
