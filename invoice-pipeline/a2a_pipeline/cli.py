"""CLI for the A2A invoice pipeline.

Subcommands:
  start        Run the single-process A2A server with all 5 agents mounted.
  run          Drive the 5-agent chain over A2A against a running server.
  agentkit-run Run one agent as an AgentKit conversational app (mock=False).
"""

from __future__ import annotations

import argparse
import json
import logging

import uvicorn

from a2a_pipeline.server import build_server
from a2a_pipeline.drive_chain import A2aDriveChain

logger = logging.getLogger(__name__)


def cmd_start(args: argparse.Namespace) -> None:
    app = build_server(mock=args.mock, host=args.host, port=args.port)
    print(f"A2A invoice pipeline server listening on http://{args.host}:{args.port}")
    print("Agents: /ocr /translation /validation /aggregation /approval")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_run(args: argparse.Namespace) -> None:
    chain = A2aDriveChain(base_url=args.base_url)
    if args.mode == "single":
        result = chain.run_single(args.invoice, image_key=args.image)
    else:
        result = chain.run_batch(args.invoices)
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


def cmd_agentkit_run(args: argparse.Namespace) -> None:
    from agentkit_app import build_app

    app = build_app(args.agent)
    print(f"AgentKit app for {args.agent} on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_mcp_run(args: argparse.Namespace) -> None:
    from a2a_pipeline.mcp_server import FormattingMCPApp

    app = FormattingMCPApp(mock=args.mock)
    print(f"Formatting MCP server (mock={args.mock}) on http://{args.host}:{args.port}/mcp")
    app.run(host=args.host, port=args.port)

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="a2a", description="Invoice pipeline over A2A")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Run the single-process A2A server")
    start.add_argument("--host", default="0.0.0.0")
    start.add_argument("--port", type=int, default=9901)
    start.add_argument("--no-mock", action="store_false", dest="mock", default=True,
                       help="Call real ModelArk models instead of mock data")
    start.set_defaults(func=cmd_start)

    run = sub.add_parser("run", help="Drive the chain over A2A against a running server")
    run.add_argument("--base-url", default="http://127.0.0.1:9901")
    run.add_argument("--mode", choices=["single", "batch"], default="single")
    run.add_argument("--invoice", default="default")
    run.add_argument("--invoices", nargs="+", default=["default", "invoice2", "invoice3"])
    run.add_argument("--image", default=None, help="Real invoice image path (single mode)")
    run.add_argument("--pretty", action="store_true", default=True)
    run.add_argument("--no-pretty", dest="pretty", action="store_false")
    run.set_defaults(func=cmd_run)

    agentkit = sub.add_parser("agentkit-run", help="Run one agent as an AgentKit app")
    agentkit.add_argument("--agent", choices=[
        "ocr_agent", "translation_agent", "validation_agent",
        "aggregation_agent", "formatting_agent", "approval_agent",
    ], default="ocr_agent")
    agentkit.add_argument("--host", default="0.0.0.0")
    agentkit.add_argument("--port", type=int, default=8080)
    agentkit.set_defaults(func=cmd_agentkit_run)

    mcp = sub.add_parser("mcp-run", help="Serve the Seedream formatting agent as an MCP server")
    mcp.add_argument("--host", default="0.0.0.0")
    mcp.add_argument("--port", type=int, default=8001)
    mcp.add_argument("--no-mock", action="store_false", dest="mock", default=True,
                     help="Call real Seedream instead of mock placeholder")
    mcp.set_defaults(func=cmd_mcp_run)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    args.func(args)


if __name__ == "__main__":
    main()
