"""Week 1 command line: python -m reqdoc.cli <transcript> --code PRJ-0421 --name "Site Diary App" --title "Kickoff" """
import argparse
import re
import sys
from datetime import date
from pathlib import Path

from .llm import LLMError, OllamaClient
from .parsers import parse_transcript
from .pipeline import generate_register
from .render import render_markdown


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Transcript -> requirement document (Markdown)")
    ap.add_argument("transcript", help=".vtt, .docx or .txt file")
    ap.add_argument("--code", required=True, help="project code, e.g. PRJ-0421")
    ap.add_argument("--name", default="", help="project name")
    ap.add_argument("--title", default="Requirements meeting", help="meeting title")
    ap.add_argument("--date", default=date.today().isoformat(), help="meeting date YYYY-MM-DD")
    ap.add_argument("--out", default="output", help="output folder")
    ap.add_argument("--model", default=None, help="Ollama model (default: OLLAMA_MODEL in .env)")
    args = ap.parse_args(argv)

    segments = parse_transcript(args.transcript)
    print(f"Parsed {len(segments)} segments from {Path(args.transcript).name}")
    llm = OllamaClient(model=args.model)
    try:
        register = generate_register(
            segments, llm, args.code, args.name, args.title, args.date,
            progress=lambda msg, frac: print(f"  [{frac:>4.0%}] {msg}"),
        )
    except LLMError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    slug = re.sub(r"[^A-Za-z0-9]+", "-", args.title).strip("-")
    stem = f"{args.date}_{args.code}_{slug}_v{register.version}_DRAFT"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stem}.md").write_text(render_markdown(register), encoding="utf-8")
    (out / f"{stem}.register.json").write_text(register.model_dump_json(indent=2), encoding="utf-8")
    flagged = sum(1 for r in register.requirements if r.needs_confirmation)
    print(f"Wrote {out / (stem + '.md')}")
    print(f"{len(register.requirements)} requirements ({flagged} to confirm), "
          f"{len(register.decisions)} decisions, {len(register.actions)} actions, {len(register.questions)} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
