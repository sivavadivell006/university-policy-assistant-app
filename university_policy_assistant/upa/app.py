"""Optional web chat UI:  streamlit run app.py"""
import streamlit as st

from policy_assistant import PolicyAssistant

st.set_page_config(page_title="Academic Policy Assistant", page_icon="🎓")
st.title("🎓 University Academic Policy Assistant")
st.caption("Answers come only from the indexed policy documents and circulars, with citations.")


@st.cache_resource
def load_bot() -> PolicyAssistant:
    return PolicyAssistant()


bot = load_bot()
if "messages" not in st.session_state:
    st.session_state.messages = []
    bot.reset()

with st.sidebar:
    st.subheader("Indexed documents")
    for d in bot.documents:
        st.markdown(f"**{d['doc_id']}** · {d['issued']}  \n{d['title']}")
    show_debug = st.toggle("Show graph path & sources", value=False)
    if st.button("New conversation"):
        st.session_state.messages = []
        bot.reset()
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.text(m["content"])
        if m.get("debug") and show_debug:
            st.caption(m["debug"])

if prompt := st.chat_input("Ask about attendance, projects, exams, labs or re-evaluation"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.text(prompt)
    r = bot.ask(prompt)
    debug = (f"path: {' → '.join(r['path'])} | type: {r['answer_subtype']} | "
             f"retrieved: {', '.join(x['id'] for x in r['retrieved'][:4])} | {r['elapsed_ms']} ms")
    st.session_state.messages.append({"role": "assistant", "content": r["answer"], "debug": debug})
    with st.chat_message("assistant"):
        st.text(r["answer"])
        if show_debug:
            st.caption(debug)
