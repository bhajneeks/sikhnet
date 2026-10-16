---
name: skillify
description: Turn a workflow the team keeps repeating into a new project skill under .claude/skills/, so every teammate's Claude can do it. Use when the user says "skillify this", "make this a skill", "we keep doing this", "save this workflow for the team".
---

# Skillify (lite)

Adapted from gbrain's `skillify` meta-skill, trimmed for a hackathon.

## Checklist

1. **Is it a skill?** Repeated ≥ 2 times, or another teammate will need it.
   One-offs are not skills.
2. **Check for overlap:** read `.claude/skills/*/SKILL.md` frontmatter. Improve
   an existing skill instead of adding a near-duplicate.
3. **Write `.claude/skills/<kebab-name>/SKILL.md`:**
   - frontmatter `name` and a `description` that lists real trigger phrases
     (that's how Claude decides to load it),
   - a short contract (what it guarantees),
   - numbered steps with exact commands/paths in this repo,
   - rules / anti-patterns.
   No hardcoded teammate names in the steps unless it's about ownership.
4. **Try it once** on a real task in this session; fix whatever was unclear.
5. **Register it:** add a row to the skills table in `CLAUDE.md`.
6. Commit with message `skill: add <name>` and mention it in your status file
   so teammates know to pull it.
