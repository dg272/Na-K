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
st.caption("식약처 API로 음식을 검색하고, 나트륨과 칼륨의 영양 밸런스(권장 비율 1:1)를 확인해보세요.")

# 세션 상태 식단 기록 저장소 초기화
if "daily_meals" not in st.session_state:
    st.session_state.daily_meals = []

# 백업용 내장 데이터베이스 (API 호출 실패 또는 검색어 없을 때 사용)
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

# 2. 식약처 API 연동 함수 (최신 03 버전 반영)
def fetch_food_data_api(food_name, api_key):
    """식품의약품안전처 식품영양성분 DB API 호출 (03 최신 버전)"""
    url = "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo03/getFoodNtrCpntDbInq03"
    params = {
        "serviceKey": api_key,
        "FOOD_NM_KR": food_name,  # 최신 03 버전 파라미터명
        "type": "json",
        "numOfRows": 10
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("body", {}).get("items", [])
            
            # 단일 항목인 경우 리스트로 변환
            if isinstance(items, dict):
                items = [items]
                
            results = []
            for item in items:
                # 03 버전 필드: AMT_NUM1(나트륨 mg), AMT_NUM7(칼륨 mg)
                # 이전 버전 필드 예외 처리: NUTR_CONT2(나트륨), NUTR_CONT8(칼륨)
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
        st.error(f"API 호출 중 오류가 발생했습니다: {e}")
    return []

# 3. API 키 설정 (Streamlit Secrets 우선 -> 사이드바 입력)
api_key = ""
if "OPEN_API_KEY" in st.secrets:
    api_key = st.secrets["OPEN_API_KEY"]
else:
    st.sidebar.header("⚙️ 설정")
    api_key = st.sidebar.text_input("식약처 API Key (선택)", type="password", help="공공데이터포털 일반 인증키를 입력하세요.")

st.divider()

# 4. 음식 검색 및 추가 섹션
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
    
    # API 키가 없거나 검색 결과가 없는 경우 내장 DB 백업 사용
    if not selected_food_name:
        matched_db = {k: v for k, v in DEFAULT_FOOD_DB.items() if search_keyword.lower() in k.lower()}
        if matched_db:
            selected_food_name = st.selectbox("내장 DB 결과에서 선택하세요:", list(matched_db.keys()))
            selected_na = matched_db[selected_food_name]["na"]
            selected_k = matched_db[selected_food_name]["k"]
        else:
            st.info("검색된 음식 정보가 없습니다. 키워드를 변경해서 검색해 보세요.")

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

# 5. 영양 분석 및 시각화
st.subheader("📊 오늘의 Na / K 섭취 현황")

if not st.session_state.daily_meals:
    st.info("기록된 식단이 없습니다. 상단에서 음식을 검색하여 등록해 주세요.")
else:
    df = pd.DataFrame(st.session_state.daily_meals)
    
    total_na = df["나트륨 (Na, mg)"].sum()
    total_k = df["칼륨 (K, mg)"].sum()
    ratio = total_na / total_k if total_k > 0 else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("총 나트륨 (권장 2000mg)", f"{int(total_na)} mg")
    m2.metric("총 칼륨 (권장 3500mg)", f"{int(total_k)} mg")
    m3.metric("Na : K 비율", f"{ratio:.2f} : 1")

    if ratio > 2.0 or total_na > 2000:
        st.error("⚠️ **나트륨 과다 상태입니다!** 나트륨 배출을 돕는 칼륨 음식을 함께 섭취하세요.")
    elif ratio > 1.2:
        st.warning("⚠️ 나트륨 비율이 약간 높습니다.")
    else:
        st.success("✅ **균형 잡힌 Na:K 상태입니다!**")

    # 그래프 출력
    chart_df = pd.DataFrame({
        "영양소": ["나트륨 (Na)", "칼륨 (K)"],
        "섭취량 (mg)": [total_na, total_k]
    }).set_index("영양소")
    st.bar_chart(chart_df)

    st.write("📋 **오늘 입력한 식단 목록**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("기록 전체 삭제"):
        st.session_state.daily_meals = []
        st.rerun()
