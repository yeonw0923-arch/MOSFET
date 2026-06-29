import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MplPolygon
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="MOSFET SIMULATOR", page_icon="🔌", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0px !important; margin-top: 0px !important; }
    [data-testid="stSidebar"] h3 { font-size:0.95rem !important; margin-bottom:5px !important; margin-top:5px !important; }
    [data-testid="stSidebar"] hr { margin:6px 0 !important; }
    [data-testid="stSidebar"] .stSlider { margin-top:0px !important; padding-bottom:0px !important; margin-bottom:-10px !important; }
    [data-testid="stSidebar"] .stSelectbox { margin-top:-4px !important; margin-bottom:-4px !important; }
    [data-testid="stSidebar"] .stTextArea { margin-top:4px !important; margin-bottom:-4px !important; }
    [data-testid="stSidebar"] .stTextArea textarea { font-size:0.78rem !important; }
    .stat-card { background:#ffffff; border-radius:12px; padding:16px; border:1px solid #eaeaea; box-shadow:0px 4px 10px rgba(0,0,0,0.02); height:100%; }
    .stat-title { font-size:0.75rem; color:#64748b; font-weight:600; text-transform:uppercase; margin-bottom:4px; }
    .stat-label { font-size:0.7rem; color:#94a3b8; font-weight:600; margin-bottom:2px; }
    .stat-value { font-size:1.15rem; font-weight:700; color:#1e293b; }
    .section-header { font-size:1.25rem; font-weight:800; color:#334155; margin-top:0px; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
    .block-container { padding-top:2.5rem !important; padding-bottom:1rem !important; }
</style>
""", unsafe_allow_html=True)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GEMINI_URL = (f"https://generativelanguage.googleapis.com/v1beta/models/"
              f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")

def call_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        return f"❌ HTTP 오류: {e.response.status_code} {e.response.text}"
    except Exception as e:
        return f"❌ API 통신 오류: {e}"

for key, default in [("vth_val", 1.0), ("vgs_val", 2.6), ("vds_val", 3.7)]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    if st.button("⬅ 홈으로 돌아가기", use_container_width=True):
        st.switch_page("app.py")
    st.markdown("### 🎛️ 제어 및 입력 패널")
    device = st.selectbox("소자 타입 선택", ["NMOS", "PMOS"])
    st.sidebar.divider()
    st.markdown("<span style='font-size:0.75rem;font-weight:700;color:#2c3e50;'>문턱 전압 |V_TH| (V)</span>", unsafe_allow_html=True)
    st.sidebar.write("")
    vth = st.slider("V_TH", 0.0, 2.0, value=float(st.session_state["vth_val"]), step=0.1, key="vth_slide", label_visibility="collapsed")
    st.session_state["vth_val"] = vth
    st.markdown("<span style='font-size:0.75rem;font-weight:700;color:#2c3e50;'>게이트 전압 V_GS (V)</span>", unsafe_allow_html=True)
    st.sidebar.write("")
    vgs = st.slider("V_GS", 0.0, 5.0, value=float(st.session_state["vgs_val"]), step=0.1, key="vgs_slide", label_visibility="collapsed")
    st.session_state["vgs_val"] = vgs
    st.markdown("<span style='font-size:0.75rem;font-weight:700;color:#2c3e50;'>드레인 전압 V_DS (V)</span>", unsafe_allow_html=True)
    st.sidebar.write("")
    vds = st.slider("V_DS", 0.0, 5.0, value=float(st.session_state["vds_val"]), step=0.1, key="vds_slide", label_visibility="collapsed")
    st.session_state["vds_val"] = vds
    st.sidebar.divider()
    st.markdown("<span style='font-size:0.8rem;font-weight:700;color:#1e293b;'>🤖 ASK AI</span>", unsafe_allow_html=True)
    user_question = st.text_area("", height=80, placeholder="e.g. 현재 전압 조건 상태에 대해 물리적으로 쉽게 설명해줘.", label_visibility="collapsed")
    ask_btn = st.button("🤖 AI 실시간 해설 보기", use_container_width=True, type="primary")

def calc_mosfet(device, vgs, vds, vth, Kn=1.0, Kp=1.0):
    if device == "NMOS":
        vgs_eff = vgs - vth
        vds_sat = max(vgs_eff, 0.0)
        if vgs_eff <= 0:
            region = "Cutoff";  id_mA = 0.0
        elif vds < vgs_eff:
            region = "Linear";  id_mA = round(Kn * (vgs_eff * vds - 0.5 * vds**2), 2)
        else:
            region = "Saturation"; id_mA = round(0.5 * Kn * vgs_eff**2, 2)
    else:
        vgs_real = -vgs; vds_real = -vds; vth_real = -vth
        vgs_eff  = vth_real - vgs_real
        vds_sat  = max(vgs_eff, 0.0)
        if vgs_real >= vth_real:
            region = "Cutoff";  id_mA = 0.0
        elif abs(vds_real) < vgs_eff:
            region = "Linear";  id_mA = round(Kp * (vgs_eff * abs(vds_real) - 0.5 * abs(vds_real)**2), 2)
        else:
            region = "Saturation"; id_mA = round(0.5 * Kp * vgs_eff**2, 2)
    return region, id_mA, vds_sat

region, id_mA, vds_sat = calc_mosfet(device, vgs, vds, vth)
region_kr   = {"Cutoff":"차단 영역","Linear":"선형 영역","Saturation":"포화 영역"}.get(region, region)
region_color= "#22c55e" if region=="Saturation" else "#f59e0b" if region=="Linear" else "#ef4444"
region_desc = {
    "Cutoff":     "V_GS < V_TH → 반전 채널 미형성 → 전류 차단 (OFF 스위치)",
    "Linear":     "V_DS < V_GS − V_TH → 채널이 저항처럼 동작 (트라이오드)",
    "Saturation": "V_DS ≥ V_GS − V_TH → 드레인 핀치오프 → 정전류원처럼 동작",
}.get(region, "")

st.markdown(f"""
<h1 style='text-align:left;font-size:2.2rem;font-weight:900;color:#1e293b;
           margin-top:0;padding-bottom:12px;border-bottom:1px solid #e2e8f0;margin-bottom:24px;'>
    🔌 {device} MOSFET SIMULATOR
</h1>""", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([0.28, 0.46, 0.26], gap="medium")

with col_left:
    st.markdown("<div class='section-header'>📊 소자 상태</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='stat-card' style='margin-bottom:24px;'>
        <div class='stat-title'>Operating Region</div>
        <div style='font-size:1.6rem;font-weight:800;color:{region_color};line-height:1.2;margin-bottom:4px;'>{region_kr}</div>
        <div style='font-size:0.9rem;color:{region_color};margin-bottom:18px;font-weight:600;'>({region})</div>
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px;'>
            <div><div class='stat-label'>인가전압 |V_DS|</div><div class='stat-value'>{vds:.2f} V</div></div>
            <div><div class='stat-label'>드레인전류 |I_D|</div><div class='stat-value'>{id_mA:.2f} mA</div></div>
            <div><div class='stat-label'>게이트전압 |V_GS|</div><div class='stat-value'>{vgs:.2f} V</div></div>
            <div><div class='stat-label'>포화전압 V_DSAT</div><div class='stat-value'>{vds_sat:.2f} V</div></div>
        </div>
        <div style='margin-top:20px;padding:12px 14px;background:#f8fafc;
                    border-left:4px solid {region_color};border-radius:6px;
                    font-size:0.78rem;font-weight:700;color:#334155;line-height:1.45;'>
            <span style='color:{region_color}'>{region_desc}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📐 MOSFET 구조</div>", unsafe_allow_html=True)
    fig_struct, ax = plt.subplots(figsize=(5, 4.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.5); ax.axis("off")
    fig_struct.patch.set_facecolor('white')
    sub_color  = "#c8dff0" if device=="NMOS" else "#fce4d6"
    sub_edge   = "#5a8abf" if device=="NMOS" else "#e67e22"
    sub_text   = "p-Substrate" if device=="NMOS" else "n-Substrate"
    sub_tc     = "#2c5f8a" if device=="NMOS" else "#a04000"
    well_text  = "n+" if device=="NMOS" else "p+"
    well_color = "#4caf7d" if device=="NMOS" else "#9b59b6"
    well_edge  = "#2e7d52" if device=="NMOS" else "#8e44ad"
    carrier_color = "#e65100" if device=="NMOS" else "#8e44ad"
    ch_color   = "#66bb6a" if device=="NMOS" else "#d2b4de"
    ch_edge    = "#388e3c" if device=="NMOS" else "#af7ac5"
    ax.add_patch(patches.FancyBboxPatch((0.3,0.3),9.4,4.8,boxstyle="round,pad=0.1",fc=sub_color,ec=sub_edge,lw=1.5))
    ax.text(5,1.0,sub_text,ha="center",va="center",fontsize=10,color=sub_tc,fontstyle='italic')
    for (x0,label) in [(0.5,"S"),(7.2,"D")]:
        ax.add_patch(patches.FancyBboxPatch((x0,3.0),2.3,2.1,boxstyle="round,pad=0.05",fc=well_color,ec=well_edge,lw=1.5))
        cx=x0+1.15
        ax.text(cx,4.1,label,ha="center",va="center",fontsize=18,fontweight="bold",color="white")
        ax.text(cx,3.35,well_text,ha="center",va="center",fontsize=10,color="#ffffff")
    ax.add_patch(patches.Rectangle((2.8,5.1),4.4,0.4,fc="#e8e8e8",ec="#aaa",lw=1.0))
    ax.text(7.35,5.3,"SiO2",ha="left",va="center",fontsize=8,color="#9400D3")
    ax.add_patch(patches.FancyBboxPatch((2.8,5.5),4.4,0.75,boxstyle="round,pad=0.05",fc="#37474f",ec="#1a1a2e",lw=1.5))
    ax.text(5,5.88,"Gate (G)",ha="center",va="center",fontsize=10,fontweight="bold",color="white")
    GATE_X_START,GATE_X_END=2.8,7.2; GATE_LEN=GATE_X_END-GATE_X_START
    SIO2_BOTTOM,CH_THICK=5.1,0.5
    if region=="Saturation":
        ratio=float(np.clip(vds_sat/max(abs(vds),0.01),0.15,0.85))
        po_x=(GATE_X_START+GATE_LEN*ratio if device=="NMOS" else GATE_X_END-GATE_LEN*ratio)
        if device=="NMOS":
            tri_pts=np.array([[GATE_X_START,SIO2_BOTTOM],[po_x,SIO2_BOTTOM],[GATE_X_START,SIO2_BOTTOM-CH_THICK]])
            dep_rect=patches.Rectangle((po_x,SIO2_BOTTOM-CH_THICK),GATE_X_END-po_x,CH_THICK,fc="#dce8f5",ec="#5a8abf",linestyle='--',alpha=0.6)
            arr_start,arr_end=GATE_X_START+0.2,po_x-0.15
        else:
            tri_pts=np.array([[GATE_X_END,SIO2_BOTTOM],[po_x,SIO2_BOTTOM],[GATE_X_END,SIO2_BOTTOM-CH_THICK]])
            dep_rect=patches.Rectangle((GATE_X_START,SIO2_BOTTOM-CH_THICK),po_x-GATE_X_START,CH_THICK,fc="#fbeee6",ec="#e67e22",linestyle='--',alpha=0.6)
            arr_start,arr_end=GATE_X_END-0.2,po_x+0.15
        ax.add_patch(MplPolygon(tri_pts,closed=True,fc=ch_color,ec=ch_edge,lw=1.2,alpha=0.9,zorder=4))
        ax.add_patch(dep_rect)
        ax.plot(po_x,SIO2_BOTTOM,'ro',ms=7,zorder=10)
        ax.text(po_x,SIO2_BOTTOM-0.8,"Pinch-off",ha="center",fontsize=7,color="red",fontweight="bold")
        ax.annotate("",xy=(arr_end,SIO2_BOTTOM-CH_THICK*0.4),xytext=(arr_start,SIO2_BOTTOM-CH_THICK*0.4),
                    arrowprops=dict(arrowstyle='->',color=carrier_color,lw=1.4),zorder=6)
    elif region=="Linear":
        drain_thin=CH_THICK*(1.0-0.4*(vds/(vds_sat if vds_sat>0 else 1)))
        trap_pts=np.array([[GATE_X_START,SIO2_BOTTOM],[GATE_X_END,SIO2_BOTTOM],[GATE_X_END,SIO2_BOTTOM-drain_thin],[GATE_X_START,SIO2_BOTTOM-CH_THICK]])
        ax.add_patch(MplPolygon(trap_pts,closed=True,fc=ch_color,ec=ch_edge,lw=1.2,alpha=0.85,zorder=4))
    else:
        ax.text(5,SIO2_BOTTOM-0.35,"No Channel (Cutoff)",ha="center",va="top",fontsize=8,color="#dc3545",
                bbox=dict(boxstyle='round,pad=0.3',fc='#fff0f0',ec='#dc3545',alpha=0.85))
    ax.text(5,7.8,f"Applied: V_GS={vgs:.1f}V | V_DS={vds:.1f}V",ha="center",fontsize=8,color="#444")
    st.pyplot(fig_struct)
    plt.close(fig_struct)

with col_mid:
    st.markdown("<div class='section-header'>📈 특성 곡선 & 밴드 다이어그램</div>", unsafe_allow_html=True)

    # ── I-V 특성 곡선 ──────────────────────────────────────
    v_ax = np.linspace(0, 5, 300)
    i_ax = [calc_mosfet(device, vgs, vd, vth)[1] for vd in v_ax]
    vgs_for_boundary = np.linspace(vth+0.01, 5.0, 300)
    sat_vds_pts, sat_id_pts = [], []
    for vg_ in vgs_for_boundary:
        vds_b = vg_ - vth
        id_b  = round(0.5*(vg_-vth)**2, 2)
        if 0 <= vds_b <= 5.0:
            sat_vds_pts.append(vds_b); sat_id_pts.append(id_b)
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=sat_vds_pts,y=sat_id_pts,mode='lines',line=dict(color='#e74c3c',dash='dash',width=1.8),name="Saturation Boundary (V_DS = V_GS − V_TH)"))
    fig_iv.add_trace(go.Scatter(x=list(v_ax),y=i_ax,mode='lines',line=dict(color='#1a5276',width=2.5),name=f"V_GS = {vgs:.1f} V"))
    fig_iv.add_trace(go.Scatter(x=[vds],y=[id_mA],mode='markers',marker=dict(color='#e74c3c',size=11,line=dict(color='white',width=1.5)),name="Operating Point"))
    fig_iv.update_layout(
        height=320,margin=dict(l=10,r=10,t=40,b=10),
        xaxis_title="|V_DS| (V)" if device=="PMOS" else "V_DS (V)",
        yaxis_title="I_D (mA)",
        xaxis=dict(range=[0,5]),yaxis=dict(rangemode='tozero'),
        legend=dict(yanchor="top",y=0.99,xanchor="left",x=0.01,bgcolor="rgba(255,255,255,0.85)",bordercolor="rgba(128,128,128,0.3)",borderwidth=1,font=dict(size=9)),
        plot_bgcolor='white',
        title=dict(text="I-V Characteristic Curve",font=dict(size=12,color="#64748b"),x=0.5,y=0.95,xanchor='center'))
    fig_iv.update_xaxes(showgrid=True,gridcolor='#f1f5f9')
    fig_iv.update_yaxes(showgrid=True,gridcolor='#f1f5f9')
    st.plotly_chart(fig_iv,use_container_width=True,theme="streamlit")

    # ════════════════════════════════════════════════════════
    #  에너지 밴드 다이어그램 (수정 버전)
    #
    #  핵심 수정 사항:
    #  1) E_F 위치:
    #     NMOS (p-substrate): E_F = E_v + ~0.15eV (E_v 가까이)
    #     PMOS (n-substrate): E_F = E_c - ~0.15eV (E_c 가까이)
    #
    #  2) 밴드 휨 방향:
    #     NMOS: V_DS > 0 → 드레인 쪽 전자 에너지 낮아짐 → E_c 하강 (drop < 0)
    #     PMOS: V_DS > 0 (슬라이더 절댓값) → 실제 V_DS < 0
    #           드레인 쪽 정공 에너지 낮아짐 → E_c 상승 (drop > 0)
    #
    #  3) 차단 모드: V_GS < V_TH → 게이트 전압이 낮아서
    #     채널 영역 E_c가 위로 굽어야 함 (NMOS 기준)
    #     → gate_bend: V_GS 증가할수록 채널 E_c 낮아짐
    #
    #  4) 소스-드레인 E_F 분리: qV_DS 만큼 정확히 분리
    #     ef_drn = ef_src - abs_vds (NMOS)
    #     ef_drn = ef_src + abs_vds (PMOS: 반대 방향)
    # ════════════════════════════════════════════════════════

    Eg       = 1.12
    abs_vgs  = abs(vgs)
    abs_vds  = abs(vds)
    abs_vth  = abs(vth)
    vgs_eff_plot = max(abs_vgs - abs_vth, 0.0)

    # ── 소스 기준 E_c 레벨 ────────────────────────────────
    E0 = 2.0   # 소스 영역 E_c (기준점)

    # ── E_F 위치 수정 ─────────────────────────────────────
    # NMOS: p-substrate → E_F는 E_v 가까이 (E_v + 0.12 eV)
    # PMOS: n-substrate → E_F는 E_c 가까이 (E_c - 0.12 eV)
    if device == "NMOS":
        ef_src_val = (E0 - Eg) + 0.12   # E_v + 0.12
    else:
        ef_src_val = E0 - 0.12           # E_c - 0.12

    # ── V_DS에 의한 드레인 쪽 밴드 강하량 ────────────────
    # NMOS: 드레인 전위 높아짐 → 전자 에너지 낮아짐 → E_c 하강 (음수)
    # PMOS: 실제 V_DS < 0 → 드레인 전위 낮아짐 → 정공 에너지 낮아짐 → E_c 상승 (양수)
    max_drop = 2.0   # 최대 표시 강하량 클램프
    if device == "NMOS":
        band_drop = -min(abs_vds * 0.45, max_drop)   # 음수: E_c 하강
    else:
        band_drop = +min(abs_vds * 0.45, max_drop)   # 양수: E_c 상승

    # ── 게이트 전압에 의한 채널 밴드 굽힘 ────────────────
    # NMOS: V_GS 증가 → 채널 E_c 아래로 당겨짐(반전층 형성)
    #        V_GS < V_TH → 채널 E_c 위로 굽음 (공핍층)
    #        채널 중앙에서의 추가 굽힘 = -(V_GS - V_TH) * 0.3 (NMOS)
    # PMOS: 반대 방향
    if device == "NMOS":
        gate_bend = -vgs_eff_plot * 0.3   # 반전 형성 시 아래로
        if region == "Cutoff":
            gate_bend = abs_vth * 0.25    # 차단 시 위로 굽음 (공핍)
    else:
        gate_bend = +vgs_eff_plot * 0.3
        if region == "Cutoff":
            gate_bend = -abs_vth * 0.25

    # ── x 좌표 ────────────────────────────────────────────
    x_src = np.linspace(0.0, 1.0, 50)
    x_ch  = np.linspace(1.0, 2.0, 80)
    x_drn = np.linspace(2.0, 3.0, 50)
    t_ch  = x_ch - 1.0   # 0 → 1

    # ── 채널 영역 E_c 프로파일 ───────────────────────────
    # V_DS 강하의 공간적 분포: 모드에 따라 집중 위치 다름
    #   Linear:     균일한 기울기 (n=1)
    #   Saturation: 드레인 근처에 집중 (n↑)
    #   Cutoff:     드레인 접합에 집중 (n=3)
    if region == "Linear" and vgs_eff_plot > 0:
        n_exp = 1.0
    elif region == "Saturation" and vgs_eff_plot > 0:
        ratio = float(np.clip(vds_sat / max(abs_vds, 0.01), 0.15, 0.85))
        n_exp = 1.0 + (1.0 - ratio) * 3.5
    else:
        n_exp = 3.0

    ec_src = np.full_like(x_src, E0)
    # 채널: gate_bend (게이트에 의한 균일 굽힘) + band_drop (V_DS에 의한 드레인 쪽 강하)
    ec_ch  = E0 + gate_bend * np.sin(t_ch * np.pi) + band_drop * (t_ch ** n_exp)
    ec_drn = np.full_like(x_drn, E0 + band_drop)

    ev_src = ec_src - Eg
    ev_ch  = ec_ch  - Eg
    ev_drn = ec_drn - Eg

    x_all  = np.concatenate([x_src, x_ch,  x_drn])
    ec_all = np.concatenate([ec_src, ec_ch, ec_drn])
    ev_all = np.concatenate([ev_src, ev_ch, ev_drn])

    # ── E_F 소스/드레인 분리: 정확히 qV_DS 만큼 ─────────
    # NMOS: 드레인 E_F = 소스 E_F - V_DS (전자 전기화학 퍼텐셜)
    # PMOS: 드레인 E_F = 소스 E_F + V_DS
    if device == "NMOS":
        ef_drn_val = ef_src_val - abs_vds * 0.45   # band_drop과 동일 스케일
    else:
        ef_drn_val = ef_src_val + abs_vds * 0.45

    ch_mid_ec = float(ec_ch[len(ec_ch) // 2])

    fig_band = go.Figure()

    fig_band.add_trace(go.Scatter(x=list(x_all), y=list(ec_all), mode='lines',
                                  line=dict(color='#e74c3c', width=2.5), name="E<sub>c</sub>"))
    fig_band.add_trace(go.Scatter(x=list(x_all), y=list(ev_all), mode='lines',
                                  line=dict(color='#2980b9', width=2.5), name="E<sub>v</sub>"))

    # 소스 E_F
    fig_band.add_trace(go.Scatter(x=[0.0, 1.0], y=[ef_src_val, ef_src_val], mode='lines',
                                  line=dict(color='purple', width=1.8, dash='dot'),
                                  name="E<sub>F</sub> (Source)"))
    # 드레인 E_F (V_DS > 0 이면 소스와 분리됨)
    fig_band.add_trace(go.Scatter(x=[2.0, 3.0], y=[ef_drn_val, ef_drn_val], mode='lines',
                                  line=dict(color='purple', width=1.8, dash='dot'),
                                  name="E<sub>F</sub> (Drain)", showlegend=True))

    # Eg 화살표
    fig_band.add_annotation(x=0.15, y=ec_src[0], ay=ev_src[0],
                             axref='x', ayref='y', xref='x', yref='y',
                             arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor='gray', ax=0.15)
    fig_band.add_annotation(x=0.15, y=ev_src[0], ay=ec_src[0],
                             axref='x', ayref='y', xref='x', yref='y',
                             arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor='gray', ax=0.15)
    fig_band.add_annotation(x=0.22, y=(ec_src[0]+ev_src[0])/2,
                             text=f"Eg={Eg}eV", showarrow=False,
                             font=dict(size=9, color='gray'), xanchor='left')

    # 동작 영역 레이블
    if region == "Saturation" and vgs_eff_plot > 0:
        fig_band.add_annotation(x=1.5, y=ch_mid_ec,
                                 text="Inversion Layer<br>(Saturation)", showarrow=False,
                                 font=dict(size=9, color='#27ae60'),
                                 bgcolor='#eafaf1', bordercolor='#27ae60', borderwidth=1)
        # 핀치오프 위치
        po_t = 0.85
        fig_band.add_annotation(x=1.0+po_t, y=E0+band_drop*(po_t**n_exp),
                                 text="Pinch-off", showarrow=True,
                                 arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor="#e74c3c",
                                 ax=16, ay=(-22 if device=="NMOS" else 22),
                                 font=dict(size=8, color="#e74c3c"))
    elif region == "Linear" and vgs_eff_plot > 0:
        fig_band.add_annotation(x=1.5, y=ch_mid_ec,
                                 text="Channel Formed<br>(Linear)", showarrow=False,
                                 font=dict(size=9, color='#f39c12'),
                                 bgcolor='#fef9e7', bordercolor='#f39c12', borderwidth=1)
    elif region == "Cutoff":
        fig_band.add_annotation(x=1.5, y=ch_mid_ec,
                                 text="No Channel<br>(Cutoff)", showarrow=False,
                                 font=dict(size=9, color='#ef4444'),
                                 bgcolor='#fff0f0', bordercolor='#ef4444', borderwidth=1)

    fig_band.update_layout(
        height=320, margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(tickvals=[0.5,1.5,2.5], ticktext=["Source","Channel","Drain"],
                   tickfont=dict(size=10), showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(title="Energy (eV)", title_font=dict(size=10),
                   showgrid=True, gridcolor='#f1f5f9'),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99,
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="rgba(128,128,128,0.3)", borderwidth=1, font=dict(size=9)),
        plot_bgcolor='white',
        title=dict(text=f"Energy Band Diagram ({device})",
                   font=dict(size=12, color="#64748b"), x=0.5, y=0.95, xanchor='center'))
    st.plotly_chart(fig_band, use_container_width=True, theme="streamlit")

with col_right:
    st.markdown("<div class='section-header'>🤖 AI 해설</div>", unsafe_allow_html=True)
    if "gemini_response" not in st.session_state:
        st.session_state.gemini_response = ""
    if ask_btn:
        question = (user_question.strip() if user_question.strip()
                    else f"현재 {device} MOSFET 조건에 대해 물리적으로 쉽게 설명해줘.")
        full_prompt = f"""
{device} MOSFET 조건 요약:
- V_GS = {vgs:.1f}V, V_DS = {vds:.1f}V, V_TH = {vth:.1f}V
- 현재 동작 영역: {region}
- 드레인 전류: {id_mA:.2f} mA
- 포화 전압: {vds_sat:.2f} V
사용자 질문: {question}
위의 소자 상태 데이터를 기반으로 전하 캐리어 이동 현상과 핀치오프 메커니즘을
전공자 관점에서 비유를 섞어 아주 쉽고 흥미롭게 한국어로 해설해줘. 4문장 내외로 마무리해줘.
"""
        with st.spinner("Gemini analyzing..."):
            st.session_state.gemini_response = call_gemini(full_prompt)
    if st.session_state.gemini_response:
        st.markdown(f"""
        <div style='background:#ffffff;padding:16px;border-radius:10px;
                    border:1px solid #e2e8f0;font-size:0.85rem;color:#1e293b;
                    line-height:1.6;white-space:pre-wrap;min-height:140px;
                    box-shadow:0px 4px 6px rgba(0,0,0,0.02);'>{st.session_state.gemini_response}</div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:#f0f9ff;padding:16px;border-radius:10px;
                    border:1px solid #bae6fd;font-size:0.88rem;font-weight:600;
                    color:#0369a1;display:flex;align-items:flex-start;gap:8px;'>
            <span>👉</span>
            <span>왼쪽 패널에서 설정을 마치고 [AI 실시간 해설 보기] 버튼을 눌러보세요.</span>
        </div>""", unsafe_allow_html=True)
