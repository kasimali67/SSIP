# SSIP GovTech Milestone Tracker

## Phase 1: PoC with Civic UI & Adapters (Local Sandbox)
- [ ] Task 1.1: Copy backend and frontend files from Claude's unzipped folder
- [ ] Task 1.2: Install backend requirements (`pyjwt[crypto]`, `rapidfuzz`, etc.)
- [ ] Task 1.3: Apply guarded migration (`to_regclass('auth.users')`) and run `alembic upgrade head`
- [ ] Task 1.4: Run verification tests (`pytest tests/test_verification.py -v`)
- [ ] Task 1.5: Verify Next.js frontend with civic theme, Mukta fonts, and sandbox personas
- [ ] Task 1.6: Freeze Stage 1 PoC branch (`stage1-poc`) to GitHub

## Phase 2: Final Prototype (Playwright & Cloud Readiness)
- [ ] Task 2.1: Implement Playwright form submission service (`submission.py`)
- [ ] Task 2.2: Connect verification success state to Playwright runner
- [ ] Task 2.3: Connect Supabase Cloud database and deploy to Vercel/Render