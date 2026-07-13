"""ETL 수동 실행 CLI.

사용 예:
    python -m app.etl stores --mode bulk --csv ./data/stores/2026Q1.csv
    python -m app.etl stores --mode api
    python -m app.etl grid-stats --boundary-dir "./data/.../2. 경계" \\
        --stats-dir "./data/.../1. 통계" --codes-xlsx "./data/.../statistics_code.xlsx"
    python -m app.etl dispositions
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.database import get_engine
from app.etl import runner
from app.etl.client.http import EtlHttpClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.etl.cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.etl")
    sub = parser.add_subparsers(dest="source", required=True)

    stores_p = sub.add_parser("stores", help="소상공인 상가정보 적재")
    stores_p.add_argument("--mode", choices=["bulk", "api"], default="bulk")
    stores_p.add_argument(
        "--csv", type=Path, help="bulk 모드: CSV 파일 또는 지역별 CSV 가 담긴 디렉토리 경로"
    )

    grid_p = sub.add_parser("grid-stats", help="국토지리정보원/SGIS 격자 경계+통계 적재")
    grid_p.add_argument("--boundary-dir", type=Path, required=True, help="'2. 경계' 폴더 경로")
    grid_p.add_argument("--stats-dir", type=Path, required=True, help="'1. 통계' 폴더 경로")
    grid_p.add_argument(
        "--codes-xlsx", type=Path, required=True, help="'제공용 코드(statistics_code).xlsx' 경로"
    )

    sub.add_parser("dispositions", help="식약처 행정처분 적재")

    args = parser.parse_args(argv)
    settings = get_settings()
    engine = get_engine()

    if args.source == "stores":
        if args.mode == "bulk":
            csv_path = args.csv or Path(settings.etl_stores_csv_path)
            result = runner.run_stores_bulk(engine, settings, csv_path)
        else:
            with EtlHttpClient(settings) as client:
                result = runner.run_stores_api(engine, settings, client)
        logger.info("stores 적재 완료: %s", result)

    elif args.source == "grid-stats":
        result = runner.run_grid_stats(
            engine, settings, args.boundary_dir, args.stats_dir, args.codes_xlsx
        )
        logger.info("grid-stats 적재 완료: %s", result)

    elif args.source == "dispositions":
        with EtlHttpClient(settings) as client:
            result = runner.run_dispositions(engine, settings, client)
        logger.info("dispositions 적재 완료: %s", result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
