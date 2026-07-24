---
name: figma-frame-export
description: Use when you need to download a Figma frame as a PNG file. Triggers: "скачай макет из Figma", "получи PNG из Figma", "экспортируй фрейм Figma", "download Figma frame", "fetch figma image".
---

# figma-frame-export

## Overview

Скачивает PNG конкретного фрейма из Figma по URL. Результат — абсолютный путь к PNG-файлу на диске. Поддерживает кэширование: повторный вызов с тем же `node-id` не выполняет сетевой запрос.

**Требования:** Node.js v18+, Figma Personal Access Token.

---

## Шаги

### 1. Проверка токена

Проверь наличие `.secrets/figma.json` в корне проекта:
```json
{ "token": "figd_xxxxxxxxxxxxxxxx" }
```

Если файл отсутствует — сообщи пользователю:

> Для загрузки макета из Figma нужен Personal Access Token.
> Создай файл `.secrets/figma.json`:
> ```json
> { "token": "figd_xxxxxxxxxxxxxxxx" }
> ```
> Получить: Figma → Account Settings → Personal access tokens.

Дождись подтверждения, затем продолжи.

### 2. Проверка URL

URL должен содержать `node-id`. URL вида `https://figma.com/design/ABC/Name` (без `?node-id=...`) не работает. Попроси пользователя выбрать конкретный фрейм в Figma и скопировать ссылку через **Share → Copy link**.

### 3. Скачивание

```bash
node .claude/skills/figma-frame-export/fetch-figma.mjs "<figma_url>"
```

Скрипт выводит в stdout абсолютный путь к PNG-файлу. Этот путь используй для передачи в другие скилл или команды.

---

## Структура

```
.claude/skills/figma-frame-export/
├── SKILL.md           # Этот файл
├── fetch-figma.mjs    # Скачивает PNG из Figma API с кэшированием
└── temp/              # Кэш скачанных изображений (gitignore)
```

---

## Pitfalls

- **Масштаб 2x:** изображения скачиваются с `scale=2`. Если сравниваешь со скриншотом устройства в 1x — размеры будут отличаться.
- **Кэш не обновляется автоматически:** при изменении макета в Figma удали `temp/<nodeId>.png` вручную.
- **URL без `node-id` не работает:** нужно выбрать конкретный фрейм, а не копировать ссылку на файл целиком.
