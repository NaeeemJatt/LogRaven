"""Application Runtime Package Extractors (Node.js npm, Python pip, Go, Rust) for SBOM."""

import json
from typing import Any, Dict, List


class AppRuntimeExtractor:
    """Extracts application packages from manifests and lockfiles."""

    @staticmethod
    def parse_package_lock_json(content: str) -> List[Dict[str, Any]]:
        """Parses npm package-lock.json v2/v3 format into CycloneDX components."""
        components = []
        try:
            data = json.loads(content)
            packages = data.get("packages", {})
            for pkg_path, info in packages.items():
                if not pkg_path:
                    continue  # root project
                name = pkg_path.split("node_modules/")[-1]
                version = info.get("version", "unknown")
                comp = {
                    "bom-ref": f"pkg:npm/{name}@{version}",
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": f"pkg:npm/{name}@{version}",
                    "properties": [{"name": "runtime", "value": "nodejs"}],
                }
                components.append(comp)
        except Exception:
            pass
        return components

    @staticmethod
    def parse_requirements_txt(content: str) -> List[Dict[str, Any]]:
        """Parses Python requirements.txt file."""
        components = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                name, ver = line.split("==", 1)
                clean_name = name.strip()
                clean_ver = ver.split(";")[0].strip()
                components.append({
                    "bom-ref": f"pkg:pypi/{clean_name}@{clean_ver}",
                    "type": "library",
                    "name": clean_name,
                    "version": clean_ver,
                    "purl": f"pkg:pypi/{clean_name}@{clean_ver}",
                    "properties": [{"name": "runtime", "value": "python"}],
                })
        return components

    @staticmethod
    def parse_cargo_lock(content: str) -> List[Dict[str, Any]]:
        """Parses Rust Cargo.lock TOML-like structure."""
        components = []
        current: Dict[str, str] = {}
        in_package = False

        for line in content.splitlines():
            line = line.strip()
            if line == "[[package]]":
                if current.get("name") and current.get("version"):
                    name = current["name"].strip('"')
                    ver = current["version"].strip('"')
                    components.append({
                        "bom-ref": f"pkg:cargo/{name}@{ver}",
                        "type": "library",
                        "name": name,
                        "version": ver,
                        "purl": f"pkg:cargo/{name}@{ver}",
                        "properties": [{"name": "runtime", "value": "rust"}],
                    })
                current = {}
                in_package = True
                continue

            if in_package and "=" in line:
                k, v = line.split("=", 1)
                current[k.strip()] = v.strip().strip('"')

        if current.get("name") and current.get("version"):
            name = current["name"].strip('"')
            ver = current["version"].strip('"')
            components.append({
                "bom-ref": f"pkg:cargo/{name}@{ver}",
                "type": "library",
                "name": name,
                "version": ver,
                "purl": f"pkg:cargo/{name}@{ver}",
                "properties": [{"name": "runtime", "value": "rust"}],
            })

        return components

