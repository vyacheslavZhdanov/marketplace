---
name: screenshot-compare
description: Use when comparing two screenshots pixel-by-pixel, or comparing a screenshot/device screen with a Figma mockup. Triggers: "сравни скриншот", "сравни с макетом", "compare screenshot", "figma compare", "pixel diff".
---

# screenshot-compare

## Overview

Запускает локальный HTTP-сервер и открывает браузерный viewer для визуального сравнения двух изображений.

Viewer предоставляет три режима: **Side-by-side**, **Overlay** (наложение с прозрачностью), **Diff** (попиксельная разница). Весь анализ выполняется пользователем в браузере — Claude изображения не читает и не анализирует.

| Сценарий | Входные данные | Что происходит |
|---|---|---|
| **1. Два скриншота** | Два локальных PNG-файла | Viewer открывается сразу |
| **2. Figma + скриншот** | Figma URL + локальный PNG | Скилл **figma-frame-export** → viewer |
| **3. Figma + устройство** | Figma URL | Скилл **adb-screenshot** → скилл **figma-frame-export** → viewer |

---

## Сценарии

### Неоднозначный запрос

Если из запроса неясно, какой сценарий применить — уточни:

```
question: "Какой сценарий использовать?"
header: "Сценарий"
options:
  - label: "Два скриншота"
    description: "Сравнить два локальных файла-скриншота"
  - label: "Figma + скриншот"
    description: "Скачать макет из Figma и сравнить с локальным скриншотом"
  - label: "Figma + устройство"
    description: "Сделать скриншот с подключённого устройства и сравнить с макетом Figma"
```

---

### Сценарий 1: Два скриншота

**Входные данные:** `<путь_a>` и `<путь_b>` — два локальных PNG.

```bash
bash .claude/skills/screenshot-compare/scripts/screenshots-compare.sh <путь_a> <путь_b>
```

**Результат:** В браузере открыт viewer. Сервер работает до `Ctrl+C`.

---

### Сценарий 2: Figma + скриншот

**Входные данные:** `<путь_к_скриншоту>` — локальный PNG, `<figma_url>` — ссылка на фрейм с `node-id`.

1. Используй скилл **figma-frame-export** для скачивания макета. Получи путь к PNG.
2. Запусти viewer:
   ```bash
   bash .claude/skills/screenshot-compare/scripts/screenshots-compare.sh <путь_к_скриншоту> <путь_figma_png>
   ```

**Результат:** В браузере открыт viewer: слева — скриншот, справа — макет из Figma.

---

### Сценарий 3: Figma + скриншот с устройства

**Входные данные:** `<figma_url>` — ссылка на фрейм с `node-id`.

1. Используй скилл **adb-screenshot** для получения скриншота устройства. Получи путь к PNG.
2. Выполни **Сценарий 2**, передав полученный путь и Figma URL.

**Результат:** В браузере открыт viewer: слева — скриншот с устройства, справа — макет из Figma.

---

## Структура скилла

```
.claude/skills/screenshot-compare/
├── SKILL.md                   # Этот файл
├── screenshots-compare.mjs    # Запускает HTTP-сервер и открывает viewer
├── scripts/
│   └── screenshots-compare.sh # Обёртка: вызывает screenshots-compare.mjs
└── viewer/
    ├── index.html             # Точка входа браузерного приложения
    ├── app.js                 # Логика viewer: Side-by-side, Overlay, Diff
    └── styles.css             # Стили viewer
```

---

## Константы

Вшиты в `viewer/app.js`, при необходимости отредактируй напрямую:
```
OVERLAY_WIDTH = 480   // ширина панели в режиме Overlay (px)
```

---

## Pitfalls

### Не анализируй изображения самостоятельно

После запуска скрипта — **задача выполнена**. Не читай скриншоты инструментом `Read`, не запрашивай Figma через MCP, не пытайся описать визуальные различия.

### Порядок параметров в скриптах

Первый аргумент — **скриншот устройства/локальный файл**, второй — **макет/Figma**. В viewer: левая панель = первый аргумент, правая = второй.

### Сервер нужно останавливать вручную

`screenshots-compare.mjs` держит HTTP-сервер запущенным. Остановить — `Ctrl+C` в терминале.
