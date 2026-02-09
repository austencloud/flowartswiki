# Command & Workflow Behaviors

## /fb Command

**Auto-select, then show the feedback, then discuss.**

When running `/fb` without an ID, auto-select the best item using:
1. Bugs first (affect current users)
2. Higher priority items
3. Clear scope over vague descriptions
4. Achievable complexity
5. Skip items with `--title` or `--description` placeholders

After selecting, display what was claimed:

- **Title** and **ID**
- **Type** (bug/feature/enhancement) and **Priority**
- **Who submitted it** and **when**
- **Page/Area** it affects
- **The full description** - word for word
- **Any existing notes or subtasks**

Format naturally - doesn't have to be a rigid template, but all the above must be visible before any analysis or recommendations.

**Then:**
1. Share your interpretation and suggested approach
2. **Ask for confirmation** before starting work - never jump into implementation

**After implementing:**
- Summarize what changed
- Give clear testing steps
- Describe expected behavior

---

## Feedback & Release Workflow

- Quick reference:
  - **5 statuses**: `new -> in-progress -> in-review -> completed -> archived`
  - **Kanban phase** (new -> in-progress -> in-review): Active development
  - **Staging phase** (completed): Items ready for next release
  - **Release phase** (archived + fixedInVersion): Released and versioned
- Key commands:
  - `/fb` - Claim and work on feedback
  - `node F:/_CODE/shared-scripts/feedback/release.js -p` - Preview next release
  - `/release` - Ship completed items as a version
- Remember: `completed` means "ready to ship", not "shipped" (that's `archived`)

---

## /release Command (CRITICAL)

**A release is NOT complete until the GitHub Release is created.**

When executing a release, complete ALL steps:

1. **Preview** - `node F:/_CODE/shared-scripts/feedback/release.js -p`
2. **Commit** - Ensure all changes are committed
3. **Execute** - `node F:/_CODE/shared-scripts/feedback/release.js --version X.Y.Z --confirm`
4. **Push tag** - `git push origin master && git push origin vX.Y.Z`
5. **Create GitHub Release** (use Git Bash on Windows):
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file release-notes.md
   ```
   Or write notes inline (Git Bash required for heredoc):
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" -F - <<EOF
   ## What's New
   ### Fixed
   - [descriptions]
   ### Added
   - [descriptions]
   EOF
   ```

**The GitHub Release is what users see.** Tags alone aren't enough.

---

## Release Notes Guidelines

**Audience: Wiki editors and flow arts enthusiasts, not developers.**

**Tone: Matter-of-fact, not promotional.**

Write release notes like Claude Code's changelog - straightforward statements of what changed. No selling, no hype, no filler words.

### Good Examples (matter-of-fact)
- "Added collapsible category tree navigation"
- "Fixed captcha not accepting valid answers on signup"
- "Improved search result relevance"
- "New prop infobox template for article standardization"

### Bad Examples (promotional AI-speak)
- "Stunning new category browsing experience!"
- "Seamlessly navigate through our comprehensive prop database"
- "Experience the power of enhanced search capabilities"

### Mark internal-only
`node F:/_CODE/shared-scripts/feedback/fetch-feedback.js <id> internal-only true`
- Docker config, Caddy changes, backup scripts, dev tooling, admin features

**Test:** Read it out loud. Does it sound like a press release or a changelog?

---

## /done Command

Two modes - automatically detected based on the first argument:

### Mode 1: Complete Existing Feedback

When first arg is a document ID (20-char alphanumeric):

```bash
/done abc123xyz "Fixed the issue"
/done abc123xyz "Admin notes" "User-facing notes"
```

### Mode 2: Auto-Create and Complete (Quick Log)

When first arg is a title (has spaces or descriptive text):

```bash
/done "Added Poi article draft"
/done "Fix upload limit" "Increased from 2MB to 10MB"
```

**What happens in auto-create mode:**

1. Creates feedback under Austen's profile
2. Sets status directly to `completed`
3. Marks as `internal-only` (excluded from user changelog)
4. Reports what was created with document ID

**Detection:** If first arg is 20+ alphanumeric chars with no spaces -> existing ID. Otherwise -> title for auto-create.

---

## /ai-bust Command

Scans user-facing text for AI writing patterns.

```
/ai-bust content/drafts/Poi.wiki
/ai-bust content/**/*.wiki
/ai-bust "Your text to check"
```

**What it catches:**
- Em dashes (dead giveaway)
- Banned openers ("In today's fast-paced world...")
- Blacklisted words (leverage, seamless, delve, etc.)
- Hedging phrases ("It's worth noting...")
- Perfect threes with uniform rhythm
- Sycophantic openers ("Absolutely!", "Great question!")

**Output:** Line-by-line violations with severity and suggested fixes.

**When to use:**
- Before publishing wiki articles
- When writing release notes
- After generating any user-facing copy
- When something "sounds AI-generated"

---

## Context Management

When context exceeds **70%**, suggest `/compact` before continuing with new tasks.
