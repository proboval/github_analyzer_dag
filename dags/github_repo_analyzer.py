from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from src.aggregate import (
    aggregate_by_language,
    aggregate_issue_stats,
    aggregate_repo_activity,
)
from src.config import (
    MAX_REPOS,
    RAW_DIR,
    STAGE_DIR,
    TOP_N_REPOS,
)
from src.marts import (
    build_language_mart,
    build_organization_mart,
    build_player_mart,
)
from src.pipeline import extract_to_raw, transform_to_stage

import pandas as pd


def _load(name, subdir):
    path = subdir / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def extract(**context):
    top_n = int(Variable.get("gh_top_n", TOP_N_REPOS))
    max_repos = int(Variable.get("gh_max_repos", MAX_REPOS))
    paths = extract_to_raw(top_n=top_n, recent_days=30, max_repos=max_repos)
    context["ti"].xcom_push(key="extract_paths", value=paths)
    return paths


def transform(**context):
    paths = transform_to_stage()
    context["ti"].xcom_push(key="transform_paths", value=paths)
    return paths


def build_marts(**context):
    repos = _load("repos_stage", STAGE_DIR)
    commits = _load("commits_stage", STAGE_DIR)
    issues = _load("issues_stage", STAGE_DIR)
    pulls = _load("pulls_stage", STAGE_DIR)

    paths = build_player_mart(repos, commits, issues, pulls)
    paths["language_mart.parquet"] = build_language_mart(repos)
    paths["organization_mart.parquet"] = build_organization_mart(repos)

    # дополнительные агрегаты сохраняем в stage для отладки
    for name, df in [
        ("agg_by_language", aggregate_by_language(repos)),
        ("agg_repo_activity", aggregate_repo_activity(repos, commits)),
        ("agg_issue_stats", aggregate_issue_stats(repos, issues)),
    ]:
        if not df.empty:
            df.to_parquet(STAGE_DIR / f"{name}.parquet", index=False)

    context["ti"].xcom_push(key="mart_paths", value=paths)
    return paths


default_args = {
    "owner": "github-analyzer",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2024, 1, 1),
    "catchup": False,
}

with DAG(
    dag_id="github_repo_analyzer",
    default_args=default_args,
    schedule_interval="@daily",
    description="Сбор данных из GitHub, трансформация, агрегация и витрины",
    doc_md=("""
# GitHub Repo Analyzer

Пайплайн: Extract (GitHub API) -> Transform -> Aggregate -> Marts (Parquet)

Запустить вручную: `airflow dags trigger github_repo_analyzer`
    """),
    tags=["github", "analytics", "parquet"],
    catchup=False,
) as dag:

    t_extract = PythonOperator(
        task_id="extract_github",
        python_callable=extract,
        provide_context=True,
    )

    t_transform = PythonOperator(
        task_id="transform_stage",
        python_callable=transform,
        provide_context=True,
    )

    t_marts = PythonOperator(
        task_id="build_marts",
        python_callable=build_marts,
        provide_context=True,
    )

    t_extract >> t_transform >> t_marts
