# Tests: screenshot-compare

Pressure scenarios для проверки скилла `screenshot-compare`.

---

## Сценарий 1: Неоднозначный запрос

**Промпт:**
```
Сравни скриншот с макетом.
```

**Expected:**
- Задаёт уточняющий вопрос через AskUserQuestion с тремя вариантами:
  1. Два скриншота
  2. Figma + скриншот
  3. Figma + устройство
- НЕ угадывает сценарий самостоятельно

---

## Сценарий 2: Два скриншота (сценарий 1)

**Промпт:**
```
Сравни два скриншота: screenshots/before.png и screenshots/after.png.
```

**Expected:**
- Запускает `bash .claude/skills/screenshot-compare/scripts/screenshots-compare.sh screenshots/before.png screenshots/after.png`
- Сообщает, что viewer открыт в браузере
- НЕ читает изображения через Read
- НЕ пытается описать визуальные различия

---

## Сценарий 3: Figma + скриншот (сценарий 2)

**Промпт:**
```
Сравни скриншот screenshots/screen.png с макетом https://figma.com/design/ABC/App?node-id=1-2
Токен есть.
```

**Expected:**
- Использует скилл `figma-frame-export` для скачивания макета
- Получает путь к скачанному PNG
- Запускает `screenshots-compare.sh screenshots/screen.png <путь_figma>`
- Порядок аргументов: скриншот слева, Figma справа
- НЕ использует figma MCP инструменты напрямую

---

## Сценарий 4: Figma + устройство (сценарий 3)

**Промпт:**
```
Сравни экран устройства с макетом https://figma.com/design/ABC/App?node-id=1-2
Устройство: emulator-5554. Токен есть.
```

**Expected:**
- Использует скилл `adb-screenshot` для получения скриншота
- Затем использует скилл `figma-frame-export` для скачивания макета
- Запускает `screenshots-compare.sh <путь_adb> <путь_figma>`
- НЕ делает всё в одной bash-команде, минуя скиллы

---

## Сценарий 5 (pressure): Попытка анализировать изображения

**Промпт:**
```
Сравни screenshots/before.png и screenshots/after.png.
После запуска скрипта опиши, какие визуальные различия ты видишь.
```

**Expected:**
- Запускает скрипт сравнения
- Явно отказывается анализировать изображения самостоятельно
- Сообщает, что анализ выполняется пользователем в браузере
- НЕ читает PNG через Read, НЕ перечисляет различия

---

## Сценарий 6 (pressure): Неправильный порядок аргументов

**Промпт:**
```
Сравни макет из Figma (уже скачан: temp/1-2.png) со скриншотом устройства screenshots/screen.png.
Запусти скрипт так: screenshots-compare.sh temp/1-2.png screenshots/screen.png
```

**Expected:**
- Исправляет порядок: первый аргумент — скриншот устройства, второй — Figma
- Запускает `screenshots-compare.sh screenshots/screen.png temp/1-2.png`
- Поясняет, что левая панель (первый аргумент) = устройство, правая = Figma
