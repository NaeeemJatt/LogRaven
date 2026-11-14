"""Process & Binary Path to Package Metadata Resolver (TC-MOD5-001)."""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

# Pre-seeded common system binary & library package mappings
SYSTEM_PACKAGE_MAP: Dict[str, Tuple[str, str]] = {
    "/usr/bin/curl": ("curl", "7.88.1-10+deb12u5"),
    "/usr/lib/x86_64-linux-gnu/libssl.so.3": ("openssl", "3.0.11-1~deb12u2"),
    "/usr/lib/x86_64-linux-gnu/libcrypto.so.3": ("openssl", "3.0.11-1~deb12u2"),
    "/usr/bin/openssl": ("openssl", "3.0.11-1~deb12u2"),
    "/usr/bin/nginx": ("nginx", "1.22.1-9"),
    "/usr/bin/python3": ("python3", "3.11.2-1+b1"),
    "/usr/bin/node": ("nodejs", "18.19.0-1nodesource1"),
    "/usr/bin/git": ("git", "1:2.39.2-1.1"),
    "/usr/bin/ssh": ("openssh-client", "1:9.2p1-2+deb12u2"),
    "/usr/sbin/sshd": ("openssh-server", "1:9.2p1-2+deb12u2"),
    "/usr/bin/runc": ("runc", "1.1.5+ds1-1+b1"),
}


class ProcessResolver:
    """Inverted index mapping file execution paths to installed package metadata."""

    def __init__(self, initial_map: Optional[Dict[str, Tuple[str, str]]] = None):
        self._path_to_pkg: Dict[str, Tuple[str, str]] = dict(SYSTEM_PACKAGE_MAP)
        if initial_map:
            self._path_to_pkg.update(initial_map)

    def register_path(self, file_path: str, package_name: str, package_version: str):
        """Registers a binary/library path to its parent package."""
        clean_path = os.path.normpath(file_path).replace("\\", "/")
        self._path_to_pkg[clean_path] = (package_name, package_version)

    def resolve(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Resolves file execution path to package in < 2ms (TC-MOD5-001)."""
        start = time.perf_counter()
        clean_path = os.path.normpath(file_path).replace("\\", "/")

        res = self._path_to_pkg.get(clean_path)
        lookup_ms = (time.perf_counter() - start) * 1000.0

        if res:
            pkg_name, pkg_version = res
            return {
                "file_path": clean_path,
                "package_name": pkg_name,
                "package_version": pkg_version,
                "lookup_time_ms": lookup_ms,
            }

        # Fallback: deduce package from binary basename
        base = os.path.basename(clean_path)
        if base in ("curl", "nginx", "python3", "openssl", "git", "runc"):
            return {
                "file_path": clean_path,
                "package_name": base,
                "package_version": "unknown",
                "lookup_time_ms": lookup_ms,
            }

        return None
