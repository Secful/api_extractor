"""Framework detection module."""

import json
import os
import re
from pathlib import Path
from typing import List, Optional, Set
from api_extractor.core.models import FrameworkType


class FrameworkDetector:
    """Detects web frameworks used in a codebase."""

    # Python dependency patterns
    PYTHON_FRAMEWORK_PATTERNS = {
        FrameworkType.FASTAPI: ["fastapi"],
        FrameworkType.FLASK: ["flask"],
        FrameworkType.DJANGO_REST: ["djangorestframework", "django-rest-framework"],
    }

    # JavaScript/TypeScript dependency patterns
    JS_FRAMEWORK_PATTERNS = {
        FrameworkType.EXPRESS: ["express"],
        FrameworkType.NESTJS: ["@nestjs/core", "@nestjs/common"],
        FrameworkType.FASTIFY: ["fastify"],
        FrameworkType.NEXTJS: ["next"],
    }

    # Java dependency patterns
    JAVA_FRAMEWORK_PATTERNS = {
        FrameworkType.SPRING_BOOT: [
            "spring-boot-starter-web",
            "spring-web",
            "spring-webmvc",
        ],
    }

    # C# dependency patterns
    CSHARP_FRAMEWORK_PATTERNS = {
        FrameworkType.ASPNET_CORE: [
            "Microsoft.AspNetCore.App",
            "Microsoft.AspNetCore.Mvc",
            "Microsoft.NET.Sdk.Web",
        ],
    }

    # Python import patterns
    PYTHON_IMPORT_PATTERNS = {
        FrameworkType.FASTAPI: [
            r"from\s+fastapi\s+import",
            r"import\s+fastapi",
        ],
        FrameworkType.FLASK: [
            r"from\s+flask\s+import",
            r"import\s+flask",
        ],
        FrameworkType.DJANGO_REST: [
            r"from\s+rest_framework\s+import",
            r"import\s+rest_framework",
        ],
    }

    # JavaScript/TypeScript import patterns
    JS_IMPORT_PATTERNS = {
        FrameworkType.EXPRESS: [
            r"require\s*\(\s*['\"]express['\"]\s*\)",
            r"from\s+['\"]express['\"]",
            r"import\s+.*\s+from\s+['\"]express['\"]",
        ],
        FrameworkType.NESTJS: [
            r"from\s+['\"]@nestjs/",
            r"import\s+.*\s+from\s+['\"]@nestjs/",
        ],
        FrameworkType.FASTIFY: [
            r"require\s*\(\s*['\"]fastify['\"]\s*\)",
            r"from\s+['\"]fastify['\"]",
            r"import\s+.*\s+from\s+['\"]fastify['\"]",
        ],
        FrameworkType.NEXTJS: [
            r"from\s+['\"]next/server['\"]",
            r"from\s+['\"]next/router['\"]",
            r"from\s+['\"]next/navigation['\"]",
        ],
    }

    # Java import patterns
    JAVA_IMPORT_PATTERNS = {
        FrameworkType.SPRING_BOOT: [
            r"import\s+org\.springframework\.web\.bind\.annotation\.",
            r"import\s+org\.springframework\.boot\.",
        ],
    }

    # C# using patterns
    CSHARP_IMPORT_PATTERNS = {
        FrameworkType.ASPNET_CORE: [
            r"using\s+Microsoft\.AspNetCore\.Mvc",
            r"using\s+Microsoft\.AspNetCore\.Builder",
        ],
    }

    def __init__(self) -> None:
        """Initialize detector."""
        pass

    def detect(self, path: str) -> Optional[List[FrameworkType]]:
        """
        Detect frameworks in the given path.

        Args:
            path: Path to codebase (local directory or extracted S3 content)

        Returns:
            List of detected frameworks, or None if no frameworks found
        """
        frameworks: Set[FrameworkType] = set()

        # Level 1: Check dependency files (fast, high confidence)
        frameworks.update(self._check_dependencies(path))

        # Level 1.5: Check directory structure (fast, high confidence for Next.js)
        frameworks.update(self._check_structure(path))

        # Level 2: Scan imports (medium speed, high confidence)
        if not frameworks:
            frameworks.update(self._scan_imports(path))

        # Level 3: Pattern matching (slower, fallback)
        if not frameworks:
            frameworks.update(self._pattern_match(path))

        # Return None if no frameworks detected
        if not frameworks:
            return None

        return list(frameworks)

    def _check_dependencies(self, path: str) -> Set[FrameworkType]:
        """
        Check dependency files for framework references.

        Args:
            path: Path to codebase

        Returns:
            Set of detected frameworks
        """
        frameworks: Set[FrameworkType] = set()

        # Check Python dependencies
        frameworks.update(self._check_python_dependencies(path))

        # Check JavaScript/TypeScript dependencies
        frameworks.update(self._check_js_dependencies(path))

        # Check Java dependencies
        frameworks.update(self._check_java_dependencies(path))

        # Check C# dependencies
        frameworks.update(self._check_csharp_dependencies(path))

        return frameworks

    def _check_python_dependencies(self, path: str) -> Set[FrameworkType]:
        """Check Python dependency files."""
        frameworks: Set[FrameworkType] = set()

        # Check requirements.txt
        req_file = os.path.join(path, "requirements.txt")
        if os.path.exists(req_file):
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.PYTHON_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        # Check pyproject.toml
        pyproject_file = os.path.join(path, "pyproject.toml")
        if os.path.exists(pyproject_file):
            try:
                with open(pyproject_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.PYTHON_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        # Check Pipfile
        pipfile = os.path.join(path, "Pipfile")
        if os.path.exists(pipfile):
            try:
                with open(pipfile, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.PYTHON_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        # Check setup.py
        setup_file = os.path.join(path, "setup.py")
        if os.path.exists(setup_file):
            try:
                with open(setup_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.PYTHON_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        return frameworks

    def _check_js_dependencies(self, path: str) -> Set[FrameworkType]:
        """Check JavaScript/TypeScript dependency files."""
        frameworks: Set[FrameworkType] = set()

        # Check package.json
        pkg_file = os.path.join(path, "package.json")
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }

                    for framework, patterns in self.JS_FRAMEWORK_PATTERNS.items():
                        if any(pattern in deps for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        return frameworks

    def _check_java_dependencies(self, path: str) -> Set[FrameworkType]:
        """Check Java dependency files (Maven pom.xml and Gradle build.gradle)."""
        frameworks: Set[FrameworkType] = set()

        # Check pom.xml (Maven)
        pom_file = os.path.join(path, "pom.xml")
        if os.path.exists(pom_file):
            try:
                with open(pom_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.JAVA_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        # Check build.gradle (Gradle)
        gradle_file = os.path.join(path, "build.gradle")
        if os.path.exists(gradle_file):
            try:
                with open(gradle_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.JAVA_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        # Check build.gradle.kts (Kotlin DSL)
        gradle_kts_file = os.path.join(path, "build.gradle.kts")
        if os.path.exists(gradle_kts_file):
            try:
                with open(gradle_kts_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for framework, patterns in self.JAVA_FRAMEWORK_PATTERNS.items():
                        if any(pattern in content for pattern in patterns):
                            frameworks.add(framework)
            except Exception:
                pass

        return frameworks

    def _check_csharp_dependencies(self, path: str) -> Set[FrameworkType]:
        """Check C# project files (.csproj) for ASP.NET Core references."""
        frameworks: Set[FrameworkType] = set()

        for root, _, files in os.walk(path):
            if any(skip in root for skip in ["bin", "obj", ".git", "node_modules"]):
                continue

            for file in files:
                if file.endswith(".csproj"):
                    csproj_file = os.path.join(root, file)
                    try:
                        with open(csproj_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Check for Sdk="Microsoft.NET.Sdk.Web"
                            if 'Sdk="Microsoft.NET.Sdk.Web"' in content:
                                frameworks.add(FrameworkType.ASPNET_CORE)
                                return frameworks
                            # Check for AspNetCore package references
                            for pattern in self.CSHARP_FRAMEWORK_PATTERNS.get(
                                FrameworkType.ASPNET_CORE, []
                            ):
                                if pattern in content:
                                    frameworks.add(FrameworkType.ASPNET_CORE)
                                    return frameworks
                    except Exception:
                        pass

        return frameworks

    def _check_structure(self, path: str) -> Set[FrameworkType]:
        """
        Check directory structure for framework-specific patterns.

        Args:
            path: Path to codebase

        Returns:
            Set of detected frameworks
        """
        frameworks: Set[FrameworkType] = set()

        # Check for Next.js API routes structure
        # App Router: app/api/ directory
        if os.path.exists(os.path.join(path, "app", "api")):
            frameworks.add(FrameworkType.NEXTJS)

        # Pages Router: pages/api/ directory
        if os.path.exists(os.path.join(path, "pages", "api")):
            frameworks.add(FrameworkType.NEXTJS)

        return frameworks

    def _scan_imports(self, path: str) -> Set[FrameworkType]:
        """
        Scan source files for import statements.

        Args:
            path: Path to codebase

        Returns:
            Set of detected frameworks
        """
        frameworks: Set[FrameworkType] = set()

        # Scan Python files
        frameworks.update(self._scan_python_imports(path))

        # Scan JavaScript/TypeScript files
        frameworks.update(self._scan_js_imports(path))

        # Scan Java files
        frameworks.update(self._scan_java_imports(path))

        # Scan C# files
        frameworks.update(self._scan_csharp_imports(path))

        return frameworks

    def _scan_python_imports(self, path: str) -> Set[FrameworkType]:
        """Scan Python files for imports."""
        frameworks: Set[FrameworkType] = set()

        for root, _, files in os.walk(path):
            # Skip virtual environments and common ignore directories
            if any(
                skip in root
                for skip in [
                    "venv",
                    ".venv",
                    "env",
                    ".env",
                    "node_modules",
                    "__pycache__",
                    ".git",
                ]
            ):
                continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in self.PYTHON_IMPORT_PATTERNS.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                                    # Early exit if we found imports
                                    if frameworks:
                                        return frameworks
                    except Exception:
                        continue

        return frameworks

    def _scan_js_imports(self, path: str) -> Set[FrameworkType]:
        """Scan JavaScript/TypeScript files for imports."""
        frameworks: Set[FrameworkType] = set()

        for root, _, files in os.walk(path):
            # Skip node_modules and common ignore directories
            if any(
                skip in root
                for skip in ["node_modules", "dist", "build", ".git", "coverage"]
            ):
                continue

            for file in files:
                if file.endswith((".js", ".ts", ".jsx", ".tsx")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in self.JS_IMPORT_PATTERNS.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                                    # Early exit if we found imports
                                    if frameworks:
                                        return frameworks
                    except Exception:
                        continue

        return frameworks

    def _scan_java_imports(self, path: str) -> Set[FrameworkType]:
        """Scan Java files for Spring Boot imports."""
        frameworks: Set[FrameworkType] = set()

        for root, _, files in os.walk(path):
            # Skip build directories
            if any(skip in root for skip in ["target", "build", ".git", ".gradle", "node_modules"]):
                continue

            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in self.JAVA_IMPORT_PATTERNS.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                                    # Early exit if we found imports
                                    if frameworks:
                                        return frameworks
                    except Exception:
                        continue

        return frameworks

    def _scan_csharp_imports(self, path: str) -> Set[FrameworkType]:
        """Scan C# files for using statements."""
        frameworks: Set[FrameworkType] = set()

        for root, _, files in os.walk(path):
            if any(skip in root for skip in ["bin", "obj", ".git", "node_modules"]):
                continue

            for file in files:
                if file.endswith(".cs"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in self.CSHARP_IMPORT_PATTERNS.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                                    if frameworks:
                                        return frameworks
                    except Exception:
                        continue

        return frameworks

    def _pattern_match(self, path: str) -> Set[FrameworkType]:
        """
        Last resort: look for framework-specific code patterns.

        Args:
            path: Path to codebase

        Returns:
            Set of detected frameworks
        """
        frameworks: Set[FrameworkType] = set()

        # Python patterns
        python_patterns = {
            FrameworkType.FASTAPI: [r"@app\.(get|post|put|delete|patch)\s*\("],
            FrameworkType.FLASK: [r"@app\.route\s*\(", r"@.*\.route\s*\("],
            FrameworkType.DJANGO_REST: [
                r"class\s+\w+\s*\(\s*viewsets\.",
                r"class\s+\w+\s*\(\s*APIView\s*\)",
            ],
        }

        # JavaScript patterns
        js_patterns = {
            FrameworkType.EXPRESS: [
                r"app\.(get|post|put|delete|patch)\s*\(",
                r"router\.(get|post|put|delete|patch)\s*\(",
            ],
            FrameworkType.NESTJS: [r"@Controller\s*\(", r"@(Get|Post|Put|Delete|Patch)\s*\("],
            FrameworkType.FASTIFY: [r"fastify\.(get|post|put|delete|patch)\s*\("],
        }

        # Java patterns
        java_patterns = {
            FrameworkType.SPRING_BOOT: [
                r"@RestController",
                r"@(Get|Post|Put|Delete|Patch)Mapping",
                r"@RequestMapping",
            ],
        }

        # Scan Python files
        for root, _, files in os.walk(path):
            if any(
                skip in root
                for skip in ["venv", ".venv", "env", "node_modules", "__pycache__", ".git"]
            ):
                continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in python_patterns.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                    except Exception:
                        continue

        # Scan JavaScript/TypeScript files
        for root, _, files in os.walk(path):
            if any(skip in root for skip in ["node_modules", "dist", "build", ".git"]):
                continue

            for file in files:
                if file.endswith((".js", ".ts", ".jsx", ".tsx")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in js_patterns.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                    except Exception:
                        continue

        # Scan Java files
        for root, _, files in os.walk(path):
            if any(skip in root for skip in ["target", "build", ".git", ".gradle", "node_modules"]):
                continue

            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for framework, patterns in java_patterns.items():
                                if any(re.search(pattern, content) for pattern in patterns):
                                    frameworks.add(framework)
                    except Exception:
                        continue

        return frameworks
