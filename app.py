import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 레이아웃 설정
st.set_page_config(layout="wide")
st.title("⚡ AI 반도체 설계 직관 보조 툴 (Gemini AX)")

# 2. API 키 보안 로드 및 엔진 주입
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # 키가 없을 때 안내 메시지 (에러 방지)
    st.error("Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요.")

# 3. 좌측 사이드바: MOSFET 컨트롤러 및 질문 입력창 배치
st.sidebar.header("🎛️ MOSFET 소자 및 전압 조절")
mosfet_type = st.sidebar.radio("소자 타입 선택 (Type)", ["NMOS", "PMOS"])

V_th_default = 0.7 if mosfet_type == "NMOS" else -0.7
V_gs_default = 3.5 if mosfet_type == "NMOS" else -3.5
V_ds_default = 2.2 if mosfet_type == "NMOS" else -2.2

if mosfet_type == "NMOS":
    V_th = st.sidebar.slider("문턱 전압 (V_th)", 0.0, 2.0, V_th_default, 0.1)
    V_gs = st.sidebar.slider("게이트 전압 (V_gs)", 0.0, 5.0, V_gs_default, 0.1)
    V_ds = st.sidebar.slider("드레인 전압 (V_ds)", 0.0, 5.0, V_ds_default, 0.1)
    K_n = 0.5
else:
    V_th = st.sidebar.slider("문턱 전압 (V_th)", -2.0, 0.0, V_th_default, 0.1)
    V_gs = st.sidebar.slider("게이트 전압 (V_gs)", -5.0, 0.0, V_gs_default, 0.1)
    V_ds = st.sidebar.slider("드레인 전압 (V_ds)", -5.0, 0.0, V_ds_default, 0.1)
    K_n = 0.5

st.sidebar.markdown("---")
st.sidebar.header("💬 AI에게 질문하기")
user_question = st.sidebar.text_area(
    "궁금한 점을 입력하세요:",
    value="현재 전압 조건 상태에 대해 물리적으로 쉽게 설명해줘.",
    height=120
)

# 4. 백엔드 알고리즘: 동작 영역 판정 및 전류 계산
v_gs_abs = abs(V_gs)
v_th_abs = abs(V_th)
v_ds_abs = abs(V_ds)

if v_gs_abs < v_th_abs:
    region = "차단 영역 (Cut-off)"
    I_d = 0.0
    condition_text = f"{mosfet_type}: |V_gs| < |V_th| 상태입니다."
elif v_ds_abs < (v_gs_abs - v_th_abs):
    region = "선형 영역 (Linear / Triode)"
    I_d = K_n * (2 * (v_gs_abs - v_th_abs) * v_ds_abs - v_ds_abs**2)
    condition_text = f"{mosfet_type}: |V_gs| >= |V_th| 이고 |V_ds| < |V_gs| - |V_th| 상태입니다."
else:
    region = "포화 영역 (Saturation)"
    I_d = K_n * ((v_gs_abs - v_th_abs)**2)
    condition_text = f"{mosfet_type}: |V_gs| >= |V_th| 이고 |V_ds| >= |V_gs| - |V_th| 상태입니다."

# 5. 화면 분할
col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("📊 실시간 소자 특성 시각화")
    st.info(f"**현재 판정 상태:** {mosfet_type} {region} (I_d = {I_d:.3f} mA)")
    
    fig_channel = go.Figure()
    if mosfet_type == "NMOS":
        sub_text = "<b>P-Substrate</b>"
        diff_text = "<b>n+</b>"
        channel_color = "rgba(0, 255, 255, 0.8)" # 투명도 조절한 청록색
        channel_label = "N-Channel (Electrons)"
    else:
        sub_text = "<b>N-Substrate</b>"
        diff_text = "<b>p+</b>"
        channel_color = "rgba(255, 0, 255, 0.8)" # 투명도 조절한 자전색
        channel_label = "P-Channel (Holes)"

    # 기본 구조물 배치
    fig_channel.add_shape(type="rect", x0=0, y0=0, x1=10, y1=4, fillcolor="#D3D3D3", line=dict(color="gray")) 
    fig_channel.add_shape(type="rect", x0=0.5, y0=2.5, x1=3.0, y1=4.0, fillcolor="#FF7F50", line=dict(color="chocolate")) 
    fig_channel.add_shape(type="rect", x0=7.0, y0=2.5, x1=9.5, y1=4.0, fillcolor="#FF7F50", line=dict(color="chocolate")) 
    fig_channel.add_shape(type="rect", x0=3.0, y0=4.0, x1=7.0, y1=4.3, fillcolor="#FFD700", line=dict(color="goldenrod")) 
    fig_channel.add_shape(type="rect", x0=3.0, y0=4.3, x1=7.0, y1=4.8, fillcolor="#555555", line=dict(color="#333333")) 

    labels = [
        dict(x=1.75, y=3.25, text=diff_text, showarrow=False, font=dict(size=14, color="white")),
        dict(x=8.25, y=3.25, text=diff_text, showarrow=False, font=dict(size=14, color="white")),
        dict(x=1.75, y=4.4, text="<b>Source</b>", showarrow=False, font=dict(size=13, color="black")),
        dict(x=8.25, y=4.4, text="<b>Drain</b>", showarrow=False, font=dict(size=13, color="black")),
        dict(x=5.0, y=5.2, text=f"<b>Gate ({mosfet_type})</b>", showarrow=False, font=dict(size=13, color="black")),
        dict(x=5.0, y=4.15, text="Gate - Insulator", showarrow=False, font=dict(size=10, color="black")),
        dict(x=5.0, y=1.2, text=sub_text, showarrow=False, font=dict(size=14, color="black")),
    ]
    for lbl in labels: fig_channel.add_annotation(lbl)
        
    y_max = 4.0
    # ----------------------------------------------------
    # [시각적 업그레이드] 영역별 동적 채널 셰이프 최적화 (포화 영역 시인성 확보)
    # ----------------------------------------------------
    if region == "차단 영역 (Cut-off)":
        fig_channel.add_annotation(x=5.0, y=3.7, text=f"<i>No Channel Formed (|V_gs| < |V_th|)</i>", showarrow=False, font=dict(size=12, color="red"))
    
    elif region == "선형 영역 (Linear / Triode)":
        # 선형 영역: 좌우 두께가 완만하게 변하는 사다리꼴 형태
        thick_source = (v_gs_abs - v_th_abs) * 0.15 + 0.05
        thick_drain = thick_source * (1 - (v_ds_abs / (v_gs_abs - v_th_abs)))
        if thick_drain < 0.05: thick_drain = 0.05
        
        fig_channel.add_trace(go.Scatter(
            x=[3.0, 7.0, 7.0, 3.0, 3.0], 
            y=[y_max, y_max, y_max - thick_drain, y_max - thick_source, y_max], 
            fill="toself", fillcolor=channel_color, mode='lines', line=dict(width=0), showlegend=False
        ))
    else:
        # 포화 영역: 핀치오프 점까지는 좁아지다가 드레인까지 미세하게 연결된 삼각형+인접선 연출
        thick_source = (v_gs_abs - v_th_abs) * 0.15 + 0.05
        # 전압에 따라 핀치오프 위치가 이동하는 효과
        pinch_x = 7.0 - (v_ds_abs - (v_gs_abs - v_th_abs)) * 0.3
        if pinch_x < 5.0: pinch_x = 5.0
        
        # 소스부터 핀치오프 지점까지의 주 채널 영역 (삼각형 형태)
        fig_channel.add_trace(go.Scatter(
            x=[3.0, pinch_x, 3.0, 3.0], 
            y=[y_max, y_max, y_max - thick_source, y_max], 
            fill="toself", fillcolor=channel_color, mode='lines', line=dict(width=0), showlegend=False
        ))
        
        # 핀치오프 지점부터 드레인(7.0)까지 연결된 얇은 고전계 흐름선 (시인성 복구)
        fig_channel.add_trace(go.Scatter(
            x=[pinch_x, 7.0], y=[y_max - 0.02, y_max - 0.02],
            mode="lines", line=dict(color="red" if mosfet_type=="NMOS" else "purple", width=3, dash="dot"),
            showlegend=False
        ))
        
        # 핀치오프 마커 표시
        fig_channel.add_trace(go.Scatter(
            x=[pinch_x], y=[4.0], mode="markers", 
            marker=dict(color="red", size=18, symbol="circle-open", line=dict(width=2)), 
            name="Pinch-off"
        ))
        fig_channel.add_annotation(x=pinch_x, y=3.4, text="<b>Pinch-off</b>", showarrow=True, arrowhead=2, arrowcolor="red", font=dict(size=11, color="red"))

    fig_channel.update_layout(title=f"<b>🎨 {mosfet_type} 내부 물리 구조 및 채널 동적 매핑</b>", xaxis=dict(visible=False, range=[-0.5, 10.5]), yaxis=dict(visible=False, range=[-0.5, 6.0]), height=350, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    st.plotly_chart(fig_channel, use_container_width=True)

    # I-V 특성 곡선 패밀리 파트
    v_ds_mesh = np.linspace(0, 5, 100)
    i_d_curve = []
    for v_ds_each in v_ds_mesh:
        if v_gs_abs < v_th_abs: 
            i_d_curve.append(0.0)
        elif v_ds_each < (v_gs_abs - v_th_abs): 
            i_d_curve.append(K_n * (2 * (v_gs_abs - v_th_abs) * v_ds_each - v_ds_each**2))
        else: 
            i_d_curve.append(K_n * ((v_gs_abs - v_th_abs)**2))
            
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_ds_mesh, y=i_d_curve, mode='lines', name='I_D', line=dict(color='blue' if mosfet_type=="NMOS" else 'purple', width=3)))
    fig_iv.add_trace(go.Scatter(x=[v_ds_abs], y=[I_d], mode='markers', name='Q-point', marker=dict(color='red', size=14, symbol='circle')))
    fig_iv.update_layout(title=f"📈 {mosfet_type} 드레인 특성 곡선 (I_D - |V_DS|)", xaxis_title="Absolute Drain-Source Voltage |V_DS| [V]", yaxis_title="Drain Current (I_D) [mA]", xaxis=dict(range=[0, 5.5]), yaxis=dict(range=[-0.5, 5]), height=300, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    st.plotly_chart(fig_iv, use_container_width=True)

with col2:
    st.subheader("🤖 AI 해설")
    st.caption(condition_text)
    
    system_instruction = f"""
    당신은 세계 최고 수준의 AI 반도체 및 회로 설계 엔지니어 교수입니다.
    **[주의] "안녕하세요", "반갑습니다", "학부생 수준" 등과 같은 지루한 자기소개나 인사말은 싹 다 생략하고 다이렉트로 답변하십시오.**
    사용자가 입력한 질문에 대해, 실제 회로 설계 제약 조건과 AI 반도체(NPU, PIM) 아키텍처 관점에서 깊이 있는 전문 지식을 제공해야 합니다.
    당신은 지금 사용자가 선택한 소자 타입({mosfet_type})의 물리적 특성을 완벽히 인지하고 해설해야 합니다.
    
    현재 사용자가 설정한 {mosfet_type} 조건:
    - 문턱 전압(V_th) = {V_th}V
    - 게이트 전압(V_gs) = {V_gs}V
    - 드레인 전압(V_ds) = {V_ds}V
    - 현재 동작 영역 = {region}
    
    [핵심 임무]
    현재 전압 조건 데이터와 사용자가 입력한 아래의 자연어 질문을 바탕으로,
    **서론 없이 가장 핵심적인 수치적/물리적 솔루션부터 제시한 뒤**,
    그것이 AI 반도체 설계에서 어떤 의미를 가지는지 '한국어 경어체'로 전문적으로 설명해 주세요.
    
    사용자 자연어 질문: "{user_question}"
    """
    
    if st.button("🚀 Gemini에게 커스텀 인사이트 질문하기"):
        with st.spinner("Gemini 엔지니어가 질문을 연산 중입니다..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(system_instruction)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")