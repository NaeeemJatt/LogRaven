"""OS Package Extractors (Debian dpkg, RPM, Alpine APK) for CycloneDX v1.5 SBOM Generation."""

from typing import Any, Dict, List, Optional
import uuid


class DpkgStatusParser:
    """Parses Debian / Ubuntu /var/lib/dpkg/status format."""

    @staticmethod
    def parse(content: str) -> List[Dict[str, Any]]:
        """Parses dpkg status file into a list of package dictionaries."""
        packages = []
        current_pkg: Dict[str, str] = {}

        for line in content.splitlines():
            line = line.rstrip()
            if not line:
                if current_pkg and "Package" in current_pkg:
                    packages.append(current_pkg)
                    current_pkg = {}
                continue

            if line.startswith(" ") or line.startswith("\t"):
                # Continuation line (e.g. for Description)
                continue

            if ":" in line:
                key, val = line.split(":", 1)
                current_pkg[key.strip()] = val.strip()

        if current_pkg and "Package" in current_pkg:
            packages.append(current_pkg)

        return packages


class OSPackageExtractor:
    """Extracts installed OS packages and normalizes to CycloneDX v1.5 JSON components."""

    @staticmethod
    def parse_dpkg_status(content: str) -> List[Dict[str, Any]]:
        """Converts /var/lib/dpkg/status into CycloneDX v1.5 component records (TC-MOD4-001)."""
        raw_pkgs = DpkgStatusParser.parse(content)
        components = []

        for p in raw_pkgs:
            name = p.get("Package", "")
            version = p.get("Version", "")
            arch = p.get("Architecture", "amd64")
            desc = p.get("Description", "")
            status = p.get("Status", "install ok installed")

            # Only include actually installed packages
            if "installed" not in status:
                continue

            comp = {
                "bom-ref": f"pkg:deb/debian/{name}@{version}?arch={arch}",
                "type": "operating-system",
                "name": name,
                "version": version,
                "description": desc,
                "properties": [
                    {"name": "architecture", "value": arch},
                    {"name": "os_family", "value": "debian"},
                ],
                "purl": f"pkg:deb/debian/{name}@{version}?arch={arch}",
            }
            components.append(comp)

        return components

    @staticmethod
    def parse_apk_installed(content: str) -> List[Dict[str, Any]]:
        """Parses Alpine /lib/apk/db/installed format."""
        components = []
        current: Dict[str, str] = {}

        for line in content.splitlines():
            line = line.strip()
            if not line:
                if "P" in current and "V" in current:
                    name = current["P"]
                    ver = current["V"]
                    arch = current.get("A", "x86_64")
                    components.append({
                        "bom-ref": f"pkg:apk/alpine/{name}@{ver}?arch={arch}",
                        "type": "operating-system",
                        "name": name,
                        "version": ver,
                        "purl": f"pkg:apk/alpine/{name}@{ver}?arch={arch}",
                        "properties": [{"name": "os_family", "value": "alpine"}],
                    })
                current = {}
                continue

            if ":" in line:
                tag, val = line.split(":", 1)
                current[tag] = val

        if "P" in current and "V" in current:
            name = current["P"]
            ver = current["V"]
            arch = current.get("A", "x86_64")
            components.append({
                "bom-ref": f"pkg:apk/alpine/{name}@{ver}?arch={arch}",
                "type": "operating-system",
                "name": name,
                "version": ver,
                "purl": f"pkg:apk/alpine/{name}@{ver}?arch={arch}",
                "properties": [{"name": "os_family", "value": "alpine"}],
            })

        return components

    @staticmethod
    def build_cyclonedx_sbom(
        asset_urn: str,
        os_family: str,
        os_version: str,
        components: List[Dict[str, Any]],
        serial_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Constructs full CycloneDX v1.5 specification JSON."""
        serial = serial_number or f"urn:uuid:{uuid.uuid4()}"
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": serial,
            "version": 1,
            "metadata": {
                "component": {
                    "type": "operating-system",
                    "name": os_family,
                    "version": os_version,
                    "properties": [{"name": "asset_urn", "value": asset_urn}],
                },
            },
            "components": components,
        }

