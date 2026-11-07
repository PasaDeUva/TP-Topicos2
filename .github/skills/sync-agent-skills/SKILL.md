---
name: sync-agent-skills
description: "Use when adding or updating repository skills. Keep .agents/skills, .opencode/skills, and .github/skills synchronized."
---

# Synchronize Agent Skills

Use `.agents/skills/` as the canonical source. The same skill must exist with identical content in:

- `.agents/skills/`
- `.opencode/skills/`
- `.github/skills/`

## Procedure

1. Make the skill change in `.agents/skills/<skill-name>/`.
2. Copy the complete skill directory to `.opencode/skills/<skill-name>/` and `.github/skills/<skill-name>/`.
3. Keep `SKILL.md` and every supporting file identical across all three directories.
4. Compare file hashes before finishing.
5. Review `git diff` and include all three copies in the commit.

Do not edit only one copy. If a skill is missing from one directory, restore it from `.agents/skills/`.
