# ATS Resume Scorer — React frontend

A React + Vite frontend for your existing ATS Resume Scorer backend, replacing
the Streamlit UI. It talks to the same FastAPI endpoints and the same
Supabase auth project — no backend changes needed.

## What's included

- Pages: **Home** (landing), **ATS Scorer**, **History**, **Resources** — same
  four views as `streamlit_app.py`'s `current_view` state.
- Auth: email/password sign in + sign up, and "Continue with Google", via
  `@supabase/supabase-js` (mirrors `services/supabase_client.py`).
- API calls matching `services/api_client.py` exactly:
  - `GET  /api/v1/health`
  - `POST /api/v1/analyze-resume` (multipart: `resume` file + `job_description`)
  - `GET  /api/v1/history`
  - `DELETE /api/v1/history/{id}`
  - `POST /api/v1/generate-pdf`
  - `GET  /api/v1/history/{id}/pdf`
- Results dashboard components matching each `components/*.py` file 1:1
  (score overview, breakdown, strengths, critical issues, skill validation,
  JD comparison, detailed feedback, action items, recommendations) — reading
  the exact same response fields (`ATS_score`, `component_scores`,
  `skill_validation_details`, `jd_comparison` / `jd_match_analysis`,
  `detailed_feedback`, etc.).

## Setup

1. Copy this whole `frontend/` folder into your project (next to your
   existing `backend/` folder is fine — this does **not** touch your
   Streamlit code, it's a separate app).
2. `cd frontend && npm install`
3. Copy `.env.example` to `.env` and fill in:
   - `VITE_BACKEND_URL` — your FastAPI backend URL (default `http://localhost:8000`)
   - `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` — same Supabase project
     your Streamlit app already uses
   - `VITE_AUTH_REDIRECT_URL` — add this exact URL to Supabase's
     **Auth → URL Configuration → Redirect URLs**
4. `npm run dev` → opens on `http://localhost:5173`
5. Make sure your backend is running (`uvicorn backend.main:app`) and has
   CORS enabled for `http://localhost:5173`.

## Build for production

```
npm run build
```
Outputs static files to `dist/` — deploy that folder anywhere (Vercel,
Netlify, S3 + CloudFront, or served by your backend).

## Notes

- Resume upload accepts PDF/DOC/DOCX; job description accepts pasted text or
  a `.txt` file — same constraint as the Streamlit version (PDF/DOCX JDs
  aren't parsed client-side).
- If a field name in your backend's `AnalysisResponse` differs from what's
  read here (e.g. you rename `ATS_score`), update `src/components/*.jsx` —
  each file only reads from `analysis`, no transformation layer to fight.
