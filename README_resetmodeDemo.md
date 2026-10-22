# Patch Reset Data Demo — FastAPI + Next.js

## 1. Copy files
- `src/demo_reset.py` → `HR-Agent/src/demo_reset.py`
- `hr-agent-nextjs/app/api/demo/reset/route.ts` → matching Next.js path
- `hr-agent-nextjs/components/ResetDemoButton.tsx` → matching Next.js path

## 2. Register router in the CURRENT `src/api.py`
After creating the FastAPI `app` and the repository instance, add:

```python
from .demo_reset import demo_reset_router
app.include_router(demo_reset_router(repository))
```

`repository` must be the existing `PostgresRepository` instance, not a newly created one. If your app is constructed inside a factory, place `include_router` inside that factory, before returning the app. Do not paste a second `app = FastAPI()`.

## 3. Backend `.env` (DEMO ONLY)

```
ENVIRONMENT=development
ENABLE_DEMO_RESET=true
DEMO_RESET_SECRET=<long-random-secret>
```

Generate a random secret using `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Use the SAME secret in Next.js. Do not commit secrets.

## 4. Next.js `.env.local` (server only)

```
APP_ENVIRONMENT=development
ENABLE_DEMO_RESET=true
DEMO_RESET_SECRET=<same-long-random-secret>
DEMO_RESET_PIN=<separate-long-admin-pin>
```

`FASTAPI_URL` must remain set. Never prefix these vars with `NEXT_PUBLIC_`. Restart both servers after changing environment variables.

## 5. Add button to HR dashboard
At top of `hr-agent-nextjs/app/page.tsx`:

```tsx
import ResetDemoButton from "@/components/ResetDemoButton";
```

Inside the HR Admin dashboard JSX (the `role === "hr"` and `page === "leaves"` section), place:

```tsx
{role === "hr" && <ResetDemoButton onReset={() => {
  // Remove local demo drafts/requests so the screen does not show stale rows.
  updateData(prev => ({ ...prev, leaves: prev.leaves.filter(l => l.employee !== "alya" && l.employee !== "bima") }));
}} />}
```

Do not remove conversations unless you explicitly want to reset chat history too. Existing repository reset only clears leave proposals, leave requests, and balances.

## 6. Security and deployment
- Reset endpoint returns 404 unless `ENABLE_DEMO_RESET=true` AND environment is `development`, `demo`, or `test`.
- Backend requires server-only shared secret. Next.js requires an independent admin PIN and confirmation dialog.
- This PIN is a **demo-only gate**, not real HR Admin authentication. Any user who learns the PIN could reset the data; do not deploy this feature publicly without real authenticated HR Admin sessions, rate limits, and CSRF/origin protection.
- Set `ENABLE_DEMO_RESET=false` on both services in production.
- Reset is destructive for both demo employees. Back up the demo database if needed.
- The existing repository method resets balances to Alya annual 8, Bima annual 3, and both sick 10 / parental 60.
- UI role selector alone is NOT authorization; the backend does not trust it.

## 7. Quick verification
1. Run FastAPI + Next.js with environment configured.
2. Open HR Admin dashboard; click Reset Data Demo; confirm; enter PIN.
3. Verify Alya annual balance = 8, Bima = 3; pending demo leave requests disappear.
4. Wrong PIN → 403; missing backend secret → 403; `ENABLE_DEMO_RESET=false` → 404.
5. Refresh employee views to load the new balances.

**Note:** Existing `MemoryRepository` does not implement `reset_demo_leave_data`; this patch targets the PostgreSQL/Neon repository.
