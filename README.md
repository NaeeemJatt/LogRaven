# 🦅 LogRaven

> **Next-Generation AI Cloud Security, SIEM & Continuous Multi-Cloud Compliance Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com)
[![Compliance](https://img.shields.io/badge/Frameworks-12_Standards-orange?style=flat-square)](https://lograven.io)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)](#license)

---

## 📖 Overview

**LogRaven** is an enterprise-grade cloud security posture management (CSPM), SIEM, and continuous compliance automation platform. Designed for modern SecOps and compliance teams, LogRaven continuously monitors multi-cloud environments, visualizes complex lateral attack paths, provides 1-click remediation scripts across multiple infrastructure-as-code formats, and streamlines regulatory audits via a tamper-evident Cryptographic Evidence Vault.

---

## ⚡ Key Capabilities

### ☁️ 1. Multi-Cloud Fleet Management
- **AWS Integration**: Zero-credential discovery via AWS Security Token Service (`STS AssumeRole`) with external ID verification.
- **Google Cloud Platform (GCP)**: Service Account JSON credentialing and project-level asset scanning.
- **Microsoft Azure**: Azure Active Directory / Entra ID Service Principal integration (`Tenant ID`, `Client ID`, `Client Secret`).
- Real-time fleet health monitoring, connection validation, and multi-tenant isolation.

### 🛡️ 2. Continuous Multi-Framework Compliance Engine
Automated scanning and continuous evidence collection across **12 global compliance frameworks**:
| Framework | Version / Scope | Primary Coverage |
|:---|:---|:---|
| **SOC 2 Type II** | Trust Services Criteria (TSC) 2017 | Security, Availability, Confidentiality |
| **ISO/IEC 27001** | 2022 Revision | Annex A Controls, Information Security Management |
| **CIS Benchmarks** | CIS AWS Foundations v3.0 | Identity, Logging, Networking, Storage |
| **PCI-DSS** | v4.0 | Cardholder Data Protection & Perimeter Hardening |
| **HIPAA Security Rule** | 45 CFR Part 160 & 164 | ePHI Safeguards & Access Controls |
| **GDPR** | Art. 25 & 32 | Technical & Organizational Measures (TOMs) |
| **NIST CSF** | v2.0 | Identify, Protect, Detect, Respond, Recover |
| **NIST SP 800-53** | Revision 5 | Federal Security & Privacy Control Catalog |
| **FedRAMP** | Moderate Baseline | Cloud Service Provider Federal Authorization |
| **CSA CCM** | v4.0 | Cloud Security Alliance Cloud Controls Matrix |
| **ISO/IEC 27017** | Cloud Security Standards | Cloud Service Customer & Provider Controls |
| **ISO/IEC 27018** | Cloud Privacy Standards | PII Protection in Public Cloud Computing |

### 🕸️ 3. Interactive Attack Path DAG & Blast Radius Analysis
- Graph-based visualization of complex multi-cloud attack chains.
- Identifies lateral movement opportunities, privilege escalation vectors, and misconfigured perimeter gateways.
- Automated blast radius calculation to quantify business risk and prioritize high-severity exposures.

### 🛠️ 4. 1-Click Multi-Format Remediation Studio
Instant, production-ready remediation blueprints tailored to your infrastructure:
- **Terraform HCL**: Native declarative configurations for automated pipeline deployment.
- **CLI Commands**: Copy-paste commands for `AWS CLI v2`, `gcloud`, and `Azure CLI`.
- **AWS CloudFormation**: Ready-to-deploy YAML / JSON templates.
- **Hardening Bash Scripts**: Zero-dependency automation scripts with rollback instructions.

### 🔐 5. Auditor Portal & Cryptographic Evidence Vault
- **Time-Limited Auditor Access**: Secure, tokenized share links with custom expiration windows.
- **Cryptographic Packaging**: Bundles audit findings, raw cloud configuration snapshots, and control mappings into an encrypted ZIP package.
- **SHA-256 Tamper-Evident Manifest**: Every evidence export includes a cryptographic `manifest.json` verifying the integrity of every included artifact.
- **Exceptions Ledger**: Formal tracking of accepted operational risks, compensating controls, and policy suppressions.

### 🔍 6. Threat Detection & SIEM Engine
- Ingests diverse log formats: **Windows EVTX**, **Syslog**, **AWS CloudTrail**, **Nginx**, and **Wazuh Decoders**.
- AI-assisted log analysis with automated mapping to **MITRE ATT&CK** Tactics, Techniques, and Procedures (TTPs).
- Generates publication-ready PDF and CSV incident investigation reports.

---

## 🏗️ Architecture & Technology Stack

```mermaid
graph TD
    Client["Modern Frontend (React 18 + Vite + TypeScript + Tailwind)"] -->|HTTPS / REST API| API["FastAPI Backend (Python 3.11)"]
    API -->|Async ORM| DB[(PostgreSQL 15)]
    API -->|Task Scheduling| Redis[(Redis 7)]
    Redis -->|Message Broker| Worker["Celery 5 Workers"]
    Worker -->|Cloud APIs| MultiCloud["AWS STS / GCP Cloud SDK / Azure Entra"]
    Worker -->|AI Grading & Triage| AIEngine["Cloud AI Engine"]
    Worker -->|Evidence Vault Generation| Storage["Local / AWS S3 Storage"]
```

| Layer | Technology | Key Responsibility |
|:---|:---|:---|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Lucide | Responsive UI, interactive DAG graphs, posture dashboards |
| **API Server** | FastAPI, Pydantic v2, Starlette | High-performance asynchronous REST endpoints |
| **Database** | PostgreSQL 15, SQLAlchemy 2.0 (asyncpg), Alembic | Relational data, multi-cloud fleet state, audit histories |
| **Task Queue** | Celery 5, Redis 7 | Distributed cloud evidence ingestion & report synthesis |
| **AI Engine** | Cloud AI Integration | Automated threat triage, root-cause correlation, compliance scoring |
| **Document Engine**| ReportLab, WeasyPrint | Cryptographic ZIP vaults, executive PDF compliance packages |

---

## 📂 Project Structure

```
LogRaven/
├── backend/
│   ├── alembic/                # Alembic database schema migrations
│   ├── app/
│   │   ├── api/                # API routers (auth, compliance, cloud accounts, auditor)
│   │   ├── compliance/         # Crosswalk engine, evidence vault, auditor logic
│   │   ├── core/               # Configuration, security, database sessions
│   │   ├── models/             # SQLAlchemy ORM models (audits, cloud accounts, users)
│   │   ├── schemas/            # Pydantic validation schemas
│   │   ├── services/           # Cloud collection, log parsers, AI analyzers
│   │   └── tasks/              # Celery background tasks & workers
│   ├── requirements.txt        # Python backend dependencies
│   └── run-api.ps1             # Backend PowerShell launcher
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable UI components & modals
│   │   ├── pages/              # Views (Compliance, Accounts, Auditor, Remediation, Threat)
│   │   ├── services/           # Axios API client bindings
│   │   └── types/              # TypeScript interface definitions
│   ├── package.json            # Node.js dependencies
│   └── vite.config.ts          # Vite build configuration
├── docker-compose.yml          # Containerized multi-service orchestration
└── README.md                   # Platform documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ & `npm`
- **PostgreSQL**: 15+ (local or containerized)
- **Redis**: 7+ (required for background tasks & Celery)

---

### Step 1: Environment Configuration

Create a root `.env` and copy it to `backend/.env`:
```bash
cp .env.example .env
cp .env.example backend/.env
```

Ensure the following core variables are configured:
```ini
# Database & Cache
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lograven
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your-secure-random-32-character-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Provider
GEMINI_API_KEY=your_gemini_or_cloud_ai_api_key

# Execution Modes
STORAGE_BACKEND=local
USE_ASYNCIO_INVESTIGATION_PIPELINE=true
```

---

### Step 2: Database Setup & Migrations

Apply the latest Alembic schema migrations:
```bash
cd backend
alembic upgrade head
```

---

### Step 3: Run the Application

#### Option A: Running Locally (Development)

**Terminal 1 — Backend API Server:**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*API will be live at `http://127.0.0.1:8000` with Swagger docs at `http://127.0.0.1:8000/docs`.*

**Terminal 2 — Celery Background Worker (for cloud audits):**
```powershell
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3 — Frontend UI:**
```bash
cd frontend
npm install
npm run dev
```
*Frontend will be live at `http://localhost:5173`.*

---

#### Option B: Running with Docker Compose

To launch the full containerized stack (API, Worker, Database, Redis):
```bash
docker compose up -d
```
All services will initialize automatically and connect across the internal Docker network.

---

## 🛡️ Cloud Provider Configuration

### Connecting AWS via STS AssumeRole
1. In the target AWS account, create an IAM Role granting read-only access (e.g., `SecurityAudit`, `ViewOnlyAccess`).
2. Set the Trust Policy Principal to your LogRaven AWS Account ID with a secure `ExternalId`.
3. In LogRaven: Navigate to **Cloud Accounts** ➡️ **Connect AWS** ➡️ Enter Role ARN & Account ID.
4. LogRaven assumes the role via STS on-demand. **No long-lived access keys are ever stored.**

### Connecting Google Cloud Platform (GCP)
1. In the GCP Console, create a Service Account with `Viewer` or `Security Reviewer` permissions.
2. Generate and download a Service Account Key in JSON format.
3. In LogRaven: Navigate to **Cloud Accounts** ➡️ **Connect GCP** ➡️ Provide Project ID & Service Account JSON credentials.

### Connecting Microsoft Azure
1. Register an Application in Azure Active Directory (Entra ID) with `Reader` role on the target Subscription.
2. Generate a Client Secret.
3. In LogRaven: Navigate to **Cloud Accounts** ➡️ **Connect Azure** ➡️ Enter `Subscription ID`, `Tenant ID`, `Client ID`, and `Client Secret`.

---

## 🧪 Testing & Verification

LogRaven features end-to-end testing coverage validating the entire pipeline from multi-cloud onboarding through auditor evidence generation.

### Run E2E Desktop Browser Suite
```bash
cd temp
node run_chrome_demo.mjs
```
*Executes automated headless/headful Chrome browser tests verifying all 10 compliance milestones.*

### Run Backend Unit & Integration Tests
```bash
cd backend
pytest tests/ -v
```

---

## 🔒 Security Best Practices

- **Zero-Storage for AWS Keys**: Uses AWS STS temporary credentials with a maximum 1-hour session duration.
- **Cryptographic Evidence Integrity**: Every evidence vault ZIP export includes an immutable SHA-256 manifest.
- **Audit Logging**: Every action across the platform is logged with user context, timestamp, and IP address.
- **Role-Based Access Control**: Granular roles for Administrators, SecOps Analysts, and External Auditors.

---

## 📄 License

Copyright © 2026 LogRaven Inc. All rights reserved.
Proprietary software. Unauthorized copying, distribution, or modification is strictly prohibited.
