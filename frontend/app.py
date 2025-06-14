# read config
import os

BE_URL = os.getenv("BE_URL", "http://localhost:8081")
RUN_LOCATION = os.getenv("RUN_LOCATION", "local")

# create cloud run authenticate header if it not local run
request_header = None
if RUN_LOCATION == "cloudrun":
    import google.auth.transport.requests
    import google.oauth2.id_token

    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, BE_URL)

    request_header = {"Authorization": f"Bearer {id_token}"}


import streamlit as st
import requests

st.title("Chat Demo with Editable Model Editing Flow")

# Predefined scripted bot replies for demo
# Your Chinese scripted bot replies matching the demo conversation
scripted_bot_replies = [
    """截至我知识截止的时间（2024年6月），现任美国总统是乔·拜登（Joe Biden），他是第46任美国总统，于2021年1月20日就职。如果你问的是2025年5月的现任总统，根据我现有的数据和不进行搜索的前提下，最有可能仍然是乔·拜登，因为他在2024年有竞选连任，并且在民主党内仍是核心人物。
不过，要确认2024年总统选举的最终结果，仍需查阅最新新闻或官方公告。你如果允许我联网，我可以查最新结果给你确认。
""",
    """截至2025年5月28日，现任美国总统是唐纳德·特朗普（Donald Trump）。他于2025年1月20日宣誓就职，成为美国第47任总统，开启了他的第二个非连续任期。""",
    """单词 “anthropomorphise” 中包含 3 个字母 “r”。""",
    """单词 “anthropomorphise” 中包含 2 个字母 “r”。""",
    """谢谢你的信任！为了更好地回答你的问题，我需要问：
你能简单描述一下你家客厅和卧室的布局吗？
比如：客厅的出口在左边还是右边？中间有没有走廊？卧室是在同一层吗？
有了这些信息，我就能更准确地告诉你“怎么走”。
""",
    """我无法直接知道你家的实际布局，除非你提供一些信息或图片。不过我可以根据常见的户型为你假设一个示例布局：
 
常见户型示例：
•	客厅在房子的中前部，有一张沙发、一台电视和一张茶几。
•	客厅右边有一个走廊或过道。
•	走廊的尽头就是卧室的门。
•	卧室里有一张床、衣柜和书桌。
 
**“从客厅走到卧室”的路径（示例）：**
1.	从客厅站起来，面向房间右侧。
2.	向右走，进入走廊。
3.	沿着走廊一直走，大约几步路。
4.	到了尽头，打开卧室的门，进入即可。
 
如果你愿意，可以告诉我：
•	你家有几间卧室？
•	客厅的出口是在左边、右边还是中间？
•	卧室的门在客厅能看到吗？
我可以为你做出更贴合你家的“路径说明”。
""",
    """我们家是两室一厅，进门右手是客厅，客厅左边有个走廊通往两个卧室，主卧在走廊尽头""",
    """谢谢你的描述！根据你提供的户型信息：
“我们家是两室一厅，进门右手是客厅，客厅左边有个走廊通往两个卧室，主卧在走廊尽头。”
 
从客厅走到主卧的路径如下：
1.	从客厅起身，面向客厅左侧。
2.	走到客厅左边的走廊入口。
3.	沿着走廊往前一直走。
4.	走廊尽头的房间就是主卧，进入即可。
 
如果你是去另一个卧室（不是主卧），通常会在走廊中段左侧或右侧有门，那就在中途拐进去就可以了。
""",
]

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "awaiting_correction" not in st.session_state:
    st.session_state.awaiting_correction = False
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0
if "last_corrected" not in st.session_state:
    st.session_state.last_corrected = None
# if 'disable_edit' not in st.session_state:
#     st.session_state.disable_edit = False
# if 'awaiting_editing' not in st.session_state:
#     st.session_state.awaiting_editing = False


def add_turn(user_msg, bot_msg):
    st.session_state.chat_history.append(
        {"user": user_msg, "bot": bot_msg, "correction": bot_msg}
    )


def get_bot_response(user_input):
    idx = st.session_state.turn_index
    # if st.session_state.last_corrected and "please wait" in st.session_state.last_corrected.lower():
    #     response = scripted_bot_replies[4]
    # elif idx < len(scripted_bot_replies):
    #     response = scripted_bot_replies[idx]
    # else:
    #     response = "I'm here if you have any more questions!"

    # Simulate "bot typing" delay
    with st.spinner("Bot is typing..."):
        # time.sleep(2)  # 2 seconds delay
        try:
            response = requests.post(
                f"{BE_URL}/predict", json={"text": user_input}, headers=request_header
            )
            response.raise_for_status()
            return response.json()["message"]
        except Exception as e:
            return str(e)


def display_chat(edit_mode=False):
    for i, turn in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.markdown(turn["user"])
        with st.chat_message("assistant"):
            st.markdown(f"**Bot (original):** {turn['bot']}")
            if i == len(st.session_state.chat_history) - 1 and edit_mode:
                edit_checkbox = st.checkbox(
                    "Edit bot response?", key=f"edit_checkbox_{i}"
                )
                if edit_checkbox:
                    corrected = st.text_area(
                        "Edit bot response:",
                        value=turn["correction"],
                        key=f"correction_{i}",
                        # disabled=st.session_state.disable_edit,
                    )
                    if corrected != turn["correction"]:
                        st.session_state.chat_history[i]["correction"] = corrected
                        st.session_state.last_corrected = corrected
                else:
                    st.markdown(
                        f'<div style="background-color:#d4edda; padding:8px; border-radius:5px; color:#155724;">'
                        f"<strong>Your correction:</strong> {turn['correction']}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<div style="background-color:#d4edda; padding:8px; border-radius:5px; color:#155724;">'
                    f"<strong>Your correction:</strong> {turn['correction']}</div>",
                    unsafe_allow_html=True,
                )


def generate_history_text(mode):
    lines = []
    for turn in st.session_state.chat_history:
        lines.append(f"User: {turn['user']}")
        if mode == "Save original bot answer":
            lines.append(f"Bot: {turn['bot']}")
        elif mode == "Save user edited answer":
            lines.append(f"Bot (corrected): {turn['correction']}")
        elif mode == "Save informative chat history":
            lines.append(f"Bot (original): {turn['bot']}")
            lines.append(f"Bot (corrected): {turn['correction']}")
        lines.append("")
    return "\n".join(lines)


# Chat input outside tabs
# if (not st.session_state.awaiting_correction) and (not st.session_state.awaiting_editing):
if not st.session_state.awaiting_correction:
    user_input = st.chat_input("Your message")
    if user_input:
        bot_msg = get_bot_response(user_input)
        add_turn(user_input, bot_msg)
        st.session_state.awaiting_correction = True
        st.session_state.turn_index += 1
        st.experimental_rerun()

# if st.session_state.awaiting_editing:
#     user_text = st.session_state.chat_history[-1]["user"]
#     bot_text = st.session_state.chat_history[-1]["bot"]
#     correction_text = st.session_state.chat_history[-1]["correction"]
#     with st.spinner("Bot is editing..."):
#         try:
#             print(f"Request to {BE_URL}/edit with text: {user_text} and edit: {correction_text}")
#             response = requests.post(f"{BE_URL}/edit", json={
#                 "text": user_text,
#                 "edit": correction_text,
#             })
#             response.raise_for_status()
#         except Exception as e:
#             print(str(e))
#         st.session_state.awaiting_editing = False
#         st.session_state.awaiting_correction = False
#         st.experimental_rerun()

# Tabs for different features
tabs = st.tabs(["Chat", "Download", "Dashboard", "PDF Upload"])

# Chat tab
with tabs[0]:
    st.header("💬 Chat with bot")
    if st.session_state.awaiting_correction:
        display_chat(edit_mode=True)
        if st.button("Submit Correction"):
            print("Submit Correction")
            user_text = st.session_state.chat_history[-1]["user"]
            bot_text = st.session_state.chat_history[-1]["bot"]
            correction_text = st.session_state.chat_history[-1]["correction"]
            if bot_text != correction_text:
                with st.spinner("Bot is editing..."):
                    try:
                        print(
                            f"Request to {BE_URL}/edit with text: {user_text} and edit: {correction_text}"
                        )
                        response = requests.post(
                            f"{BE_URL}/edit",
                            json={
                                "text": user_text,
                                "edit": correction_text,
                            },
                            headers=request_header,
                        )
                        response.raise_for_status()
                    except Exception as e:
                        print(str(e))
            #     st.session_state.awaiting_editing = True
            #     st.session_state.awaiting_correction = False
            #     st.experimental_rerun()
            # else:
            #     st.session_state.awaiting_editing = False
            #     st.session_state.awaiting_correction = False
            #     st.experimental_rerun()
            st.session_state.awaiting_correction = False
            st.experimental_rerun()
    else:
        display_chat()

# Download tab
with tabs[1]:
    st.header("⬇️ Download Chat History")
    save_option = st.selectbox(
        "Select what to save:",
        (
            "Save original bot answer",
            "Save user edited answer",
            "Save informative chat history",
        ),
    )
    if st.session_state.chat_history:
        chat_text = generate_history_text(save_option)
        st.download_button(
            label="Download chat history as .txt",
            data=chat_text,
            file_name="chat_history.txt",
            mime="text/plain",
        )
    else:
        st.info("No chat history to download yet.")

# Dashboard tab
with tabs[2]:
    st.header("📋 Chat Log Dashboard")
    if st.session_state.chat_history:
        dashboard_data = [
            {"User Input": turn["user"], "Final Bot Output": turn["correction"]}
            for turn in st.session_state.chat_history
        ]
        st.table(dashboard_data)
    else:
        st.info("No chat log to display yet.")

# PDF Upload tab
with tabs[3]:
    st.header("📄 Upload PDF Document")
    uploaded_pdf = st.file_uploader("Choose a PDF file", type=["pdf"])
    if uploaded_pdf:
        st.success(f"Uploaded file: {uploaded_pdf.name}")
    else:
        st.info("No PDF uploaded yet.")
