# Pattern Implementation: Hexagonal Architecture (Ports & Adapters)

This document outlines the high-level design and standardized implementation of the Hexagonal Architecture pattern for the Ottobon Jobs platform. This architecture ensures that core business logic remains isolated from external infrastructure, enabling rapid testing and infrastructure flexibility.

---

## 1. Abstract Pattern Definition

Hexagonal Architecture (Ports and Adapters) organizes the system around a **Core Domain**. This core defines **Ports** (interfaces) for any interaction it requires. External systems fulfill these requirements via **Adapters** (concrete implementations).

- **The Hexagon (Core)**: Contains Domain Models and Service Logic. It represents the "business truth."
- **Ports**: Specification of *what* the application needs to do.
- **Adapters**: The technical implementation (infrastructure) of *how* to do it.

---

## 2. Directory Structure & Taxonomy

To ensure continuity across teams (Binding, Data, and Frontend), we follow this strict map:

```text
backend/app/
├── domain/         # MODELS: Pure business entities & Pydantic schemas
├── services/       # LOGIC: Orchestration; Coordinates multiple ports
├── ports/          # CONTRACTS: Abstract Base Classes (ABCs)
├── adapters/       # INFRASTRUCTURE: Implementation of ports (SQL, AI, Storage)
├── routers/        # DRIVERS: API endpoints; Translates HTTP to Core calls
└── dependencies.py # GLUE: Dependency Injection; Binds Adapters to Ports
```

---

## 3. Implementation Steps (Execution Flow)

1.  **Define the Domain Model**: Create Pydantic models in `app/domain/models.py`. These are the "language" used across all ports.
2.  **Define the Port (Contract)**: Create an Abstract Base Class (ABC) in `app/ports/`. Use only Domain Models in method signatures.
3.  **Implement the Adapter (Infrastructure)**: Create a concrete class in `app/adapters/`. This is where third-party SDKs (Supabase, OpenAI, PyPDF) are used.
4.  **Register in Dependency Injection**: Bind the adapter to the port in `app/dependencies.py`.
5.  **Inject into Service**: Pass the Port into the `JobService` or `ChatService` constructor.

---

## 4. Reference Code (AI Enrichment Pattern)

### A. The Port (The "What")
Located in `app/ports/ai_port.py`. Notice it has no knowledge of "OpenAI".

```python
from abc import ABC, abstractmethod
from app.domain.models import AIEnrichment

class AIPort(ABC):
    @abstractmethod
    async def generate_enrichment(
        self, description: str, skills: list[str]
    ) -> AIEnrichment:
        """Requirement: Input description/skills, return validated enrichment object."""
        pass
```

### C. The Service (The Orchestrator)
Located in `app/services/job_service.py`. The service **never** imports an Adapter; it only injects a Port.

```python
from app.ports.database_port import DatabasePort

class JobService:
    def __init__(self, db: DatabasePort):
        self._db = db

    async def create_job(self, job_data: dict) -> dict:
        # Core logic: validation, mapping, then calling the port
        return await self._db.create_job(job_data)
```

### D. The Glue (Dependency Injection)
Located in `app/dependencies.py`. This is where we bind concrete Adapters to abstract Ports.

```python
from app.adapters.supabase_adapter import SupabaseAdapter
from app.ports.database_port import DatabasePort

def get_db() -> DatabasePort:
    # WIRING: To switch DBs, only change the implementation class here
    return SupabaseAdapter(client=supabase_client)
```

### E. The Driver (The Router)
Located in `app/routers/jobs.py`. This is the **Binding Side** that triggers the Hexagon.

```python
from fastapi import APIRouter, Depends
from app.dependencies import get_db
from app.services.job_service import JobService

router = APIRouter()

@router.post("/jobs")
async def create(data: JobCreate, db: DatabasePort = Depends(get_db)):
    # Driver: translates HTTP -> Service Logic
    svc = JobService(db)
    return await svc.create_job(data.dict())
```

---

## 5. Error & Continuity Strategy

### Boundary Translation
Adapters must catch infrastructure exceptions (e.g., `openai.RateLimitError`) and re-throw them as **Domain Exceptions**. This prevents infrastructure "leaking" into the core.

### Cross-Validation
- **Binding Side**: Every Router must only depend on Services or Ports, never directly on Adapters.
- **Data Side**: The Database (Supabase) is just one implementation. If we move from REST to a direct SQL driver, we only change the `adapters/` folder.
- **Validation**: All Adapters must inherit from their Port ABC to ensure they strictly fulfill the contract.

---

## 6. Project Objective Alignment

This pattern was chosen specifically to solve the "Provider Lock-in" and "Testing Latency" risks:
- **Fast Testing**: We test services by mocking Ports.
- **Zero-Downtime Migration**: We can switch LLM providers or Databases by swapping a single line in `dependencies.py`.
