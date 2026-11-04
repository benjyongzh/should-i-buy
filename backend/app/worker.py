import argparse
import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.jobs import process_one


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    configure_logging()
    while True:
        processed = process_one(SessionLocal)
        if args.once:
            return
        if processed is None:
            time.sleep(settings().worker_poll_seconds)


if __name__ == "__main__":
    main()
