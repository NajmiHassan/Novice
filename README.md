# Novice

Teach an AI that plays a confused student. It holds a specific wrong belief
and argues from it. You have to teach it until it genuinely understands — then
it takes a quiz **alone**, and its score is **your teaching score**.

## Why this works: the protégé effect

People learn material better when they prepare to teach it to someone else.
Explaining forces you to find the gaps in your own understanding. Here the
"someone else" is an LLM roleplaying a stubborn learner, so you get the
teaching practice on demand.

## The one rule that keeps it honest

The **misconception** and the **quiz** are hardcoded in `topics.json`, written
in advance. The LLM never invents them and never grades itself — it only
*roleplays* the student. Grading is done in plain Python against a known answer
key. That's what makes the score objective: the app cannot hallucinate your
grade, and at least 3 of every topic's 5 questions are "trap" questions that a
student stuck on the misconception gets wrong.

The quiz is taken **without the conversation in context** — the student sees
only its current belief state, not the transcript. So it can't just parrot back
your words. If you never actually corrected its wrong model, it answers as a
believer and fails the traps. Real teaching is the only way to a high score.

## Files

- `topics.json` — misconceptions + quizzes (the measurement instrument)
- `llm.py` — the single Groq call
- `student.py` — the agent: `reply` (roleplay), `assess` (judge), `take_quiz` (alone)
- `app.py` — the Streamlit UI
- `runs/` — every finished session saved as JSON for later analysis

## Run it

```
pip install -r requirements.txt
cp .env.example .env      # then put your Groq API key in .env
streamlit run app.py
```

Get a free API key at https://console.groq.com. The app fails loudly if the
key is missing — there is no offline fallback and no fake data.
