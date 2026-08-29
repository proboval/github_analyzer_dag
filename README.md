# GitHub Repo Analyzer (DAG)

Пет-проект: полный ETL-пайплайн сбора данных о популярных GitHub-репозиториях, их трансформации, агрегации и построения витрин данных.

## Стек
- **Python 3.11**
- **Apache Airflow** (оркестрация DAG) — в Docker
- **pandas + pyarrow** (Parquet)
- **GitHub REST API** (источник)

## Архитектура пайплайна

```
GitHub API ──► [Extract]  ──► raw/ (JSON)
                 │
                 ▼
            [Transform] ──► stage/ (Parquet, очищенные/нормализованные)
                 │
                 ▼
            [Aggregate] ──► агрегаты (by language/owner/activity)
                 │
                 ▼
            [Marts] ──► marts/ (Parquet витрины)
```

### Слои данных
| Слой | Формат | Содержимое |
|------|--------|------------|
| `data/raw/` | JSON | Сырые данные GitHub API (репозитории, коммиты, issues, PR) |
| `data/stage/` | Parquet | Очищенные и нормализованные таблицы |
| `data/marts/` | Parquet | Витрины: репозитории, по языкам, по организациям |

### Этапы
1. **Extract** — через GitHub Search API получает топ-репозитории по звёздам; для каждого собирает недавние коммиты (последние 30 дней), открытые issues и pull requests.
2. **Transform** — нормализация (типы дат, числа, дедупликация, извлечение авторов/owner/license).
3. **Aggregate** — метрики по языкам, владельцам, активности, issues.
4. **Marts** — финальные витрины в Parquet:
   - `repo_mart.parquet` — сводные метрики по каждому репозиторию (звёзды, форки, коммиты, issues, PR, активность)
   - `language_mart.parquet` — агрегаты по языкам
   - `organization_mart.parquet` — агрегаты по организациям/владельцам

## Структура проекта
```
.
├── dags/
│   └── github_repo_analyzer.py   # Airflow DAG
├── src/
│   ├── config.py                 # конфигурация, пути, параметры
│   ├── extract.py                # GitHub API клиент (rate-limit, пагинация)
│   ├── transform.py              # очистка/нормализация
│   ├── aggregate.py              # агрегации
│   ├── marts.py                  # построение витрин
│   ├── pipeline.py               # сквозные функции этапов
│   └── pipeline_run.py           # локальный запуск без Airflow
├── data/ {raw, stage, marts}
├── docker-compose.yml            # Airflow (webserver + scheduler + postgres)
└── requirements.txt
```

## Быстрый старт (локально, без Airflow)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# малый запуск (5 репо, 3 деталей) — для проверки
.venv/bin/python -m src.pipeline_run --top-n 100 --max-repos 20 --recent-days 30
```

`--token` можно передать токен GitHub для большего rate-limit:
```bash
.venv/bin/python -m src.pipeline_run --token ghp_xxx
```

## Запуск через Airflow (Docker)

1. Создайте `.env` с токеном (опционально):
   ```bash
   echo "GITHUB_TOKEN=ghp_xxx" > .env
   ```
2. В `.env` также требуется `AIRFLOW_FERNET_KEY` (можно сгенерировать):
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. Запуск:
   ```bash
   docker compose up -d
   ```
4. UI: http://localhost:8080 (admin / admin). Запуск дага вручную: `github_repo_analyzer` → Trigger.

## Примечания
- GitHub API без токена имеет лимит 60 запросов/час — при больших выборках используйте токен.
- `open_issues` / `open_prs` в витринах считаются по выбранной выборке (лимит 50 на репозиторий), это ограничение пайплайна для пет-проекта.
- Параметры запуска в Airflow переопределяются через Variables (`gh_top_n`, `gh_max_repos`).
```
