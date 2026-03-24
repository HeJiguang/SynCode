# SynCode Front-AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `front-ai` single-application frontend for SynCode with a polished user-first learning experience, gateway-only API access, and an AI-assisted practice workspace, while reserving the admin domain for later integration.

**Architecture:** Create a new Vue 3 + TypeScript + Vite application at the repo root under `front-ai`. Separate the app into `public`, `user`, `workspace`, and `admin` shells, with shared request, auth, and design-token foundations. Deliver the homepage, login page, problems page, AI learning workspace, and basic personal center first, then leave `admin` route placeholders and backend AI enhancement requirements as documentation.

**Tech Stack:** Vue 3, TypeScript, Vite, Vue Router, Pinia, Vitest, Vue Test Utils, Monaco Editor, `@microsoft/fetch-event-source`, CSS variables

---

## File Structure

### New app root

- Create: `front-ai/package.json`
- Create: `front-ai/package-lock.json`
- Create: `front-ai/tsconfig.json`
- Create: `front-ai/tsconfig.node.json`
- Create: `front-ai/vite.config.ts`
- Create: `front-ai/vitest.config.ts`
- Create: `front-ai/index.html`
- Create: `front-ai/README.md`
- Create: `front-ai/.gitignore`

### App bootstrap and routing

- Create: `front-ai/src/main.ts`
- Create: `front-ai/src/App.vue`
- Create: `front-ai/src/router/index.ts`
- Create: `front-ai/src/router/guards.ts`
- Create: `front-ai/src/router/routes/public.ts`
- Create: `front-ai/src/router/routes/user.ts`
- Create: `front-ai/src/router/routes/workspace.ts`
- Create: `front-ai/src/router/routes/admin.ts`

### Layouts

- Create: `front-ai/src/layouts/PublicShell.vue`
- Create: `front-ai/src/layouts/UserShell.vue`
- Create: `front-ai/src/layouts/WorkspaceShell.vue`
- Create: `front-ai/src/layouts/AdminShell.vue`

### Shared foundation

- Create: `front-ai/src/styles/tokens.css`
- Create: `front-ai/src/styles/base.css`
- Create: `front-ai/src/styles/utilities.css`
- Create: `front-ai/src/shared/config/env.ts`
- Create: `front-ai/src/shared/api/client.ts`
- Create: `front-ai/src/shared/api/types.ts`
- Create: `front-ai/src/shared/api/modules/auth.ts`
- Create: `front-ai/src/shared/api/modules/problems.ts`
- Create: `front-ai/src/shared/api/modules/contests.ts`
- Create: `front-ai/src/shared/api/modules/profile.ts`
- Create: `front-ai/src/shared/api/modules/ai.ts`
- Create: `front-ai/src/shared/utils/token.ts`
- Create: `front-ai/src/shared/utils/result.ts`
- Create: `front-ai/src/shared/utils/sse.ts`
- Create: `front-ai/src/shared/ui/AppBrand.vue`
- Create: `front-ai/src/shared/ui/AppButton.vue`
- Create: `front-ai/src/shared/ui/AppCard.vue`
- Create: `front-ai/src/shared/ui/AppEmpty.vue`
- Create: `front-ai/src/shared/ui/AppStatusPill.vue`

### Stores

- Create: `front-ai/src/stores/auth.ts`
- Create: `front-ai/src/stores/problems.ts`
- Create: `front-ai/src/stores/workspace.ts`

### Pages and feature modules

- Create: `front-ai/src/pages/public/HomePage.vue`
- Create: `front-ai/src/pages/public/LoginPage.vue`
- Create: `front-ai/src/pages/user/ProblemsPage.vue`
- Create: `front-ai/src/pages/user/ProblemDetailPage.vue`
- Create: `front-ai/src/pages/user/ContestsPage.vue`
- Create: `front-ai/src/pages/user/ContestDetailPage.vue`
- Create: `front-ai/src/pages/user/ProfilePage.vue`
- Create: `front-ai/src/pages/user/ProfileContestsPage.vue`
- Create: `front-ai/src/pages/user/ProfileMessagesPage.vue`
- Create: `front-ai/src/pages/user/ProfileSubmissionsPage.vue`
- Create: `front-ai/src/pages/workspace/PracticeWorkspacePage.vue`
- Create: `front-ai/src/pages/workspace/ContestWorkspacePage.vue`
- Create: `front-ai/src/pages/admin/AdminPlaceholderPage.vue`
- Create: `front-ai/src/features/problems/ProblemFilters.vue`
- Create: `front-ai/src/features/problems/ProblemGrid.vue`
- Create: `front-ai/src/features/problems/ProblemPreviewCard.vue`
- Create: `front-ai/src/features/workspace/WorkspaceTopBar.vue`
- Create: `front-ai/src/features/workspace/LearningPanel.vue`
- Create: `front-ai/src/features/workspace/CodePanel.vue`
- Create: `front-ai/src/features/workspace/ResultPanel.vue`
- Create: `front-ai/src/features/workspace/AiCoachPanel.vue`
- Create: `front-ai/src/features/workspace/AiQuickActions.vue`
- Create: `front-ai/src/features/workspace/MonacoEditor.vue`
- Create: `front-ai/src/features/profile/LearningOverview.vue`

### Docs for backend follow-up

- Create: `front-ai/docs/backend-requirements/ai-assistant-upgrades.md`

### Tests

- Create: `front-ai/src/shared/api/__tests__/client.test.ts`
- Create: `front-ai/src/shared/utils/__tests__/result.test.ts`
- Create: `front-ai/src/stores/__tests__/auth.test.ts`
- Create: `front-ai/src/stores/__tests__/problems.test.ts`
- Create: `front-ai/src/stores/__tests__/workspace.test.ts`
- Create: `front-ai/src/features/workspace/__tests__/AiCoachPanel.test.ts`
- Create: `front-ai/src/features/workspace/__tests__/ResultPanel.test.ts`
- Create: `front-ai/src/router/__tests__/guards.test.ts`
- Create: `front-ai/src/pages/public/__tests__/HomePage.test.ts`

## Task 1: Scaffold the `front-ai` workspace

**Files:**
- Create: `front-ai/package.json`
- Create: `front-ai/tsconfig.json`
- Create: `front-ai/tsconfig.node.json`
- Create: `front-ai/vite.config.ts`
- Create: `front-ai/vitest.config.ts`
- Create: `front-ai/index.html`
- Create: `front-ai/.gitignore`
- Create: `front-ai/src/main.ts`
- Create: `front-ai/src/App.vue`
- Test: `front-ai/package.json`

- [ ] **Step 1: Scaffold the Vue + TypeScript app shell**

Run: `npm create vite@latest front-ai -- --template vue-ts`
Expected: Vite creates the `front-ai` directory with a TypeScript Vue starter

- [ ] **Step 2: Add testing and streaming dependencies**

Run: `npm install @microsoft/fetch-event-source monaco-editor pinia vue-router`
Run: `npm install -D vitest @vitest/ui @vue/test-utils jsdom`
Expected: `package.json` includes the runtime and test dependencies

- [ ] **Step 3: Replace starter scripts with project scripts**

Update `front-ai/package.json` so scripts match this shape:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Step 4: Add Vitest config**

Create `front-ai/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

- [ ] **Step 5: Run the baseline build**

Run: `npm run build`
Expected: Vite build completes successfully inside `front-ai`

- [ ] **Step 6: Commit**

```bash
git add front-ai
git commit -m "feat: scaffold front-ai app"
```

## Task 2: Establish routing, shells, and role guards

**Files:**
- Create: `front-ai/src/router/index.ts`
- Create: `front-ai/src/router/guards.ts`
- Create: `front-ai/src/router/routes/public.ts`
- Create: `front-ai/src/router/routes/user.ts`
- Create: `front-ai/src/router/routes/workspace.ts`
- Create: `front-ai/src/router/routes/admin.ts`
- Create: `front-ai/src/layouts/PublicShell.vue`
- Create: `front-ai/src/layouts/UserShell.vue`
- Create: `front-ai/src/layouts/WorkspaceShell.vue`
- Create: `front-ai/src/layouts/AdminShell.vue`
- Test: `front-ai/src/router/__tests__/guards.test.ts`

- [ ] **Step 1: Write the failing route-guard tests**

Create `front-ai/src/router/__tests__/guards.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { resolveAccess } from '../guards'

describe('resolveAccess', () => {
  it('allows public routes without a token', () => {
    expect(resolveAccess({ requiresAuth: false }, null)).toEqual({ allow: true })
  })

  it('redirects anonymous users away from protected routes', () => {
    expect(resolveAccess({ requiresAuth: true, role: 'user' }, null)).toEqual({
      allow: false,
      redirectTo: '/login',
    })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm run test -- src/router/__tests__/guards.test.ts`
Expected: FAIL because `resolveAccess` and guard files do not exist yet

- [ ] **Step 3: Implement the minimal guard layer**

Create `front-ai/src/router/guards.ts`:

```ts
export type RouteAccess = { requiresAuth?: boolean; role?: 'user' | 'admin' }

export function resolveAccess(meta: RouteAccess, token: string | null) {
  if (!meta.requiresAuth) return { allow: true as const }
  if (!token) return { allow: false as const, redirectTo: '/login' }
  return { allow: true as const }
}
```

Then wire `createRouter`, `beforeEach`, and the four shell route groups.

- [ ] **Step 4: Create placeholder pages and shell layouts**

Each shell should render:

```vue
<template>
  <div class="shell">
    <RouterView />
  </div>
</template>
```

The routes must include:

- `/`
- `/login`
- `/problems`
- `/workspace/practice/:questionId`
- `/workspace/contest/:examId/:questionId`
- `/me`
- `/admin`

- [ ] **Step 5: Run the tests and build**

Run: `npm run test -- src/router/__tests__/guards.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/router front-ai/src/layouts
git commit -m "feat: add front-ai shells and route guards"
```

## Task 3: Build the visual foundation and shared UI primitives

**Files:**
- Create: `front-ai/src/styles/tokens.css`
- Create: `front-ai/src/styles/base.css`
- Create: `front-ai/src/styles/utilities.css`
- Create: `front-ai/src/shared/ui/AppBrand.vue`
- Create: `front-ai/src/shared/ui/AppButton.vue`
- Create: `front-ai/src/shared/ui/AppCard.vue`
- Create: `front-ai/src/shared/ui/AppEmpty.vue`
- Create: `front-ai/src/shared/ui/AppStatusPill.vue`
- Modify: `front-ai/src/main.ts`
- Modify: `front-ai/src/App.vue`

- [ ] **Step 1: Define the design tokens**

Create `front-ai/src/styles/tokens.css` with project variables like:

```css
:root {
  --sc-bg: #eef3f8;
  --sc-surface: rgba(255, 255, 255, 0.82);
  --sc-surface-strong: #ffffff;
  --sc-ink: #0f172a;
  --sc-muted: #5b6b82;
  --sc-line: rgba(15, 23, 42, 0.08);
  --sc-accent: #2f7cff;
  --sc-accent-strong: #0f5cff;
  --sc-success: #16a34a;
  --sc-warning: #f59e0b;
  --sc-danger: #ef4444;
  --sc-workspace-bg: #09111f;
}
```

- [ ] **Step 2: Add global base styles**

Set up `base.css` for:

- full-height app
- font stack
- app background
- link resets
- button resets

- [ ] **Step 3: Build small reusable UI primitives**

Keep the components focused:

- `AppBrand.vue`: SynCode logo + wordmark
- `AppButton.vue`: primary and ghost variants
- `AppCard.vue`: frosted card container
- `AppEmpty.vue`: reusable empty state
- `AppStatusPill.vue`: difficulty and result badge

- [ ] **Step 4: Register the global styles**

Import the styles in `front-ai/src/main.ts`:

```ts
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/utilities.css'
```

- [ ] **Step 5: Run the build**

Run: `npm run build`
Expected: PASS and no missing-style import errors

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/styles front-ai/src/shared/ui front-ai/src/main.ts front-ai/src/App.vue
git commit -m "feat: add SynCode visual foundation"
```

## Task 4: Add the gateway request layer, token utilities, and auth store

**Files:**
- Create: `front-ai/src/shared/config/env.ts`
- Create: `front-ai/src/shared/api/client.ts`
- Create: `front-ai/src/shared/api/types.ts`
- Create: `front-ai/src/shared/api/modules/auth.ts`
- Create: `front-ai/src/shared/utils/token.ts`
- Create: `front-ai/src/shared/utils/result.ts`
- Create: `front-ai/src/stores/auth.ts`
- Test: `front-ai/src/shared/api/__tests__/client.test.ts`
- Test: `front-ai/src/stores/__tests__/auth.test.ts`

- [ ] **Step 1: Write the failing request-layer test**

Create `front-ai/src/shared/api/__tests__/client.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { mapApiResult } from '../client'

describe('mapApiResult', () => {
  it('returns payload for success code 1000', () => {
    expect(mapApiResult({ code: 1000, data: { ok: true }, msg: 'ok' })).toEqual({ ok: true })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm run test -- src/shared/api/__tests__/client.test.ts`
Expected: FAIL because the request layer does not exist yet

- [ ] **Step 3: Implement the gateway-only request client**

Create `front-ai/src/shared/api/client.ts` around a single Vite proxy base:

```ts
export const API_PREFIX = '/api'

export function mapApiResult<T>(payload: { code: number; data: T; msg: string }) {
  if (payload.code !== 1000) throw new Error(payload.msg || 'Request failed')
  return payload.data
}
```

Then add fetch helpers for:

- JSON requests
- token header injection
- consistent error normalization

- [ ] **Step 4: Add the auth store**

The auth store must support:

- `token`
- `identity`
- `fetchUserInfo()`
- `logout()`
- `isLoggedIn`

Test `auth.test.ts` against default store state before and after setting a token.

- [ ] **Step 5: Run tests and build**

Run: `npm run test -- src/shared/api/__tests__/client.test.ts src/stores/__tests__/auth.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/shared front-ai/src/stores
git commit -m "feat: add gateway api layer and auth store"
```

## Task 5: Implement the homepage and login page

**Files:**
- Create: `front-ai/src/pages/public/HomePage.vue`
- Create: `front-ai/src/pages/public/LoginPage.vue`
- Modify: `front-ai/src/layouts/PublicShell.vue`
- Modify: `front-ai/src/router/routes/public.ts`
- Modify: `front-ai/src/shared/api/modules/auth.ts`

- [ ] **Step 1: Write a small rendering test for the homepage hero**

Create a component test that checks the homepage renders:

- `SynCode`
- a learning-first headline
- a primary CTA

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm run test -- src/pages/public/__tests__/HomePage.test.ts`
Expected: FAIL because the page does not exist yet

- [ ] **Step 3: Build the homepage**

The homepage should include:

- strong hero section
- featured learning value proposition
- quick links to problems and contests
- AI-learning framing instead of generic OJ copy

Use a structure like:

```vue
<section class="hero">
  <AppBrand />
  <h1>Use AI to understand problems, write code, and learn faster.</h1>
  <div class="actions">
    <AppButton>Start Learning</AppButton>
    <AppButton variant="ghost">Explore Problems</AppButton>
  </div>
</section>
```

- [ ] **Step 4: Build the login page**

Support the existing code-login backend flow:

- phone input
- verification code input
- send-code action
- login action

Do not style it like the old classroom demo. Keep it visually consistent with the homepage.

- [ ] **Step 5: Run tests and build**

Run: `npm run test -- src/pages/public/__tests__/HomePage.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/pages/public front-ai/src/layouts/PublicShell.vue front-ai/src/router/routes/public.ts
git commit -m "feat: add SynCode public entry pages"
```

## Task 6: Implement the problems page and problem detail page

**Files:**
- Create: `front-ai/src/shared/api/modules/problems.ts`
- Create: `front-ai/src/stores/problems.ts`
- Create: `front-ai/src/pages/user/ProblemsPage.vue`
- Create: `front-ai/src/pages/user/ProblemDetailPage.vue`
- Create: `front-ai/src/features/problems/ProblemFilters.vue`
- Create: `front-ai/src/features/problems/ProblemGrid.vue`
- Create: `front-ai/src/features/problems/ProblemPreviewCard.vue`

- [ ] **Step 1: Write the failing store test**

Create a problems-store test for:

- default filter state
- filter update behavior

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm run test -- src/stores/__tests__/problems.test.ts`
Expected: FAIL because the store does not exist yet

- [ ] **Step 3: Implement the problems API and store**

Map these backend endpoints through the gateway:

- list problems
- hot problems
- get problem detail

The store should own:

- search keyword
- difficulty filter
- loading state
- problem list
- hot problem list

- [ ] **Step 4: Build the two user pages**

`ProblemsPage.vue` should include:

- search
- difficulty filter
- hot-problem rail
- polished card/grid layout

`ProblemDetailPage.vue` should include:

- title
- difficulty
- knowledge tags
- summary section
- start-practice CTA

- [ ] **Step 5: Run tests and build**

Run: `npm run test -- src/stores/__tests__/problems.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/pages/user front-ai/src/features/problems front-ai/src/shared/api/modules/problems.ts front-ai/src/stores/problems.ts
git commit -m "feat: add learning-first problems experience"
```

## Task 7: Implement the workspace state, Monaco editor, and result panel

**Files:**
- Create: `front-ai/src/stores/workspace.ts`
- Create: `front-ai/src/features/workspace/MonacoEditor.vue`
- Create: `front-ai/src/features/workspace/WorkspaceTopBar.vue`
- Create: `front-ai/src/features/workspace/LearningPanel.vue`
- Create: `front-ai/src/features/workspace/CodePanel.vue`
- Create: `front-ai/src/features/workspace/ResultPanel.vue`
- Create: `front-ai/src/pages/workspace/PracticeWorkspacePage.vue`
- Test: `front-ai/src/stores/__tests__/workspace.test.ts`
- Test: `front-ai/src/features/workspace/__tests__/ResultPanel.test.ts`

- [ ] **Step 1: Write the failing workspace-store tests**

Cover:

- setting current problem context
- updating code draft
- recording latest judge result

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test -- src/stores/__tests__/workspace.test.ts src/features/workspace/__tests__/ResultPanel.test.ts`
Expected: FAIL because the store and result panel do not exist yet

- [ ] **Step 3: Implement the workspace store**

State should include:

- current mode
- current problem
- current contest
- code draft
- language
- last judge result
- AI panel draft question

- [ ] **Step 4: Implement the workspace UI**

Build the three-column layout:

- top context bar
- left learning panel
- center code panel with Monaco
- result panel beneath the editor

The result panel should branch between:

- idle
- pending
- pass
- fail

- [ ] **Step 5: Run tests and build**

Run: `npm run test -- src/stores/__tests__/workspace.test.ts src/features/workspace/__tests__/ResultPanel.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/stores/workspace.ts front-ai/src/features/workspace front-ai/src/pages/workspace/PracticeWorkspacePage.vue
git commit -m "feat: add SynCode practice workspace foundation"
```

## Task 8: Integrate the AI coach panel with plain, detail, and streaming responses

**Files:**
- Create: `front-ai/src/shared/api/modules/ai.ts`
- Create: `front-ai/src/shared/utils/sse.ts`
- Create: `front-ai/src/features/workspace/AiQuickActions.vue`
- Create: `front-ai/src/features/workspace/AiCoachPanel.vue`
- Modify: `front-ai/src/pages/workspace/PracticeWorkspacePage.vue`
- Test: `front-ai/src/features/workspace/__tests__/AiCoachPanel.test.ts`

- [ ] **Step 1: Write the failing AI coach panel tests**

Cover:

- rendering quick actions
- rendering user and assistant messages
- rendering `intent` and `nextAction`

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test -- src/features/workspace/__tests__/AiCoachPanel.test.ts`
Expected: FAIL because the AI coach components do not exist yet

- [ ] **Step 3: Implement the AI module**

Provide helpers for:

- `askAi()`
- `askAiDetail()`
- `streamAi()`

The request payload should always be assembled from workspace context:

```ts
{
  questionTitle,
  questionContent,
  userCode,
  judgeResult,
  userMessage,
}
```

- [ ] **Step 4: Build the AI coach panel**

The panel must include:

- quick action buttons
- conversation thread
- streaming message updates
- metadata strip for `intent`, `confidence`, `nextAction`
- one-click action to explain the latest judge result

- [ ] **Step 5: Run tests and build**

Run: `npm run test -- src/features/workspace/__tests__/AiCoachPanel.test.ts`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/shared/api/modules/ai.ts front-ai/src/shared/utils/sse.ts front-ai/src/features/workspace/AiQuickActions.vue front-ai/src/features/workspace/AiCoachPanel.vue front-ai/src/pages/workspace/PracticeWorkspacePage.vue
git commit -m "feat: add AI learning coach panel"
```

## Task 9: Build the contests and profile basics, reserve the admin shell, and document backend AI upgrades

**Files:**
- Create: `front-ai/src/shared/api/modules/contests.ts`
- Create: `front-ai/src/shared/api/modules/profile.ts`
- Create: `front-ai/src/pages/user/ContestsPage.vue`
- Create: `front-ai/src/pages/user/ContestDetailPage.vue`
- Create: `front-ai/src/pages/user/ProfilePage.vue`
- Create: `front-ai/src/pages/user/ProfileContestsPage.vue`
- Create: `front-ai/src/pages/user/ProfileMessagesPage.vue`
- Create: `front-ai/src/pages/user/ProfileSubmissionsPage.vue`
- Create: `front-ai/src/pages/admin/AdminPlaceholderPage.vue`
- Create: `front-ai/docs/backend-requirements/ai-assistant-upgrades.md`
- Modify: `front-ai/src/router/routes/user.ts`
- Modify: `front-ai/src/router/routes/admin.ts`

- [ ] **Step 1: Create the contests and profile page placeholders**

Each page should render real page structure, not TODO text:

- header
- summary cards
- empty states or loading states
- future data regions

- [ ] **Step 2: Add the admin placeholder route**

`/admin` should be routable and clearly marked as reserved for future integration.

- [ ] **Step 3: Write the backend AI requirements document**

Document future needs:

- memory across sessions
- layered hints
- structured teaching payloads
- personalized recommendations
- code-line error localization
- auto summaries

- [ ] **Step 4: Connect the routes and navigation**

Expose:

- contests entry
- profile entry
- admin placeholder route

- [ ] **Step 5: Run tests and build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add front-ai/src/pages/user front-ai/src/pages/admin front-ai/src/router/routes/user.ts front-ai/src/router/routes/admin.ts front-ai/docs/backend-requirements/ai-assistant-upgrades.md
git commit -m "feat: add contests profile scaffolds and backend AI requirements"
```

## Task 10: Final integration verification and documentation

**Files:**
- Modify: `front-ai/README.md`
- Modify: `front-ai/package.json`
- Modify: `front-ai/src/pages/public/HomePage.vue`
- Modify: `front-ai/src/pages/user/ProblemsPage.vue`
- Modify: `front-ai/src/pages/workspace/PracticeWorkspacePage.vue`

- [ ] **Step 1: Document local setup and gateway assumptions**

Update `front-ai/README.md` with:

- install command
- dev command
- build command
- gateway-only API note
- current AI backend assumptions

- [ ] **Step 2: Run the full test suite**

Run: `npm run test`
Expected: PASS

- [ ] **Step 3: Run the production build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: Perform a manual smoke run**

Run: `npm run dev`
Expected: local dev server starts and main routes can be opened

- [ ] **Step 5: Commit**

```bash
git add front-ai
git commit -m "docs: finalize front-ai implementation docs"
```

## Notes for Execution

- Do not modify backend code while executing this plan.
- Keep all API calls routed through the gateway entry configured for the frontend.
- Prefer small, reviewable commits per task.
- If the current repo state contains unrelated modified files, do not revert them.
- If Monaco integration becomes unexpectedly costly, keep the wrapper thin and avoid over-customization in the first pass.
- The first polished milestone is reached when homepage, problems page, and practice workspace all run locally and the AI coach panel works against the current backend contracts.
