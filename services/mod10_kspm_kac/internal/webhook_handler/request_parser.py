"""Kubernetes AdmissionReview v1 Request Parser (PRD-MOD-10).

Extracts Pod specifications from direct Pod manifests or higher-level workloads
(Deployments, DaemonSets, StatefulSets, Jobs, CronJobs).
"""

from typing import Any, Dict, Optional, Tuple


class AdmissionRequestParser:
    """Parses Kubernetes AdmissionReview v1 payload."""

    @classmethod
    def parse_review(cls, payload: Dict[str, Any]) -> Tuple[str, str, str, str, str, Dict[str, Any], bool]:
        """Extracts (uid, kind, name, namespace, operation, pod_spec, dry_run)."""
        req = payload.get("request", {})
        if not req:
            raise ValueError("AdmissionReview payload is missing 'request' object.")

        uid = req.get("uid", "")
        kind_obj = req.get("kind", {})
        kind = kind_obj.get("kind", "Pod") if isinstance(kind_obj, dict) else str(kind_obj)
        namespace = req.get("namespace", "default")
        operation = req.get("operation", "CREATE")
        dry_run = bool(req.get("dryRun", False))

        obj = req.get("object", {}) or {}
        metadata = obj.get("metadata", {}) or {}
        name = metadata.get("name") or metadata.get("generateName") or "unnamed-workload"

        # Extract pod spec depending on workload kind
        pod_spec = cls._extract_pod_spec(kind, obj)

        return uid, kind, name, namespace, operation, pod_spec, dry_run

    @classmethod
    def _extract_pod_spec(cls, kind: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Unwraps the pod spec from Pod or controller templates."""
        spec = obj.get("spec", {}) or {}

        # Direct Pod
        if kind == "Pod":
            return spec

        # Deployment, ReplicaSet, DaemonSet, StatefulSet, Job
        if "template" in spec:
            template = spec.get("template", {}) or {}
            return template.get("spec", {}) or {}

        # CronJob
        if "jobTemplate" in spec:
            job_template = spec.get("jobTemplate", {}) or {}
            job_spec = job_template.get("spec", {}) or {}
            template = job_spec.get("template", {}) or {}
            return template.get("spec", {}) or {}

        return spec
