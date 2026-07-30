#!/usr/bin/env python3
"""
Alembic Migration Runner for Scoratis

Usage:
    python scripts/run_migrations.py upgrade      # Apply all pending migrations
    python scripts/run_migrations.py downgrade    # Rollback one migration
    python scripts/run_migrations.py current      # Show current revision
    python scripts/run_migrations.py history      # Show migration history
    python scripts/run_migrations.py generate "description"  # Create new migration
"""

import os
import sys
import subprocess
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)


def run_alembic(*args):
    """Run alembic command with proper environment."""
    # Set database URL from environment or default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://scoratis:scoratis_password@localhost:5434/scoratis"
    )

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    cmd = ["alembic"] + list(args)
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, env=env, cwd=backend_dir)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1].lower()

    if command == "upgrade":
        # Apply all pending migrations
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_alembic("upgrade", revision)

    elif command == "downgrade":
        # Rollback one migration (or to specific revision)
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return run_alembic("downgrade", revision)

    elif command == "current":
        # Show current revision
        return run_alembic("current")

    elif command == "history":
        # Show migration history
        return run_alembic("history", "--verbose")

    elif command == "generate" or command == "revision":
        # Generate new migration
        if len(sys.argv) < 3:
            print("Error: Please provide a migration description")
            print("Usage: python scripts/run_migrations.py generate 'Add new column'")
            return 1
        description = sys.argv[2]
        return run_alembic("revision", "--autogenerate", "-m", description)

    elif command == "stamp":
        # Stamp the database with a revision without running migrations
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_alembic("stamp", revision)

    elif command == "heads":
        # Show current heads
        return run_alembic("heads")

    elif command == "branches":
        # Show branch points
        return run_alembic("branches")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
