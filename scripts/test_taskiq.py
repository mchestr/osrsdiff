#!/usr/bin/env python3
"""
Script to test TaskIQ setup and demonstrate task execution.

Usage:
    python scripts/test_taskiq.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.workers.tasks import health_check_task, retry_task, timeout_task


async def main():
    """Test TaskIQ tasks."""
    print("Testing TaskIQ setup...")
    print("=" * 50)
    
    try:
        # Test health check task
        print("\n1. Testing health check task...")
        health_task = await health_check_task.kiq()
        health_result = await health_task.wait_result(timeout=10)
        print(f"Health check result: {health_result}")
        
        # Test retry task (success)
        print("\n2. Testing retry task (success)...")
        retry_success_task = await retry_task.kiq(should_fail=False)
        retry_success_result = await retry_success_task.wait_result(timeout=10)
        print(f"Retry task (success) result: {retry_success_result}")
        
        # Test timeout task
        print("\n3. Testing timeout task...")
        timeout_test_task = await timeout_task.kiq(delay_seconds=1.0)
        timeout_result = await timeout_test_task.wait_result(timeout=15)
        print(f"Timeout task result: {timeout_result}")
        
        print("\n" + "=" * 50)
        print("✅ All TaskIQ tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ TaskIQ test failed: {e}")
        print("\nMake sure Redis is running and the TaskIQ worker is started:")
        print("  docker run -d -p 6379:6379 redis:7")
        print("  mise run worker")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())