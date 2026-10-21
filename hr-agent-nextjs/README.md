# HRAgent — Next.js UI for HR Agent Milestone 2

Responsive Next.js UI with demo login for **Alya**, **Bima**, **HR Admin**, and **Monitoring Admin**. Includes conversation bubbles, per-user local chat history, light/dark/system themes, leave request drafting with explicit confirmation, HR approval/rejection, and monitoring demo.

## Run locally

Requires Node.js 20+.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Select a demo role and click **Masuk sebagai ...**. **No password is required because this is a UI prototype.**

## Optional FastAPI connection

Copy `.env.example` to `.env.local`, set `FASTAPI_URL`, `FASTAPI_CHAT_PATH` (the exact `API_PATHS["chat"]` value from your `ui_contract.py`), and `DEMO_TOKEN_ALYA` / `DEMO_TOKEN_BIMA`. Restart `npm run dev`.

The Next.js server proxies chat to FastAPI, keeping demo tokens out of client-side JavaScript. The backend response is displayed with citations. The UI's multi-turn leave flow is **demo logic**, not a replacement for backend-side agent memory.

## Important limitations before production

- **Demo login is not secure authentication.** The selected role is stored in browser session storage. Do not use real HR/employee data or expose admin actions publicly.
- **Demo leave requests and approvals are saved only in localStorage** and synchronize across tabs on the same browser, not across devices or users. Connect HR actions to role-authorized FastAPI endpoints and Neon PostgreSQL for real shared state.
- **Monitoring metrics are placeholders** until a protected admin endpoint is connected.
- The demo leave confirmation does **not** call the FastAPI proposal confirmation endpoint; production integration must use the existing proposal ID, idempotency key, and explicit confirmation.
- The UI supports multiple turns for a simple leave request. Real conversational memory and identity authorization must be enforced on the backend.
- The instructor's Docker Compose / Streamlit acceptance requirements should be checked before removing existing Streamlit files.

## Integration targets

Existing `app.py` functionality maps to: `API_PATHS["chat"]`, `API_PATHS["confirm"]`, `API_PATHS["my_requests"]`, `API_PATHS["monitoring_summary"]`, `API_PATHS["monitoring_alerts"]`. HR approval/rejection endpoints need to be confirmed or implemented in FastAPI. Keep monitoring and HR admin roles separate.
