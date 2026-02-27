# Ottobon Jobs: Backend System Design Patterns

The backend of Ottobon Jobs is designed for modularity, maintainability, and scalability. It primarily follows a decoupled architecture that separates business logic from infrastructure.

## 1. Hexagonal Architecture (Ports and Adapters)
This is the core architectural foundation of the project. It ensures that the business logic (Domain and Services) is independent of external tools, databases, and APIs.

- **Ports (`/backend/app/ports/`)**: Abstract Base Classes (ABCs) that define the "socket" or interface for external services. For example, `DatabasePort` defines how the app interacts with data without knowing *which* database is used.
- **Adapters (`/backend/app/adapters/`)**: Concrete implementations of the ports. For example, `SupabaseAdapter` implements `DatabasePort` specifically for Supabase.

## 2. Service Layer Pattern
All non-trivial business logic is encapsulated in the `/backend/app/services/` directory.

- **Deep Dive**: See [SERVICE_LAYER_PATTERN.md](file:///C:/Users/adity/Desktop/Ottobon/Jobs/docs/SERVICE_LAYER_PATTERN.md) for full architectural specs.
- **Purpose**: Services like `ChatService` or `MatchingService` orchestrate complex workflows by coordinating between multiple ports. This keeps the API routers clean and focused on request/response handling.

## 3. Dependency Injection (DI)
The backend utilizes FastAPI's dependency injection system to manage lifetimes and mock external dependencies.

- **Location**: Managed in `app/dependencies.py`.
- **Advantages**: It allows for easy swapping of implementations (e.g., using a mock DB adapter for tests) without changing the business logic or router code.

## 4. Adapter Pattern (Wrapper)
Beyond the hexagonal scope, the project uses the Adapter pattern to wrap third-party SDKs like OpenAI or Supabase. This prevents "vendor lock-in" by ensuring that the application logic only interacts with our standardized wrappers.

## 5. Domain Model Pattern
Data structures are defined using Pydantic models in `/backend/app/domain/models.py`.

- **Role**: These models act as the unified contract for data validation, serialization, and type hints across the entire application stack.

## 6. Strategy Pattern
Used within the scraping and AI workflows.

- **Implementation**: The system defines a high-level task (e.g., "Scrape a corporate portal"), and different adapter classes (e.g., `EYAdapter`, `KPMGAdapter`) provide the specific strategy for executing that task based on the target site.

## 7. Connection Manager (Observer-like)
In the chat module (`app/routers/chat.py`), the `ConnectionManager` maintains the state of active WebSocket connections. It tracks who is online and routes messages between seekers and admins.

## 8. Asynchronous Programming (Event Loop)
The backend is built entirely on Python's `asyncio`.

- **Pattern**: Every I/O-bound operation (database query, AI call, file storage) is non-blocking. This allows the server to process a high volume of concurrent users per instance.
