# RIBIF frontend

Next.js App Router UI for RIBIF: project upload, the workflow page that chains the backend modules (`src/app/workflow/[id]/page.tsx`), the per-module result views in `src/sections/`, the digital twin (`src/app/twin/`) and the Vapi voice negotiation page (`src/app/voice-call/`). See the root README for the full pipeline.

```bash
pnpm install
pnpm dev          # http://localhost:3000, expects the backend on NEXT_PUBLIC_BACKEND_URL
pnpm lint
pnpm exec tsc --noEmit
pnpm test         # vitest; the live Supabase test is skipped unless SUPABASE_TEST_LIVE=1
```

Copy `.env.example` to `.env.local` and fill in the backend URL, Supabase keys and the Vapi public key.
