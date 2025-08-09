#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, argparse
from typing import Any, Dict
from rich import print
from dotenv import load_dotenv
import anthropic
from providers import openai_spec, openai_review, aclient, ANTHROPIC_MODEL
from tools import read_file, write_file, bash, git_diff, git_apply, repo_root
from prompts import IMPLEMENT_SYSTEM_PROMPT

load_dotenv()

def cmd_spec(args):
    if not args.prompt:
        print("[red]Provide a prompt after 'spec'[/red]"); sys.exit(1)
    spec = openai_spec(args.prompt)
    (repo_root() / "aidev_spec.json").write_text(json.dumps(spec, indent=2))
    print("[green]Spec saved to aidev_spec.json[/green]")
    print(json.dumps(spec, indent=2))

def _tool_execute(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if name == "read_file":  return read_file(payload["path"])
    if name == "write_file": return write_file(payload["path"], payload["content"])
    if name == "bash":       return bash(payload["command"], timeout=int(payload.get("timeout",90)))
    if name == "git_diff":   return git_diff()
    if name == "git_apply":  return git_apply(payload["patch"])
    return {"ok": False, "error": f"unknown tool {name}"}

TOOLS_SCHEMA = [
    {"name":"read_file","description":"Read a file within the repo","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"write_file","description":"Write a file within the repo","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
    {"name":"bash","description":"Run allowed shell commands with timeout","input_schema":{"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"number"}},"required":["command"]}},
    {"name":"git_diff","description":"Show git diff of working tree","input_schema":{"type":"object","properties":{}} },
    {"name":"git_apply","description":"Stage a unified diff patch","input_schema":{"type":"object","properties":{"patch":{"type":"string"}},"required":["patch"]}},
]

def cmd_implement(args):
    spec_path = repo_root() / "aidev_spec.json"
    if not spec_path.exists():
        print("[red]aidev_spec.json not found. Run 'spec' first.[/red]"); sys.exit(1)
    spec = json.loads(spec_path.read_text())
    system_prompt = IMPLEMENT_SYSTEM_PROMPT + "\n\nSPEC:\n" + json.dumps(spec, indent=2)

    # Initial request to Claude
    msg = aclient.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        system=system_prompt,
        tools=TOOLS_SCHEMA,
        messages=[{"role":"user","content":"Begin implementing. Ask for tools as needed. Stop when done_criteria are met and return git_diff."}],
    )

    # Tool loop
    while True:
        last = msg.content[-1]
        if last.type == "tool_use":
            result = _tool_execute(last.name, last.input)
            msg = aclient.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1500,
                system=system_prompt,
                tools=TOOLS_SCHEMA,
                messages=[*msg.messages, {"role":"tool","tool_use_id": last.id, "content": json.dumps(result)}],
            )
            continue
        print("[cyan]Claude output:[/cyan]")
        for block in msg.content:
            if block.type == "text":
                print(block.text)
        break

def cmd_review(args):
    spec_path = repo_root() / "aidev_spec.json"
    if not spec_path.exists():
        print("[red]aidev_spec.json not found. Run 'spec' first.[/red]"); sys.exit(1)
    spec = json.loads(spec_path.read_text())
    diff = git_diff()
    if not diff.get("ok"): print(diff); sys.exit(1)
    report = openai_review(diff["diff"], spec)
    (repo_root() / "aidev_review.json").write_text(json.dumps(report, indent=2))
    print("[green]Review saved to aidev_review.json[/green]")
    print(json.dumps(report, indent=2))

def cmd_patch(args):
    d = git_diff()
    if not d.get("ok"): print(d); sys.exit(1)
    diff_text = d["diff"]
    if not diff_text.strip():
        print("[yellow]No changes to stage.[/yellow]"); return
    if args.apply:
        ok = git_apply(diff_text)
        if ok.get("ok"):
            print("[green]Patch staged. Run `git commit -m \"aidev changes\"`[/green]")
        else:
            print(ok)
    else:
        print(diff_text)

def main():
    ap = argparse.ArgumentParser(prog="aidev", description="GPT-5 × Claude Code terminal orchestrator")
    sp = ap.add_subparsers(dest="cmd")

    p1 = sp.add_parser("spec", help="Create spec from plain English"); p1.add_argument("prompt", nargs='?', default=None); p1.set_defaults(func=cmd_spec)
    sp.add_parser("implement", help="Implement with Claude Code").set_defaults(func=cmd_implement)
    sp.add_parser("review", help="Review with GPT-5").set_defaults(func=cmd_review)
    p4 = sp.add_parser("patch", help="Show/apply git diff"); p4.add_argument("--apply", action="store_true"); p4.set_defaults(func=cmd_patch)

    args = ap.parse_args()
    if not args.cmd: ap.print_help(); sys.exit(0)
    args.func(args)

if __name__ == "__main__":
    main()
