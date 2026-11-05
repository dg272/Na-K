import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Na/K & 수분 밸런스 계산기",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ 체내 Na/K 밸런스 & 수분 트래커")
st.caption("식약처 API 기반 영양 밸런스 계산과 맞춤형 음식 추천을 제공하는 헬스케어 리포트")

# 세션 상태(Session State) 초기화
if "daily_meals" not in st.session_state:
    st.session_state.daily_meals = []

if "water_intake" not in st.session_state:
    st.session_state.water_intake = 0  # 단위: ml

# 백업용 내장 데이터베이스
DEFAULT_FOOD_DB = {
    "김치찌개": {"na": 1960.0, "k": 320.0},
    "라면": {"na": 1790.0, "k": 180.0},
    "자장면": {"na": 1500.0, "k": 260.0},
    "바나나": {"na": 1.0, "k": 358.0},
    "시금치나물": {"na": 120.0, "k": 460.0},
    "찐감자": {"na": 5.0, "k": 420.0},
    "닭가슴살 샐러드": {"na": 220.0, "k": 380.0},
    "우유 (200ml)": {"na": 100.0, "k": 300.0},
    "아보카도": {"na": 7.0, "k": 485.0},
    "찐고구마": {"na": 10.0, "k": 540.0},
    "토마토": {"na": 5.0, "k": 230.0}
}

# 2. 식약처 API 연동 함수 (03 최신 버전)
def fetch_food_data_api(food_name, api_key):
    """식품의약품안전처 식품영양성분 DB API 호출"""
    url = "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo03/getFoodNtrCpntDbInq03"
    params = {
        "serviceKey": api_key,
        "FOOD_NM_KR": food_name,
        "type": "json",
        "numOfRows": 10
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("body", {}).get("items", [])
            
            if isinstance(items, dict):
                items = [items]
                
            results = []
            for item in items:
                na_val = float(item.get("AMT_NUM1") or item.get("NUTR_CONT2") or 0)
                k_val = float(item.get("AMT_NUM7") or item.get("NUTR_CONT8") or 0)
                food_nm = item.get("FOOD_NM_KR") or item.get("DESC_KOR") or "이름 없음"
                
                results.append({
                    "name": food_nm,
                    "na": na_val,
                    "k": k_val
                })
            return results
    except Exception as e:
        st.error(f"API 호출 중 오류 발생: {e}")
    return []

# 3. 사이드바: API 키 및 개인 신체 정보 설정
st.sidebar.header("⚙️ 개인 설정 & API")

api_key = ""
if "OPEN_API_KEY" in st.secrets:
    api_key = st.secrets["OPEN_API_KEY"]
else:
    api_key = st.sidebar.text_input("식약처 API Key (선택)", type="password", help="공공데이터포털 일반 인증키를 입력하세요.")

st.sidebar.divider()
st.sidebar.subheader("💧 체수분 설정")
weight = st.sidebar.number_input("현재 체중 (kg)", min_value=30, max_value=150, value=65, step=1)
recommended_water = int(weight * 33)
st.sidebar.info(f"💡 **{weight}kg** 기준 하루 권장 수분 섭취량: **{recommended_water} ml**")

st.divider()

# 4. 일일 수분 섭취 트래커 섹션
st.subheader("💧 일일 수분 섭취 트래커")

current_water = st.session_state.water_intake
water_ratio = min(current_water / recommended_water, 1.0) if recommended_water > 0 else 0.0
st.progress(water_ratio)
st.write(f"현재 섭취량: **{current_water} ml** / 권장량: **{recommended_water} ml** ({int(water_ratio * 100)}% 달성)")

w_col1, w_col2, w_col3 = st.columns([1.5, 1, 1])

with w_col1:
    custom_water = st.number_input("직접 용량 입력 (ml)", min_value=10, max_value=2000, value=150, step=50, label_visibility="collapsed")
    if st.button(f"+ {custom_water}ml 추가", use_container_width=True):
        st.session_state.water_intake += custom_water
        st.rerun()

with w_col2:
    if st.button("+ 200ml (한 컵)", use_container_width=True):
        st.session_state.water_intake += 200
        st.rerun()

with w_col3:
    if st.button("+ 500ml (텀블러)", use_container_width=True):
        st.session_state.water_intake += 500
        st.rerun()

st.divider()

# 5. 음식 검색 및 추가 섹션
st.subheader("🍴 오늘 먹은 음식 검색 & 추가")

col_search, col_servings = st.columns([3, 1])

with col_search:
    search_keyword = st.text_input("음식 이름 검색 (예: 김치찌개, 비빔밥, 신라면)", value="")

with col_servings:
    servings = st.number_input("인분 / 개수", min_value=0.1, max_value=10.0, value=1.0, step=0.5)

selected_food_name = ""
selected_na = 0.0
selected_k = 0.0

if search_keyword.strip():
    if api_key.strip():
        with st.spinner("식약처 DB에서 검색 중..."):
            api_results = fetch_food_data_api(search_keyword, api_key)
            
        if api_results:
            options = [f"{item['name']} (Na: {item['na']}mg, K: {item['k']}mg)" for item in api_results]
            selected_option = st.selectbox("검색된 API 결과 중 선택하세요:", options)
            idx = options.index(selected_option)
            selected_food_name = api_results[idx]['name']
            selected_na = api_results[idx]['na']
            selected_k = api_results[idx]['k']
        else:
            st.warning("API 검색 결과가 없습니다. 내장 DB에서 찾습니다.")
    
    if not selected_food_name:
        matched_db = {k: v for k, v in DEFAULT_FOOD_DB.items() if search_keyword.lower() in k.lower()}
        if matched_db:
            selected_food_name = st.selectbox("내장 DB 결과에서 선택하세요:", list(matched_db.keys()))
            selected_na = matched_db[selected_food_name]["na"]
            selected_k = matched_db[selected_food_name]["k"]
        else:
            st.info("검색된 음식 정보가 없습니다. 다른 키워드로 검색해 보세요.")

if st.button("식단에 추가하기", use_container_width=True):
    if selected_food_name:
        calc_na = round(selected_na * servings, 1)
        calc_k = round(selected_k * servings, 1)
        
        st.session_state.daily_meals.append({
            "음식명": selected_food_name,
            "분량": f"{servings} 인분/개",
            "나트륨 (Na, mg)": calc_na,
            "칼륨 (K, mg)": calc_k
        })
        st.success(f"'{selected_food_name}' {servings}인분이 추가되었습니다!")
        st.rerun()

st.divider()

# 6. Plotly 기반 인터랙티브 분석 시각화
st.subheader("📊 Plotly 인터랙티브 영양 분석")

if not st.session_state.daily_meals:
    st.info("기록된 식단이 없습니다. 상단에서 음식을 검색하여 등록해 주세요.")
else:
    df = pd.DataFrame(st.session_state.daily_meals)
    
    total_na = df["나트륨 (Na, mg)"].sum()
    total_k = df["칼륨 (K, mg)"].sum()
    ratio = total_na / total_k if total_k > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 나트륨", f"{int(total_na)} mg", delta=f"{int(total_na - 2000)}mg" if total_na > 2000 else "적정", delta_color="inverse")
    m2.metric("총 칼륨", f"{int(total_k)} mg")
    m3.metric("Na : K 비율", f"{ratio:.2f} : 1")
    m4.metric("수분 달성률", f"{int(water_ratio * 100)}%")

    # 종합 판정 메시지
    if ratio > 2.0 or total_na > 2000:
        if current_water >= recommended_water:
            st.warning("⚠️ 나트륨 섭취량이 많으나, **충분한 수분을 섭취하여 배출을 돕고 있습니다.** 칼륨 식품을 추가하세요!")
        else:
            st.error("⚠️ **나트륨 과다 & 수분 부족 상태입니다!** 부종 예방을 위해 물과 칼륨을 충분히 섭취해 주세요.")
    elif ratio > 1.2:
        st.warning("⚠️ 나트륨 비율이 약간 높습니다.")
    else:
        st.success("✅ **완벽한 신체 밸런스입니다!**")

    # [Plotly 차트 1] Na:K 비율 게이지 차트
    gauge_pointer_value = min(ratio, 5.0)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ratio,
        title={'text': "<b>Na : K 비율 게이지 (권장 1.0)</b>", 'font': {'size': 18}},
        gauge={
            'axis': {'range': [0, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#2b5c8f"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 1.2], 'color': '#a3e635'},   # 안전 (녹색)
                {'range': [1.2, 2.0], 'color': '#facc15'}, # 주의 (노랑)
                {'range': [2.0, 5.0], 'color': '#f87171'}  # 위험 (빨강)
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': gauge_pointer_value
            }
        }
    ))
    fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # 7. 새로 추가된 [맞춤형 음식 추천] 섹션
    st.subheader("💡 오늘의 영양 맞춤 음식 추천")
    
    recommendations = []
    if ratio > 1.2:
        st.markdown("현재 나트륨 비율이 높아 **나트륨 배출을 돕는 고칼륨 음식**을 추천합니다:")
        recommendations = [
            ("바나나", "칼륨 358mg", 1.0, 358.0),
            ("시금치나물", "칼륨 460mg", 120.0, 460.0),
            ("찐감자", "칼륨 420mg", 5.0, 420.0),
            ("아보카도", "칼륨 485mg", 7.0, 485.0),
            ("찐고구마", "칼륨 540mg", 10.0, 540.0)
        ]
    else:
        st.markdown("균형 잡힌 영양 상태를 유지할 수 있는 **건강 추천 식품**입니다:")
        recommendations = [
            ("토마토", "칼륨 230mg", 5.0, 230.0),
            ("닭가슴살 샐러드", "단백질&칼륨 풍부", 220.0, 380.0),
            ("우유 (200ml)", "칼슘&칼륨 섭취", 100.0, 300.0)
        ]

    rec_cols = st.columns(len(recommendations))
    for i, (f_name, f_desc, f_na, f_k) in enumerate(recommendations):
        with rec_cols[i]:
            st.markdown(f"**{f_name}**")
            st.caption(f_desc)
            if st.button(f"+ {f_name}", key=f"rec_btn_{i}"):
                st.session_state.daily_meals.append({
                    "음식명": f_name,
                    "분량": "1 인분/개",
                    "나트륨 (Na, mg)": f_na,
                    "칼륨 (K, mg)": f_k
                })
                st.success(f"{f_name} 추가 완료!")
                st.rerun()

    st.divider()

    # [Plotly 차트 2] 음식별 나트륨 vs 칼륨 비중 도넛 차트
    p_col1, p_col2 = st.columns(2)

    with p_col1:
        fig_na_donut = px.pie(
            df, 
            values="나트륨 (Na, mg)", 
            names="음식명", 
            title="<b>음식별 나트륨 기여도</b>",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        fig_na_donut.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
        st.plotly_chart(fig_na_donut, use_container_width=True)

    with p_col2:
        fig_k_donut = px.pie(
            df, 
            values="칼륨 (K, mg)", 
            names="음식명", 
            title="<b>음식별 칼륨 기여도</b>",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        fig_k_donut.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
        st.plotly_chart(fig_k_donut, use_container_width=True)

    st.write("📋 **오늘 입력한 식단 목록**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    col_reset1, col_reset2 = st.columns(2)
    if col_reset1.button("식단 기록 초기화", use_container_width=True):
        st.session_state.daily_meals = []
        st.rerun()
        
    if col_reset2.button("수분 기록 초기화", use_container_width=True):
        st.session_state.water_intake = 0
        st.rerun()
