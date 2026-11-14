"""Container Runtime Socket Mount Checker (PRD-MOD-10 / TC-MOD10-002).

Detects hostPath mounts of Docker, containerd, CRI-O, or Podman sockets,
which allows container breakout and full host takeover.
"""

from typing import Any, Dict, List, Set

DANGEROUS_SOCKET_PATHS: Set[str] = {
    "/var/run/docker.sock",
    "/run/containerd/containerd.sock",
    "/run/docker.sock",
    "/var/run/crio/crio.sock",
    "/run/crio/crio.sock",
    "/run/podman/podman.sock",
    "/var/run/podman/podman.sock",
}


class SocketMountChecker:
    """Detects volume mounts exposing host container engine sockets."""

    DENIAL_MESSAGE = "DENIED: Mounting container runtime socket is prohibited by LogRaven KSPM policy"

    @classmethod
    def evaluate_pod_spec(cls, pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        volumes = pod_spec.get("volumes", [])
        dangerous_vol_names: Set[str] = set()

        # Check hostPath volumes in pod
        for vol in volumes:
            vol_name = vol.get("name", "")
            host_path_obj = vol.get("hostPath", {})
            if host_path_obj:
                path = host_path_obj.get("path", "").strip()
                if path in DANGEROUS_SOCKET_PATHS or any(s in path for s in ("docker.sock", "containerd.sock", "crio.sock")):
                    dangerous_vol_names.add(vol_name)
                    findings.append({
                        "rule_id": "K8S_CONTAINER_RUNTIME_SOCKET_MOUNT",
                        "severity": "CRITICAL",
                        "volume_name": vol_name,
                        "socket_path": path,
                        "message": cls.DENIAL_MESSAGE,
                    })

        # Check container volumeMounts as well
        all_containers: List[Dict[str, Any]] = []
        all_containers.extend(pod_spec.get("containers", []))
        all_containers.extend(pod_spec.get("initContainers", []))
        all_containers.extend(pod_spec.get("ephemeralContainers", []))

        for c in all_containers:
            c_name = c.get("name", "unknown")
            for vm in c.get("volumeMounts", []):
                mount_path = vm.get("mountPath", "")
                vol_name = vm.get("name", "")
                if (
                    mount_path in DANGEROUS_SOCKET_PATHS
                    or any(s in mount_path for s in ("docker.sock", "containerd.sock", "crio.sock"))
                    or vol_name in dangerous_vol_names
                ):
                    if not any(f.get("volume_name") == vol_name for f in findings):
                        findings.append({
                            "rule_id": "K8S_CONTAINER_RUNTIME_SOCKET_MOUNT",
                            "severity": "CRITICAL",
                            "container": c_name,
                            "volume_name": vol_name,
                            "mount_path": mount_path,
                            "message": cls.DENIAL_MESSAGE,
                        })

        return findings
