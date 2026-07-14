"""The only place that talks to the LLM. One function: chat().

Model comes from GROQ_MODEL, key from GROQ_API_KEY, both loaded from a .env
file via python-dotenv. If the model returns nothing, we raise loudly rather
than hand back an empty string and pretend everything is fine.
"""

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def chat(system: str, messages: list, max_tokens: int) -> str:
    """Send a system prompt + message history to Groq and return the reply text.

    `messages` is a list of {"role": "user"|"assistant", "content": str}.
    Raises a clear error if the key is missing or the response is empty.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and put your "
            "Groq API key in it. This app has no offline fallback on purpose."
        )

    model = os.environ.get("GROQ_MODEL")
    if not model:
        raise RuntimeError("GROQ_MODEL is not set. See .env.example for a value.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content
    if not content or not content.strip():
        # Reasoning models can burn the whole budget on hidden thinking and
        # return empty visible content when max_tokens is too small.
        raise RuntimeError(
            f"Model '{model}' returned empty content. If it is a reasoning "
            f"model, raise max_tokens (currently {max_tokens}) or switch "
            "GROQ_MODEL to a non-reasoning model like llama-3.3-70b-versatile."
        )

    return content.strip()
