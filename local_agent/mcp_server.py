"""One shipped read-only stdio server. No HTTP, commands, roots or sampling authority."""
import argparse
import json
import sys
from pathlib import Path

# Source execution uses -I and an absolute trusted script, never project sys.path.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_agent.mcp_contract import SERVER_NAME, SERVER_VERSION, descriptor, read_text
from local_agent.safety import Policy


def main(argv=None):
    import anyio
    import mcp_types as types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args(argv)
    policy = Policy({"paths": {"workspace": args.root, "state": args.state}}, create=False)

    async def listing(ctx, params):
        return types.ListToolsResult(tools=[types.Tool(**descriptor())])

    async def calling(ctx, params):
        try:
            if (params.name != "read_text" or type(params.arguments) is not dict
                    or set(params.arguments) != {"path"}):
                raise ValueError("Unsupported request")
            result = read_text(policy, params.arguments["path"])
            return types.CallToolResult(content=[types.TextContent(
                type="text", text=json.dumps(result, ensure_ascii=False))])
        except Exception:  # noqa: BLE001 -- no raw exception or source text crosses the boundary
            return types.CallToolResult(isError=True, content=[types.TextContent(
                type="text", text="Project read refused or input changed.")])

    server = Server(SERVER_NAME, version=SERVER_VERSION, on_list_tools=listing, on_call_tool=calling)

    async def serve():
        async with stdio_server() as streams:
            await server.run(*streams, server.create_initialization_options())

    anyio.run(serve)


if __name__ == "__main__":
    main()
