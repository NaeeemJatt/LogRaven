# LogRaven — Compliance Framework Registry
#
# Importing this package registers every framework content pack (side effect).
# Add a new framework by dropping a module here and importing it below — no
# engine changes required.

from app.compliance.frameworks.base import (  # noqa: F401
    Control,
    Framework,
    REGISTRY,
    get_framework,
    is_registered,
    list_frameworks,
    register,
)

# MVP packs
from app.compliance.frameworks import soc2  # noqa: F401,E402
from app.compliance.frameworks import iso27001  # noqa: F401,E402
from app.compliance.frameworks import cis_aws  # noqa: F401,E402
from app.compliance.frameworks import pci_dss  # noqa: F401,E402

# Expansion packs
from app.compliance.frameworks import hipaa  # noqa: F401,E402
from app.compliance.frameworks import gdpr  # noqa: F401,E402
from app.compliance.frameworks import nist_csf  # noqa: F401,E402
from app.compliance.frameworks import nist_800_53  # noqa: F401,E402
from app.compliance.frameworks import fedramp  # noqa: F401,E402
from app.compliance.frameworks import csa_ccm  # noqa: F401,E402
from app.compliance.frameworks import iso27017  # noqa: F401,E402
from app.compliance.frameworks import iso27018  # noqa: F401,E402

DEFAULT_FRAMEWORK = "soc2"

__all__ = [
    "Control",
    "Framework",
    "REGISTRY",
    "DEFAULT_FRAMEWORK",
    "get_framework",
    "is_registered",
    "list_frameworks",
    "register",
]
