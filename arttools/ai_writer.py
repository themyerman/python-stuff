"""Generate artist descriptions using Claude."""
import os
import anthropic

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        _CLIENT = anthropic.Anthropic(api_key=key)
    return _CLIENT


def generate_description(title: str, prompt: str, size: str) -> tuple[str, list[str]]:
    """
    Returns (description_paragraph, tags_list).
    prompt is a short artist note — e.g. 'swirling earth tones, movement and transformation'
    """
    system = (
        "You are writing artist statements for Tom Myer, a Hodinǫ̱hsǫ́:nih and Ngäbe-Buglé "
        "Indigenous digital artist based in Colorado. His work spans wildlife, futurism, "
        "Indigenous culture, and political art. His voice is direct, personal, and grounded "
        "— never pretentious. Statements are 2-4 sentences, written in first person, and feel "
        "like something he'd actually say out loud."
    )

    desc_prompt = (
        f'Write an artist statement for a print titled "{title}" ({size} inches). '
        f"Artist's notes: {prompt}\n\n"
        "Output ONLY the statement — no title, no label, no quotes."
    )

    tags_prompt = (
        f'Generate 6-10 search tags for a digital art print titled "{title}". '
        f"Artist's notes: {prompt}\n\n"
        "Output ONLY a JSON array of lowercase single-word or hyphenated tags. "
        'Example: ["crow","wildlife","colorado","portrait"]'
    )

    desc_msg = _client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": desc_prompt}],
    )
    description = desc_msg.content[0].text.strip()

    tags_msg = _client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": tags_prompt}],
    )

    import json
    try:
        raw = tags_msg.content[0].text.strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        tags = json.loads(raw)
    except Exception:
        tags = [w.strip().lower() for w in prompt.replace(",", " ").split() if len(w) > 2]

    return description, tags
