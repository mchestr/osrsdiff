"""Player-related services for OSRS player tracking."""

from app.services.player.history import (
    BossProgress,
    HistoryService,
    ProgressAnalysis,
    SkillProgress,
    get_history_service,
)
from app.services.player.records import (
    PlayerRecords,
    RecordsService,
    SkillRecord,
    get_records_service,
)
from app.services.player.service import (
    PlayerService,
    get_player_service,
)
from app.services.player.statistics import (
    NoDataAvailableError,
    StatisticsService,
    get_statistics_service,
)
from app.services.player.summary import (
    SummaryGenerationError,
    SummaryService,
    get_summary_service,
    parse_summary_text,
)
from app.services.player.type_classifier import (
    PlayerTypeClassificationError,
    PlayerTypeClassifier,
)

__all__ = [
    # Service classes
    "PlayerService",
    "HistoryService",
    "StatisticsService",
    "SummaryService",
    "RecordsService",
    "PlayerTypeClassifier",
    # Data classes
    "ProgressAnalysis",
    "SkillProgress",
    "BossProgress",
    "PlayerRecords",
    "SkillRecord",
    # Exceptions
    "PlayerTypeClassificationError",
    "SummaryGenerationError",
    "NoDataAvailableError",
    # Dependency injection functions
    "get_player_service",
    "get_history_service",
    "get_statistics_service",
    "get_summary_service",
    "get_records_service",
    # Utility functions
    "parse_summary_text",
]
