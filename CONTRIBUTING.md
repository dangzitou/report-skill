# Contributing

Thanks for helping! report-skill aims to stay **small, dependency-free and private by default**.

## Dev setup

```bash
git clone https://github.com/dangzitou/report-skill && cd report-skill
python3 -m unittest discover -s tests -t .   # tests (stdlib only)
python3 -m report_skill --raw                # run from source
python3 -m report_skill week --prompt        # inspect exactly what the AI receives
```

## Layout

```
report_skill/
  collectors/        one module per source; each returns Session / Commit objects
  summarize.py       groups everything by project, estimates time
  render.py          offline Markdown draft
  ai.py              prompt + running claude / codex
  skill/             SKILL.md + writing guides (installed into agents)
tests/
```

## Adding a source

1. Create `report_skill/collectors/<tool>.py` with `collect(start, end, root=None) -> List[Session]`.
2. Read **only** what the human typed and which files were edited; filter agent-injected text.
3. Never write to the tool's data; open SQLite read-only.
4. Register it in `collectors/__init__.py`, add a fixture-based test, and add a row to both READMEs.

## Ground rules

- No runtime dependencies. Python 3.9 compatible.
- Never put real chat logs or reports in issues, tests or examples; use synthetic data.
- Changes to the writing guide should land in both `guide.zh.md` and `guide.en.md`.
