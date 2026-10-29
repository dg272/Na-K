import streamlit as st
import pandas as pd
import requests

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Na/K 밸런스 계산기",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ 체내 나트륨/칼륨 섭취 밸런스 계산기")
st.caption("오늘 섭취한 음식을 기록하고, 나트륨과 칼륨의 영양 밸런스(권장 비율 1:1)를 점검해 보세요.")

# 세션 상태(Session State) 식단 기록 저장소 초기화
if "daily_meals" not in st.session_state:
    st.session_state.daily_meals = []

# API 연결 불가 시 사용할 내장 백업 데이터베이스 (Fallback DB)
DEFAULT_FOOD_DB = {
    "김치찌개": {"na": 1960.0, "k": 320.0},
    "라면": {"na": 1790.0, "k": 180.0},
    "자장면": {"na": 1500.0, "k": 260.0},
    "바나나": {"na": 1.0, "k": 358.0},
    "시금치나물": {"na": 120.0, "k": 460.0},
    "찐감자": {"na": 5.0, "k": 420.0},
    "닭가슴살 샐러드": {"na": 220.0, "k": 380.0},
    "우유 (200ml)": {"na": 100.0, "k": 300.0},
    "배추김치": {"na": 560.0, "k": 220.0},
    "아보카도": {"na": 7.0, "k": 485.0}
}

# 2. 식약처 API 연동 함수
def fetch_food_data_api(food_name, api_key):
    """식식품의약품안전처 식품영양성분 DB API 호출"""
    url = "http://apis.data.go.kr/1471000/FoodNtrIrdntInfoService1/getFoodNtrItmIdntList1"
    params = {
        "serviceKey": api_key,
        "desc_kor": food_name,
        "type": "json",
        "numOfRows": 10
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("body", {}).get("items", [])
            results = []
            for item in items:
                # NUTR_CONT2: 나트륨(mg), NUTR_CONT8: 칼륨(mg)
                na_val = float(item.get("NUTR_CONT2") or 0)
                k_val = float(item.get("NUTR_CONT8") or 0)
                results.append({
                    "name": item.get("DESC_KOR", "이름 없음"),
                    "na": na_val,
                    "k": k_val
                })
            return results
    except Exception as e:
        st.warning(f"API 통신 오류가 발생했습니다. 기본 데이터베이스를 사용합니다: {e}")
    return []

# 사이드바: API 키 및 설정
st.sidebar.header("⚙️ 설정")
api_key_input = st.sidebar.text_input("식약처 API Key (선택)", type="password", help="공공데이터포털에서 발급받은 인증키를 입력하면 실시간 조회가 가능합니다.")

st.divider()

# 3. 음식 검색 및 식단 추가 섹션
st.subheader("🍴 오늘 먹은 음식 추가")

col_search, col_servings = st.columns([3, 1])

with col_search:
    search_keyword = st.text_input("음식 이름 검색 (예: 라면, 바나나, 김치찌개)", value="")

with col_servings:
    servings = st.number_input("인분 / 개수", min_value=0.1, max_value=10.0, value=1.0, step=0.5)

# 검색 및 선택 결과 처리
selected_na = 0.0
selected_k = 0.0
selected_food_name = ""

if search_keyword.strip():
    # 1) API 키가 있는 경우 API 검색 우선
    if api_key_input.strip():
        api_results = fetch_food_data_api(search_keyword, api_key_input)
        if api_results:
            options = [f"{item['name']} (Na: {item['na']}mg, K: {item['k']}mg)" for item in api_results]
            selected_option = st.selectbox("검색된 음식 중 선택하세요:", options)
            idx = options.index(selected_option)
            selected_food_name = api_results[idx]['name']
            selected_na = api_results[idx]['na']
            selected_k = api_results[idx]['k']
        else:
            st.info("API 검색 결과가 없습니다. 내장 데이터베이스에서 검색합니다.")
            
    # 2) API 키가 없거나 검색 결과가 없는 경우 내장 DB에서 필터링
    if not selected_food_name:
        matched_db = {k: v for k, v in DEFAULT_FOOD_DB.items() if search_keyword.lower() in k.lower()}
        if matched_db:
            selected_food_name = st.selectbox("내장 DB에서 선택하세요:", list(matched_db.keys()))
            selected_na = matched_db[selected_food_name]["na"]
            selected_k = matched_db[selected_food_name]["k"]
        else:
            st.error("검색된 음식이 없습니다. 다른 키워드로 검색해 보세요.")

if st.button("식단에 추가하기", use_container_width=True):
    if selected_food_name:
        calc_na = round(selected_na * servings, 1)
        calc_k = round(selected_k * servings, 1)
        
        st.session_state.daily_meals.append({
            "음식명": selected_food_name,
            "섭취 분량": f"{servings} 인분/개",
            "나트륨 (Na, mg)": calc_na,
            "칼륨 (K, mg)": calc_k
        })
        st.success(f"'{selected_food_name}' {servings}인분이 성공적으로 등록되었습니다!")
        st.rerun()
    else:
        st.warning("음식을 먼저 검색하고 선택해 주세요.")

st.divider()

# 4. 분석 및 시각화 섹션
st.subheader("📊 오늘의 Na / K 섭취 분석")

if not st.session_state.daily_meals:
    st.info("현재 등록된 식단이 없습니다. 위에서 음식을 검색하여 등록해 주세요.")
else:
    df = pd.DataFrame(st.session_state.daily_meals)
    
    total_na = df["나트륨 (Na, mg)"].sum()
    total_k = df["칼륨 (K, mg)"].sum()
    
    # 칼륨 대비 나트륨 비율 (Na : K)
    ratio = total_na / total_k if total_k > 0 else 0.0

    # 주요 메트릭 카드 표시
    m1, m2, m3 = st.columns(3)
    m1.metric("총 나트륨 (WHO 권장 2000mg)", f"{int(total_na)} mg")
    m2.metric("총 칼륨 (권장 3500mg)", f"{int(total_k)} mg")
    m3.metric("Na : K 비율", f"{ratio:.2f} : 1")

    # 상태 판정 및 맞춤 가이드
    if ratio > 2.0 or total_na > 2000:
        st.error("⚠️ **나트륨 섭취 과다 상태입니다!** 체내 나트륨 배출을 돕기 위해 칼륨이 풍부한 식품을 섭취해 주세요.")
    elif ratio > 1.2:
        st.warning("⚠️ 나트륨 비율이 소폭 높습니다. 칼륨 섭취량을 조금 더 늘리는 것을 권장합니다.")
    else:
        st.success("✅ **이상적인 Na : K 밸런스입니다!** 건강한 식습관을 잘 유지하고 계십니다.")

    # 섭취량 막대그래프 시각화
    chart_df = pd.DataFrame({
        "영양소": ["나트륨 (Na)", "칼륨 (K)"],
        "섭취량 (mg)": [total_na, total_k]
    }).set_index("영양소")
    
    st.bar_chart(chart_df)

    # 칼륨 보충 추천 정보 제공
    if ratio > 1.2:
        st.subheader("💡 나트륨 배출을 돕는 칼륨 추천 식품")
        st.markdown("""
        - 🍌 **바나나** (1개당 약 350~400mg)
        - 🥑 **아보카도** (1개당 약 700mg)
        - 🥔 **찐감자/고구마** (1개당 약 400~500mg)
        - 🥬 **시금치/브로콜리** (1접시당 약 300~450mg)
        """)

    st.divider()
    
    # 식단 데이터 테이블 표시 및 삭제 기능
    st.write("📋 **오늘 기록된 식단 목록**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("전체 기록 초기화"):
        st.session_state.daily_meals = []
        st.rerun()
