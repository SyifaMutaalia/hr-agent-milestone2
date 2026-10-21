# Next.js ↔ FastAPI integration

1. Start FastAPI in the parent HR-Agent directory: `uv run uvicorn src.api:app --reload --port 8000`.
2. Copy `.env.example` to `.env.local` in `hr-agent-nextjs`; configure server-only tokens from `demo_personas.json` and `FASTAPI_URL`.
3. `npm install && npm run dev`, open http://localhost:3000.
4. Chat forwards to POST `/api/v1/chat`; action confirmation to POST `/api/v1/action-proposals/{proposal_id}/confirm`; employee leave list to GET `/api/v1/leave-requests/me`; monitoring to GET `/api/v1/monitoring/summary` and `/api/v1/monitoring/alerts`.

**Important limitations:** Login is still a role picker (NOT authentication). The frontend uses server-side demo tokens; the proxy must NOT be deployed publicly in this form because a client could claim a different role. Add real login/session validation before deployment. HR approval/rejection endpoint is NOT in the provided backend contract; HR status buttons still change browser demo data only and do NOT update Neon. Chat history is localStorage and is NOT passed as conversation context to FastAPI. The demo fallback remains active when no FastAPI URL/token is configured. Only real backend-confirmed actions should be treated as submitted requests. Backend proposal fields may need adaptation to the actual schema.
