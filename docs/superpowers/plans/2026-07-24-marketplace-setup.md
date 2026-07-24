# Marketplace Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать личный Claude Code маркетплейс на GitHub для синхронизации скиллов между устройствами.

**Architecture:** Монорепо `zhdanov/marketplace` — каталог маркетплейса и плагины в одном репозитории. Маркетплейс регистрируется в Claude Code один раз на каждом устройстве, после чего все плагины устанавливаются одной командой.

**Tech Stack:** Git, GitHub CLI (`gh`), Claude Code plugin system.

---

## File Map

| Файл | Назначение |
|------|-----------|
| `F:/marketplace/.claude-plugin/marketplace.json` | Каталог плагинов маркетплейса |
| `F:/marketplace/plugins/my-tools/.claude-plugin/plugin.json` | Манифест плагина my-tools |
| `F:/marketplace/README.md` | Документация репозитория |

---

### Task 1: Аутентификация в личном GitHub через GitHub CLI

**Files:**
- Не создаются / не изменяются (операция в терминале)

- [ ] **Step 1: Проверить текущий статус авторизации gh**

```bash
gh auth status
```

Ожидаемый результат: либо уже авторизован в `github.com`, либо сообщение об отсутствии авторизации.

- [ ] **Step 2: Авторизоваться в личном GitHub**

```bash
gh auth login --hostname github.com
```

В интерактивном диалоге выбрать:
- `GitHub.com` → уже указано флагом
- `HTTPS` как протокол
- `Login with a web browser` → откроется браузер, ввести one-time code

Ожидаемый результат:
```
✓ Logged in as zhdanov
```

- [ ] **Step 3: Проверить авторизацию**

```bash
gh auth status
```

Ожидаемый результат:
```
github.com
  ✓ Logged in to github.com account zhdanov
  - Active account: true
  - Token scopes: ...
```

---

### Task 2: Создать репозиторий на GitHub

**Files:**
- Не создаются (репозиторий создаётся на GitHub)

- [ ] **Step 1: Создать публичный репозиторий**

```bash
gh repo create zhdanov/marketplace --public --description "Personal Claude Code plugins"
```

Ожидаемый результат:
```
✓ Created repository zhdanov/marketplace on GitHub
```

- [ ] **Step 2: Убедиться, что репозиторий создан**

```bash
gh repo view zhdanov/marketplace
```

Ожидаемый результат: информация о репозитории (имя, visibility: public, URL).

---

### Task 3: Инициализировать git в локальной папке и связать с GitHub

**Files:**
- Изменяется: `F:/marketplace/` (git init)

- [ ] **Step 1: Инициализировать git**

```bash
cd "F:/marketplace" && git init
```

Ожидаемый результат:
```
Initialized empty Git repository in F:/marketplace/.git/
```

- [ ] **Step 2: Настроить локальный git на личный аккаунт**

Чтобы коммиты шли от личного аккаунта (а не корпоративного):

```bash
git config user.name "Viacheslav Zhdanov"
git config user.email "твой_личный@email.com"
```

> Замени `твой_личный@email.com` на email, привязанный к личному GitHub.

- [ ] **Step 3: Добавить remote**

```bash
git remote add origin https://github.com/zhdanov/marketplace.git
```

- [ ] **Step 4: Проверить remote**

```bash
git remote -v
```

Ожидаемый результат:
```
origin  https://github.com/zhdanov/marketplace.git (fetch)
origin  https://github.com/zhdanov/marketplace.git (push)
```

---

### Task 4: Создать файлы маркетплейса

**Files:**
- Create: `F:/marketplace/.claude-plugin/marketplace.json`
- Create: `F:/marketplace/plugins/my-tools/.claude-plugin/plugin.json`
- Create: `F:/marketplace/README.md`

- [ ] **Step 1: Создать `.claude-plugin/marketplace.json`**

Файл `F:/marketplace/.claude-plugin/marketplace.json`:

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

- [ ] **Step 2: Создать `plugins/my-tools/.claude-plugin/plugin.json`**

Файл `F:/marketplace/plugins/my-tools/.claude-plugin/plugin.json`:

```json
{
  "name": "my-tools",
  "description": "My custom skills",
  "version": "1.0.0",
  "author": { "name": "Zhdanov_Viacheslav" }
}
```

- [ ] **Step 3: Создать `README.md`**

Файл `F:/marketplace/README.md`:

```markdown
# marketplace

Personal Claude Code plugin marketplace.

## Setup on a new device

```bash
gh auth login --hostname github.com
/plugin marketplace add zhdanov/marketplace
/plugin install my-tools@zhdanov-plugins
```

## Adding skills

1. Create `plugins/my-tools/skills/<skill-name>/SKILL.md`
2. Commit and push
3. On other devices: `/plugin marketplace update`
```

- [ ] **Step 4: Проверить структуру папок**

```bash
find "F:/marketplace" -not -path "*/.git/*" | sort
```

Ожидаемый результат:
```
F:/marketplace
F:/marketplace/.claude-plugin
F:/marketplace/.claude-plugin/marketplace.json
F:/marketplace/docs/superpowers/plans/2026-07-24-marketplace-setup.md
F:/marketplace/docs/superpowers/specs/2026-07-24-marketplace-design.md
F:/marketplace/plugins
F:/marketplace/plugins/my-tools
F:/marketplace/plugins/my-tools/.claude-plugin
F:/marketplace/plugins/my-tools/.claude-plugin/plugin.json
F:/marketplace/plugins/my-tools/skills
F:/marketplace/README.md
```

---

### Task 5: Первый коммит и пуш на GitHub

**Files:**
- Все файлы из `F:/marketplace/`

- [ ] **Step 1: Добавить все файлы в staging**

```bash
cd "F:/marketplace" && git add .
```

- [ ] **Step 2: Создать первый коммит**

```bash
git commit -m "feat: initial marketplace setup"
```

Ожидаемый результат:
```
[main (root-commit) xxxxxxx] feat: initial marketplace setup
 N files changed, ...
```

- [ ] **Step 3: Запушить на GitHub**

```bash
git push -u origin main
```

Ожидаемый результат:
```
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

- [ ] **Step 4: Убедиться, что репозиторий доступен на GitHub**

```bash
gh repo view zhdanov/marketplace --web
```

Откроется браузер с репозиторием. Убедиться, что все файлы на месте.

---

### Task 6: Подключить маркетплейс в Claude Code

**Files:**
- Не создаются (конфигурация Claude Code)

- [ ] **Step 1: Зарегистрировать маркетплейс**

В терминале Claude Code:

```
/plugin marketplace add zhdanov/marketplace
```

Ожидаемый результат: маркетплейс `zhdanov-plugins` добавлен.

- [ ] **Step 2: Установить плагин my-tools**

```
/plugin install my-tools@zhdanov-plugins
```

- [ ] **Step 3: Проверить, что плагин активен**

```
/plugin list
```

Ожидаемый результат: `my-tools@zhdanov-plugins` присутствует в списке.