#!/usr/bin/env python3
"""Script to inject 30 days of fake history data for a player.

Usage:
    python scripts/inject_fake_history.py <username>
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import select

from app.models.base import AsyncSessionLocal, close_db
from app.models.hiscore import HiscoreRecord
from app.models.player import Player

# OSRS skills in order
OSRS_SKILLS = [
    "attack",
    "hitpoints",
    "mining",
    "strength",
    "agility",
    "smithing",
    "defence",
    "herblore",
    "fishing",
    "ranged",
    "thieving",
    "cooking",
    "prayer",
    "crafting",
    "firemaking",
    "magic",
    "fletching",
    "woodcutting",
    "runecraft",
    "slayer",
    "farming",
    "construction",
    "hunter",
    "sailing",
]

# Some common OSRS bosses
OSRS_BOSSES = [
    "abyssal_sire",
    "alchemical_hydra",
    "barrows_chests",
    "bryophyta",
    "callisto",
    "cerberus",
    "chambers_of_xeric",
    "chambers_of_xeric_challenge_mode",
    "chaos_elemental",
    "chaos_fanatic",
    "commander_zilyana",
    "corporeal_beast",
    "crazy_archaeologist",
    "dagannoth_prime",
    "dagannoth_rex",
    "dagannoth_supreme",
    "deranged_archaeologist",
    "general_graardor",
    "giant_mole",
    "grotesque_guardians",
    "hespori",
    "kalphite_queen",
    "king_black_dragon",
    "kraken",
    "kree_arra",
    "kril_tsutsaroth",
    "mimic",
    "nex",
    "nightmare",
    "obor",
    "phantom_muspah",
    "sarachnis",
    "scorpia",
    "skotizo",
    "tempoross",
    "the_gauntlet",
    "the_corrupted_gauntlet",
    "theatre_of_blood",
    "theatre_of_blood_hard_mode",
    "thermonuclear_smoke_devil",
    "tombs_of_amascut",
    "tombs_of_amascut_expert",
    "tzkal_zuk",
    "tztok_jad",
    "venenatis",
    "vet_ion",
    "vorkath",
    "wintertodt",
    "zalcano",
    "zulrah",
]


def get_experience_for_level(level: int) -> int:
    """Calculate experience required for a given level."""
    if level <= 1:
        return 0
    total = 0
    for i in range(1, level):
        total += int(i + 300 * (2 ** (i / 7)))
    return int(total / 4)


def get_level_for_experience(exp: int) -> int:
    """Calculate level from experience."""
    if exp <= 0:
        return 1
    level = 1
    while get_experience_for_level(level + 1) <= exp and level < 99:
        level += 1
    return level


def generate_initial_skills() -> Dict[str, Dict[str, int]]:
    """Generate initial skill data with realistic starting values."""
    skills = {}
    base_rank = random.randint(50000, 200000)

    for skill in OSRS_SKILLS:
        # Start with varied levels (some skills higher than others)
        if skill in ["attack", "strength", "defence", "hitpoints"]:
            # Combat skills start higher
            base_level = random.randint(50, 80)
        elif skill in ["cooking", "fishing", "woodcutting"]:
            # Easy skills start higher
            base_level = random.randint(40, 70)
        else:
            # Other skills start lower
            base_level = random.randint(1, 50)

        experience = get_experience_for_level(base_level)
        # Add some random XP on top
        experience += random.randint(0, experience // 10)

        skills[skill] = {
            "rank": base_rank + random.randint(-10000, 10000),
            "level": get_level_for_experience(experience),
            "experience": experience,
        }

    return skills


def generate_initial_bosses() -> Dict[str, Dict[str, int]]:
    """Generate initial boss kill counts."""
    bosses = {}
    base_rank = random.randint(10000, 100000)

    # Only include some bosses (not all players kill all bosses)
    selected_bosses = random.sample(OSRS_BOSSES, k=random.randint(5, 15))

    for boss in selected_bosses:
        # Some bosses have more kills than others
        if boss in ["zulrah", "vorkath", "barrows_chests"]:
            kill_count = random.randint(50, 500)
        else:
            kill_count = random.randint(0, 100)

        bosses[boss] = {
            "rank": base_rank + random.randint(-5000, 5000),
            "kill_count": kill_count,
        }

    return bosses


def progress_skills(skills: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """Progress skills forward by simulating daily gains."""
    new_skills = {}
    base_rank = random.randint(50000, 200000)

    for skill, data in skills.items():
        current_exp = data["experience"]
        current_level = data["level"]

        # Different skills progress at different rates
        if skill in ["attack", "strength", "defence", "ranged", "magic"]:
            # Combat skills: moderate XP gain
            daily_xp = random.randint(50000, 200000)
        elif skill in ["slayer"]:
            # Slayer: high XP gain
            daily_xp = random.randint(100000, 300000)
        elif skill in ["runecraft", "agility"]:
            # Slow skills: low XP gain
            daily_xp = random.randint(10000, 50000)
        else:
            # Other skills: varied XP gain
            daily_xp = random.randint(20000, 150000)

        # Add some randomness (not every day is the same)
        daily_xp = int(daily_xp * random.uniform(0.5, 1.5))

        new_exp = current_exp + daily_xp
        new_level = get_level_for_experience(new_exp)

        new_skills[skill] = {
            "rank": base_rank + random.randint(-10000, 10000),
            "level": min(new_level, 99),  # Cap at 99
            "experience": new_exp,
        }

    return new_skills


def progress_bosses(bosses: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """Progress boss kill counts forward."""
    new_bosses = {}
    base_rank = random.randint(10000, 100000)

    for boss, data in bosses.items():
        current_kc = data["kill_count"]

        # Some bosses get more kills per day
        if boss in ["zulrah", "vorkath"]:
            daily_kills = random.randint(5, 20)
        elif boss in ["barrows_chests", "theatre_of_blood"]:
            daily_kills = random.randint(1, 10)
        else:
            # Most bosses: occasional kills
            daily_kills = random.randint(0, 3)

        new_kc = current_kc + daily_kills

        new_bosses[boss] = {
            "rank": base_rank + random.randint(-5000, 5000),
            "kill_count": new_kc,
        }

    return new_bosses


async def inject_fake_history(username: str, days: int = 30) -> None:
    """Inject fake history data for a player.

    Args:
        username: OSRS player username
        days: Number of days of history to generate
    """
    async with AsyncSessionLocal() as session:
        # Find the player
        stmt = select(Player).where(Player.username.ilike(username))
        result = await session.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            print(f"Error: Player '{username}' not found in database.")
            sys.exit(1)

        print(f"Found player: {player.username} (ID: {player.id})")
        print(f"Generating {days} days of fake history data...")

        # Generate initial data
        skills = generate_initial_skills()
        bosses = generate_initial_bosses()

        # Calculate overall stats
        overall_level = sum(s["level"] for s in skills.values())
        overall_experience = sum(s["experience"] for s in skills.values())
        overall_rank = random.randint(10000, 100000)

        # Generate records for each day
        records_created = 0
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        for day in range(days):
            # Calculate date for this record
            record_date = start_date + timedelta(days=day)

            # Progress skills and bosses
            if day > 0:
                skills = progress_skills(skills)
                bosses = progress_bosses(bosses)

            # Recalculate overall stats
            overall_level = sum(s["level"] for s in skills.values())
            overall_experience = sum(s["experience"] for s in skills.values())

            # Create hiscore record
            record = HiscoreRecord(
                player_id=player.id,
                fetched_at=record_date,
                overall_rank=overall_rank + random.randint(-1000, 1000),
                overall_level=overall_level,
                overall_experience=overall_experience,
                skills_data=skills.copy(),
                bosses_data=bosses.copy(),
            )

            session.add(record)
            records_created += 1

            if (day + 1) % 10 == 0:
                print(f"  Created {day + 1}/{days} records...")

        # Commit all records
        await session.commit()
        print(f"\nSuccessfully created {records_created} history records!")

        # Update player's last_fetched
        player.last_fetched = datetime.now(timezone.utc)
        await session.commit()
        print(f"Updated player's last_fetched timestamp.")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/inject_fake_history.py <username> [days]")
        sys.exit(1)

    username = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    if days <= 0:
        print("Error: Days must be a positive integer.")
        sys.exit(1)

    try:
        await inject_fake_history(username, days)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())

