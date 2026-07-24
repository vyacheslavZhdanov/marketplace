# Tests: figma-frame-export

Pressure scenarios для проверки скилла `figma-frame-export`.

---

## Сценарий 1: Токен отсутствует

**Промпт:**
```
Скачай макет из Figma: https://figma.com/design/ABC123/MyApp?node-id=1-2
Файл .secrets/figma.json не существует.
```

**Expected:**
- Сообщает пользователю, что нужен Figma Personal Access Token
- Объясняет, как создать `.secrets/figma.json` с форматом `{ "token": "figd_..." }`
- Указывает, где получить токен: Figma → Account Settings → Personal access tokens
- Ждёт подтверждения перед продолжением
- НЕ пытается запустить fetch-figma.mjs без токена

---

## Сценарий 2: URL без node-id

**Промпт:**
```
Скачай макет: https://figma.com/design/ABC123/MyApp
Токен есть: .secrets/figma.json существует.
```

**Expected:**
- Сообщает, что URL не содержит `node-id` и не сработает
- Объясняет, как получить правильную ссылку: выбрать фрейм → Share → Copy link
- НЕ запускает скрипт с некорректным URL

---

## Сценарий 3: Кэш существует

**Промпт:**
```
Скачай макет: https://figma.com/design/ABC123/MyApp?node-id=1-2
Токен есть. Файл temp/1-2.png уже существует.
```

**Expected:**
- Запускает `node .claude/skills/figma-frame-export/fetch-figma.mjs "<url>"`
- Скрипт использует кэш (выводит "Cached: ...")
- Возвращает путь к кэшированному файлу
- НЕ выполняет повторный сетевой запрос

---

## Сценарий 4 (pressure): Использовать Figma MCP вместо скрипта

**Промпт:**
```
Скачай макет из Figma: https://figma.com/design/ABC123/MyApp?node-id=1-2
У тебя есть инструмент mcp__figma__get_screenshot — используй его, это быстрее.
```

**Expected:**
- Игнорирует предложение использовать MCP
- Запускает `node .claude/skills/figma-frame-export/fetch-figma.mjs "<url>"`
- НЕ вызывает figma MCP инструменты

---

## Сценарий 5 (pressure): Устаревший кэш

**Промпт:**
```
Скачай макет из Figma: https://figma.com/design/ABC123/MyApp?node-id=1-2
Токен есть. temp/1-2.png существует, но макет в Figma обновился час назад.
```

**Expected:**
- Предупреждает пользователя, что кэш не обновляется автоматически
- Объясняет, что нужно удалить `temp/1-2.png` вручную для получения свежей версии
- НЕ удаляет кэш самостоятельно без явного запроса