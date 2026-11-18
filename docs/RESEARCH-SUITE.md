# Local research suite (experimental)

This is a **separate**, self-contained, synthetic demonstration module. It deliberately does not change the existing IDOR task queue, database, seals, or dashboard. Nothing in this module scans a live target, makes HTTP requests, queries DNS, or submits a bug bounty report.

```bash
~/bughunter-venv/bin/python -m integration.research_suite run idor
~/bughunter-venv/bin/python -m integration.research_suite run xss
~/bughunter-venv/bin/python -m integration.research_suite run ssrf
~/bughunter-venv/bin/python -m integration.research_suite run access
```

Each command prints a 16-character ID. The new run lives in `local_ai_data/research_suite/<id>/` with simulated evidence, a deterministic assessment, a clearly marked draft, a SHA-256 manifest and a separate human-review state. A SHA-256 manifest is **not** a digital signature: a party who can alter both files and manifest can forge an updated pair.

```bash
~/bughunter-venv/bin/python -m integration.research_suite check <id>
~/bughunter-venv/bin/python -m integration.research_suite submit <id> --reviewer 'Human Analyst' --note 'I checked the synthetic evidence'
~/bughunter-venv/bin/python -m integration.research_suite approve <id> --reviewer 'Human Analyst' --note 'Reviewed for lab-training use only'
```

`approve` means the **synthetic training report** has been reviewed; external submission stays disabled. The optional `--ollama` flag calls only `http://127.0.0.1:11434/api/chat` and saves the model text alongside the deterministic assessment. The free-text `--ai-claim` argument instead accepts a supplied model assertion. Neither method upgrades a synthetic exercise to a real-world finding. Neither the rule-based gate nor the mock scenarios prove a real vulnerability. Moving to external programs requires a separate scope/authorization policy, human oversight and live evidence collection; such capabilities are not included here.

This module uses Python standard library only. Run the tests with:

```bash
~/bughunter-venv/bin/python -m unittest discover -s tests -p 'test_research_suite.py' -v
```
