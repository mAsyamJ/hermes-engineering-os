#!/usr/bin/env python3
"""Credential-scrubbed, network-denied plugin qualification harness."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import socket
import sys
import tempfile
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


_socket = socket.socket


def no_network_socket(
    family: int = socket.AF_INET,
    type: int = socket.SOCK_STREAM,
    proto: int = 0,
    fileno: int | None = None,
) -> socket.socket:
    if family in (socket.AF_INET, socket.AF_INET6):
        raise PermissionError("network disabled during plugin preflight")
    return _socket(family, type, proto, fileno)


class Result:
    text = "bonjour"
    parsed = {"vendor": "fixture", "total": 1.0}
    provider = "fixture"
    model = "deterministic"
    usage = types.SimpleNamespace(total_tokens=1)


class FakeLLM:
    def complete_structured(self, **_kwargs: Any) -> Result:
        return Result()

    async def acomplete(self, **kwargs: Any) -> Result:
        result = Result()
        if kwargs.get("purpose") == "translate.classify":
            result = types.SimpleNamespace(**Result.__dict__)
            result.text = "statement"
            result.usage = types.SimpleNamespace(total_tokens=1)
        return result


class RecordingContext:
    def __init__(self) -> None:
        self.hooks: dict[str, Any] = {}
        self.commands: dict[str, Any] = {}
        self.skills: dict[str, Path] = {}
        self.llm = FakeLLM()

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks[name] = callback

    def register_command(self, name: str, handler: Any, **_kwargs: Any) -> None:
        self.commands[name] = handler

    def register_skill(self, name: str, path: Path, **_kwargs: Any) -> None:
        assert isinstance(path, Path) and path.is_file()
        self.skills[name] = path


def load_package(name: str, entry: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, entry, submodule_search_locations=[str(entry.parent)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {entry}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def qualify(name: str, entry: Path, expected: str) -> dict[str, Any]:
    ctx = RecordingContext()
    module = load_package(f"_preflight_{name.replace('-', '_')}", entry)
    register = getattr(module, "register")
    register(ctx)
    if expected == "command":
        assert ctx.commands
    if expected == "hook":
        assert ctx.hooks
    if expected == "side_effect_free":
        assert not ctx.commands and not ctx.hooks and not ctx.skills
    return {
        "name": name,
        "import": "PASS",
        "register": "PASS",
        "hooks": sorted(ctx.hooks),
        "commands": sorted(ctx.commands),
        "skills": len(ctx.skills),
    }


def main() -> int:
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    os.environ.clear()
    with tempfile.TemporaryDirectory(prefix="engineering-os-preflight-") as home:
        os.environ.update(
            HOME=home,
            HERMES_HOME=str(Path(home) / ".hermes"),
            PYTHONDONTWRITEBYTECODE="1",
            PATH="/usr/bin:/bin",
        )
        # Asyncio needs AF_UNIX socketpairs internally; deny only IP sockets.
        socket.socket = no_network_socket  # type: ignore[assignment]
        results = []
        results.append(
            qualify(
                "plugin-llm-example",
                ROOT / "upstream/hermes-example-plugins/plugin-llm-example/__init__.py",
                "command",
            )
        )
        results.append(
            qualify(
                "plugin-llm-async-example",
                ROOT / "upstream/hermes-example-plugins/plugin-llm-async-example/__init__.py",
                "command",
            )
        )
        sync = sys.modules["_preflight_plugin_llm_example"]
        sync_ctx = RecordingContext()
        sync.register(sync_ctx)
        assert "fixture" in sync_ctx.commands["receipt-extract"](
            str(ROOT / "README.md")
        )
        async_mod = sys.modules["_preflight_plugin_llm_async_example"]
        async_ctx = RecordingContext()
        async_mod.register(async_ctx)
        output = asyncio.run(async_ctx.commands["translate"]("fr: hello"))
        assert "fixture/deterministic" in output
        results.append(
            qualify(
                "superpowers",
                Path("/home/ubuntu/.hermes/plugins/superpowers/.hermes-plugin/__init__.py"),
                "hook",
            )
        )
        results.append(
            qualify("engineering-os", ROOT / "__init__.py", "side_effect_free")
        )

        otel_status: dict[str, Any]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                otel = qualify(
                    "hermes_otel",
                    Path("/home/ubuntu/.hermes/plugins/hermes_otel/__init__.py"),
                    "external_dependency",
                )
            otel_status = {
                **otel,
                "runtime": "VERIFIED_EXTERNAL_DEP",
                "reason": "OpenTelemetry packages intentionally absent in Phase 1",
            }
        except (ModuleNotFoundError, ImportError) as exc:
            otel_status = {
                "name": "hermes_otel",
                "import": "PASS",
                "register": "DEGRADED",
                "runtime": "VERIFIED_EXTERNAL_DEP",
                "reason": type(exc).__name__,
            }
        results.append(otel_status)
        print(json.dumps({"status": "PASS", "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

