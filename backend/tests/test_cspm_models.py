"""
Unit tests for Module 02: Database Schema & Migration (024_cspm_deterministic_engine).
Verifies SQLAlchemy models, table definitions, constraints, indexes, and Alembic revision linking.
"""

import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import inspect
from sqlalchemy.schema import CheckConstraint, UniqueConstraint

from app.models.cspm import (
    CSPMControlCatalog,
    CSPMPolicyCatalog,
    CSPMMandateCatalog,
    CSPMEvaluationFinding,
)
from app.models import Base


def test_models_registered_in_metadata():
    tables = Base.metadata.tables
    assert "cspm_controls_catalog" in tables
    assert "cspm_policies_catalog" in tables
    assert "cspm_mandates_catalog" in tables
    assert "cspm_evaluation_findings" in tables


def test_control_catalog_table_structure():
    table = Base.metadata.tables["cspm_controls_catalog"]
    cols = {c.name: c for c in table.columns}

    assert "cid" in cols
    assert cols["cid"].primary_key is True
    assert "control_name" in cols
    assert cols["control_name"].nullable is False
    assert "service" in cols
    assert "platform" in cols
    assert "criticality" in cols
    assert "rule_spec_json" in cols


def test_policy_catalog_table_structure():
    table = Base.metadata.tables["cspm_policies_catalog"]
    cols = {c.name: c for c in table.columns}

    assert "policy_title" in cols
    assert cols["policy_title"].primary_key is True
    assert "provider" in cols
    assert "mapped_cids" in cols


def test_mandate_catalog_table_structure():
    table = Base.metadata.tables["cspm_mandates_catalog"]
    cols = {c.name: c for c in table.columns}

    assert "mandate_name" in cols
    assert cols["mandate_name"].primary_key is True
    assert "version" in cols
    assert "publisher" in cols
    assert "mapped_cids" in cols


def test_evaluation_findings_constraints_and_indexes():
    table = Base.metadata.tables["cspm_evaluation_findings"]
    cols = {c.name: c for c in table.columns}

    assert "id" in cols
    assert cols["id"].primary_key is True
    assert "tenant_id" in cols
    assert "cid" in cols
    assert "resource_urn" in cols
    assert "status" in cols

    # Verify unique constraint on (tenant_id, cid, resource_urn)
    uq_names = [c.name for c in table.constraints if isinstance(c, UniqueConstraint)]
    assert "uq_cspm_findings_tenant_cid_urn" in uq_names

    # Verify check constraint on status
    check_names = [c.name for c in table.constraints if isinstance(c, CheckConstraint)]
    assert "ck_cspm_findings_status" in check_names

    # Verify composite index idx_findings_tenant_status
    idx_names = [idx.name for idx in table.indexes]
    assert "idx_findings_tenant_status" in idx_names


def test_alembic_migration_024_chain():
    mig_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "024_cspm_deterministic_engine.py"
    assert mig_path.is_file(), f"Migration file not found at {mig_path}"

    spec = importlib.util.spec_from_file_location("mig_024", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "024"
    assert mod.down_revision == "023"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)
