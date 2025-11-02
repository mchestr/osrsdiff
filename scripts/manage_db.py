#!/usr/bin/env python3
"""Database management script for OSRS Diff."""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.models.base import create_tables, drop_tables, close_db


async def create_all_tables():
    """Create all database tables using SQLAlchemy."""
    print("Creating all database tables...")
    await create_tables()
    print("✓ All tables created successfully")


async def drop_all_tables():
    """Drop all database tables using SQLAlchemy."""
    print("Dropping all database tables...")
    await drop_tables()
    print("✓ All tables dropped successfully")


async def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/manage_db.py [create|drop]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "create":
            await create_all_tables()
        elif command == "drop":
            await drop_all_tables()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: create, drop")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())