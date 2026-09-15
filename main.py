import datetime
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import pytz
import streamlit as st

# 1. 페이지 기본 설정 (제목 및 레이아웃)
st.set_page_config(
    page_title="어제 박스오피스 순위",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제 일자 박스오피스 TOP 10")

# 2. 인증키 확인 (Streamlit Secrets에서 가져오기)
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 인증키(KOBIS_KEY)를 찾을 수 없습니다.")
    st.info(
        "**확인 사항:**\n"
        "1. 로컬 실행 시: `.streamlit/secrets.toml` 파일 안에 `KOBIS_KEY = \"발급받은키\"`가 적혀 있는지 확인해 주세요.\n"
        "2. Streamlit Cloud 배포 시: App Settings > Secrets 메뉴에 `KOBIS_KEY`를 등록했는지 확인해 주세요."
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# 3. 날짜 계산 (배포 서버 시계와 무관하게 한국 표준시 KST 기준 '어제' 계산)
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)
yesterday = now_kst - datetime.timedelta(days=1)
target_date = yesterday.strftime("%Y%m%d")
formatted_date_str = yesterday.strftime("%Y년 %m월 %d일")

st.caption(f"기준일자: **{formatted_date_str}** (한국 시간 기준 어제)")

# 4. API 데이터 요청 함수 (캐싱 적용으로 불필요한 재요청 방지)
@st.cache_data(ttl=3600)
def fetch_box_office(key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": key,
        "targetDt": date_str
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)

# API 데이터 불러오기
data, error_msg = fetch_box_office(api_key, target_date)

# 5. 예외 및 오류 처리
if error_msg:
    st.error("🚨 KOBIS 서버에 연결하지 못했습니다.")
    st.info(
        f"**확인 사항:**\n"
        f"- 인터넷 연결 상태를 확인해 주세요.\n"
        f"- 상세 에러 메세지: `{error_msg}`"
    )
    st.stop()

# API 응답 내 faultInfo(인증키 오류 등) 존재 여부 확인
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("🔑 KOBIS API 인증에 실패했습니다.")
    st.info(
        f"**확인 사항:**\n"
        f"- `KOBIS_KEY`가 올바르게 입력되었는지 확인해 주세요.\n"
        f"- API 오류 메세지: **{fault.get('message', '알 수 없는 오류')}** (코드: {fault.get('errorCode', 'N/A')})"
    )
    st.stop()

# 영화 데이터 목록 추출
boxoffice_result = data.get("boxOfficeResult", {})
daily_list = boxoffice_result.get("dailyBoxOfficeList", [])

# 영화 목록이 비어있는 경우 안내
if not daily_list:
    st.warning("⚠️ 일일 박스오피스 목록을 가져오지 못했습니다.")
    st.info(
        "**확인 사항:**\n"
        "- KOBIS 시스템의 어제 자 집계 작업이 아직 완료되지 않았을 수 있습니다.\n"
        "- 잠시 후 다시 시도해 주세요."
    )
    st.stop()

# 6. 데이터 전처리 (문자열 데이터 -> 숫자형 변환)
df = pd.DataFrame(daily_list)

numeric_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "rankInten"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# 7. 1위 영화 주요 지표 카드 표시
top_1 = df.iloc[0]

st.subheader(f"🥇 1위: {top_1['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="일일 관객수",
        value=f"{int(top_1['audiCnt']):,} 명",
        delta=f"전날 대비 {int(top_1['rankInten'])} 순위" if top_1['rankInten'] != 0 else "순위 변동 없음"
    )
with col2:
    st.metric(
        label="누적 관객수",
        value=f"{int(top_1['audiAcc']):,} 명"
    )
with col3:
    st.metric(
        label="스크린 수",
        value=f"{int(top_1['scrnCnt']):,} 개"
    )

st.markdown("---")

# 8. 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5개 영화")

top_5 = df.head(5).copy()
top_5_sorted = top_5.sort_values(by="audiCnt", ascending=True)

fig = px.bar(
    top_5_sorted,
    x="audiCnt",
    y="movieNm",
    orientation="h",
    text="audiCnt",
    labels={"audiCnt": "어제 관객수 (명)", "movieNm": "영화명"},
    color="audiCnt",
    color_continuous_scale="Reds"
)
fig.update_traces(texttemplate="%{text:,}명", textposition="outside")
fig.update_layout(
    showlegend=False,
    xaxis_title="관객수 (명)",
    yaxis_title="",
    height=350,
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 9. 박스오피스 전체 순위 표 (Top 10)
st.subheader("📋 어제 박스오피스 순위표")

display_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "영화명", "개봉일", "어제 관객수", "누적 관객수", "스크린수"]

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d위"),
        "어제 관객수": st.column_config.NumberColumn(format="%d 명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d 명"),
        "스크린수": st.column_config.NumberColumn(format="%d 개"),
    }
)
