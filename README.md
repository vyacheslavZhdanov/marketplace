# marketplace

Personal Claude Code plugin marketplace.

## Setup on a new device

```bash
gh auth login --hostname github.com
/plugin marketplace add vyacheslavZhdanov/marketplace
/plugin install my-tools@zhdanov-plugins
```

## Adding skills

1. Create `plugins/my-tools/skills/<skill-name>/SKILL.md`
2. Commit and push
3. On other devices: `/plugin marketplace update`