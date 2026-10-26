"""To-be steps -> Mermaid flowchart. Built by code, not by the AI, so it always parses."""
import re

MAX_NODES = 30


def _label(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    text = text.replace('"', "'").replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    return text if len(text) <= 70 else text[:67].rstrip() + "..."


def mermaid_from_steps(steps: list[str]) -> str:
    """Linear flow top to bottom. Steps that start with 'If' become decision diamonds
    (the next step is the 'Yes' branch). Returns '' when there are no steps."""
    steps = [s for s in steps if s.strip()][:MAX_NODES]
    if not steps:
        return ""
    lines = ["flowchart TD", "    START([Start])"]
    prev, edge_label = "START", ""
    for n, step in enumerate(steps, 1):
        node = f"N{n}"
        is_decision = bool(re.match(r"^\s*(if|when|where)\b", step, re.I))
        lines.append(f'    {node}{{"{_label(step)}"}}' if is_decision else f'    {node}["{_label(step)}"]')
        lines.append(f"    {prev} -->{f'|{edge_label}|' if edge_label else ''} {node}")
        prev, edge_label = node, ("Yes" if is_decision else "")
    lines += ["    END([End])", f"    {prev} -->{f'|{edge_label}|' if edge_label else ''} END"]
    return "\n".join(lines)
