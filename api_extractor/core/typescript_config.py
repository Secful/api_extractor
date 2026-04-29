"""TypeScript configuration parser for tsconfig.json."""

import json
import os
from pathlib import Path
from typing import Optional


class TypeScriptConfig:
    """Parse and resolve TypeScript path aliases from tsconfig.json."""

    def __init__(self, project_root: str) -> None:
        """
        Initialize TypeScript config resolver.

        Args:
            project_root: Root directory to search for tsconfig.json
        """
        self.project_root = project_root
        self.tsconfig_path: Optional[str] = None
        self.base_url: Optional[str] = None
        self.paths: dict[str, list[str]] = {}

        # Try to find and parse tsconfig.json
        self._find_and_parse_tsconfig()

    def _find_and_parse_tsconfig(self) -> None:
        """Find tsconfig.json or tsconfig.base.json and parse path mappings."""
        # Look for tsconfig files in project root (try both patterns)
        for filename in ["tsconfig.json", "tsconfig.base.json"]:
            tsconfig_path = os.path.join(self.project_root, filename)
            if os.path.exists(tsconfig_path):
                self.tsconfig_path = tsconfig_path
                self._parse_tsconfig(tsconfig_path)
                break

    def _parse_tsconfig(self, tsconfig_path: str) -> None:
        """
        Parse tsconfig.json file.

        Args:
            tsconfig_path: Path to tsconfig.json
        """
        try:
            with open(tsconfig_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Try parsing as-is first (many tsconfig files are valid JSON)
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                # If that fails, try removing comments
                lines = []
                in_block_comment = False
                for line in content.split("\n"):
                    # Handle block comments
                    if "/*" in line:
                        in_block_comment = True
                    if "*/" in line:
                        in_block_comment = False
                        # Remove everything up to and including */
                        line = line.split("*/", 1)[-1]

                    if in_block_comment:
                        continue

                    # Handle line comments
                    if "//" in line:
                        line = line.split("//", 1)[0]

                    lines.append(line)

                cleaned_content = "\n".join(lines)
                config = json.loads(cleaned_content)

            # Handle "extends" property to load base config
            if "extends" in config:
                extends_path = config["extends"]
                # Resolve relative to current tsconfig
                base_config_path = os.path.normpath(
                    os.path.join(os.path.dirname(tsconfig_path), extends_path)
                )
                if os.path.exists(base_config_path):
                    # Recursively parse the base config first
                    self._parse_tsconfig(base_config_path)
                    # Current config will override base config values

            # Extract compiler options
            compiler_options = config.get("compilerOptions", {})

            # Get baseUrl (defaults to tsconfig.json directory)
            base_url = compiler_options.get("baseUrl")
            if base_url:
                # Resolve baseUrl relative to tsconfig.json location
                tsconfig_dir = os.path.dirname(tsconfig_path)
                self.base_url = os.path.normpath(os.path.join(tsconfig_dir, base_url))
            elif not self.base_url:
                # Default to tsconfig directory if not already set
                self.base_url = os.path.dirname(tsconfig_path)

            # Get path mappings and merge with existing
            paths = compiler_options.get("paths", {})
            if paths:
                self.paths.update(paths)

        except Exception:
            # If parsing fails, just continue without tsconfig
            pass

    def resolve_alias(self, import_path: str, from_file: str) -> Optional[str]:
        """
        Resolve an aliased import to an absolute file path.

        Args:
            import_path: Import path like '@ghostfolio/common/interfaces'
            from_file: File making the import (not used for aliases but kept for consistency)

        Returns:
            Resolved absolute file path or None if not found
        """
        if not self.paths or not self.base_url:
            return None

        # Try to match against path patterns
        for alias_pattern, target_patterns in self.paths.items():
            # Handle wildcard patterns
            if alias_pattern.endswith("/*"):
                # Check if import starts with the alias prefix
                alias_prefix = alias_pattern[:-2]  # Remove /*
                if import_path.startswith(alias_prefix):
                    # Extract the suffix after the alias
                    suffix = import_path[len(alias_prefix) :]
                    if suffix.startswith("/"):
                        suffix = suffix[1:]

                    # Try each target pattern
                    for target_pattern in target_patterns:
                        if target_pattern.endswith("/*"):
                            # Replace wildcard with suffix
                            target_path = target_pattern[:-2] + "/" + suffix
                        else:
                            target_path = target_pattern + "/" + suffix

                        # Resolve relative to baseUrl
                        resolved = os.path.join(self.base_url, target_path)

                        # Try with various extensions
                        for ext in [".ts", ".tsx", ".d.ts", "/index.ts"]:
                            test_path = resolved + ext
                            if os.path.exists(test_path):
                                return test_path

            else:
                # Exact match (no wildcard)
                if import_path == alias_pattern:
                    # Try each target
                    for target_pattern in target_patterns:
                        resolved = os.path.join(self.base_url, target_pattern)

                        # Try with various extensions
                        for ext in ["", ".ts", ".tsx", ".d.ts"]:
                            test_path = resolved + ext
                            if os.path.exists(test_path):
                                return test_path

        return None

    @staticmethod
    def find_tsconfig(start_path: str) -> Optional["TypeScriptConfig"]:
        """
        Find tsconfig.json or tsconfig.base.json by walking up directory tree.

        Args:
            start_path: Starting directory or file path

        Returns:
            TypeScriptConfig instance or None
        """
        if os.path.isfile(start_path):
            start_path = os.path.dirname(start_path)

        current = start_path
        while True:
            # Try both tsconfig.json and tsconfig.base.json
            for filename in ["tsconfig.json", "tsconfig.base.json"]:
                tsconfig_path = os.path.join(current, filename)
                if os.path.exists(tsconfig_path):
                    return TypeScriptConfig(current)

            parent = os.path.dirname(current)
            if parent == current:
                # Reached root
                break
            current = parent

        return None
