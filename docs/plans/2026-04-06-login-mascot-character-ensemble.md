# Login Mascot Character Ensemble Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the login-page mascot area into a character-driven line-art ensemble with distinct personalities, differentiated reactions, and more fluid motion.

**Architecture:** Replace the current mostly shared mascot behavior with a profile-driven scene model. Each mascot keeps its own geometry, follow strength, hover temperament, email-probe behavior, code-avoid behavior, and idle rhythm, while the renderer stays in the login page as a single inline SVG scene for low integration risk.

**Tech Stack:** Next.js app router, React 19, inline SVG motion derived from frame state, `tsx` smoke tests.

---

### Task 1: Lock the new behavior surface in smoke checks

**Files:**
- Modify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Add failing source-level expectations**

Assert that the login page source now contains:
- `mascotProfiles`
- `hoverInfluence`
- `anger`
- `codeAvoid`

**Step 2: Run the test suite and confirm failure**

Run: `npm run test -w @aioj/app`

Expected: the smoke test fails because the old login scene does not yet expose the new behavior-system markers.

### Task 2: Rebuild the mascot scene around profile-driven behavior

**Files:**
- Modify: `frontend/apps/app/src/app/login/page.tsx`

**Step 1: Introduce profile/state/pose types**

Add:
- a mascot profile table for the five characters,
- a shared scene-state input,
- a pose resolver that computes gaze, probe, recoil, anger, avoid, and blink values per mascot.

**Step 2: Redraw the bodies with more expressive geometry**

Move away from near-identical pillars and render each mascot from:
- independent spine and contour lines,
- head groups with rotation and offsets,
- role-specific accessories and gesture marks.

**Step 3: Differentiate behavior**

Implement explicit differences:
- active tracker behavior,
- cautious recoil,
- steady leader attention,
- grumpy hover anger,
- aloof slow-follow motion,
- email focus probe,
- code focus avoidance and eye closing.

**Step 4: Preserve boundaries**

Do not change the login form, auth flow, or overall split layout. Keep changes isolated to the mascot scene and related source-level test expectations.

### Task 3: Verify runtime safety

**Files:**
- Verify: `frontend/apps/app/src/app/login/page.tsx`
- Verify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Run tests**

Run: `npm run test -w @aioj/app`

Expected: all tests pass.

**Step 2: Run production build**

Run: `npm run build -w @aioj/app`

Expected: the app builds successfully and `/login` remains in the generated route list.
