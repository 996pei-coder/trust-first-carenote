"""Back up the current local demo database and recreate the synthetic seed state."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app.database import Base, build_engine, build_session_factory, default_database_url
from app.models import Comment, Entry, Highlight, SourceArtifact
from app.seed import seed_database


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "carenote.db"
BACKUP_DIR = ROOT / "tmp" / "recording-backups"


def reset() -> Path | None:
    backup: Path | None = None
    if DATABASE.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / f"carenote-before-recording-{stamp}.db"
        shutil.move(str(DATABASE), str(backup))

    engine = build_engine(default_database_url())
    try:
        Base.metadata.create_all(engine)
        factory = build_session_factory(engine)
        with factory() as session:
            seed_database(session)
            counts = {
                "entries": session.scalar(select(func.count(Entry.id))),
                "highlights": session.scalar(select(func.count(Highlight.id))),
                "comments": session.scalar(select(func.count(Comment.id))),
                "source_artifacts": session.scalar(select(func.count(SourceArtifact.id))),
            }
        expected = {"entries": 5, "highlights": 3, "comments": 1, "source_artifacts": 0}
        if counts != expected:
            raise RuntimeError(f"Unexpected seed counts: {counts}; expected {expected}")
    except Exception:
        engine.dispose()
        if DATABASE.exists():
            DATABASE.unlink()
        if backup is not None:
            shutil.move(str(backup), str(DATABASE))
        raise
    engine.dispose()
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Back up carenote.db and recreate the five-entry synthetic recording state."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that the local demo server is stopped and the reset should run.",
    )
    args = parser.parse_args()
    if not args.confirm:
        parser.error("stop the demo server, then rerun with --confirm")
    backup = reset()
    print("Synthetic demo database reset successfully.")
    print(f"Previous database backup: {backup if backup else 'none (no prior database)'}")


if __name__ == "__main__":
    main()
