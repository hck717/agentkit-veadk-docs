"""veadk-studio-local patch (idempotent, reversible).

Two independent hunks, each with its own marker so they apply/revert
separately.

--- veadk-studio-local-storage -------------------------------------------
Makes the Studio 环境 / 工作区 / 产物 tabs work without TOS object storage.

Those tabs are served by three modules that persist their state through a
duck-typed TOS client injected via `create_tos_client_factory`:

    frontend/server/environments/   (create_environment_service)
    frontend/server/workspaces/     (create_workspace_service)
    frontend/server/artifacts/      (create_service)

When `VEADK_STUDIO_TOS_BUCKET` / `VEADK_STUDIO_TOS_REGION` are absent, Studio
returns HTTP 503 (管理员未配置持久化存储). This patch adds a filesystem-backed
client and routes the TOS factory to it when `VEADK_STUDIO_LOCAL_STORAGE` is on,
so all three tabs read/write under a local directory instead.

--- veadk-studio-local-openviking ----------------------------------------
Lets Studio's 调试/试运行 runner reach a self-hosted OpenViking.

`_safe_runner_env()` hands the debug subprocess a whitelisted environment that
covers model and Volcengine/BytePlus credentials but omits `DATABASE_OPENVIKING_*`.
The runner executes the generated project from a temp dir with no `.env`, so
`LongTermMemory(backend="openviking")` aborts at import:

    ValidationError: OpenViking URL is required.
    Set DATABASE_OPENVIKING_URL or pass url.

This patch forwards the OpenViking settings to the runner.

Apply:    python3 studio_local_storage_patch.py apply   [<cli_frontend.py path>]
Revert:   python3 studio_local_storage_patch.py revert  [<cli_frontend.py path>]
Default target is this project's venv. Backups: *.localstorage.bak
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

MARKER = "veadk-studio-local-storage"
RUNNER_ENV_MARKER = "veadk-studio-local-openviking"

DEFAULT_TARGET = Path(
    "/Users/brianho/agentkit-veadk-docs/projects/brian_assistant/.venv"
    "/lib/python3.11/site-packages/veadk/cli/cli_frontend.py"
)

# --------------------------------------------------------------------------
# frontend/server/storage/local_fs.py  (new file)
# --------------------------------------------------------------------------
LOCAL_FS_SOURCE = '''\
"""Filesystem-backed stand-in for the Studio TOS client.

See `studio_local_storage_patch.py` in the project root. Enabled by
`VEADK_STUDIO_LOCAL_STORAGE=1`; objects live under
`VEADK_STUDIO_LOCAL_STORAGE_DIR` (default `<cwd>/.veadk-studio-storage`).

Implements only the surface the Studio repositories actually call:
list_objects_type2 / get_object / put_object / delete_object / pre_signed_url.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote

DEFAULT_ROOT = ".veadk-studio-storage"


class LocalStorageError(RuntimeError):
    """Carries an HTTP-ish status code the repositories inspect."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def resolve_local_storage_root() -> Path:
    raw = (os.environ.get("VEADK_STUDIO_LOCAL_STORAGE_DIR") or "").strip()
    root = Path(raw).expanduser() if raw else Path.cwd() / DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._data[self._offset :]
            self._offset = len(self._data)
            return chunk
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        self._offset = len(self._data)

    def __iter__(self):
        while True:
            chunk = self.read(64 * 1024)
            if not chunk:
                return
            yield chunk


class _Object:
    __slots__ = ("key",)

    def __init__(self, key: str) -> None:
        self.key = key


class _Listing:
    def __init__(self, keys: list[str]) -> None:
        self.contents = [_Object(key) for key in keys]
        self.is_truncated = False
        self.next_continuation_token = ""


class _SignedUrl:
    def __init__(self, url: str) -> None:
        self.signed_url = url


class LocalFsTosClient:
    """Minimal TOS-compatible client backed by a local directory tree."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._lock = Lock()

    def _base(self, bucket: str) -> Path:
        name = (bucket or "").strip() or "local-fs"
        return self._root / quote(name, safe="")

    def _path(self, bucket: str, key: str) -> Path:
        parts = [part for part in str(key).split("/") if part not in ("", ".", "..")]
        if not parts:
            raise LocalStorageError(400, "empty object key")
        return self._base(bucket).joinpath(*parts)

    def list_objects_type2(
        self,
        bucket: str,
        prefix: str = "",
        continuation_token: str = "",
        max_keys: int = 1000,
        **_kwargs: Any,
    ) -> _Listing:
        base = self._base(bucket)
        keys: list[str] = []
        if base.exists():
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(base).as_posix()
                if relative.startswith(prefix):
                    keys.append(relative)
        keys.sort()
        try:
            limit = max(1, int(max_keys or 1000))
        except (TypeError, ValueError):
            limit = 1000
        return _Listing(keys[:limit])

    def get_object(self, bucket: str, key: str, **_kwargs: Any) -> _Body:
        path = self._path(bucket, key)
        if not path.is_file():
            raise LocalStorageError(404, f"object not found: {key}")
        return _Body(path.read_bytes())

    def put_object(
        self,
        bucket: str,
        key: str,
        content: Any,
        content_length: int | None = None,
        content_type: str | None = None,
        forbid_overwrite: bool = False,
        **_kwargs: Any,
    ) -> None:
        path = self._path(bucket, key)
        data = content.read() if hasattr(content, "read") else content
        if isinstance(data, bytearray):
            data = bytes(data)
        if not isinstance(data, bytes):
            raise LocalStorageError(400, "unsupported object body")
        with self._lock:
            if forbid_overwrite and path.exists():
                raise LocalStorageError(412, f"object already exists: {key}")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)

    def delete_object(self, bucket: str, key: str, **_kwargs: Any) -> None:
        path = self._path(bucket, key)
        if path.is_file():
            path.unlink()

    def pre_signed_url(
        self,
        method: Any,
        bucket: str,
        key: str,
        expires: int = 900,
        **_kwargs: Any,
    ) -> _SignedUrl:
        return _SignedUrl(self._path(bucket, key).as_uri())


def create_local_client_factory(bucket: str = "") -> Any:
    """Return a zero-arg factory matching the Studio client_factory contract."""

    _ = bucket
    root = resolve_local_storage_root()
    return lambda: LocalFsTosClient(root)


__all__ = [
    "DEFAULT_ROOT",
    "LocalFsTosClient",
    "LocalStorageError",
    "create_local_client_factory",
    "resolve_local_storage_root",
]
'''

# --------------------------------------------------------------------------
# frontend/server/storage/__init__.py
# --------------------------------------------------------------------------
STORAGE_HELPER = '''\
def studio_local_storage_enabled(
    source: Mapping[str, str] | None = None,
) -> bool:
    """Return whether Studio should persist to the local filesystem.

    === veadk-studio-local-storage ===
    """
    environment = source if source is not None else os.environ
    return _value(environment, "VEADK_STUDIO_LOCAL_STORAGE").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


__all__ = [
'''

STORAGE_FALLBACK = '''\
        # === veadk-studio-local-storage: fall back to a local filesystem store ===
        if not bucket and studio_local_storage_enabled(environment):
            bucket = "local-fs"
            region = region or "local"
'''

# --------------------------------------------------------------------------
# frontend/server/storage/tos.py
# --------------------------------------------------------------------------
TOS_BRANCH = '''\
    # === veadk-studio-local-storage: filesystem client when TOS is absent ===
    from . import studio_local_storage_enabled

    if studio_local_storage_enabled():
        from .local_fs import create_local_client_factory

        return create_local_client_factory(config.bucket)
'''

# (relative path under site-packages, anchor, replacement)
STORAGE_EDITS = [
    (
        "frontend/server/storage/__init__.py",
        '        if region and not endpoint:\n',
        STORAGE_FALLBACK + '        if region and not endpoint:\n',
    ),
    (
        "frontend/server/storage/__init__.py",
        '__all__ = [\n    "STUDIO_STORAGE_ROOT_PREFIX",\n',
        STORAGE_HELPER + '    "STUDIO_STORAGE_ROOT_PREFIX",\n',
    ),
    (
        "frontend/server/storage/tos.py",
        '    """Create clients lazily and select a reachable Volcengine endpoint once."""\n',
        '    """Create clients lazily and select a reachable Volcengine endpoint once."""\n'
        + TOS_BRANCH,
    ),
]

# --------------------------------------------------------------------------
# veadk/cli/cli_frontend.py  (_safe_runner_env allow-list)
# --------------------------------------------------------------------------
RUNNER_ENV_ANCHOR = '''\
            "OBSERVABILITY_OPENTELEMETRY_APMPLUS_API_KEY",
            *_STUDIO_STORAGE_ENV_KEYS,
        ):
'''

RUNNER_ENV_REPLACEMENT = '''\
            "OBSERVABILITY_OPENTELEMETRY_APMPLUS_API_KEY",
            *_STUDIO_STORAGE_ENV_KEYS,
            # === veadk-studio-local-openviking: reach a self-hosted OpenViking ===
            "DATABASE_OPENVIKING_URL",
            "DATABASE_OPENVIKING_API_KEY",
            "DATABASE_OPENVIKING_USER_ID",
            "DATABASE_OPENVIKING_MEMORY_POLICY",
        ):
'''

RUNNER_ENV_EDITS = [
    ("veadk/cli/cli_frontend.py", RUNNER_ENV_ANCHOR, RUNNER_ENV_REPLACEMENT),
]

# (marker, file the marker lives in, edits)
GROUPS = [
    (MARKER, "frontend/server/storage/tos.py", STORAGE_EDITS),
    (RUNNER_ENV_MARKER, "veadk/cli/cli_frontend.py", RUNNER_ENV_EDITS),
]


def _site_packages(cli_frontend: Path) -> Path:
    return cli_frontend.parents[2]


def _apply_once(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise SystemExit(
            f"{label}: anchor matched {count} times (expected 1); aborting.\n{old[:160]!r}"
        )
    return src.replace(old, new, 1)


def main() -> None:
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TARGET
    action = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if action not in {"apply", "revert"}:
        raise SystemExit(f"unknown action: {action}")
    if not target.exists():
        raise SystemExit(f"target not found: {target}")

    site_packages = _site_packages(target)
    local_fs = site_packages / "frontend/server/storage/local_fs.py"
    origin = target.with_suffix(target.suffix + ".localstorage.bak")

    def present(marker: str, relative: str) -> bool:
        return marker in (site_packages / relative).read_text(encoding="utf-8")

    groups = list(reversed(GROUPS)) if action == "revert" else list(GROUPS)
    for marker, marker_relative, edits in groups:
        if action == "apply" and present(marker, marker_relative):
            print(f"[skip] {marker}: already applied")
            continue
        if action == "revert" and not present(marker, marker_relative):
            print(f"[skip] {marker}: not applied")
            continue

        if action == "apply" and marker == MARKER:
            if not origin.exists():
                shutil.copy2(target, origin)
                print(f"backup: {origin}")
            local_fs.write_text(LOCAL_FS_SOURCE, encoding="utf-8")
            print(f"wrote: {local_fs}")

        revisions = edits if action == "apply" else list(reversed(edits))
        for relative, anchor, replacement in revisions:
            path = site_packages / relative
            source = path.read_text(encoding="utf-8")
            if action == "revert":
                anchor, replacement = replacement, anchor
            path.write_text(
                _apply_once(source, anchor, replacement, f"{relative}"),
                encoding="utf-8",
            )
            print(f"[{action}] {relative}")

        if action == "revert" and marker == MARKER:
            local_fs.unlink(missing_ok=True)
            print(f"removed: {local_fs}")

    if action == "revert" and not any(
        present(marker, marker_relative) for marker, marker_relative, _ in GROUPS
    ):
        origin.unlink(missing_ok=True)

    print(f"{action} done -> {site_packages}")


if __name__ == "__main__":
    main()
