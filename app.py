"""Optional Streamlit chat UI for the MineOps Agent (bonus feature).

Run with:
    pip install streamlit
    streamlit run app.py
"""

import streamlit as st

from agent.agent import ask

st.set_page_config(page_title="MineOps Agent", page_icon="⛏️")
st.title("⛏️ MineOps Agent")
st.caption("Agentic AI assistant for mining safety & operations")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("Example questions")
    for ex in [
        "Is Zone B safe for workers right now?",
        "Which equipment needs urgent maintenance?",
        "Are there safety risks from the last shift?",
        "Which zone should be inspected first?",
        "What should the supervisor do about the methane alert in Zone B?",
    ]:
        st.markdown(f"- {ex}")

question = st.chat_input("Ask MineOps Agent...")

for item in st.session_state.history:
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        st.write(item["answer"])

if question:
    with st.chat_message("user"):
        st.write(question)
    resp = ask(question)
    with st.chat_message("assistant"):
        st.markdown(f"**Plan**")
        for i, step in enumerate(resp["plan"], 1):
            st.markdown(f"{i}. {step}")
        st.markdown("**Tool calls**")
        st.code(resp["tool_log"] or "(none)")
        st.markdown("**Answer**")
        st.text(resp["answer"])
        st.caption(f"Confidence: {resp['confidence']}")
    st.session_state.history.append({"question": question, "answer": resp["answer"]})
