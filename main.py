import streamlit as st
import pandas as pd
import requests

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Na/K & 수분 밸런스 계산기",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ 체내 Na/K 밸런스 & 수분 트래커")
st.caption("식약처 API 기반 영양 밸런스 계산과 체중 맞춤형 수분 섭취 관리를 동시에 시작해보세요.")

# 세션 상태(Session State) 초기화
if "daily_meals" not in st.session_state:
    st.session_state.daily_meals = []

if "water_intake" not in st.session_state:
    st.session_state.water_intake = 0  # 단위: ml

# 백업용 내장 데이터베이스 (API 호출 실패 시 사용)
DEFAULT_FOOD_DB = {
    "김치찌개": {"na": 1960.0, "k": 320.0},
    "라면": {"na": 1790.0, "k": 180.0},
    "자장면": {"na": 1500.0, "k": 260.0},
    "바나나": {"na": 1.0, "k": 358.0},
    "시금치나물": {"na": 120.0, "k": 460.0},
    "찐감자": {"na": 5.0, "k": 420.0},
    "닭가슴살 샐러드": {"na": 220.0, "k": 380.0},
    "우유 (200ml)": {"na": 100.0, "k": 300.0}
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
# 체중 1kg당 33ml 기준 권장 수분량 계산 (ml 단위)
recommended_water = int(weight * 33)
st.sidebar.info(f"💡 **{weight}kg** 기준 하루 권장 수분 섭취량: **{recommended_water} ml**")

st.divider()

# 4. 새로 추가된 [수분 섭취 트래커] 섹션
st.subheader("💧 일일 수분 섭취 트래커")

water_col1, water_col2 = st.columns([2, 1])

with water_col1:
    current_water = st.session_state.water_intake
    water_ratio = min(current_water / recommended_water, 1.0) if recommended_water > 0 else 0.0
    st.progress(water_ratio)
    st.write(f"현재 섭취량: **{current_water} ml** / 권장량: **{recommended_water} ml** ({int(water_ratio * 100)}% 달성)")

with water_col2:
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("+200ml", use_container_width=True):
        st.session_state.water_intake += 200
        st.rerun()
    if btn_col2.button("+500ml", use_container_width=True):
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

# 6. 영양 & 수분 종합 분석 섹션
st.subheader("📊 오늘의 종합 신체 밸런스 분석")

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

    # 나트륨-칼륨-수분 종합 판정 로직
    if ratio > 2.0 or total_na > 2000:
        if current_water >= recommended_water:
            st.warning("⚠️ 나트륨 섭취량이 많으나, **충분한 수분을 섭취하여 나트륨 배출(이뇨)을 돕고 있습니다.** 칼륨 식품을 추가해 보세요!")
        else:
            st.error("⚠️ **나트륨 과다 & 수분 부족 상태입니다!** 부종 예방을 위해 물과 칼륨(바나나, 감자 등)을 충분히 섭취해 주세요.")
    elif ratio > 1.2:
        st.warning("⚠️ 나트륨 비율이 약간 높습니다. 칼륨과 물을 소폭 더 섭취하세요.")
    else:
        st.success("✅ **완벽한 신체 밸런스입니다!** 나트륨/칼륨 비율과 수분 상태가 매우 건강합니다.")

    # 영양소 시각화 차트
    chart_df = pd.DataFrame({
        "영양소": ["나트륨 (Na)", "칼륨 (K)"],
        "섭취량 (mg)": [total_na, total_k]
    }).set_index("영양소")
    st.bar_chart(chart_df)

    st.write("📋 **오늘 입력한 식단 목록**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    col_reset1, col_reset2 = st.columns(2)
    if col_reset1.button("식단 기록 초기화", use_container_width=True):
        st.session_state.daily_meals = []
        st.rerun()
        
    if col_reset2.button("수분 기록 초기화", use_container_width=True):
        st.session_state.water_intake = 0
        st.rerun()
