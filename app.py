import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="BJT 시뮬레이터")

st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width:260px; max-width:260px; }
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p { margin-bottom:0.2rem !important; }
    [data-testid="stSidebar"] hr { margin:6px 0 !important; }
    [data-testid="stSidebar"] .stSlider { margin-top:-15px !important; margin-bottom:-5px !important; }
    [data-testid="stSidebar"] .stNumberInput div[data-baseweb="input"],
    [data-testid="stSidebar"] .stNumberInput div[data-baseweb="base-input"] { background-color:#fff !important; }
    [data-testid="stSidebar"] .stNumberInput input {
        height:26px !important; padding:1px 4px !important;
        font-size:0.75rem !important; color:#2c3e50 !important; background:#fff !important; }
    [data-testid="stSidebar"] .stTextArea textarea {
        font-size:0.78rem !important; padding:5px !important; color:#2c3e50 !important; }
    div[data-testid="stRadio"] > div { flex-direction:row !important; gap:4px !important; }
    .block-container { padding-top:0.8rem !important; padding-bottom:1rem !important; }
    .card { background:#fff; border-radius:12px; padding:16px;
            border:1px solid #eaeaea; box-shadow:0 2px 8px rgba(0,0,0,0.05); }
    .stat-label { font-size:0.68rem; color:#95a5a6; font-weight:600; }
    .stat-value { font-size:1.05rem; font-weight:700; color:#2c3e50; }
    .sec-title { font-size:0.72rem; font-weight:700; color:#64748b;
                 text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; }
</style>
""", unsafe_allow_html=True)

if "GEMINI_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── 사이드바 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔌 BJT 시뮬레이터")
    bjt_type = st.radio("타입", ["NPN","PNP"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<span style='font-size:0.8rem;font-weight:700;color:#1e293b;'>접합 전압 인가</span>", unsafe_allow_html=True)

    if "v_be_val" not in st.session_state: st.session_state.v_be_val = 0.75
    if "v_bc_val" not in st.session_state: st.session_state.v_bc_val = -2.0

    def update_be_slider(): st.session_state.v_be_val = st.session_state.be_num
    def update_be_num():    st.session_state.be_num   = st.session_state.v_be_val
    def update_bc_slider(): st.session_state.v_bc_val = st.session_state.bc_num
    def update_bc_num():    st.session_state.bc_num   = st.session_state.v_bc_val

    label_be = "V_BE (V)" if bjt_type=="NPN" else "V_EB (V)"
    st.markdown(f"<span style='font-size:0.75rem;font-weight:700;color:#2c3e50;'>{label_be}</span>", unsafe_allow_html=True)
    V_be = st.slider(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                     key="v_be_val", on_change=update_be_num, label_visibility="collapsed")
    st.number_input(label_be, min_value=-1.0, max_value=1.0, step=0.05,
                    key="be_num", on_change=update_be_slider,
                    value=st.session_state.v_be_val, label_visibility="collapsed")

    label_bc = "V_BC (V)" if bjt_type=="NPN" else "V_CB (V)"
    st.markdown(f"<span style='font-size:0.75rem;font-weight:700;color:#2c3e50;'>{label_bc}</span>", unsafe_allow_html=True)
    V_bc = st.slider(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                     key="v_bc_val", on_change=update_bc_num, label_visibility="collapsed")
    st.number_input(label_bc, min_value=-5.0, max_value=5.0, step=0.1,
                    key="bc_num", on_change=update_bc_slider,
                    value=st.session_state.v_bc_val, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<span style='font-size:0.8rem;font-weight:700;color:#1e293b;'>💬 AI 질문</span>", unsafe_allow_html=True)
    user_question = st.text_area("질문", height=80, label_visibility="collapsed",
                                 value="현재 바이어스 상태가 증폭기로서 왜 적합한지 밴드 다이어그램 관점에서 설명해줘.")
    ai_btn = st.button("🚀 Gemini 분석 요청", use_container_width=True)

# ── 파라미터 계산 ─────────────────────────────────────────────────────
V_CC=5.0; R_C=800.0; beta=150; V_AF=100.0; early_k=1.0/V_AF
be_fwd = V_be > 0
bc_fwd = V_bc > 0

if   be_fwd and not bc_fwd: mode="순방향 활성 영역"; mode_en="Forward Active"; mode_color="#f39c12"; anim_key="forward_active"
elif be_fwd and     bc_fwd: mode="포화 영역";        mode_en="Saturation";     mode_color="#28a745"; anim_key="saturation"
elif not be_fwd and bc_fwd: mode="역방향 활성 영역"; mode_en="Reverse Active"; mode_color="#9b59b6"; anim_key="reverse_active"
else:                       mode="차단 영역";        mode_en="Cutoff";         mode_color="#dc3545"; anim_key="cutoff"

R_B_eff=30000.0
I_B_A = max(0.0, V_be/R_B_eff) if be_fwd else 0.0
if mode_en=="Forward Active":
    q_ic_A=max(0.0,min(beta*I_B_A,(V_CC-0.2)/R_C)); q_vce=max(0.2,V_CC-q_ic_A*R_C)
elif mode_en=="Saturation":
    q_vce=0.2; q_ic_A=(V_CC-q_vce)/R_C
else:
    q_vce=V_CC; q_ic_A=0.0
q_ic_mA = q_ic_A*1000

desc_map = {
    "forward_active": "B-E 순방향 + B-C 역방향 → 전자 확산 후 표류 → 증폭기 동작",
    "saturation":     "양쪽 접합 순방향 → 캐리어 범람 → 닫힌 스위치 (V_CE ≈ 0.2V)",
    "reverse_active": "B-E 역방향 + B-C 순방향 → C→E 방향 역전 흐름",
    "cutoff":         "양쪽 접합 역방향 → 전위장벽↑ → 캐리어 이동 없음 → 개방 스위치",
}

# ── SVG 소자 구조도 ───────────────────────────────────────────────────
if bjt_type=="NPN":
    ef,es,el="#1a3a5c","#3a7abf","N⁺"; bf,bs,bl,bt="#4a1a3a","#bf3a8a","P","#f9c"
    cf,cs,cl="#1a3a1a","#3abf3a","N"; vl1,vl2=f"V_BE={V_be:.2f}V",f"V_BC={V_bc:.2f}V"
else:
    ef,es,el="#5c1a1a","#bf3a3a","P⁺"; bf,bs,bl,bt="#1a3a2a","#3abf6a","N","#9fc"
    cf,cs,cl="#3a2a1a","#bf8a3a","P"; vl1,vl2=f"V_EB={V_be:.2f}V",f"V_CB={V_bc:.2f}V"

# BE/BC 접합 순방향/역방향 표기
be_label = "순방향 ▶" if be_fwd else "◀ 역방향"
bc_label = "순방향 ▶" if bc_fwd else "◀ 역방향"
be_svg_color = "#e74c3c" if be_fwd else "#3498db"
bc_svg_color = "#e74c3c" if bc_fwd else "#3498db"
be_ax1, be_ax2 = (160, 183) if be_fwd else (183, 160)
bc_ax1, bc_ax2 = (257, 280) if bc_fwd else (280, 257)

bjt_svg = f"""<svg width="560" height="135" style="display:block;max-width:100%;background:white;border-radius:8px;">
  <defs>
    <marker id="ar2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#555" stroke-width="1.5"/></marker>
  </defs>

  <!-- ── 소자 블록: 에너지밴드와 동일한 배경색 ── -->
  <rect x="80"  y="18" width="110" height="44" rx="3"
        fill="rgba(173,216,230,0.6)" stroke="#3a7abf" stroke-width="1.5"/>
  <text x="135" y="37" text-anchor="middle" fill="#1a3a5c" font-size="13" font-family="monospace" font-weight="bold">{el}</text>
  <text x="135" y="53" text-anchor="middle" fill="#1565C0" font-size="9"  font-family="monospace">Emitter</text>

  <rect x="190" y="18" width="70"  height="44" rx="0"
        fill="rgba(255,182,193,0.6)" stroke="#bf3a8a" stroke-width="1.5"/>
  <text x="225" y="37" text-anchor="middle" fill="#7B1818" font-size="13" font-family="monospace" font-weight="bold">{bl}</text>
  <text x="225" y="53" text-anchor="middle" fill="#B71C1C" font-size="9"  font-family="monospace">Base</text>

  <rect x="260" y="18" width="110" height="44" rx="3"
        fill="rgba(144,238,144,0.6)" stroke="#3abf3a" stroke-width="1.5"/>
  <text x="315" y="37" text-anchor="middle" fill="#1B5E20" font-size="13" font-family="monospace" font-weight="bold">{cl}</text>
  <text x="315" y="53" text-anchor="middle" fill="#1B5E20" font-size="9"  font-family="monospace">Collector</text>

  <!-- ── 단자 배선 ── -->
  <line x1="30"  y1="40" x2="78"  y2="40" stroke="#555" stroke-width="1.5" marker-end="url(#ar2)"/>
  <text x="22"   y="44" text-anchor="middle" fill="#333" font-size="12" font-family="monospace" font-weight="bold">E</text>
  <line x1="372" y1="40" x2="400" y2="40" stroke="#555" stroke-width="1.5"/>
  <text x="410"  y="44" text-anchor="middle" fill="#333" font-size="12" font-family="monospace" font-weight="bold">C</text>
  <line x1="225" y1="62" x2="225" y2="80"  stroke="#555" stroke-width="1.5"/>
  <text x="225"  y="93" text-anchor="middle" fill="#333" font-size="12" font-family="monospace" font-weight="bold">B</text>

  <!-- ── V_BE 배터리 회로 ──
    NPN: 순방향(V_BE>0) → E(-) B(+) / 역방향(V_BE<0) → E(+) B(-)
    PNP: 순방향(V_EB>0=V_BE<0) → E(+) B(-) / 역방향 → E(-) B(+)
    즉 E쪽 + : NPN역방향 or PNP순방향 → be_fwd XOR (bjt=='NPN')
  -->
  <line x1="30"  y1="40"  x2="30"  y2="110" stroke="#555" stroke-width="1.2"/>
  <line x1="30"  y1="110" x2="118" y2="110" stroke="#555" stroke-width="1.2"/>
  <line x1="120" y1="104" x2="120" y2="116" stroke="#1565C0" stroke-width="2.5"/>
  <line x1="127" y1="107" x2="127" y2="113" stroke="#1565C0" stroke-width="1.5"/>
  <line x1="134" y1="104" x2="134" y2="116" stroke="#1565C0" stroke-width="2.5"/>
  <line x1="141" y1="107" x2="141" y2="113" stroke="#1565C0" stroke-width="1.5"/>
  <line x1="141" y1="110" x2="225" y2="110" stroke="#555" stroke-width="1.2"/>
  <line x1="225" y1="110" x2="225" y2="82"  stroke="#555" stroke-width="1.2"/>
  <!-- E쪽 극성: NPN순방향=E(-), NPN역방향=E(+), PNP순방향=E(+), PNP역방향=E(-) -->
  <text x="112" y="108" text-anchor="middle" fill="#1565C0" font-size="13" font-weight="bold">{"+" if (bjt_type=="NPN" and not be_fwd) or (bjt_type=="PNP" and be_fwd) else "−"}</text>
  <text x="149" y="108" text-anchor="middle" fill="#1565C0" font-size="13" font-weight="bold">{"−" if (bjt_type=="NPN" and not be_fwd) or (bjt_type=="PNP" and be_fwd) else "+"}</text>
  <text x="140" y="128" text-anchor="middle" fill="#1565C0" font-size="9" font-family="monospace" font-weight="bold">{vl1} ({'순방향' if be_fwd else '역방향'})</text>

  <!-- ── V_BC 배터리 회로 ──
    NPN: 역방향(V_BC<0) → C(-) B(+) / 순방향(V_BC>0) → C(+) B(-)
    PNP: 역방향(V_CB>0=V_BC<0) → C(+) B(-) / 순방향 → C(-) B(+)
    C쪽 + : NPN순방향 or PNP역방향
  -->
  <line x1="400" y1="40"  x2="400" y2="110" stroke="#555" stroke-width="1.2"/>
  <line x1="400" y1="110" x2="332" y2="110" stroke="#555" stroke-width="1.2"/>
  <line x1="330" y1="104" x2="330" y2="116" stroke="#C62828" stroke-width="2.5"/>
  <line x1="323" y1="107" x2="323" y2="113" stroke="#C62828" stroke-width="1.5"/>
  <line x1="316" y1="104" x2="316" y2="116" stroke="#C62828" stroke-width="2.5"/>
  <line x1="309" y1="107" x2="309" y2="113" stroke="#C62828" stroke-width="1.5"/>
  <line x1="309" y1="110" x2="225" y2="110" stroke="#555" stroke-width="1.2"/>
  <!-- C쪽 극성: NPN순방향=C(+), NPN역방향=C(-), PNP순방향=C(-), PNP역방향=C(+) -->
  <text x="338" y="108" text-anchor="middle" fill="#C62828" font-size="13" font-weight="bold">{"+" if (bjt_type=="NPN" and bc_fwd) or (bjt_type=="PNP" and not bc_fwd) else "−"}</text>
  <text x="301" y="108" text-anchor="middle" fill="#C62828" font-size="13" font-weight="bold">{"−" if (bjt_type=="NPN" and bc_fwd) or (bjt_type=="PNP" and not bc_fwd) else "+"}</text>
  <text x="312" y="128" text-anchor="middle" fill="#C62828" font-size="9" font-family="monospace" font-weight="bold">{vl2} ({'순방향' if bc_fwd else '역방향'})</text>

  <!-- BJT 타입 -->
  <text x="490" y="32" fill="#555" font-size="11" font-family="monospace" font-weight="bold">{bjt_type}</text>
  <text x="490" y="46" fill="#888" font-size="9"  font-family="monospace">BJT</text>

  <!-- 현재 모드 배너 -->
  <rect x="80" y="68" width="290" height="15" rx="3" fill="{mode_color}" opacity="0.15"/>
  <text x="225" y="78" text-anchor="middle" fill="{mode_color}"
        font-size="9" font-family="monospace" font-weight="bold">{mode} ({mode_en})</text>
</svg>"""

# ════════════════════════════════════════════════════════════════════
#  LAYOUT
#  Row 1: [동작영역 카드 (45%)] [캐리어 애니메이션 (55%)]
#  Row 2: [에너지밴드 다이어그램 (50%)] [I-V 특성 곡선 (50%)]
#  Row 3: [AI 해설 전체 너비]
# ════════════════════════════════════════════════════════════════════

# ── Row 1: 동작영역 + 캐리어 애니메이션 ──────────────────────────────
row1_left, row1_right = st.columns([0.42, 0.58])

with row1_left:
    st.markdown("<div class='sec-title'>📌 동작 영역</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='card'>
      <div style='font-size:0.68rem;color:#94a3b8;font-weight:700;text-transform:uppercase;margin-bottom:4px;'>Operating Region</div>
      <div style='font-size:1.4rem;font-weight:800;color:{mode_color};margin-bottom:12px;'>
        {mode}<br><span style='font-size:0.88rem;font-weight:500;'>({mode_en})</span>
      </div>
      <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
        <div><div class='stat-label'>인가전압 V_CE</div><div class='stat-value'>{abs(V_be-V_bc):.2f} V</div></div>
        <div><div class='stat-label'>컬렉터전류 I_C</div><div class='stat-value'>{q_ic_mA:.2f} mA</div></div>
        <div><div class='stat-label'>베이스전류 I_B</div><div class='stat-value'>{I_B_A*1e6:.1f} μA</div></div>
        <div><div class='stat-label'>Q점 V_CEQ</div><div class='stat-value'>{q_vce:.2f} V</div></div>
      </div>
      <div style='margin-top:12px;padding:10px;background:#f8fafc;border-radius:8px;
                  border-left:3px solid {mode_color};font-size:0.8rem;color:{mode_color};
                  font-weight:600;line-height:1.5;'>
        {desc_map[anim_key]}
      </div>
    </div>
    """, unsafe_allow_html=True)

with row1_right:
    st.markdown("<div class='sec-title'>⚡ 캐리어 이동 애니메이션</div>", unsafe_allow_html=True)
    canvas_html = f"""
<div style="display:flex;flex-direction:column;gap:8px;">
  {bjt_svg}
  <canvas id="bjtCvs" width="560" height="120"
    style="background:#ffffff;border-radius:8px;display:block;width:100%;border:1px solid #eaeaea;
           box-shadow:0 2px 8px rgba(0,0,0,0.05);"></canvas>
  <div style="font-size:0.75rem;color:#aaa;font-family:sans-serif;">
    <span style="color:#00E6FF;font-weight:700;">● 전자 (Electron)</span>&nbsp;&nbsp;
    <span style="color:#FF7043;font-weight:700;">● 정공 (Hole)</span>
  </div>
</div>
<script>
(function(){{
  const c=document.getElementById('bjtCvs');
  if(!c)return;
  if(c._aid)cancelAnimationFrame(c._aid);
  const ctx=c.getContext('2d');
  const W=c.width,H=c.height;
  const MODE='{anim_key}',BJT='{bjt_type}';
  const XBE=Math.round(W*0.33),XBC=Math.round(W*0.67),YM=H/2;

  // ── 물리적 초기 배치 ──────────────────────────────────────────────
  // NPN:
  //   전자(e⁻) → 이미터(N+) 영역 + 컬렉터(N) 영역에 다수 존재
  //   정공(h⁺) → 베이스(P) 영역에만 존재
  // PNP:
  //   정공(h⁺) → 이미터(P+) 영역 + 컬렉터(P) 영역에 다수 존재
  //   전자(e⁻) → 베이스(N) 영역에만 존재
  //
  // 각 파티클: {{x, y, r, t('e'|'h'), zone('E'|'B'|'C'), recomb, recombT}}

  function randY() {{ return YM - 35 + Math.random()*70; }}

  let pts = [];

  if(BJT === 'NPN') {{
    // 이미터 전자 20개
    for(let i=0;i<20;i++) pts.push({{x:Math.random()*(XBE-10)+5, y:randY(), r:4.2, t:'e', zone:'E', recomb:false, recombT:0}});
    // 컬렉터 전자 16개
    for(let i=0;i<16;i++) pts.push({{x:Math.random()*(W-XBC-10)+XBC+5, y:randY(), r:4.2, t:'e', zone:'C', recomb:false, recombT:0}});
    // 베이스 정공 12개
    for(let i=0;i<12;i++) pts.push({{x:Math.random()*(XBC-XBE-10)+XBE+5, y:randY(), r:4.0, t:'h', zone:'B', recomb:false, recombT:0}});
  }} else {{
    // PNP: 이미터 정공, 컬렉터 정공, 베이스 전자
    for(let i=0;i<20;i++) pts.push({{x:Math.random()*(XBE-10)+5, y:randY(), r:4.0, t:'h', zone:'E', recomb:false, recombT:0}});
    for(let i=0;i<16;i++) pts.push({{x:Math.random()*(W-XBC-10)+XBC+5, y:randY(), r:4.0, t:'h', zone:'C', recomb:false, recombT:0}});
    for(let i=0;i<12;i++) pts.push({{x:Math.random()*(XBC-XBE-10)+XBE+5, y:randY(), r:4.2, t:'e', zone:'B', recomb:false, recombT:0}});
  }}

  // ── 재결합 이벤트 타이머 ──────────────────────────────────────────
  let recombEvents = [];  // {{x, y, t(남은 프레임)}}

  function frame(){{
    ctx.clearRect(0,0,W,H);

    // 배경
    ctx.fillStyle='rgba(173,216,230,0.35)';  ctx.fillRect(0,0,XBE,H);
    ctx.fillStyle='rgba(255,182,193,0.35)';   ctx.fillRect(XBE,0,XBC-XBE,H);
    ctx.fillStyle='rgba(144,238,144,0.35)';   ctx.fillRect(XBC,0,W-XBC,H);

    // 경계선
    [XBE,XBC].forEach(x=>{{
      ctx.strokeStyle='rgba(100,100,100,0.4)';ctx.lineWidth=1;
      ctx.setLineDash([4,4]);
      ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();
      ctx.setLineDash([]);
    }});

    // 영역 라벨
    ctx.font='bold 10px monospace';
    ctx.fillStyle='#1565C0'; ctx.fillText(BJT==='NPN'?'Emitter(N+)':'Emitter(P+)',6,15);
    ctx.fillStyle='#B71C1C'; ctx.fillText(BJT==='NPN'?'Base(P)':'Base(N)',XBE+8,15);
    ctx.fillStyle='#1B5E20'; ctx.fillText(BJT==='NPN'?'Collector(N)':'Collector(P)',XBC+6,15);

    // 재결합 플래시 렌더링
    recombEvents = recombEvents.filter(ev => ev.t > 0);
    recombEvents.forEach(ev => {{
      const alpha = ev.t / 25;
      const r = (25 - ev.t) * 0.6 + 4;
      ctx.beginPath();
      ctx.arc(ev.x, ev.y, r, 0, Math.PI*2);
      ctx.strokeStyle = `rgba(255,220,50,${{alpha}})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      ev.t--;
    }});

    // ── 파티클 업데이트 ────────────────────────────────────────────
    pts.forEach(p => {{
      // 주 캐리어 색 (NPN: 전자=파랑, 정공=빨강 / PNP 동일)
      const col = p.t==='e' ? '#00E6FF' : '#FF7043';
      ctx.shadowBlur=4; ctx.shadowColor=col; ctx.fillStyle=col;
      ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill();
      ctx.shadowBlur=0;

      let vx=0, vy=0;

      if(MODE==='cutoff') {{
        // 차단: 완전 정지 (열진동만)
        vx=(Math.random()-0.5)*0.5;
        vy=(Math.random()-0.5)*0.5;

      }} else if(MODE==='forward_active') {{
        // ── NPN 순방향 활성 ──────────────────────────────────────
        // 전자: 이미터에서 베이스 통과 후 컬렉터로 (왼→오)
        // 정공: 베이스 안에서만 브라운 운동 (일부 재결합)
        if(BJT==='NPN') {{
          if(p.t==='e') {{
            vx = 3.5;  // 이미터→컬렉터 방향
            vy = (Math.random()-0.5)*0.8;
            if(p.x > W) {{ p.x=5; p.zone='E'; }}  // 리셋: 이미터로 돌아감
          }} else {{
            // NPN 베이스 정공: 베이스→이미터 방향으로 역확산
            // (교안 그림 2-7: 정공이 이미터 방향으로 확산되며 일부 재결합)
            vx = -1.5 + (Math.random()-0.5)*1.5;
            vy = (Math.random()-0.5)*2.0;
            // 이미터 영역으로 넘어가면 재결합 플래시 후 베이스로 리셋
            if(p.x < XBE - 8) {{
              recombEvents.push({{x:p.x, y:p.y, t:22}});
              p.x = Math.random()*(XBC-XBE-10)+XBE+5;
              p.y = randY();
            }}
            // BC 경계는 못 넘음
            if(p.x > XBC-4) p.x = XBC-4;
            // 베이스 통과 중인 전자와 재결합
            if(Math.random() < 0.004) {{
              recombEvents.push({{x:p.x, y:p.y, t:25}});
              p.x = Math.random()*(XBC-XBE-10)+XBE+5;
              p.y = randY();
            }}
          }}
        // ── PNP 순방향 활성 ──────────────────────────────────────
        }} else {{
          if(p.t==='h') {{
            vx = 3.5;
            vy = (Math.random()-0.5)*0.8;
            if(p.x > W) {{ p.x=5; p.zone='E'; }}
          }} else {{
            // PNP 베이스 전자: 베이스→이미터 방향으로 역확산
            vx = -1.5 + (Math.random()-0.5)*1.5;
            vy = (Math.random()-0.5)*2.0;
            if(p.x < XBE - 8) {{
              recombEvents.push({{x:p.x, y:p.y, t:22}});
              p.x = Math.random()*(XBC-XBE-10)+XBE+5;
              p.y = randY();
            }}
            if(p.x > XBC-4) p.x = XBC-4;
            if(Math.random() < 0.004) {{
              recombEvents.push({{x:p.x, y:p.y, t:25}});
              p.x = Math.random()*(XBC-XBE-10)+XBE+5;
              p.y = randY();
            }}
          }}
        }}

      }} else if(MODE==='saturation') {{
        // ── 포화: 양쪽 접합 모두 순방향 ──────────────────────────
        // 주 캐리어가 양방향으로 범람 (방향성 약함, 확산 지배)
        // NPN: 전자 양방향, 정공은 베이스에서 양방향 넘침
        // PNP: 정공 양방향, 전자는 베이스에서 양방향 넘침
        const mainType = BJT==='NPN' ? 'e' : 'h';
        if(p.t===mainType) {{
          // 주 캐리어: 넓은 확산 (방향 랜덤)
          vx = (Math.random()-0.5)*4.0;
          vy = (Math.random()-0.5)*2.0;
        }} else {{
          // 소수 캐리어: 베이스 바깥으로도 약하게 넘침
          vx = (Math.random()-0.5)*2.5;
          vy = (Math.random()-0.5)*1.5;
        }}
        // 경계: 전체 너비 내에서 반사
        if(p.x>W-4) p.x=W-4;
        if(p.x<4)   p.x=4;

      }} else if(MODE==='reverse_active') {{
        // ── 역방향 활성: 순방향 활성의 반대 ─────────────────────
        // NPN: 전자가 컬렉터→이미터 방향 (오→왼)
        // PNP: 정공이 컬렉터→이미터 방향 (오→왼)
        const mainType = BJT==='NPN' ? 'e' : 'h';
        if(p.t===mainType) {{
          vx = -3.5;
          vy = (Math.random()-0.5)*0.8;
          if(p.x < 0) {{ p.x=W-5; }}
        }} else {{
          vx = (Math.random()-0.5)*1.2;
          vy = (Math.random()-0.5)*1.2;
          if(p.x < XBE+4) p.x = XBE+4;
          if(p.x > XBC-4) p.x = XBC-4;
        }}
      }}

      p.x += vx;
      p.y += vy;
      p.y = Math.max(22, Math.min(H-14, p.y));
    }});

    c._aid=requestAnimationFrame(frame);
  }}
  frame();
}})();
</script>
"""
    components.html(canvas_html, height=360)

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ── Row 2: 에너지 밴드 + I-V 곡선 ────────────────────────────────────
row2_left, row2_right = st.columns([0.50, 0.50])

with row2_left:
    st.markdown("<div class='sec-title'>🔋 에너지 밴드 다이어그램</div>", unsafe_allow_html=True)

    E_g=1.12; x_all=np.linspace(0,8.0,400); ec_all=np.zeros_like(x_all)
    v_be_eff=float(np.clip(V_be,-5.0,0.75)); v_bc_eff=float(np.clip(V_bc,-5.0,0.75))
    if bjt_type=="NPN":
        E_F_Base=0.0; E_V_Base=-0.1; E_C_Base=E_V_Base+E_g
        E_F_Emitter=E_F_Base+v_be_eff; E_F_Collector=E_F_Base+v_bc_eff
        E_C_Emitter=E_F_Emitter-0.05;  E_C_Collector=E_F_Collector-0.15
    else:
        E_F_Base=0.0; E_C_Base=0.1; E_V_Base=E_C_Base-E_g
        E_F_Emitter=E_F_Base-v_be_eff; E_F_Collector=E_F_Base-v_bc_eff
        E_V_Emitter=E_F_Emitter+0.05;  E_V_Collector=E_F_Collector+0.15
        E_C_Emitter=E_V_Emitter+E_g;   E_C_Collector=E_V_Collector+E_g

    for i,x in enumerate(x_all):
        if   x<=2.4: ec_all[i]=E_C_Emitter
        elif x>=5.6: ec_all[i]=E_C_Collector
        elif 3.2<=x<=4.8: ec_all[i]=E_C_Base
        elif 2.4<x<3.2:
            t=(x-2.4)/0.8*np.pi; ec_all[i]=E_C_Emitter+(E_C_Base-E_C_Emitter)*(1-np.cos(t))/2
        else:
            t=(x-4.8)/0.8*np.pi; ec_all[i]=E_C_Base+(E_C_Collector-E_C_Base)*(1-np.cos(t))/2
    ev_all=ec_all-E_g

    fig_band=go.Figure()
    fig_band.add_vrect(x0=0,  x1=2.8,fillcolor="rgba(173,216,230,0.25)",line_width=0)
    fig_band.add_vrect(x0=2.8,x1=5.2,fillcolor="rgba(255,182,193,0.25)",line_width=0)
    fig_band.add_vrect(x0=5.2,x1=8.0,fillcolor="rgba(144,238,144,0.25)",line_width=0)
    fig_band.add_trace(go.Scatter(x=x_all,y=ec_all,mode='lines',line=dict(color='black',width=2.5),name='E_c'))
    fig_band.add_trace(go.Scatter(x=x_all,y=ev_all,mode='lines',line=dict(color='black',width=2.5),name='E_v'))
    fig_band.add_trace(go.Scatter(x=[0,2.4],  y=[E_F_Emitter,E_F_Emitter],  mode='lines',line=dict(color='blue',width=2,dash='dash'),name='E_F(E)'))
    fig_band.add_trace(go.Scatter(x=[3.2,4.8],y=[E_F_Base,E_F_Base],        mode='lines',line=dict(color='blue',width=2,dash='dash'),name='E_F(B)'))
    fig_band.add_trace(go.Scatter(x=[5.6,8.0],y=[E_F_Collector,E_F_Collector],mode='lines',line=dict(color='blue',width=2,dash='dash'),name='E_F(C)'))
    fig_band.add_annotation(x=8.15,y=ec_all[-1]+0.05,text="<b>E_C</b>",showarrow=False,font=dict(size=12))
    fig_band.add_annotation(x=8.15,y=ev_all[-1]-0.05,text="<b>E_V</b>",showarrow=False,font=dict(size=12))
    e_lbl="EMITTER (N⁺)" if bjt_type=="NPN" else "EMITTER (P⁺)"
    b_lbl="BASE (P)"      if bjt_type=="NPN" else "BASE (N)"
    c_lbl="COLLECTOR (N)" if bjt_type=="NPN" else "COLLECTOR (P)"
    fig_band.add_annotation(x=1.4,y=max(ec_all)+0.55,text=f"<b>{e_lbl}</b>",showarrow=False,font=dict(size=10,color='#1565C0'))
    fig_band.add_annotation(x=4.0,y=max(ec_all)+0.55,text=f"<b>{b_lbl}</b>",showarrow=False,font=dict(size=10,color='#B71C1C'))
    fig_band.add_annotation(x=6.6,y=max(ec_all)+0.55,text=f"<b>{c_lbl}</b>",showarrow=False,font=dict(size=10,color='#1B5E20'))
    np.random.seed(42)
    if bjt_type=="NPN":
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2,2.2,16),y=E_C_Emitter+np.random.uniform(0.02,0.15,16),mode='markers',marker=dict(color='#1565C0',size=9,line=dict(color='#0D47A1',width=1.5)),name='전자(e⁻)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.4,4.6,10),y=E_V_Base-np.random.uniform(0.02,0.15,10),mode='markers',marker=dict(color='#C62828',size=10,line=dict(color='#7B1818',width=1.5)),name='정공(h⁺)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(5.8,7.8,12),y=E_C_Collector+np.random.uniform(0.02,0.15,12),mode='markers',marker=dict(color='#1565C0',size=9,line=dict(color='#0D47A1',width=1.5)),showlegend=False))
    else:
        fig_band.add_trace(go.Scatter(x=np.random.uniform(0.2,2.2,16),y=E_V_Emitter-np.random.uniform(0.02,0.15,16),mode='markers',marker=dict(color='#C62828',size=10,line=dict(color='#7B1818',width=1.5)),name='정공(h⁺)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(3.4,4.6,10),y=E_C_Base+np.random.uniform(0.02,0.15,10),mode='markers',marker=dict(color='#1565C0',size=9,line=dict(color='#0D47A1',width=1.5)),name='전자(e⁻)'))
        fig_band.add_trace(go.Scatter(x=np.random.uniform(5.8,7.8,12),y=E_V_Collector-np.random.uniform(0.02,0.15,12),mode='markers',marker=dict(color='#C62828',size=10,line=dict(color='#7B1818',width=1.5)),showlegend=False))
    fig_band.add_vline(x=2.8,line=dict(color='gray',width=1,dash='dot'))
    fig_band.add_vline(x=5.2,line=dict(color='gray',width=1,dash='dot'))
    fig_band.update_layout(
        xaxis=dict(visible=False,range=[-0.2,8.6]),
        yaxis=dict(visible=False,range=[min(ev_all)-0.4,max(ec_all)+0.9]),
        height=340,margin=dict(l=5,r=5,t=5,b=5),
        showlegend=True,
        legend=dict(x=0.01,y=0.02,bgcolor='rgba(255,255,255,0.85)',
                    bordercolor='lightgray',borderwidth=1,font=dict(size=9),orientation='h'),
        plot_bgcolor='white')
    st.plotly_chart(fig_band, use_container_width=True)

with row2_right:
    st.markdown("<div class='sec-title'>📈 I_C – V_CE 특성 곡선 & 직류 부하선</div>", unsafe_allow_html=True)

    fig_iv=go.Figure()
    sign=1 if bjt_type=="NPN" else -1
    v_arr=np.linspace(0,V_CC+0.8,300)
    bc=(255,127,14) if bjt_type=="NPN" else (148,103,189)
    for idx,ib_uA in enumerate([10,20,30,40,50]):
        ic_sat=beta*(ib_uA*1e-6)*1000
        col=f"rgba({bc[0]},{bc[1]},{bc[2]},{0.38+0.13*idx:.2f})"
        ic_c=[max(0.0,ic_sat*np.tanh(v/0.12)*(1+early_k*v)) for v in v_arr]
        fig_iv.add_trace(go.Scatter(x=[sign*v for v in v_arr],y=[sign*ic for ic in ic_c],
                                    mode='lines',line=dict(color=col,width=2.2),showlegend=False))
        fig_iv.add_annotation(x=sign*(V_CC+0.85),y=sign*ic_sat*(1+early_k*(V_CC+0.8)),
                               text=f"I_B={ib_uA}μA",showarrow=False,font=dict(size=9,color='gray'),
                               xanchor='left' if bjt_type=="NPN" else 'right')
    sat_ic=(V_CC/R_C)*1000
    fig_iv.add_trace(go.Scatter(x=[0,sign*V_CC],y=[sign*sat_ic,0],
                                 mode='lines',line=dict(color='black',width=2.8),name='직류 부하선'))
    fig_iv.add_vline(x=sign*0.2,line=dict(color='purple',width=1.2,dash='dot'))
    fig_iv.add_annotation(x=sign*0.22,y=sign*sat_ic*0.55,text="V_CE,sat",
                           showarrow=False,font=dict(size=9,color='purple'),textangle=-90)
    q_x,q_y=sign*q_vce,sign*q_ic_mA
    fig_iv.add_trace(go.Scatter(x=[q_x],y=[q_y],mode='markers',
                                 marker=dict(color='red',size=13,symbol='circle',line=dict(color='white',width=2)),
                                 name=f"Q점"))
    fig_iv.add_annotation(x=q_x,y=q_y+sign*0.4,
                           text=f"<b>Q ({q_x:.2f}V, {q_y:.2f}mA)</b>",
                           showarrow=False,font=dict(color='red',size=11))
    fig_iv.add_shape(type='line',x0=q_x,x1=q_x,y0=0,y1=q_y,line=dict(color='red',width=1,dash='dash'))
    fig_iv.add_shape(type='line',x0=0,x1=q_x,y0=q_y,y1=q_y,line=dict(color='red',width=1,dash='dash'))
    fig_iv.add_annotation(x=sign*0.15,y=sign*(sat_ic+0.3),text="<b>포화점</b>",
                           showarrow=True,ax=sign*0.7,ay=sign*(sat_ic-0.5),arrowhead=2,font=dict(size=10))
    fig_iv.add_annotation(x=sign*(V_CC-0.15),y=sign*0.35,text="<b>차단점</b>",
                           showarrow=True,ax=sign*(V_CC-0.9),ay=sign*0.9,arrowhead=2,font=dict(size=10))
    xr=[-0.1,V_CC+1.3] if bjt_type=="NPN" else [-(V_CC+1.3),0.1]
    yr=[-0.3,sat_ic+1.4] if bjt_type=="NPN" else [-(sat_ic+1.4),0.3]
    fig_iv.update_layout(
        xaxis_title="V_CE [V]",yaxis_title="I_C [mA]",
        xaxis=dict(range=xr,showgrid=True,gridcolor='#EEEEEE',zeroline=True,zerolinecolor='black',zerolinewidth=1.5),
        yaxis=dict(range=yr,showgrid=True,gridcolor='#EEEEEE',zeroline=True,zerolinecolor='black',zerolinewidth=1.5),
        height=340,margin=dict(l=10,r=10,t=5,b=40),showlegend=True,
        legend=dict(x=0.55 if bjt_type=="NPN" else 0.01,y=0.98 if bjt_type=="NPN" else 0.15,
                    bgcolor='rgba(255,255,255,0.88)',bordercolor='#ddd',borderwidth=1,font=dict(size=10)),
        plot_bgcolor='white')
    st.plotly_chart(fig_iv, use_container_width=True)

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ── Row 3: AI 해설 전체 너비 ─────────────────────────────────────────
st.markdown("<div class='sec-title'>🤖 AI 상세 해설</div>", unsafe_allow_html=True)
if ai_btn and "GEMINI_API_KEY" in st.secrets:
    with st.spinner("분석 중..."):
        try:
            prompt = f"""반도체 소자 물리학 전문가. 인삿말 없이 바로 분석 시작.
BJT={bjt_type}, V_BE={V_be:.2f}V, V_BC={V_bc:.2f}V, 모드={mode}({mode_en})
I_B={I_B_A*1e6:.2f}μA, I_C={q_ic_mA:.2f}mA, V_CEQ={q_vce:.2f}V
6주차 에너지밴드 교안(열적평형, 순방향 장벽 하강, 캐리어 확산/표류)과
7주차 바이어스 교안(직류 부하선, Q점 설계, 왜곡 방지)을 연결하여
한국어 마크다운으로 상세 답변하세요.
질문: "{user_question}"
"""
            resp = genai.GenerativeModel('gemini-2.5-flash').generate_content(prompt)
            st.markdown(f"""
            <div style='background:#f8f9fa;padding:20px;border-radius:12px;
                        border:1px solid #eaeaea;font-size:0.85rem;line-height:1.6;'>
              <strong>💡 AI 물리적 해설</strong><br><br>{resp.text}
            </div>""", unsafe_allow_html=True)
        except Exception as e:
            st.error(str(e))
elif ai_btn:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
else:
    st.markdown(f"""
    <div style='background:#f8f9fa;padding:20px;border-radius:12px;border:1px solid #eaeaea;
                display:flex;align-items:center;gap:16px;'>
      <div style='font-size:2rem;'>🤖</div>
      <div>
        <div style='font-size:0.85rem;font-weight:700;color:#2c3e50;margin-bottom:4px;'>AI 상세 해설 대기 중</div>
        <div style='font-size:0.8rem;color:#64748b;'>사이드바에서 질문을 입력하고 <b>Gemini 분석 요청</b> 버튼을 누르면
        현재 바이어스 상태에 대한 물리적 해설이 이 자리에 표시됩니다.</div>
      </div>
    </div>""", unsafe_allow_html=True)
