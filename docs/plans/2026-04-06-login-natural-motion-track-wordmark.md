# Login Natural Motion And Track Wordmark Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the login-page mascots feel more natural by splitting motion into slow body, medium head, and fast eye response, and replace the standalone `SynCode` plaque with a background-integrated track wordmark.

**Architecture:** Keep the login page scene inline in `src/app/login/page.tsx`, but move the motion model away from a single shared pointer response. The new scene will run a layered smoothing model where body, head, and eye track different filtered targets, and the wordmark becomes part of the SVG background language instead of a separate floating label.

**Tech Stack:** Next.js app router, React 19, inline SVG, `tsx` smoke tests.

---

### Task 1: Lock the new scene markers in smoke checks

**Files:**
- Modify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Add failing expectations**

Assert that the login scene source contains:
- `bodyTargetRef`
- `headTargetRef`
- `eyeTargetRef`
- `syncode-track-wordmark`

**Step 2: Run tests and confirm failure**

Run: `npm run test -w @aioj/app`

Expected: the smoke test fails until the new motion model and background wordmark are implemented.

### Task 2: Rebuild motion smoothing

**Files:**
- Modify: `frontend/apps/app/src/app/login/page.tsx`

**Step 1: Introduce layered targets**

Track separate filtered targets for:
- body
- head
- eyes

The body should move the slowest, the head should follow more quickly, and the eyes should be the quickest.

**Step 2: Add deadzone and damping**

Prevent tiny cursor jitter from moving the whole ensemble. Keep movement nearly still when the pointer is effectively stationary.

**Step 3: Preserve hard rules**

When the code field is focused, all mascots must turn away from the code area at the body and head level, not only at the eye level.

### Task 3: Integrate the wordmark into the background

**Files:**
- Modify: `frontend/apps/app/src/app/login/page.tsx`

**Step 1: Remove the standalone plaque**

Delete the rounded rectangle sign and its isolated text treatment.

**Step 2: Add track wordmark**

Render `SynCode` as a low-contrast background line wordmark that feels sketched into the scene, not attached on top of it.

### Task 4: Verify

**Files:**
- Verify: `frontend/apps/app/src/app/login/page.tsx`
- Verify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Run tests**

Run: `npm run test -w @aioj/app`

**Step 2: Run build**

Run: `npm run build -w @aioj/app`
