# Ottobon Jobs Backend: Service Layer Architecture

## 1. Introduction

The Service Layer Pattern serves as the central **"brain"** of the Ottobon Jobs backend application. Its primary purpose is to orchestrate complex business processes while strictly maintaining isolation from infrastructure components (like databases) and transport protocols (like HTTP).

### Core Objectives:

- **Isolation**: Prevents API routers from becoming bloated with business logic.
- **Reusability**: Ensures the same logic (e.g., `JobService`) can be triggered by a REST API, a background worker, or a CLI tool without modification.
- **Atomicity**: Allows services to manage transactions and coordinate multiple operations across domains as a single unit.

---

## 2. Architectural Overview

The Service Layer acts as a strict boundary between the **API Routers** (Transport Layer) and the **Ports/Adapters** (Infrastructure Layer).

![Service Layer Architecture & Orchestration Flow](file:///C:/Users/adity/.gemini/antigravity/brain/2749fb5c-9250-418f-8cfc-80955298d095/media__1771954679414.jpg)

### Conceptual Flow:
- **Top Tier (Strategic Flow)**: Visualizes the entry point from HTTP/FastAPI into the pure Python service engine. Notice the bidirectional flow: Python arguments enter, and validated Pydantic Domain Models exit.
- **Bottom Tier (Tactical Orchestration)**: Using `MatchingService` as the reference implementation, it shows the multi-step retrieval, computation, and AI enrichment sequence that happens behind the scenes for every query.

### Shared Responsibilities

| **Component** | **Primary Responsibility** |
| --- | --- |
| **API Router** | Parses incoming requests, handles authentication, calls the Service, and returns HTTP status codes. |
| **Service Layer** | Validates internal business rules, calculates results, and orchestrates multiple Ports. |
| **Ports / Adapters** | Handles raw external I/O operations (SQL databases, AI API calls) and returns Domain Models. |

> [!IMPORTANT]
> **THE GOLDEN RULE:** Services must never know they are being called via HTTP. They deal strictly and exclusively with Python objects and Domain Models.

---

## 3. Standardized Implementation

### Directory Taxonomy

All service layer components reside in `backend/app/services/` to maintain logical grouping.

```plaintext
backend/app/services/
├── matching_service.py      # Large orchestration (DB + AI)
├── enrichment_service.py    # Background task orchestration
├── chat_service.py          # State-heavy logic
└── job_service.py           # Simple CRUD orchestration
```

### Dependency Injection Pattern

Services **must** inject their dependencies (Ports) via the constructor. This is critical for swapping real infrastructure (Postgres) with fakes (In-Memory) during testing.

```python
class MyService:
    def __init__(self, db_port: DatabasePort, ai_port: AIPort):
        self._db = db_port  # Dependency is injected, not imported
        self._ai = ai_port
```

---

## 4. Reference Code: MatchingService Deep-Dive

The `MatchingService` is the flagship reference for how to coordinate between the Database and the AI Engine.

```python
class MatchingService:
    """Flagship Orchestration Service"""

    def __init__(self, db: DatabasePort, ai: AIPort):
        self._db = db
        self._ai = ai

    async def calculate_match(self, user_id: str, job_id: str) -> MatchResult:
        # 1. ORCHESTRATION: Retrieve data via Ports
        user = await self._db.get_user(user_id)
        job = await self._db.get_job(job_id)

        # 2. BUSINESS RULES: Pure Python logic
        score = compute_similarity(user.embedding, job.embedding)
        gap_detected = score < 0.70 

        # 3. SEQUENCE CONTROL: Conditional logic
        if gap_detected:
            analysis = await self._ai.analyze_gap(user.text, job.text)
            return MatchResult(score=score, gap_analysis=analysis)

        # 4. RETURN: Always return a clean Domain Model
        return MatchResult(score=score)
```

---

## 5. Developer Workflow: Implementation Steps

1. **Interface Mapping**: Identify the Ports needed. If a database operation is missing, work with the Data Team to update the `DatabasePort` interface first.
2. **Domain Logic**: Write the business logic in the service method. **Do not** place SQL queries or AI configuration settings (e.g., temperatures) here; those belong in Adapters.
3. **DI Injection**: Register your new service in `backend/app/dependencies.py` to make it available to routers.

---

## 6. Unit Testing Patterns

Because services inject Ports (Abstract Base Classes), tests run isolated from databases or API keys, reducing test time from seconds to milliseconds.

- **Mock the Port**: Use `unittest.mock` to generate a fake `DatabasePort`.
- **Define Behavior**: Program the mock to return a specific `UserProfile` for the test case.
- **Assert Logic**: Execute the service and verify that it correctly calculates business outcomes based on the mock data.

---

## 7. Project Continuity & Objectives

- **Frontend Continuity**: Changes to API request formats do not affect core matching logic.
- **Type Safety**: All service methods must return **Domain Models** (Pydantic objects) rather than raw dictionaries to maintain type safety across the application.
- **Future Proofing**: We can swap databases or AI providers by changing **Ports**, not the **Service**.
