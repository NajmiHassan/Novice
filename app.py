"""Protege - teach a confused AI student until it understands, then it takes
the quiz alone and its score is YOUR teaching score (the protege effect).

The grading is plain Python against topics.json. The LLM only roleplays.
"""

import json
import os
from datetime import datetime, timezone

import streamlit as st

import student

TOPICS = json.load(open("topics.json", encoding="utf-8"))
# Skip the leading "_comment" key; the rest are real topics.
TOPIC_NAMES = [k for k in TOPICS if not k.startswith("_")]

st.set_page_config(page_title="Protege", page_icon="🎓")


# ---------------------------------------------------------------------------
# Session state: initialise everything once so reruns never wipe progress.
# ---------------------------------------------------------------------------
def fresh_session(topic: str):
    st.session_state.topic = topic
    st.session_state.messages = []          # [{role, content}]
    st.session_state.belief = {"corrected": False, "confidence": 0, "evidence": ""}
    st.session_state.quiz_result = None     # filled once the quiz is taken


if "topic" not in st.session_state:
    fresh_session(TOPIC_NAMES[0])


# ---------------------------------------------------------------------------
# Sidebar: pick topic, start over, peek at the belief state.
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Protege")
    picked = st.selectbox("Topic", TOPIC_NAMES, index=TOPIC_NAMES.index(st.session_state.topic))
    if picked != st.session_state.topic:
        fresh_session(picked)
        st.rerun()

    if st.button("Start over", use_container_width=True):
        fresh_session(st.session_state.topic)
        st.rerun()

    st.divider()
    # Hidden by default: the user shouldn't watch the answer key while teaching.
    show_belief = st.toggle("Show what the student believes", value=False)
    if show_belief:
        b = st.session_state.belief
        st.write(f"**Corrected:** {b['corrected']}")
        st.write(f"**Confidence:** {b['confidence']}%")
        st.write(f"**Evidence:** {b['evidence'] or '_(nothing yet)_'}")


topic = st.session_state.topic
data = TOPICS[topic]

st.title("Teach your protege")
st.caption(f"Topic: **{topic}** — it holds a stubborn misconception. Teach it until it truly gets it.")

# Confidence progress bar, updated after each turn.
conf = st.session_state.belief["confidence"]
st.progress(conf / 100, text=f"Student confidence: {conf}%")


# ---------------------------------------------------------------------------
# Conversation.
# ---------------------------------------------------------------------------
# Kick off with the student's opening line if the chat is empty.
if not st.session_state.messages:
    opener = student.reply(topic, data["misconception"], [])
    st.session_state.messages.append({"role": "assistant", "content": opener})

for m in st.session_state.messages:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        st.write(m["content"])

if prompt := st.chat_input("Explain it to your student..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Student replies in character.
    with st.chat_message("assistant"):
        with st.spinner("The student is thinking..."):
            answer = student.reply(topic, data["misconception"], st.session_state.messages)
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Re-judge the belief state after every user message.
    with st.spinner("Checking what the student believes..."):
        st.session_state.belief = student.assess(
            topic, data["misconception"], st.session_state.messages
        )
    st.rerun()


# ---------------------------------------------------------------------------
# The quiz. Enabled any time. Student answers ALONE, then plain-Python grading.
# ---------------------------------------------------------------------------
st.divider()

def save_run(result):
    os.makedirs("runs", exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join("runs", f"{stamp}-{topic.replace(' ', '_')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "topic": topic,
                "transcript": st.session_state.messages,
                "final_belief_state": st.session_state.belief,
                "quiz_answers": result["answers"],
                "score": result["score"],
            },
            f,
            indent=2,
        )
    return path


if st.button("Give the quiz", type="primary", use_container_width=True):
    quiz = data["quiz"]
    with st.spinner("The student is taking the quiz alone..."):
        answers = student.take_quiz(
            topic, data["misconception"], st.session_state.belief, quiz
        )
    score = sum(1 for i, item in enumerate(quiz) if answers[i] == item["correct"])
    st.session_state.quiz_result = {"answers": answers, "score": score}
    saved = save_run(st.session_state.quiz_result)
    st.session_state.quiz_result["saved"] = saved

# Render the quiz result (survives reruns because it lives in session_state).
result = st.session_state.quiz_result
if result:
    quiz = data["quiz"]
    answers = result["answers"]
    score = result["score"]

    st.subheader(f"YOUR TEACHING SCORE: {score}/{len(quiz)}")

    for i, item in enumerate(quiz):
        chosen = answers[i]
        right = chosen == item["correct"]
        mark = "✅" if right else "❌"
        tag = " _(trap)_" if item.get("trap") else ""
        st.markdown(f"**{mark} Q{i + 1}. {item['q']}**{tag}")
        st.write(f"- Student answered: {item['options'][chosen]}")
        if not right:
            st.write(f"- Correct answer: {item['options'][item['correct']]}")

    # Debrief: which traps it got right, and WHAT the user said that worked.
    st.divider()
    traps = [i for i, item in enumerate(quiz) if item.get("trap")]
    traps_right = [i for i in traps if answers[i] == quiz[i]["correct"]]
    st.markdown("### Debrief")
    st.write(
        f"Trap questions passed: **{len(traps_right)}/{len(traps)}** "
        f"(these are the ones a student stuck on the misconception gets wrong)."
    )
    ev = st.session_state.belief["evidence"]
    st.write(f"What worked (from the judge): _{ev or 'the misconception was never corrected.'}_")
    st.caption(f"Session saved to `{result.get('saved', 'runs/')}`")
