"""Low-level wrapper around the Obsidian CLI binary.

All vault shell operations go through this module — no other module should
invoke the Obsidian binary directly.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


DEFAULT_BINARY = "/Applications/Obsidian.app/Contents/MacOS/obsidian"

# Stderr lines that are noise — not real errors.
_STDERR_NOISE = ("Loading...", "out of date", "Obsidian", "Warning:")


class ObsidianCLIError(Exception):
    """Raised when the Obsidian CLI returns a non-zero exit code or cannot be found."""


class ObsidianCLI:
    """Thin wrapper around the Obsidian CLI binary for vault operations.

    Args:
        vault_name: Name of the Obsidian vault as shown in the app.
        binary_path: Filesystem path to the obsidian binary.
    """

    def __init__(
        self,
        vault_name: str,
        binary_path: str = DEFAULT_BINARY,
    ) -> None:
        self.vault_name = vault_name
        self.binary_path = binary_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, args: str, timeout: int = 30) -> str:
        """Execute a CLI command and return stdout.

        Args:
            args: The argument string appended after the binary path.
            timeout: Seconds before the subprocess is killed.

        Returns:
            Stripped stdout from the process.

        Raises:
            ObsidianCLIError: If the process exits non-zero or times out.
        """
        cmd = f'"{self.binary_path}" {args}'
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ObsidianCLIError(f"CLI timed out after {timeout}s: {cmd}") from exc
        except FileNotFoundError as exc:
            raise ObsidianCLIError(f"Obsidian binary not found: {self.binary_path}") from exc

        # Filter known noise from stderr before deciding whether to raise.
        stderr_lines = [
            line for line in result.stderr.splitlines()
            if line.strip() and not any(noise in line for noise in _STDERR_NOISE)
        ]
        real_stderr = "\n".join(stderr_lines)

        if result.returncode != 0:
            detail = real_stderr or result.stdout.strip() or f"exit code {result.returncode}"
            raise ObsidianCLIError(f"CLI error: {detail}")

        return result.stdout.strip()

    def _get_vault_path(self) -> Optional[str]:
        """Return the filesystem path for the configured vault, or None on failure."""
        try:
            raw = self._run(f'vault info=path vault="{self.vault_name}"')
            # The CLI may return a bare path or JSON — normalise.
            if raw.startswith("{"):
                data = json.loads(raw)
                return data.get("path")
            return raw or None
        except (ObsidianCLIError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, path: str, content: str) -> None:
        """Create a note at *path* with *content*.

        Prefers a direct filesystem write via the vault path for safety with
        complex markdown.  Falls back to a CLI ``write`` command when the vault
        path is unavailable.

        Args:
            path: Relative note path inside the vault (e.g. ``NPCs/Theron.md``).
            content: Full markdown content to write.
        """
        vault_path = self._get_vault_path()
        if vault_path:
            note_path = Path(vault_path) / path
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(content, encoding="utf-8")
        else:
            # Fallback: use the CLI write command.
            safe_content = content.replace('"', '\\"')
            self._run(
                f'write path="{path}" vault="{self.vault_name}" content="{safe_content}"'
            )

    def read(self, path: str) -> str:
        """Read and return the raw content of a note.

        Args:
            path: Relative note path inside the vault.

        Returns:
            The note's markdown content as a string.

        Raises:
            ObsidianCLIError: If the note cannot be read.
        """
        return self._run(f'read path="{path}" vault="{self.vault_name}"')

    def append(self, path: str, content: str) -> None:
        """Append *content* to an existing note.

        Prefers a filesystem append; falls back to CLI.

        Args:
            path: Relative note path inside the vault.
            content: Markdown text to append.
        """
        vault_path = self._get_vault_path()
        if vault_path:
            note_path = Path(vault_path) / path
            with note_path.open("a", encoding="utf-8") as fh:
                fh.write(content)
        else:
            safe_content = content.replace('"', '\\"')
            self._run(
                f'append path="{path}" vault="{self.vault_name}" content="{safe_content}"'
            )

    def search(self, query: str) -> list[str]:
        """Search the vault and return a list of matching note paths.

        Args:
            query: Plain-text search query.

        Returns:
            List of relative note paths that match the query.
        """
        raw = self._run(
            f'search query="{query}" vault="{self.vault_name}" format=json'
        )
        return json.loads(raw)

    def set_property(self, path: str, name: str, value: str) -> None:
        """Set a frontmatter property on a note.

        Args:
            path: Relative note path inside the vault.
            name: Property key.
            value: Property value.
        """
        self._run(
            f'property:set path="{path}" vault="{self.vault_name}" name="{name}" value="{value}"'
        )

    def list_files(self, folder: Optional[str] = None) -> list[str]:
        """Return a list of all note paths in the vault (or a subfolder).

        Args:
            folder: Optional subfolder to restrict the listing.

        Returns:
            List of relative note paths.
        """
        if folder:
            raw = self._run(
                f'files vault="{self.vault_name}" folder="{folder}" format=json'
            )
        else:
            raw = self._run(f'files vault="{self.vault_name}" format=json')
        return json.loads(raw)

    def list_folders(self) -> list[str]:
        """Return a list of all folder paths in the vault.

        Returns:
            List of folder path strings.
        """
        raw = self._run(f'folders vault="{self.vault_name}"')
        # The CLI may return newline-separated paths or JSON.
        if raw.startswith("["):
            return json.loads(raw)
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def delete(self, path: str) -> None:
        """Move a note to the system trash.

        Args:
            path: Relative note path inside the vault.
        """
        self._run(f'delete path="{path}" vault="{self.vault_name}"')

    def note_exists(self, path: str) -> bool:
        """Return True if *path* exists in the vault, False otherwise.

        Args:
            path: Relative note path inside the vault.
        """
        try:
            self.read(path)
            return True
        except ObsidianCLIError:
            return False

    def find_notes_in_folder(self, folder: str) -> list[str]:
        """Return all note paths that live directly inside *folder*.

        Args:
            folder: Folder prefix to filter by (e.g. ``"NPCs/"``).

        Returns:
            Filtered list of relative note paths.
        """
        all_files = self.list_files()
        return [f for f in all_files if f.startswith(folder)]

    def health_check(self) -> bool:
        """Return True if the CLI binary is reachable, False otherwise."""
        try:
            self._run("version")
            return True
        except ObsidianCLIError:
            return False
