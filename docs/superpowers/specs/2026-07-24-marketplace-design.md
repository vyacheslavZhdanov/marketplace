# Marketplace Design — Personal Claude Code Plugin Marketplace

**Date:** 2026-07-24  
**Author:** Zhdanov_Viacheslav  
**Status:** Approved

---

## Goal

A personal Claude Code plugin marketplace hosted on GitHub (`zhdanov/marketplace`) for syncing custom skills across multiple personal devices.

---

## Architecture

**Approach:** Monorepo — marketplace catalog and plugins live in the same repository. Everything is installed in one step via the marketplace.

**Repository:** `github.com/zhdanov/marketplace`  
**Local path:** `F:\marketplace\`

---

## Repository Structure

```
F:\marketplace\
├── .claude-plugin/
│   └── marketplace.json        # Plugin catalog
├── plugins/
│   └── my-tools/               # Custom skills plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/             # Skills added here over time
└── README.md
```

---

## Key Files

### `.claude-plugin/marketplace.json`

```json
{
  "name": "zhdanov-plugins",
  "description": "Personal Claude Code plugins",
  "owner": { "name": "Zhdanov_Viacheslav" },
  "plugins": [
    {
      "name": "my-tools",
      "description": "My custom skills",
      "source": "./plugins/my-tools"
    }
  ]
}
```

To add external plugins later, append entries with GitHub/npm sources.

### `plugins/my-tools/.claude-plugin/plugin.json`

```json
{
  "name": "my-tools",
  "description": "My custom skills",
  "version": "1.0.0",
  "author": { "name": "Zhdanov_Viacheslav" }
}
```

---

## Device Setup (First Time)

```bash
# 1. Authenticate with personal GitHub account
gh auth login --hostname github.com

# 2. Clone the marketplace repository
gh repo clone zhdanov/marketplace "F:\marketplace"

# 3. Register the marketplace in Claude Code
/plugin marketplace add zhdanov/marketplace

# 4. Install plugins
/plugin install my-tools@zhdanov-plugins
```

---

## Syncing to a New Device

```bash
gh auth login --hostname github.com
/plugin marketplace add zhdanov/marketplace
/plugin install my-tools@zhdanov-plugins
```

---

## Adding Skills Over Time

1. Create `plugins/my-tools/skills/<skill-name>/SKILL.md`
2. Commit and push to GitHub
3. On other devices: `/plugin marketplace update`

---

## Adding External Plugins

Append to `marketplace.json`:

```json
{
  "name": "superpowers",
  "description": "Superpowers plugin",
  "source": { "source": "github", "repo": "owner/superpowers-repo" }
}
```

---

## Out of Scope

- Private/team access (public repo, personal use only)
- Per-plugin versioning (single monorepo, version managed via git commits)
- SSH key setup (GitHub CLI handles authentication)