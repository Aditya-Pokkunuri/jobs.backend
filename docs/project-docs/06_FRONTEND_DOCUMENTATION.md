# Ottobon Jobs — Frontend Documentation

---

## 1. Overview

The frontend is a React 18 single-page application built with Vite. It provides the user interface for job browsing, resume management, match analysis, real-time chat, and admin operations. The application uses role-based routing to show different features to Seekers, Providers, and Admins.

---

## 2. Project Structure

```
Frontend/
├── index.html               # HTML entry point
├── package.json             # Dependencies and scripts
├── vite.config.js           # Vite configuration
├── src/
│   ├── App.jsx              # Root component with routing
│   ├── main.jsx             # React DOM render entry
│   ├── index.css            # Global styles and CSS variables
│   │
│   ├── api/                 # HTTP client and API modules
│   │   ├── client.js        # Axios instance + Supabase SDK
│   │   ├── authApi.js       # Login, register, logout
│   │   ├── usersApi.js      # Profile, resume upload
│   │   ├── jobsApi.js       # Job CRUD and feed
│   │   ├── matchingApi.js   # Match analysis
│   │   ├── chatApi.js       # Chat session management
│   │   └── adminApi.js      # Ingestion trigger
│   │
│   ├── context/
│   │   └── AuthContext.jsx  # Global auth state (memoized)
│   │
│   ├── hooks/
│   │   ├── useAuth.js       # Auth context consumer
│   │   └── useWebSocket.js  # WebSocket with heartbeat
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── AppShell.jsx # Main layout wrapper
│   │   │   ├── Navbar.jsx   # Top navigation bar
│   │   │   └── Sidebar.jsx  # Side navigation
│   │   ├── ui/
│   │   │   ├── Button.jsx   # Multi-variant button
│   │   │   ├── Card.jsx     # Glass-panel card
│   │   │   ├── Badge.jsx    # Skill/tag pill
│   │   │   ├── Loader.jsx   # Spinner component
│   │   │   └── ScoreGauge.jsx # Circular score display
│   │   └── ProtectedRoute.jsx # Role-based route guard
│   │
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── LoginPage.jsx
│   │   │   └── RegisterPage.jsx
│   │   ├── seeker/
│   │   │   ├── JobFeedPage.jsx
│   │   │   ├── JobDetailPage.jsx
│   │   │   ├── MatchPage.jsx
│   │   │   └── ProfilePage.jsx
│   │   ├── chat/
│   │   │   └── ChatPage.jsx
│   │   ├── provider/
│   │   │   ├── CreateJobPage.jsx
│   │   │   └── MyListingsPage.jsx
│   │   └── admin/
│   │       ├── ControlTowerPage.jsx
│   │       └── IngestionPage.jsx
│   │
│   └── utils/
│       └── constants.js     # API URLs, WebSocket URL, role constants
```

---

## 3. Routing

**File:** `src/App.jsx`

The application uses React Router v6 with nested routes. All authenticated routes are wrapped in an `AppShell` layout (Navbar + Sidebar + content area).

### Route Table

| Path | Page | Access | Description |
|------|------|--------|-------------|
| `/login` | LoginPage | Public | Email/password login |
| `/register` | RegisterPage | Public | Registration with role selection |
| `/` | Redirect → `/jobs` | Authenticated | Default redirect |
| `/jobs` | JobFeedPage | Authenticated | Browse all active jobs |
| `/jobs/:id` | JobDetailPage | Authenticated | Full job detail with 4 pillars |
| `/jobs/:id/match` | MatchPage | Seeker only | Match analysis and resume upload |
| `/profile` | ProfilePage | Seeker only | View profile and manage resume |
| `/chat` | ChatPage | Seeker only | AI Career Coach chat |
| `/provider/create` | CreateJobPage | Provider only | Create a new job posting |
| `/provider/listings` | MyListingsPage | Provider only | View own job listings |
| `/admin/tower` | ControlTowerPage | Admin only | Chat session management |
| `/admin/ingest` | IngestionPage | Admin only | Trigger job scraping |

### Route Protection

The `ProtectedRoute` component checks:
1. Is the user authenticated? If not, redirect to `/login`
2. Does the user's role match the `allowedRoles` array? If not, redirect to home

---

## 4. Authentication Context

**File:** `src/context/AuthContext.jsx`

The `AuthProvider` wraps the entire application and provides authentication state to all components.

### State Provided

| Property | Type | Description |
|----------|------|-------------|
| `user` | object or null | Supabase auth user object |
| `session` | object or null | Supabase session with JWT |
| `role` | string or null | User role: "seeker", "provider", or "admin" |
| `loading` | boolean | True during initial session check |
| `isAuthenticated` | boolean | Shorthand for `!!session?.user` |

### How It Works

1. On mount, calls `supabase.auth.getSession()` to check for an existing session
2. If a session exists, sets the user and fetches their role from the backend
3. Registers an `onAuthStateChange` listener for future login/logout events
4. Uses a `useRef` flag to skip the initial auth event (already handled)
5. On 503 errors, retries `fetchRole` up to 2 times with 1-second delays

### Performance Optimization

The context value is wrapped in `useMemo` with `[session, user, role, loading]` dependencies. This prevents unnecessary re-renders of consumer components when unrelated state changes occur.

**Architectural rule:** High-frequency state (like chat typing indicators) should never be placed in AuthContext. Use a separate dedicated context scoped to the relevant component subtree.

---

## 5. API Layer

**File:** `src/api/client.js`

### Axios Client

- Base URL: `VITE_API_BASE_URL` from environment variables
- **Request interceptor**: Automatically attaches the Supabase JWT to every outgoing request
- **Response interceptor**: Auto-retries 503 errors up to 3 times with linear backoff (1s, 2s, 3s)

### Supabase Client

- Created using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- Used for authentication (login, register, logout)

### API Modules

| Module | Functions | Description |
|--------|-----------|-------------|
| `authApi.js` | `loginUser(email, pw)`, `registerUser(email, pw, role)`, `logoutUser()` | Supabase Auth operations |
| `usersApi.js` | `getMyProfile()`, `uploadResume(file)` | User profile and resume management |
| `jobsApi.js` | `createJob(data)`, `getProviderJobs()`, `getJobFeed(skip, limit)`, `getJobDetails(id)` | Job CRUD operations |
| `matchingApi.js` | `matchJob(jobId)` | Match analysis |
| `chatApi.js` | `createChatSession()`, `getChatSession(id)` | Chat session management |
| `adminApi.js` | `triggerIngestion(source)` | Admin ingestion trigger |

---

## 6. Pages

### 6.1 Auth Pages

**LoginPage** — Email/password form. On success, navigates to `/jobs`. Shows error messages for invalid credentials.

**RegisterPage** — Email, password, and role selector (Seeker/Provider). Calls Supabase `signUp()`. On success, navigates to `/login` with a success message.

### 6.2 Seeker Pages

**JobFeedPage** — Displays a grid of active job cards. Includes a search bar that filters by title, company, and skills in real time. Each card shows the job title, company, required skills (as badges), and a link to the detail page. Fetches the first 50 jobs on mount.

**JobDetailPage** — Shows the full 4-pillar job detail:
1. Description — Raw job description
2. Skills Required — List of skills as badges
3. Interview Prep — 5 AI-generated questions
4. Resume Tips — 5 AI-generated optimization tips

Includes a "Check My Fit" button (links to MatchPage) and a "Check Again" button if AI enrichment is still processing.

**MatchPage** — Two-phase page:
1. Resume upload zone (if no resume uploaded yet)
2. Match analysis display with:
   - Circular ScoreGauge showing percentage (0-100%)
   - Gap detection badge (red if score < 70%)
   - "Talk to Career Coach" button (links to ChatPage)
   - "Apply Now" button (links to external application URL)

**ProfilePage** — Shows user information (email, name, role) and resume management:
- Upload zone accepting PDF/DOCX files
- Processing status indicator during upload
- Current resume filename display
- Success/error feedback messages

### 6.3 Chat Page

**ChatPage** — Full-screen real-time chat interface:
- Creates or reuses a chat session
- Connects to WebSocket and displays message history
- Messages are visually differentiated by role:
  - User messages: right-aligned with accent background
  - Assistant messages: left-aligned with surface background
  - System messages: centered with muted styling
  - Admin messages: left-aligned with distinct styling
- Input field at the bottom with send button
- Connection status indicator

### 6.4 Provider Pages

**CreateJobPage** — Form with three fields:
- Title (required, minimum 3 characters)
- Description (required, minimum 20 characters)
- Skills (comma-separated list)

On submit, calls `POST /jobs` and shows a success message with the note that AI enrichment is processing in the background.

**MyListingsPage** — Table or card view of all jobs posted by the logged-in provider. Shows title, status, creation date, and skills.

### 6.5 Admin Pages

**ControlTowerPage** — Dashboard showing all active chat sessions. Admin can view session details and trigger a takeover to switch from AI to human mode.

**IngestionPage** — Four branded cards (one per scraper source) plus a "Sync All" button:
- Deloitte (green), PwC (orange), KPMG (blue), EY (yellow)
- Each card triggers ingestion for that specific source
- Results are displayed as formatted JSON on completion
- Shows loading spinners during processing

---

## 7. Components

### 7.1 Layout Components

**AppShell** — Main layout wrapper. Renders the Navbar at the top, Sidebar on the left, and routed page content via `<Outlet>`.

**Navbar** — Top navigation bar with:
- Ottobon Jobs branding
- User dropdown menu (Profile, Settings, Logout)
- Role-aware menu items

**Sidebar** — Left navigation with role-based links:
- Seeker: Jobs, Profile, Chat
- Provider: Create Job, My Listings
- Admin: Control Tower, Ingestion

### 7.2 UI Components

**Button** — Multi-variant button component:
- Variants: `primary` (accent color), `secondary`, `ghost`, `danger`
- Sizes: `sm`, `md`, `lg`
- Loading state: Shows a spinning Lucide Loader2 icon
- Disabled state supported

**Card** — Glass-panel container with optional hover effect and padding.

**Badge** — Small pill component for displaying skill tags or status labels.

**Loader** — Spinning animation with optional `fullScreen` mode (centered on viewport).

**ScoreGauge** — Circular SVG gauge that displays a match score percentage. Changes color based on score range (green for high, yellow for medium, red for low).

### 7.3 ProtectedRoute

Checks authentication and role authorization:
1. If `loading`, shows nothing (prevents flash)
2. If not authenticated, redirects to `/login`
3. If role not in `allowedRoles`, redirects to `/`
4. Otherwise, renders the child routes via `<Outlet>`

---

## 8. Hooks

### 8.1 useAuth

**File:** `src/hooks/useAuth.js`

Simple wrapper that calls `useContext(AuthContext)`. Provides access to `user`, `session`, `role`, `loading`, and `isAuthenticated`.

### 8.2 useWebSocket

**File:** `src/hooks/useWebSocket.js`

Manages a WebSocket connection for real-time chat.

**Features:**
- Connects to `WS_BASE_URL/ws/chat/{sessionId}` when a session ID is provided
- Handles message types: `history_replay`, `ai_reply`, `queued`, `admin_takeover`
- Optimistic message sending (shows the message before server confirms)
- 30-second heartbeat ping (`__ping__` frames) to prevent load balancer idle drops
- Pong response filtering (prevents `__pong__` from appearing in messages)
- JSON parse safety (ignores non-JSON frames)
- Proper cleanup on unmount and session change (clears heartbeat interval + closes socket)

**Returns:** `{ messages, sendMessage, isConnected, sessionStatus }`

---

## 9. Styling

- **Tailwind CSS v4** for utility classes
- **CSS Custom Properties** defined in `index.css` for theming:
  - `--accent`: Primary action color (#0066cc)
  - `--text-primary`, `--text-muted`: Text colors
  - `--bg-primary`, `--bg-surface`: Background colors
  - `--border-color`: Border color
  - `--danger`, `--success`: Status colors
  - `--radius-sm`, `--radius-md`, `--radius-lg`: Border radii
- Components use a mix of Tailwind utilities and CSS variable references
