# API Testing Guide

> **Why you got `401 Unauthorized`:** Protected endpoints require a Supabase JWT Bearer token.  
> Since there's no frontend login yet, you need to get the token manually from Supabase.

---

## Step 1: Create a Test User in Supabase

1. Go to your **Supabase Dashboard** → **Authentication** → **Users**
2. Click **"Add User"** → **"Create New User"**
3. Fill in:
   - Email: `test@ottobon.cloud`
   - Password: `TestPass123!`
   - ✅ Auto-confirm email
4. Click **Create User**
5. **Copy the user's UUID** from the user list (you'll need it for Step 2)

---

## Step 2: Insert the User into Your `users` Table

The Supabase Auth user exists in `auth.users`, but your API reads from `public.users`. You need to insert a matching row:

```sql
-- Run in Supabase SQL Editor
INSERT INTO public.users (id, email, role, full_name)
VALUES (
  'PASTE-UUID-FROM-STEP-1',
  'test@ottobon.cloud',
  'provider',          -- use 'seeker', 'provider', or 'admin'
  'Test User'
);
```

> **Tip:** Create one user per role for thorough testing:
> - `provider@ottobon.cloud` with role `provider`
> - `seeker@ottobon.cloud` with role `seeker`
> - `admin@ottobon.cloud` with role `admin`

---

## Step 3: Get a JWT Token

### Option A: Using curl (recommended)

```bash
curl -X POST "https://YOUR-PROJECT.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR-ANON-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ottobon.cloud",
    "password": "TestPass123!"
  }'
```

### Option A (PowerShell version):

```powershell
$body = @{
    email = "test@ottobon.cloud"
    password = "TestPass123!"
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Uri "https://YOUR-PROJECT.supabase.co/auth/v1/token?grant_type=password" `
  -Method POST `
  -Headers @{ "apikey" = "YOUR-ANON-KEY"; "Content-Type" = "application/json" } `
  -Body $body

# Copy this token:
$response.access_token
```

### Option B: Using Supabase JavaScript Console

1. Go to **Supabase Dashboard** → **SQL Editor**
2. Or open browser DevTools console on any Supabase page and run:

```javascript
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'test@ottobon.cloud',
  password: 'TestPass123!'
});
console.log(data.session.access_token);
```

**The response will contain an `access_token`** — this is your JWT Bearer token. Copy it.

---

## Step 4: Use the Token in Swagger UI

1. Open **http://127.0.0.1:8000/docs**
2. Click the **🔒 Authorize** button (top-right)
3. In the **Value** field, paste your token:
   ```
   Bearer eyJhbGciOiJIUzI1NiIs...your-token-here
   ```
4. Click **Authorize** → **Close**
5. Now all protected endpoints will include the token automatically ✅

---

## Step 5: Test the Endpoints

### Test order (recommended):

| # | Endpoint | What to verify |
|---|---|---|
| 1 | `GET /` | Health check — should always return `200 OK` (no auth needed) |
| 2 | `GET /users/me` | Returns your profile — confirms auth works |
| 3 | `POST /jobs` | Create a job — should return `202` with a job ID |
| 4 | `GET /jobs/feed` | Should list the job you just created |
| 5 | `GET /jobs/{id}/details` | Paste the job ID — after ~5 sec, resume_guide and prep_guide should be populated |
| 6 | `POST /users/resume` | Upload a PDF/DOCX — should parse and store |
| 7 | `GET /users/me` | Check that `resume_text` and `resume_file_name` are now populated |
| 8 | `GET /users/me/resume` | Should return a signed download URL |
| 9 | `POST /jobs/{id}/match` | Match your resume against the job — returns similarity score |
| 10 | `POST /chat/sessions` | Create a new chat session |
| 11 | `GET /chat/sessions/{id}` | Verify the session was created |

### WebSocket testing (Step 12):

Swagger can't test WebSockets. Use a tool like **Postman** or a simple script:

```python
# Save as test_ws.py and run: python test_ws.py
import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/ws/chat/YOUR-SESSION-ID"
    async with websockets.connect(uri) as ws:
        await ws.send("Hello, what jobs do you have?")
        response = await ws.recv()
        print(f"AI replied: {response}")

asyncio.run(test())
```

---

## Quick Reference: Replace These Placeholders

| Placeholder | Where to find it |
|---|---|
| `YOUR-PROJECT` | Supabase Dashboard → Settings → API → Project URL |
| `YOUR-ANON-KEY` | Supabase Dashboard → Settings → API → `anon` `public` key |
| `PASTE-UUID-FROM-STEP-1` | Supabase Dashboard → Authentication → Users → click user → UUID |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `401 Not authenticated` | No token or expired token | Get a fresh token (Step 3) |
| `401 Invalid token` | Wrong `SUPABASE_JWT_SECRET` in `.env` | Copy from Supabase → Settings → API → JWT Secret |
| `404 User not found` | Auth user exists but not in `public.users` | Run the INSERT from Step 2 |
| `422 Unprocessable Entity` | Invalid request body | Check the schema in Swagger |
| `500 Internal Server Error` | Check terminal logs for details | Usually a missing `.env` value |

---

*Save this file. Once the frontend is built, login will handle all of this automatically.*
