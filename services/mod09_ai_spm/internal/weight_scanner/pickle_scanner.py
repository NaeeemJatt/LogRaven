"""Pickle AST & Bytecode Scanner for detecting unsafe model weight deserialization (PRD-MOD-09 / TC-MOD9-001).

Uses Python's built-in `pickletools.genops` to safely disassemble pickle opcodes
and detect arbitrary code execution gadgets (e.g., os.system, subprocess, eval)
WITHOUT ever executing the bytecode or instantiating objects.
"""

import io
import pickletools
from typing import Any, Dict, List, Optional, Set, Tuple

# Modules and functions commonly weaponized for Pickle RCE
DANGEROUS_CALLABLES: Dict[str, Set[str]] = {
    "os": {"system", "popen", "spawn", "posix_spawn", "fork", "execv", "execve"},
    "posix": {"system", "popen", "fork", "execv", "execve"},
    "nt": {"system", "popen", "spawn"},
    "subprocess": {"call", "check_call", "check_output", "Popen", "run"},
    "builtins": {"eval", "exec", "compile", "open", "__import__", "getattr"},
    "__builtin__": {"eval", "exec", "compile", "open", "__import__", "getattr"},
    "sys": {"modules"},
    "shutil": {"rmtree"},
    "pty": {"spawn"},
    "commands": {"getoutput", "getstatusoutput"},
    "socket": {"socket", "connect"},
}


class PickleScanResult:
    """Analysis result for a scanned model weight buffer."""

    def __init__(
        self,
        is_safe: bool,
        finding_code: Optional[str] = None,
        dangerous_imports: Optional[List[Dict[str, str]]] = None,
        extracted_payloads: Optional[List[str]] = None,
        details: Optional[str] = None,
    ):
        self.is_safe = is_safe
        self.finding_code = finding_code  # e.g., 'CRITICAL_PICKLE_RCE'
        self.dangerous_imports = dangerous_imports or []
        self.extracted_payloads = extracted_payloads or []
        self.details = details or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "finding_code": self.finding_code,
            "dangerous_imports": self.dangerous_imports,
            "extracted_payloads": self.extracted_payloads,
            "details": self.details,
        }


class PickleScanner:
    """Disassembles and audits pickle bytecode to detect arbitrary code execution."""

    @classmethod
    def scan_bytes(cls, data: bytes) -> PickleScanResult:
        """Parses raw bytecode instructions without executing them."""
        if not data:
            return PickleScanResult(is_safe=True, details="Empty buffer")

        dangerous_findings: List[Dict[str, str]] = []
        extracted_strings: List[str] = []
        recent_stack: List[Any] = []

        try:
            ops = list(pickletools.genops(data))
        except Exception as err:
            # If it cannot be parsed as pickle, check for common magic bytes
            return PickleScanResult(
                is_safe=False,
                finding_code="CORRUPTED_OR_OBFUSCATED_PICKLE",
                details=f"Pickle disassembly failed: {str(err)}",
            )

        for opcode, arg, pos in ops:
            opname = opcode.name

            # Track string constants pushed onto the pickle stack
            if opname in (
                "SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE",
                "SHORT_BINSTRING", "BINSTRING", "STRING"
            ):
                if isinstance(arg, str):
                    extracted_strings.append(arg)
                    recent_stack.append(arg)
                    if len(recent_stack) > 16:
                        recent_stack.pop(0)

            # GLOBAL opcode: arg is "module callable"
            elif opname == "GLOBAL":
                if isinstance(arg, str):
                    parts = arg.strip().split()
                    if len(parts) >= 2:
                        module_name, func_name = parts[0], parts[1]
                    elif len(parts) == 1:
                        module_name, func_name = parts[0], ""
                    else:
                        module_name, func_name = "", ""

                    if cls._is_dangerous(module_name, func_name):
                        dangerous_findings.append({
                            "module": module_name,
                            "callable": func_name,
                            "position": str(pos),
                        })

            # STACK_GLOBAL opcode: pops module and name from stack
            elif opname == "STACK_GLOBAL":
                if len(recent_stack) >= 2:
                    func_name = str(recent_stack[-1])
                    module_name = str(recent_stack[-2])
                    if cls._is_dangerous(module_name, func_name):
                        dangerous_findings.append({
                            "module": module_name,
                            "callable": func_name,
                            "position": str(pos),
                        })

            # REDUCE opcode executes the callable on the tuple arguments!
            elif opname == "REDUCE":
                # If we recently flagged a dangerous import, REDUCE confirms execution
                pass

        if dangerous_findings:
            # Extract possible shell commands from strings found in the payload
            # Look for common malicious commands, shell invocations, etc.
            payloads: List[str] = []
            for s in extracted_strings:
                if any(x in s for x in ("sh", "curl", "wget", "bash", "exec", "python", "nc", "chmod", "rm", "cat")):
                    payloads.append(s)
            if not payloads and extracted_strings:
                payloads = extracted_strings[-3:]

            return PickleScanResult(
                is_safe=False,
                finding_code="CRITICAL_PICKLE_RCE",
                dangerous_imports=dangerous_findings,
                extracted_payloads=payloads,
                details=f"Detected {len(dangerous_findings)} dangerous callable(s) capable of remote code execution.",
            )

        return PickleScanResult(
            is_safe=True,
            details="No dangerous execution opcodes or imports detected.",
        )

    @classmethod
    def _is_dangerous(cls, module: str, callable_name: str) -> bool:
        """Determines if the module/callable pair poses arbitrary execution risk."""
        mod = module.strip().lower()
        fn = callable_name.strip().lower()

        if mod in DANGEROUS_CALLABLES:
            allowed_dangerous = DANGEROUS_CALLABLES[mod]
            if fn in allowed_dangerous or "*" in allowed_dangerous:
                return True

        # Catch dynamic import or exec calls
        if any(bad in mod for bad in ("subprocess", "pty", "commands")):
            return True

        if any(bad in fn for bad in ("system", "popen", "spawn", "eval", "exec")):
            return True

        return False
