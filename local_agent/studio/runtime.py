import argparse
import asyncio
import json
import multiprocessing
import os
import socket
import sys
import threading
import time
from pathlib import Path

from local_agent.config import load
from local_agent.safety import redact


def create_server_loop():
    # The local ASGI process owns TCP only. Windows Proactor socket shutdown can
    # raise 10054 after a peer reset, before closing/detaching the transport.
    # Workers are fresh processes and retain their default subprocess-capable loop.
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    return loop


def run_server(server, listener):
    if os.name != "nt":
        return server.run(sockets=[listener])
    try:
        with asyncio.Runner(loop_factory=create_server_loop) as runner:
            return runner.run(server.serve(sockets=[listener]))
    finally:
        asyncio.set_event_loop(None)


def main():
    if sys.argv[1:2] == ["--mcp-project-server"]:
        from local_agent.mcp_server import main as project_server
        project_server(sys.argv[2:])
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--port", type=int, default=17861)
    args = parser.parse_args()
    try:
        import uvicorn

        from local_agent.studio.api import create_app
    except ImportError as exc:
        print(json.dumps({"error": f"Missing desktop backend dependency: {exc.name}. Run setup-desktop.ps1."}), flush=True)
        return 1
    credential = os.environ.pop("LOCAL_AGENT_STUDIO_TOKEN", "")
    if len(credential) < 32:
        print(json.dumps({"error": "Missing launch credential; use the desktop launcher."}), flush=True)
        return 1
    try:
        config = load(args.config)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": "Cannot load configuration: " + redact(str(exc))}), flush=True)
        return 1
    browsers = Path(config["base"]) / ".runtime/browsers"
    if browsers.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
    listener = socket.socket()
    if os.name == "nt":
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        listener.bind(("127.0.0.1", args.port))
        listener.listen(128)
    except OSError:
        print(json.dumps({"error": f"Port {args.port} is occupied. Another backend may already be running."}), flush=True)
        listener.close()
        return 1
    try:
        app = create_app(config, credential)
    except Exception as exc:  # noqa: BLE001 -- structured startup failure for the desktop
        listener.close()
        print(json.dumps({"error": "Backend initialization failed: " + redact(str(exc))}), flush=True)
        return 1
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False,
                                          ws_max_size=32768, timeout_graceful_shutdown=5))

    def parent_watch():
        # Rust owns stdin. EOF on GUI exit also closes tasks via FastAPI lifespan.
        if os.name == "nt":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            # A blocking read on the inherited Windows pipe can stall a spawned
            # Python interpreter while it initializes its standard streams.
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            api.PeekNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                         ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            api.PeekNamedPipe.restype = wintypes.BOOL
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            while not server.should_exit:
                available = wintypes.DWORD()
                if not api.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None):
                    break  # Parent closed its pipe.
                if available.value:
                    break  # Parent sent the shutdown request; no blocking read needed.
                time.sleep(0.1)
        else:
            sys.stdin.readline()
        server.should_exit = True

    threading.Thread(target=parent_watch, daemon=True).start()
    print(json.dumps({"port": listener.getsockname()[1]}), flush=True)
    try:
        run_server(server, listener)
    finally:
        app.state.manager.close(shutdown=True)
        if not app.state.manager.running:
            app.state.state_owner.close()
        listener.close()
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
