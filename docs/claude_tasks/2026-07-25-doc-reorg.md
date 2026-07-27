# Objective

Reorganize the documentation structure into a scalable engineering documentation system.

The purpose is to separate long-term architecture documents from implementation tasks and architecture reviews.

No source code changes.

Documentation only.

---

# Requirements

Create the following directories under docs if they do not exist:

architecture/

claude_tasks/

reviews/

milestones/

adr/

Move existing files into appropriate locations.

Suggested mapping:

architecture.md
architecture_future.md
development.md
project_structure.md
strategy.md
roadmap.md
h1_patterns.md

→ docs/architecture/

Keep

docs/claude_tasks/

Keep

docs/reviews/

Create

docs/milestones/

Create

docs/adr/

---

# Naming Convention

Claude Tasks

YYYY-MM-DD-short-description.md

Examples

2026-07-25-trading-engine-interfaces-v1.md

Architecture Reviews

review-v0.1.md

ADR

ADR-001-bar-driven-engine.md

ADR-002-knowledge-first.md

Milestones

v0.2.md

v0.3.md

v1.0.md

---

# Out of Scope

Do NOT modify any implementation code.

Do NOT change package structure.

Do NOT change git history.

Do NOT rewrite document contents except where necessary to fix links.

---

# Deliverables

Updated documentation directory.

Fixed relative links.

README updated if necessary.

---

# Acceptance Criteria

All architecture documents live under docs/architecture.

Implementation tasks live under docs/claude_tasks.

Architecture reviews live under docs/reviews.

ADR and Milestones directories exist.

All markdown links remain valid.