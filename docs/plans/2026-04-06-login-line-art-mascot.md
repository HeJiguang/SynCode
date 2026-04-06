# Login Line-Art Mascot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redraw the app login-page mascot scene as a pure line-art illustration while preserving the existing layout, interaction hooks, and brand plaque.

**Architecture:** Keep the current `MascotCanvas` and `SceneMascot` component structure in place so the page layout and pointer-driven motion remain stable. Replace the current heavy glow-and-fill visual language with lightweight stroke-only shapes, remove the colored ambient circles, and keep only subtle framing, floor lines, and the existing `SynCode` plaque for scene context.

**Tech Stack:** Next.js app router, React 19, inline SVG in `src/app/login/page.tsx`, simple `tsx` smoke tests.

---

### Task 1: Lock the intended login mascot contract in a smoke check

**Files:**
- Modify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Write the failing test**

Add a source-level assertion that expects the login page to include a line-art specific scene token such as `scene.ringStroke` or another explicit stroke-only marker that does not exist yet.

**Step 2: Run test to verify it fails**

Run: `npm test --workspace @aioj/app`

Expected: the smoke test fails because the new line-art marker is not present in `src/app/login/page.tsx`.

**Step 3: Keep the assertion minimal**

Avoid snapshot-style checks. Assert only the existence of the new line-art scene token so the test protects the intended redraw direction without making the SVG brittle.

### Task 2: Redraw the mascot scene as line art

**Files:**
- Modify: `frontend/apps/app/src/app/login/page.tsx`

**Step 1: Replace scene palette**

Introduce a restrained scene palette for frame lines, plaque border, floor line, outline stroke, accent stroke, and muted shadow stroke. Remove the current filled ambient glow circles.

**Step 2: Convert mascot bodies to stroke-first outlines**

Keep each mascot’s overall placement and expressive face logic, but replace the thick dual-body render with:
- one subtle outer stroke for spatial weight,
- one main outline stroke,
- optional interior guide line or face-detail stroke,
- no filled body shapes.

**Step 3: Simplify background**

Retain only very light border geometry, floor contour lines, and the `SynCode` plaque. Remove or drastically reduce filled atmosphere so the scene reads as illustration rather than poster art.

**Step 4: Preserve interaction cues**

Keep pointer tracking, wiggle behavior, eye movement, and mood-specific features such as the hat, leader arc, and balloon details, but render them with the same line-art language.

### Task 3: Verify the redraw

**Files:**
- Verify: `frontend/apps/app/src/app/login/page.tsx`
- Verify: `frontend/apps/app/src/__tests__/smoke.test.tsx`

**Step 1: Run the app test suite**

Run: `npm test --workspace @aioj/app`

Expected: all app tests pass.

**Step 2: Spot-check the source diff**

Confirm the login page no longer contains the colored fill-circle atmosphere and that the scene exposes the new line-art token used by the smoke test.
