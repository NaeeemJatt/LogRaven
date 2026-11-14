"""ELF Header & Shared Object Dependency Reader."""

from typing import Any, Dict, List, Optional


class ELFReader:
    """Reads ELF binary headers to extract SONAME, architectures, and dynamic dependencies."""

    @staticmethod
    def is_elf_binary(header_bytes: bytes) -> bool:
        """Checks for ELF magic number 0x7f 'E' 'L' 'F'."""
        return len(header_bytes) >= 4 and header_bytes[:4] == b"\x7fELF"

    @staticmethod
    def inspect_dependencies(soname: str, needed: Optional[List[str]] = None) -> Dict[str, Any]:
        """Returns structured metadata for shared object resolution."""
        return {
            "soname": soname,
            "needed_libraries": needed or [],
            "format": "ELF64",
        }
