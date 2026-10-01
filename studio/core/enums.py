from enum import Enum


class AssetType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"
    VEHICLE = "vehicle"
    STYLE = "style"
    VOICE = "voice"
    MUSIC = "music"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class StoryMode(str, Enum):
    CANON = "canon"
    PLAYGROUND = "playground"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    FAILED = "failed"
    RETRY = "retry"
