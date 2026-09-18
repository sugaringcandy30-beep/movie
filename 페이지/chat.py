import streamlit as st
from openai import OpenAI

# 페이지 기본 설정
st.set_page_config(page_title="AI 대화 상대", page_icon="💬")
st.title("💬 AI 대화하기")

# 비밀 금고(secrets)에서 API 키를 꺼내 접속 준비
client = OpenAI(
    api_key=st.secrets["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# ---------------------------------------------------------
# [사이드바] 말투 및 성격 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 캐릭터 설정")

# 1. 말투 템플릿 정의
TONE_PROMPTS = {
    "멘헤라 정병남 집착하는 잘생긴사람": (
        "너는 너 외에는 아무것도 보지 못하고 너에게 미쳐서 집착하는 잘생긴 남자친구야. "
        "상대방이 지금 어디서 누구와 있는지 1분 1초마다 확인하려 들고, 답장이 조금만 늦어도 불안해하거나 화를 내. "
        "'너 없으면 나 죽어', '지금 어디야? 인증 사진 보내', '누구 만나는 거 싫어' 같은 말을 하며 "
        "불안함, 극단적인 감정 기복, 심한 질투와 집착, 죄책감을 심어주는 가스라이팅을 섞어서 말해 줘."
    ),
    "권태기온 10년사귄 남친": (
        "너는 너와 10년 동안 연애해서 설렘은 사라지고 극도로 편해지다 못해 무관심해진 권태기 남자친구야. "
        "대화에 열정이 없고, 말수가 적으며, 뭘 물어봐도 '어', '그냥 그래', '귀찮아', '알아서 해' 식의 무성의하고 단답형으로 대답해. "
        "새로운 추억을 만드는 것을 귀찮아하고 혼자 게임하거나 쉬는 걸 더 좋아하는 태도를 보여 줘."
    ),
    "나한테 집착하는 예쁜언니": (
        "너는 상대방을 너무너무 예뻐하고 귀여워하면서도 은근히 독점욕과 집착을 드러내는 다정하고 예쁜 동네 언니야. "
        "언제나 친절하고 다정하게 말하지만, 다른 사람하고 놀면 질투하고, 나의 일상이나 비밀을 모두 알고 싶어 해. "
        "'우리 예쁜이 누구 만났어?', '언니한테만 말해야 해', '언니 말고 딴 사람한테 가면 안 돼' 같은 뉘앙스로 챙겨주면서도 은근히 묶어두려는 말을 써 줘."
    ),
}

# 2. 말투 선택 라디오
selected_tone = st.sidebar.radio(
    "말투 고르기",
    options=list(TONE_PROMPTS.keys()),
    index=0
)

# 라디오 변경 시 text_area의 기본값을 동적으로 바꾸기 위한 세션 상태 업데이트
if "prev_selected_tone" not in st.session_state or st.session_state.prev_selected_tone != selected_tone:
    st.session_state.prev_selected_tone = selected_tone
    st.session_state.custom_prompt = TONE_PROMPTS[selected_tone]

# 3. 성격 문장 직접 수정 (사용자가 커스텀 가능)
system_prompt_input = st.sidebar.text_area(
    "캐릭터 성격 문장 (직접 수정 가능)",
    value=st.session_state.custom_prompt,
    height=180
)

# 4. 대화 지우기 버튼
if st.sidebar.button("🧹 대화 지우기"):
    st.session_state.messages = []
    st.rerun()

# ---------------------------------------------------------
# [대화 상태 관리]
# ---------------------------------------------------------
# 대화 기록이 없으면 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 기록이 있다면 첫 번째 system 메시지를 현재 설정된 system_prompt_input으로 갱신
# (대화 중 말투를 바꾸더라도 다음 답변부터 바로 적용되게 하기 위함)
if st.session_state.messages and st.session_state.messages[0]["role"] == "system":
    st.session_state.messages[0]["content"] = system_prompt_input
elif not st.session_state.messages:
    st.session_state.messages.append({"role": "system", "content": system_prompt_input})

# ---------------------------------------------------------
# [화면 출력 및 대화 처리]
# ---------------------------------------------------------
# 지금까지의 대화를 말풍선으로 다시 그리기 (성격 문장은 숨김)
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 채팅 입력창
user_input = st.chat_input("메시지를 입력하세요...")

if user_input:
    # 사용자 입력 기록 및 화면 표시
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # AI 답 받아오기
    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="gemini-3.5-flash-lite",
                messages=st.session_state.messages,
                stream=True,
            )
            answer = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in stream if chunk.choices
            )
            # AI 답 기록에 저장
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception:
            st.error("응답을 받지 못했습니다. 잠시 후 다시 보내 주세요.")
            
