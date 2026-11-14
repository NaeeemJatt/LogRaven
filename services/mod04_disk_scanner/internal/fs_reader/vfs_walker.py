"""Virtual Filesystem (VFS) Tree Traversal for Out-of-Band Disk Scans."""

from typing import Dict, List, Optional, Tuple


class VirtualFileSystem:
    """Read-only in-memory filesystem tree representing the unpacked disk volume."""

    def __init__(self, initial_files: Optional[Dict[str, str]] = None):
        # file_path -> file_content (string)
        self.files: Dict[str, str] = dict(initial_files or {})

    def add_file(self, path: str, content: str):
        normalized = "/" + path.lstrip("/")
        self.files[normalized] = content

    def read_file(self, path: str) -> Optional[str]:
        normalized = "/" + path.lstrip("/")
        return self.files.get(normalized)

    def find_package_manifests(self) -> List[Tuple[str, str, str]]:
        """Finds package database files and lockfiles.
        
        Returns list of tuples: (manifest_type, file_path, file_content)
        """
        manifests = []
        for path, content in self.files.items():
            if path.endswith("/var/lib/dpkg/status") or path == "/var/lib/dpkg/status":
                manifests.append(("dpkg", path, content))
            elif path.endswith("/lib/apk/db/installed") or path == "/lib/apk/db/installed":
                manifests.append(("apk", path, content))
            elif path.endswith("package-lock.json"):
                manifests.append(("npm", path, content))
            elif path.endswith("requirements.txt"):
                manifests.append(("pip", path, content))
            elif path.endswith("Cargo.lock"):
                manifests.append(("cargo", path, content))
        return manifests

    def find_credential_files(self) -> List[Tuple[str, str]]:
        """Finds files in sensitive paths (/etc, /home/*/.ssh, /home/*/.aws, /root, /app)."""
        target_prefixes = ("/etc", "/home", "/root", "/app", "/var/www")
        sensitive = []
        for path, content in self.files.items():
            if any(path.startswith(prefix) for prefix in target_prefixes):
                sensitive.append((path, content))
        return sensitive

