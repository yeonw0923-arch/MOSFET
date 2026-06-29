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

# 3. 좌측 사이드바: BJT 타입 및 전압 제어 배치
st.sidebar.header("🎛️ BJT 소자 및 바이어스 조절")
bjt_type = st.sidebar.radio("소자 타입 선택 (Type)", ["NPN", "PNP"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 접합 전압 인가 (Bias)")

# NPN/PNP에 따른 전압 기본 가이드 및 슬라이더 동적 배치
if bjt_type == "NPN":
    V_be = st.sidebar.slider("베이스-이미터 전압 (V_BE) [V]", -1.0, 1.5, 0.7, 0.05)
    V_bc = st.sidebar.slider("베이스-컬렉터 전압 (V_BC) [V]", -3.0, 1.5, -2.0, 0.1)
else:
    # PNP는 직관성을 위해 부호 가이드를 주거나 반대로 제어
    V_be = st.sidebar.slider("이미터-베이스 전압 (V_EB) [V]", -1.5, 1.0, 0.7, 0.05)
    V_bc = st.sidebar.slider("컬렉터-베이스 전압 (V_CB) [V]", -1.5, 3.0, -2.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.header("💬 AI에게 질문하기")
user_question = st.sidebar.text_area(
    "궁금한 점을 입력하세요:",
    value="현재 접합 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.",
    height=100
)

# 4. 백엔드 알고리즘: 6주차/7주차 교안 기준 동작 모드 판정 및 전류 수식 계산
# NPN/PNP 부호 조건 판정 파트
if bjt_type == "NPN":
    be_forward = V_be > 0.6  # 턴온 전압 대략 0.6~0.7V 기준
    bc_forward = V_bc > 0.4
    V_CE = V_be - V_bc
else:
    be_forward = V_be > 0.6
    bc_forward = V_bc > 0.4
    V_CE = V_be - V_bc  # PNP에서는 V_EC 관점

# 동작 모드 4가지 판정 (교안 6페이지 표 2-2 / 16페이지 표 참조)
if be_forward and not bc_forward:
    mode = "순방향 활성 모드 (Forward Active)"
    description = "B-E 순방향, B-C 역방향 바이어스 상태입니다. 캐리어 증폭 작용이 일어납니다."
    # 임시 수식 모델링 (Q점 시각화용)
    I_B = max(0.0, (V_be - 0.6) / 10) # mA 단위 간이 모델
    beta = 100
    I_C = beta * I_B
elif be_forward and bc_forward:
    mode = "포화 모드 (Saturation)"
    description = "B-E 순방향, B-C 순방향 바이어스 상태입니다. 스위치가 닫힌(Closed) 것처럼 동작합니다."
    I_C = max(0.1, 4.0 * (V_be / 0.7)) # 컬렉터 전류 포화 제한
elif not be_forward and not bc_forward:
    mode = "차단 모드 (Cut-off)"
    description = "B-E 역방향, B-C 역방향 바이어스 상태입니다. 전류가 흐르지 않는 개방 스위치 상태입니다."
    I_C = 0.0
else:
    mode = "역방향 활성 모드 (Reverse Active)"
    description = "B-E 역방향, B-C 순방향 바이어스 상태입니다. 소자 효율이 극도로 낮아 거의 사용되지 않습니다."
    I_C = 0.05

# 5. 화면 분할 (시각화 파트와 AI 분석 파트)
col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("📊 실시간 BJT 물리 상태 시각화")
    st.info(f"**판정 모드:** {bjt_type} {mode}  \n**설명:** {description}")
    
    # ------------------------------------------------------------------
    # [차트 1] 동적 에너지 밴드 다이어그램 및 캐리어 애니메이션 연출 (6주차 교안 기반)
    # ------------------------------------------------------------------
    fig_band = go.Figure()
    
    # 전압에 따른 밴드 벤딩(변화량) 계산 기하학적 매핑
    # E = -qV 준위 매핑 기법 적용
    be_shift = -V_be * 0.8
    bc_shift = -V_bc * 0.8
    
    # 영역별 X축 좌표 지정 (이미터: 0~3, 베이스: 3~5, 컬렉터: 5~8)
    x_e = np.linspace(0, 3, 30)
    x_b = np.linspace(3, 5, 20)
    x_c = np.linspace(5, 8, 30)
    
    # 전도대(Ec) 기본 형태 빌드
    y_e = np.zeros_like(x_e) + 1.5
    
    # 베이스 영역: BE 전압이 낮을수록 장벽이 높게 유지됨
    y_b_start = 1.5 + (0.8 if bjt_type == "NPN" else -0.8) + be_shift
    y_b = np.linspace(1.5, y_b_start, len(x_b))
    
    # 컬렉터 영역: BC 전압(역방향)에 의해 장벽이 깎이거나 올라감
    y_c_start = y_b_start - (0.8 if bjt_type == "NPN" else -0.8) - bc_shift
    y_c = np.zeros_like(x_c) + y_c_start
    
    # 전체 밴드 데이터 병합
    x_total = np.concatenate([x_e, x_b, x_c])
    y_ec = np.concatenate([y_e, y_b, y_c])
    y_ev = y_ec - 1.0  # 밴드갭 고정 격차 표시
    
    # 전도대(Ec) 및 가전자대(Ev) 플로팅
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ec, mode='lines', line=dict(color='black', width=3), name='E_c'))
    fig_band.add_trace(go.Scatter(x=x_total, y=y_ev, mode='lines', line=dict(color='black', width=3), name='E_v'))
    
    # 캐리어(전자/정공) 이동 애니메이션 입자 효과 연출 (Scatter Markers 사용)
    if bjt_type == "NPN":
        # 다수 캐리어: 전자 (전도대 위를 이동)
        # 이미터 영역 고정 전자들
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 15), y=np.random.uniform(1.55, 1.7, 15), mode='markers', marker=dict(color='#1f77b4', size=8), name='전자 (e-)'))
        
        # 모드별 베이스/컬렉터 장벽 탈출 및 흐름 애니메이션 점 연출
        if mode == "순방향 활성 모드 (Forward Active)":
            # 이미터에서 베이스를 거쳐 컬렉터 미끄럼틀로 넘어가는 캐리어 흐름 연출
            fig_band.add_trace(go.Scatter(x=[3.2, 3.8, 4.5, 5.2, 6.0, 7.0], y=[1.8, 2.0, 1.9, 1.2, 0.8, 0.8], mode='markers+lines', line=dict(dash='dot', color='red'), marker=dict(color='#1f77b4', size=9, symbol='arrow-bar-up')))
            fig_band.add_annotation(x=4.0, y=2.2, text="🥇 확산 (Diffusion)", showarrow=False, font=dict(color="blue"))
            fig_band.add_annotation(x=6.2, y=1.4, text="⚡ 표류 (Drift 빨려 들어감)", showarrow=False, font=dict(color="red"))
        elif mode == "포화 모드 (Saturation)":
            # 양쪽 접합이 다 낮아져 베이스 영역에 전자가 바글바글 축적되는 현상 고증
            fig_band.add_trace(go.Scatter(x=np.random.uniform(3.2, 4.8, 10), y=np.random.uniform(y_b_start+0.05, y_b_start+0.2, 10), mode='markers', marker=dict(color='#1f77b4', size=8)))
            fig_band.add_annotation(x=4.0, y=y_b_start+0.4, text="⚠️ 베이스 캐리어 축적 (Saturation)", showarrow=False, font=dict(color="orange"))
    else:
        # PNP 다수 캐리어: 정공 (가전자대 Ev 아래에서 거꾸로 움직임)
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2, 2.8, 15), y=np.random.uniform(0.3, 0.45, 15), mode='markers', marker=dict(color='#e377c2', size=8), name='정공 (h+)'))
        if mode == "순방향 활성 모드 (Forward Active)":
            fig_band.add_trace(go.Scatter(x=[3.2, 4.0, 5.2, 6.5], y=[0.2, 0.0, 0.5, 0.6], mode='markers', marker=dict(color='#e377c2', size=9)))
            fig_band.add_annotation(x=4.0, y=-0.3, text="정공 확산 및 표류", showarrow=False, font=dict(color="purple"))

    # 구역 구분선 및 라벨 배치
    fig_band.add_vline(x=3.0, line_dash="dash", line_color="gray")
    fig_band.add_vline(x=5.0, line_dash="dash", line_color="gray")
    fig_band.update_layout(
        title="<b>🔋 6주차 고증: 전전압 연동형 BJT 에너지 밴드 & 캐리어 다이내믹스</b>",
        xaxis=dict(visible=False, range=[-0.5, 8.5]),
        yaxis=dict(visible=False, range=[-2.0, 4.0]),
        height=330, margin=dict(l=10, r=10, t=40, b=10), showlegend=False
    )
    st.plotly_chart(fig_band, use_container_width=True)

    # ------------------------------------------------------------------
    # [차트 2] 직류 부하선(Load Line) 및 Q-point 특성 플롯 (7주차 교안 3p 기준)
    # ------------------------------------------------------------------
    st.markdown(" ")
    V_CC = 6.0  # 교안 시뮬레이션 베이스 전압 기준 가상의 6V 세팅
    R_C = 1000  # 1k옴 부하저항 가산
    
    v_ce_mesh = np.linspace(0, V_CC, 100)
    # 직류 부하선 공식: I_C = -1/R_C * V_CE + V_CC/R_C
    i_c_load_line = -(1/R_C) * v_ce_mesh + (V_CC/R_C)
    i_c_load_line_mA = i_c_load_line * 1000  # mA 변환
    
    fig_iv = go.Figure()
    # 1. 직류 부하선 그리기
    fig_iv.add_trace(go.Scatter(x=v_ce_mesh, y=i_c_load_line_mA, mode='lines', name='직류 부하선', line=dict(color='black', width=2, dash='dash')))
    
    # 2. 소자 특성 곡선 패밀리 맵 생성
    for ib_val in [0.01, 0.02, 0.03, 0.04, 0.05]:
        # 간이 선형-포화 거동 구현
        i_c_curve = [min(-(1/R_C)*v + (V_CC/R_C), ib_val * 100 * (1 - np.exp(-v/0.3))) * 1000 for v in v_ce_mesh]
        fig_iv.add_trace(go.Scatter(x=v_ce_mesh, y=i_c_curve, mode='lines', line=dict(color='rgba(31, 119, 180, 0.3)', width=1.5), showlegend=False))
        
    # 3. 실시간 동작점(Q-point) 찍기
    q_vce = max(0.2, min(V_CC, V_CE + 2.5)) # 전압 입력 연동 모델링 파싱
    q_ic = max(0.0, min(V_CC/R_C*1000, I_C if mode=="순방향 활성 모드 (Forward Active)" else (V_CC-q_vce)/R_C*1000))
    
    fig_iv.add_trace(go.Scatter(x=[q_vce], y=[q_ic], mode='markers', name='동작점 (Q)', marker=dict(color='red', size=14, symbol='circle')))
    
    # 7주차 교안 극점 주석 매핑 (포화점, 차단점 표시)
    fig_iv.add_annotation(x=0.2, y=V_CC/R_C*1000, text="<b>포화점 (Saturation)</b>", showarrow=True, arrowhead=1, arrowcolor="orange")
    fig_iv.add_annotation(x=V_CC, y=0.1, text="<b>차단점 (Cut-off)</b>", showarrow=True, arrowhead=1, arrowcolor="blue")
    fig_iv.add_annotation(x=q_vce, y=q_ic+0.4, text=f"<b>동작점 Q</b><br>({q_vce:.2f}V, {q_ic:.2f}mA)", showarrow=False, font=dict(color="red"))
    
    fig_iv.update_layout(
        title=f"📈 <b>7주차 고증: BJT 직류 부하선 & 동작점(Q) 분석 맵</b>",
        xaxis_title="컬렉터-이미터 전압 V_CE [V]",
        yaxis_title="컬렉터 전류 I_C [mA]",
        xaxis=dict(range=[0, V_CC + 0.5]), yaxis=dict(range=[-0.5, (V_CC/R_C*1000)+1.0]),
        height=320, margin=dict(l=10, r=10, t=40, b=10), showlegend=False
    )
    st.plotly_chart(fig_iv, use_container_width=True)

with col2:
    st.subheader("🤖 AI 반도체 엔지니어 아키텍트 분석")
    st.caption(f"시스템 타겟 파라미터 상태: {bjt_type} / {mode}")
    
    # 6주차, 7주차 교안 통합형 하이엔드 프롬프트 빌드 아키텍처
    system_instruction = f"""
    당신은 전 세계 반도체 소자 물리학 및 증폭 회로 설계 부문의 최고 권위자 엔지니어 교수입니다.
    **[Stict Rule] 인삿말("안녕하세요", "반갑습니다")이나 학부생 대상조의 서론은 절대 하지 말고 본론 수치 분석부터 출력하세요.**
    
    현재 사용자가 시뮬레이터에서 설정한 조건:
    - BJT 종류: {bjt_type}형 트랜지스터
    - 인가 바이어스 조건: V_BE = {V_be}V, V_BC = {V_bc}V
    - 판정된 결과적 물리 모드: {mode}
    
    [미션]
    6주차 에너지 밴드 교안(열적 평형, 순방향 장벽 하강, 캐리어 확산/표류 메커니즘)과 7주차 바이어스 회로 교안(직류 부하선 상의 Q-point 설계 마진, 차단/포화 파형 잘림 왜곡 방지)을 기막히게 융합하여, 사용자의 질문에 대해 수치적/물리적으로 예리한 솔루션을 한국어 경어체로 다이렉트 마크다운 답변을 하십시오.
    
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
