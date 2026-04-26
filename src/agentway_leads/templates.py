from typing import Dict


def render_template(text: str, context: Dict[str, str]) -> str:
    rendered = text
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", value or "")
    return rendered
