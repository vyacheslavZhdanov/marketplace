---
name: detekt-fix
description: Use when running detekt static analysis on Kotlin/Android code, need to review rule violations with plain-language explanations, and fix simple issues automatically or ask about complex ones
---

# Detekt Review and Fix

Форматирование → анализ → объяснение → авто-фикс простых → решение сложных с пользователем.

## Параметры

`MAX_DEBT = 15 min` | `MAX_CLASSES = 2`

Классификация — **на каждое вхождение отдельно** (не сумма по правилу):
- **Простое** → авто-фикс: debt < MAX_DEBT **И** файлов ≤ MAX_CLASSES
- **Сложное** → спросить: debt ≥ MAX_DEBT **ИЛИ** файлов > MAX_CLASSES

## Команды

```bash
bash scripts/ktfmt-changed.sh 2>&1   # форматирование сначала
./gradlew detektAll 2>&1             # анализ
```

Формат строки вывода: `/path/File.kt:10:5: error: Описание (RuleName) - Debt: 5 min`  
Читай консоль напрямую — XML не нужен.

## Сводка перед исправлениями

```
Найдено X нарушений, debt: Zh Nm

Авто-исправлю:  RuleName (N файлов, Nm) — [объяснение]
Спрошу у вас:   RuleName (N файлов, Nh) — [объяснение]
```

Для незнакомых правил: `https://detekt.dev/docs/rules/<ruleset>` (style / complexity / naming / comments / exceptions / performance)

## Сложные нарушения

Спрашивай по одному за раз. Несколько правил в одном месте — один вопрос:

```
[1/3] OrderRepository.kt:45
  • LongMethod — метод слишком длинный
  • ComplexMethod — слишком много ветвлений

1. Вынести вспомогательные методы
2. Разбить метод на части
3. Пропустить сейчас
4. Другое?
5. Suppress (@Suppress("detekt.LongMethod", "detekt.ComplexMethod"))
```

Suppress — запомни, не применяй сразу.

## Применение

1. Сначала — все авто-фиксы и согласованные исправления
2. Suppress-стратегия по итогу диалога:
   - **Большинство suppress** → `./gradlew detektGenerateBaseline 2>&1` (добавляет все оставшиеся нарушения в baseline)
   - **Меньшинство suppress** → `@Suppress("detekt.RuleName")` точечно на каждый элемент
3. Финальная проверка: `./gradlew detektAll 2>&1`

## Ограничения

- Не трогай сгенерированный код
- Не изменяй тесты без их последующего запуска
