---
name: architecture-review
description: Use this skill before designing, adding, refactoring, or touching any architecture in this project — new features, new modules, new services, new endpoints, restructuring folders, or changes that cross boundaries between subsystems (frontend/backend/mobile/ML/hardware). Also use it whenever asked to "add a feature", "build X", "integrate Y", "refactor Z", or "design the architecture for...". This project is a complex multi-platform system (full-stack web, mobile, ML pipeline, hardware-software integration), so consistency across subsystems matters more than usual. Always consult this skill before writing code that spans more than one file or one subsystem, even if not explicitly asked to "design" anything.
---

# Architecture Review

## Why this skill exists

This project spans multiple platforms and domains (web, mobile, ML, hardware/firmware). The single biggest failure mode observed so far is **breaking existing structure and introducing inconsistent patterns** — e.g. a new endpoint that doesn't follow the existing API conventions, a new mobile screen that ignores the existing state-management pattern, an ML component wired in a way that doesn't match how other services talk to each other, or a hardware interface touched without respecting the existing abstraction layer.

The fix is not "write more code carefully." The fix is: **look before you build, and say what you found before you build.**

## Process (follow in order, every time)

### 1. Map the existing territory first
Before writing or proposing any code:
- Find and read the relevant existing modules/files in the subsystem(s) you're about to touch.
- Identify the existing pattern: naming conventions, folder structure, error handling style, how data flows in/out, how this subsystem talks to the others (API contracts, message formats, shared types/schemas).
- If a `references/` file in this skill (see below) documents the pattern for that subsystem, read it. If it doesn't exist yet, note that as a gap out loud rather than guessing.

### 2. State what you found before proposing anything
Explicitly tell the user, in a few lines:
- "Here's the existing pattern I found in [subsystem]: ..."
- "Here's how this crosses into [other subsystem]: ..."
- If you *can't* find a clear existing pattern (inconsistent already, or genuinely new territory), say so explicitly instead of picking one silently.

Do not skip this step even if the user's request seems simple. A one-line request ("add a field to the user profile") can still touch a schema shared across backend, mobile, and ML — that's exactly the situation this skill exists for.

### 3. Propose the plan, not just the code
Before implementing, lay out:
- Which files/modules will change
- Which subsystem boundaries this crosses (if any) and how compatibility is preserved across them (e.g. API contract version, shared schema, message format)
- Any place where you are **deviating** from the existing pattern, and why
- Any assumption you're making about ambiguous requirements — state it, don't silently pick one

Wait for a green light on non-trivial or cross-boundary changes. For small, clearly-scoped, single-file changes that match existing patterns exactly, you can proceed directly but still briefly state what you're doing.

### 4. Build to match, not to impress
- Reuse existing utilities, types, and abstractions instead of writing new ones that do the same thing.
- Match existing naming and file organization even if you'd personally organize it differently.
- If the existing pattern is genuinely bad (not just different from your preference), flag it explicitly as a suggestion — don't silently "fix" it as a side effect of an unrelated task.
- Don't introduce a new library, framework, or architectural pattern (state management approach, ORM, message broker, etc.) without calling it out and getting confirmation, even if it seems like an improvement.

### 5. Check boundary consistency explicitly
Before finishing, verify:
- [ ] Does this match the naming/style conventions of the subsystem I touched?
- [ ] If this crosses a subsystem boundary (e.g. backend ↔ mobile, ML pipeline ↔ backend, software ↔ hardware interface), do both sides agree on the contract (types, schema, units, error format)?
- [ ] Did I avoid introducing a second way of doing something the codebase already does one way?
- [ ] Did I leave a trail (comment, note, or message to the user) anywhere I deviated from an existing pattern?

## Cross-platform boundary notes

Flag these explicitly whenever a change crosses them — they are the highest-risk spots for inconsistency:

- **Backend ↔ Frontend/Mobile**: API contract shape, versioning, auth assumptions, error response format.
- **Backend ↔ ML pipeline**: data schema/format expected in vs. out, units, preprocessing assumptions, model versioning.
- **Software ↔ Hardware**: interface/protocol assumptions, timing/latency assumptions, failure modes (what happens if hardware doesn't respond).
- **Shared types/schemas**: if one platform's type changes, check whether it's duplicated (not shared) elsewhere and would silently drift out of sync.

## Reference files

If this project has subsystem-specific convention docs, keep them here and read the relevant one before touching that subsystem:
- `references/backend.md`
- `references/frontend.md`
- `references/mobile.md`
- `references/ml.md`
- `references/hardware.md`

(These don't exist yet — create one the first time you do a deep-dive into a subsystem's conventions, so the next task doesn't have to rediscover them from scratch.)

## What NOT to do

- Don't silently refactor unrelated code "while you're in there."
- Don't invent a new pattern when an existing (even imperfect) one already solves the problem.
- Don't assume ambiguous requirements — state the assumption and proceed, or ask if the ambiguity is truly blocking.
- Don't skip step 1–2 because the task "seems small." Small tasks in cross-platform systems are exactly where silent breakage happens.
