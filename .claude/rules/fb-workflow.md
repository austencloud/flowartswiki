# Feedback Workflow

## Wiki Domain Context

Users may use vague or incorrect terminology. Here's the actual structure:

**Content Areas** (what feedback may reference):
- `articles` - Main namespace wiki pages (poi, staff, fans, techniques)
- `templates` - Infobox, navbox, technique templates
- `categories` - Taxonomy (Props, Techniques, Culture, Safety)
- `skin` - Citizen skin styling and overrides
- `config` - LocalSettings.php, extensions, permissions
- `infra` - Docker, Caddy, backups, deployment

**Common user confusions:**
- "home page" / "front page" -> Main Page
- "the article" -> could be any main namespace page
- "formatting" / "layout" -> likely template or skin issue
- "can't edit" / "permission" -> account/group permissions
- "broken link" -> red link to nonexistent article
- "search doesn't work" -> Citizen search or MW search config

---

## Claim Health System

**Claims go stale after 45 minutes of inactivity.** Stale claims can be taken over by other agents.

### Keep Your Claim Active

Every 30 minutes while actively working, run:
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js heartbeat <id> "Brief status message"
```

This resets the 45-minute staleness timer.

### Record Files Being Edited (Optional)

For better work recovery if your session dies:
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js touch <id> "LocalSettings.php"
```

### View Work History

See all activity on an item (claims, heartbeats, status changes):
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js journal <id>
```

---

## Claim Takeover Protocol

**Fresh claims (<45 min activity) are protected.** You cannot just unclaim them.

### If You Need Someone Else's Claim:

1. **Check if stale first:**
   ```bash
   node F:/_CODE/shared-scripts/feedback/fetch-feedback.js list  # Shows staleness info
   ```

2. **If stale (>45 min inactive):** Just claim it normally
   ```bash
   node F:/_CODE/shared-scripts/feedback/fetch-feedback.js claim <id>
   ```

3. **If active:** Submit a request and wait 15 minutes
   ```bash
   node F:/_CODE/shared-scripts/feedback/fetch-feedback.js request-claim <id> "Why you need it"
   ```
   After 15 minutes, claim normally. The current holder can see your request.

4. **True emergency only:** Use emergency flag (audited, logged, flagged for review)
   ```bash
   node F:/_CODE/shared-scripts/feedback/fetch-feedback.js unclaim <id> --emergency "Blocking release"
   ```

### What NOT to Do

- **NEVER bypass protection** by chaining unclaim/claim
- **NEVER use --emergency for non-emergencies** - it's audited
- **NEVER assume a fresh claim is abandoned** - the agent may be actively working

---

## Auto-Selection (when no ID provided)

When running `/fb` without an argument, Claude auto-selects the best item.

**Selection priority:**

1. **Bugs first** - bugs affect current users, features can wait
2. **Higher priority** - high > medium > low > unset
3. **Clear scope** - items with clear titles/descriptions over vague ones
4. **Achievable complexity** - prefer items that can be completed in one session
5. **Skip incomplete metadata** - avoid items with `--title` or `--description` placeholders

**BE DECISIVE.** Run `list` once, apply criteria, pick the first match, claim it. Do NOT cycle through 3+ items second-guessing yourself.

After selecting, announce the choice with 1-sentence rationale, then immediately claim and display it.

---

## Display Feedback First

When running `/fb`, start your response with raw feedback details:

```
## Claimed Feedback: [Title or "Untitled"]

**ID:** [document-id]
**Type:** [bug/feature/enhancement]
**Priority:** [low/medium/high]
**User:** [username]
**Page/Area:** [page or area]

---

**Description:**
[Full feedback text exactly as provided]

---
```

**Then** proceed with assessment and recommendations.

---

## Model Triage (Mandatory)

After displaying feedback, assess complexity to route to the most cost-effective model.

### TRIVIAL -> Delegate to Haiku

**Only for:**
- Literal string/text swaps in articles
- Single-line config changes
- Fixing a typo in a template

**NOT for Haiku:**
- CSS fixes requiring investigation
- Template logic changes
- Changes where solution isn't already known

### MEDIUM -> Delegate to Sonnet (default)

- CSS tweaks, skin overrides
- Single-file template fixes
- Clear bug with reproduction steps
- Config changes scoped to 1-3 settings

### COMPLEX -> Handle as Opus

- Extension integration
- Multi-template coordination
- Security/permission changes
- Ambiguous requirements
- Changes touching config + templates + CSS

---

## Announce Triage Decision

```
**Complexity Assessment:** [TRIVIAL / MEDIUM / COMPLEX]
**Model Routing:** [Delegating to Haiku / Delegating to Sonnet / Handling as Opus]
**Reasoning:** [Brief explanation]
```

---

## Get Confirmation

**MANDATORY:** After triage, ask for explicit confirmation before proceeding.

**DO NOT:**
- Start working without confirmation
- Delegate without confirmation
- Skip this step for "simple" tasks

---

## Status Values & State Machine

Valid statuses and allowed transitions:

| From | Allowed To | Action |
|------|------------|--------|
| `new` | `in-progress` | Claim the item |
| `in-progress` | `new`, `in-review` | Unclaim or resolve |
| `in-review` | `in-progress`, `completed` | Needs more work or confirm fixed |
| `completed` | `archived`, `in-review` | Release or retest |
| `archived` | `new` | Reopen (admin only) |

**Invalid transitions are blocked.** You cannot skip steps (e.g., `new` -> `completed`).

---

## Commands Quick Reference

### Queue Commands
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js              # Auto-claim next item
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js claim <id>   # Claim specific item
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js list         # See queue status
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js mine         # Your in-progress items
```

### Claim Health
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js heartbeat <id> "status"   # Keep claim active
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js touch <id> "filepath"     # Record file edit
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js journal <id>              # View activity log
```

### Claim Takeover
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js unclaim <id>              # Release stale claim
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js request-claim <id> "why"  # Request active claim
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js unclaim <id> --emergency "reason"  # Emergency only
```

### Item Management
```bash
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js <id>                      # View item details
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js <id> <status> "notes"     # Update status
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js <id> priority <level>     # Set priority
node F:/_CODE/shared-scripts/feedback/fetch-feedback.js <id> resolution "notes"   # Add resolution
```

**CRITICAL:** Always use `claim <id>` before working on an item. Just viewing with `<id>` alone does NOT prevent other agents from picking it up.
