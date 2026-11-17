# Настройка ИИ-агентов (OpenCode)

Проект собран в OpenCode командой из трёх агентов. Ниже — вся обвязка, которая
использовалась, в исходном виде.

## Проектная обвязка (в репозитории, как есть)

- `.opencode/opencode.json` — конфиг проекта: агент по умолчанию, права на
  команды, запрет чтения `.env` и медиа.
- `.opencode/AGENTS.md` — правила для всех агентов проекта.
- `.opencode/agents/lead.md` — Team Lead: архитектура, контракт API, инфраструктура, git.
- `.opencode/agents/backend.md` — backend-агент (FastAPI, БД, worker, тесты).
- `.opencode/agents/frontend.md` — frontend-агент (Vue 3 + TS).

## Глобальная обвязка (копия из `~/.config/opencode/`)

- `AGENTS.global.md` — глобальные правила (стиль ответов, дисциплина вывода,
  работа с инструментами).
- `opencode.global.sanitized.jsonc` — глобальный конфиг OpenCode: провайдеры,
  модели, MCP. Секреты заменены на `REDACTED`, остальное без изменений.
- `skills/caveman/`, `skills/ultracave/`, `skills/megacave/` — скиллы стиля
  ответов, которые были активны во время работы.

## Диалоги

Полные диалоги — в `docs/session/*.json`. Это исходные JSON-экспорты OpenCode
(`{"info": ..., "messages": [...]}`), по одному на этап: `m0`–`m7` и
`bugs-fixed`. Файлы не пересказаны и не отредактированы.
