"""To-be steps -> Mermaid flowchart. Built by code, not by the AI, so it always parses."""
import re

from .flowchart import clean_steps, is_decision


def _label(text: str) -> str:
    text = text.rstrip(".")
    return text.replace('"', "'").replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")


def mermaid_from_steps(steps: list[str]) -> str:
    """Text version of the flow (kept in the register and the Markdown export; the website and Word
    show the box-to-box picture from flowchart.py). Steps that start with 'If' become decision diamonds
    (the next step is the 'Yes' branch). Returns '' when there are no steps."""
    steps = clean_steps(steps)
    if not steps:
        return ""
    lines = ["flowchart TD", "    START([Start])"]
    prev, edge_label = "START", ""
    for n, step in enumerate(steps, 1):
        node = f"N{n}"
        lines.append(f'    {node}{{"{_label(step)}"}}' if is_decision(step) else f'    {node}["{_label(step)}"]')
        lines.append(f"    {prev} -->{f'|{edge_label}|' if edge_label else ''} {node}")
        prev, edge_label = node, ("Yes" if is_decision(step) else "")
    lines += ["    END([End])", f"    {prev} -->{f'|{edge_label}|' if edge_label else ''} END"]
    return "\n".join(lines)
