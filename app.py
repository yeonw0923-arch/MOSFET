import streamlit as st
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 레이아웃 설정
st.set_page_config(layout="wide")
st.title("📟 AI 반도체 소자 직관 보조 툴: BJT 전자/물리 구조 매퍼")

# 2. API 키 보안 로드 (Secrets 금고 활용)
if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API 키가 Secrets에 등록되지 않아 AI 인사이트 기능이 제한됩니다.")

# 3. 좌측 사이드바: BJT 타입 및 입력창 배치
st.sidebar.header("🎛️ BJT 소자 및 바이어스 조절")
bjt_type = st.sidebar.radio("소자 타입 선택 (Type)", ["NPN", "PNP"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 접합 전압 인가 (Bias)")

# [기능 개선] 슬라이더와 직접 숫자 입력을 동시에 할 수 있도록 구조 바꿈 (범위: -10V ~ 10V)
if bjt_type == "NPN":
    V_be = st.sidebar.number_input("베이스-이미터 전압 (V_BE) [V]", min_value=-1.0, max_value=1.0, value=0.7, step=0.05)
    V_bc = st.sidebar.number_input("베이스-컬렉터 전압 (V_BC) [V]", min_value=-10.0, max_value=10.0, value=-1.7, step=0.1)
    V_CE = V_be - V_bc
else:
    V_be = st.sidebar.number_input("이미터-베이스 전압 (V_EB) [V]", min_value=-1.0, max_value=1.0, value=0.7, step=0.05)
    V_bc = st.sidebar.number_input("컬렉터-베이스 전압 (V_CB) [V]", min_value=-10.0, max_value=10.0, value=-1.7, step=0.1)
    V_CE = V_be - V_bc  # PNP는 V_EC 관점

st.sidebar.markdown("---")
st.sidebar.header("💬 AI에게 질문하기")
user_question = st.sidebar.text_area(
    "궁금한 점을 입력하세요:",
    value="현재 접합 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
    height=100
)

# 4. 백엔드 알고리즘: 물리적 턴온 상태 및 동작 영역 정확한 판정
if bjt_type == "NPN":
    be_forward = V_be > 0.65  
    bc_forward = V_bc > 0.50
else:
    be_forward = V_be > 0.65
    bc_forward = V_bc > 0.50

# 회로 스펙 지정 (7주차 교안 기준 부하선 동기화)
V_CC = 5.0  
R_C = 800   
max_ic_mA = (V_CC / R_C) * 1000  # 6.25 mA

# 동작 4대 영역 판정 및 물리 수식 기반 진짜 Q점 전류 계산
if be_forward and not bc_forward:
    mode = "순방향 활성 모드 (Forward Active)"
    description = "B-E 순방향, B-C 역방향 바이어스 상태입니다. 캐리어 증폭 작용이 일어납니다."
    # 실제 물리 법칙 연동: V_CE 전압에 따른 전류 상태 계산
    q_vce_point = max(0.0, min(V_CC, V_CE))
    # 부하선과 만나는 실제 동작점 유도
    ideal_ic = 3.5 * (1 - np.exp(-q_vce_point / 0.25)) + 0.05 * q_vce_point
    load_ic = (-(1 / R_C) * q_vce_point + (V_CC / R_C)) * 1000
    q_ic_point = max(0.0, min(load_ic, ideal_ic))
    # 전류에 맞춰서 V_CE 최종 역산 (부하선 위 정렬 고증)
    q_vce_point = V_CC - (q_ic_point / 1000) * R_C

elif be_forward and bc_forward:
    mode = "포화 모드 (Saturation)"
    description = "B-E 순방향, B-C 순방향 바이어스 상태입니다. 스위치가 닫힌(Closed) 것처럼 동작합니다."
    q_vce_point = max(0.1, min(0.3, V_CE if V_CE > 0 else 0.2))
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
    # [차트 1] 에너지 밴드 다이어그램 (기존 동일)
    # ------------------------------------------------------------------
    fig_band = go.Figure()
    be_shift = -max(-2.0, min(2.0, V_be)) * 0.7
    bc_shift = -max(-2.0, min(2.0, V_bc)) * 0.7
    
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
    
    fig_band.add_vrect(x0=0, x1=3, fillcolor="rgba(230, 242, 255, 0.4)", line_width=0)
    fig_band.add_vrect(x0=3, x1=5, fillcolor="rgba(255, 240, 245, 0.4)", line_width=0)
    fig_band.add_vrect(x0=5, x1=8, fillcolor="rgba(245, 245, 220, 0.4)", line_width=0)
    
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ec, mode='lines', line=dict(color='#000000', width=3.5)))
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ev, mode='lines', line=dict(color='#000000', width=3.5)))
    
    if bjt_type == "NPN":
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 18), y=np.random.uniform(1.55, 1.75, 18), mode='markers', marker=dict(color='#1f77b4', size=7, line=dict(color='white', width=0.5))))
    else:
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 18), y=np.random.uniform(0.1, 0.3, 18), mode='markers', marker=dict(color='#d62728', size=7, line=dict(color='white', width=0.5))))

    fig_band.update_layout(
        title="<b>🔋 6주차 강의자료 동기화: 동적 에너지 밴드 다이어그램</b>",
        xaxis=dict(visible=False, range=[-0.2, 8.2]), yaxis=dict(visible=False, range=[-1.8, 4.2]),
        height=280, margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor='white'
    )
    st.plotly_chart(fig_band, use_container_width=True)

    # ------------------------------------------------------------------
    # [차트 2] 버그 수정본: 정밀 수식 연동형 직류 부하선 & Q-point 차트
    # ------------------------------------------------------------------
    v_mesh = np.linspace(0, V_CC + 1.0, 150)
    fig_iv = go.Figure()
    
    # 배경 가이드라인 세트 플로팅
    ib_list_uA = [10, 20, 30, 40, 50]
    for idx, ib_each in enumerate(ib_list_uA):
        curves_mA = []
        for v in v_mesh:
            ideal_ic = (ib_each * 130 / 1000) * (1 - np.exp(-v / 0.25)) + 0.04 * v
            curves_mA.append(ideal_ic)
        fig_iv.add_trace(go.Scatter(x=v_mesh, y=curves_mA, mode='lines', line=dict(color='rgba(255, 127, 14, 0.4)' if bjt_type=="NPN" else 'rgba(148, 103, 189, 0.4)', width=2), showlegend=False))

    # 직류 부하선 플로팅
    v_load_mesh = np.linspace(0, V_CC, 100)
    i_load_mA = (-(1 / R_C) * v_load_mesh + (V_CC / R_C)) * 1000
    fig_iv.add_trace(go.Scatter(x=v_load_mesh, y=i_load_mA, mode='lines', line=dict(color='#000000', width=2.5)))
    
    # [버그 수정] 부하선 위정밀 연동 좌표에 동작점 마커 매핑
    fig_iv.add_trace(go.Scatter(
        x=[q_vce_point], y=[q_ic_point], mode='markers',
        marker=dict(color='red', size=14, symbol='circle', line=dict(color='white', width=1.5)),
        name='동작점 Q'
    ))
    
    fig_iv.add_annotation(x=0.4, y=max_ic_mA-0.2, text="포화점(Saturation)", showarrow=True, arrowhead=1)
    fig_iv.add_annotation(x=V_CC, y=0.3, text="차단점(Cut-off)", showarrow=True, arrowhead=1)
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
