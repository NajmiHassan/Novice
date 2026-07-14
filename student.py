"""The AI novice. Three jobs, three functions, nothing else.

  reply()      -> roleplays a confused student who argues from a fixed
                  misconception and only lets go of it for a real reason.
  assess()     -> a SEPARATE, non-roleplay judge that reads the transcript
                  and reports whether the misconception has been corrected.
                  This is the student's belief state.
  take_quiz()  -> the student answers the fixed quiz ALONE, seeing only its
                  belief state, never the conversation. If it was never
                  taught, it must answer as a believer and fail the traps.

The misconception and the quiz live in topics.json. This file never invents
them and never grades anything.
"""

import json

from llm import chat


def _extract_json(text: str):
    """Pull the first JSON object/array out of a model reply.

    Models sometimes wrap JSON in prose or ```json fences. We grab the span
    between the first opening and last matching closing bracket and parse it.
    """
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from model reply:\n{text}")


def reply(topic: str, misconception: str, history: list) -> str:
    """The student's next line in the conversation. 2-4 sentences, in character."""
    system = (
        f"You are a curious, slightly stubborn student trying to learn about "
        f"'{topic}'. You secretly hold this exact mental model, in your own words:\n"
        f'"{misconception}"\n\n'
        "Rules for staying in character:\n"
        "- Reason OUT LOUD from your mental model. Think through the tutor's "
        "explanation and check whether it fits what you already believe.\n"
        "- Ask the tutor questions. Push back when their explanation clashes "
        "with your model.\n"
        "- Do NOT suddenly 'get it' just because the tutor asserts something or "
        "sounds confident. You only update your belief when they give a concrete "
        "reason or a specific example that actually breaks your wrong model. If "
        "they give one, you may genuinely start to understand.\n"
        "- Never mention that you hold a misconception. Never say you are "
        "roleplaying or being a 'confused student'. Never break character.\n"
        "- Keep it to 2-4 sentences. Talk like a real learner, not a textbook."
    )
    return chat(system, history, max_tokens=400)


def assess(topic: str, misconception: str, history: list) -> dict:
    """Judge (NOT roleplay) whether the misconception has been corrected yet.

    Returns {"corrected": bool, "confidence": 0-100, "evidence": str}.
    Runs after every user message; this is the student's belief state.
    """
    transcript = "\n".join(
        f"{'TUTOR' if m['role'] == 'user' else 'STUDENT'}: {m['content']}"
        for m in history
    )
    system = (
        "You are a strict, impartial judge grading a teaching transcript. You are "
        "NOT the student and you do NOT roleplay. Your only job is to decide "
        "whether the tutor has actually corrected the student's misconception.\n\n"
        f"Topic: {topic}\n"
        f'The misconception being taught against: "{misconception}"\n\n'
        "The misconception counts as CORRECTED only if the tutor gave a concrete "
        "reason or specific example that genuinely breaks that wrong model — not "
        "just an assertion, and not the student politely agreeing. Be conservative: "
        "if in doubt, it is not corrected.\n\n"
        "Reply with ONLY a JSON object, no other text:\n"
        '{"corrected": true or false, "confidence": integer 0-100, '
        '"evidence": "the exact thing the tutor said that fixed it, or what is '
        'still missing"}'
    )
    messages = [{"role": "user", "content": f"TRANSCRIPT:\n{transcript}"}]
    raw = chat(system, messages, max_tokens=400)
    data = _extract_json(raw)
    # Normalize so the UI can trust the shape.
    return {
        "corrected": bool(data.get("corrected", False)),
        "confidence": int(data.get("confidence", 0)),
        "evidence": str(data.get("evidence", "")),
    }


def take_quiz(topic: str, misconception: str, belief_state: dict, quiz: list) -> list:
    """The student answers the fixed quiz ALONE and returns chosen indices.

    The conversation is deliberately NOT in context here — only the belief
    state. If the misconception was never corrected, the student must answer
    as someone who STILL believes it, getting the trap questions wrong. It is
    explicitly not allowed to be secretly competent.
    """
    corrected = belief_state.get("corrected", False)

    if corrected:
        stance = (
            "You were successfully taught and NOW UNDERSTAND this topic correctly. "
            "Answer to the best of your genuine, corrected understanding."
        )
    else:
        stance = (
            "You were NOT successfully taught. You STILL fully believe your "
            "misconception below. Answer every question AS A STUDENT WHO STILL "
            "BELIEVES IT — reason from the misconception, which means you WILL get "
            "the trap questions wrong. You are NOT allowed to secretly know the "
            "right answers or quietly correct yourself. Stay true to the wrong "
            "model.\n"
            f'Your misconception: "{misconception}"'
        )

    # Build a clean, numbered quiz. No 'correct' field is ever shown to the model.
    lines = []
    for i, item in enumerate(quiz):
        opts = "; ".join(f"{j}) {opt}" for j, opt in enumerate(item["options"]))
        lines.append(f"Q{i} ({item['q']}) -> {opts}")
    quiz_text = "\n".join(lines)

    system = (
        f"You are a student taking a multiple-choice quiz on '{topic}', ALONE. "
        "There is no tutor here and no conversation to look back on.\n\n"
        f"{stance}\n\n"
        "Reply with ONLY a JSON array of integers: the index of your chosen "
        "option for each question, in order. Example for 5 questions: [1,0,2,1,1]. "
        "No explanations, no other text."
    )
    messages = [{"role": "user", "content": f"QUIZ:\n{quiz_text}"}]
    raw = chat(system, messages, max_tokens=200)
    answers = _extract_json(raw)

    # Coerce to a clean list of valid indices, one per question.
    result = []
    for i, item in enumerate(quiz):
        n_opts = len(item["options"])
        try:
            choice = int(answers[i])
        except (IndexError, ValueError, TypeError):
            choice = 0
        if not 0 <= choice < n_opts:
            choice = 0
        result.append(choice)
    return result
