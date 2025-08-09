from __future__ import annotations
import os, json
from typing import Any, Dict
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

if not OPENAI_API_KEY:
    raise SystemExit("❌ Missing OPENAI_API_KEY in .env file. Copy .env.template to .env and add your API keys.")
if not ANTHROPIC_API_KEY:
    raise SystemExit("❌ Missing ANTHROPIC_API_KEY in .env file. Copy .env.template to .env and add your API keys.")

oai = OpenAI(api_key=OPENAI_API_KEY)
aclient = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def openai_spec(prompt: str) -> Dict[str, Any]:
    from prompts import SPEC_PROMPT
    msg = oai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"system","content":SPEC_PROMPT},
                  {"role":"user","content":prompt}],
        response_format={"type":"json_object"},
        temperature=0.2,
    )
    return json.loads(msg.choices[0].message.content)

def openai_review(diff_text: str, spec_json: Dict[str, Any]) -> Dict[str, Any]:
    from prompts import REVIEW_PROMPT
    msg = oai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role":"system","content":REVIEW_PROMPT},
            {"role":"user","content":f"SPEC JSON:\n```json\n{json.dumps(spec_json, indent=2)}\n```\n\nDIFF:\n```diff\n{diff_text}\n```"}
        ],
        response_format={"type":"json_object"},
        temperature=0.2,
    )
    return json.loads(msg.choices[0].message.content)
