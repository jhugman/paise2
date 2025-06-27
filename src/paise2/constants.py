"""ABOUTME: Central constants module for PAISE2 configuration and directory paths.
ABOUTME: Provides consistent access to environment variables and system paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# Environment variable names
PAISE2_PROFILE_ENV: Final[str] = "PAISE2_PROFILE"
PAISE_CONFIG_DIR_ENV: Final[str] = "PAISE_CONFIG_DIR"

# Profile names
DEFAULT_PROFILE: Final[str] = "development"
VALID_PROFILES: Final[tuple[str, ...]] = ("development", "production", "test")

# Default directories
DEFAULT_CONFIG_DIR: Final[str] = "~/.config/paise2"
DEFAULT_DATA_DIR: Final[str] = "~/.local/share/paise2"

# Application directories (relative to package root)
PROFILES_DIR: Final[str] = "src/paise2/profiles"


def get_profile() -> str:
    """Get the active PAISE2 profile from environment variable.

    Returns:
        Profile name, defaults to 'development' if not set or invalid.
    """
    profile = os.getenv(PAISE2_PROFILE_ENV, DEFAULT_PROFILE).lower()
    if profile not in VALID_PROFILES:
        return DEFAULT_PROFILE
    return profile


def get_config_dir() -> str:
    """Get the configuration directory from environment variable.

    Returns:
        Configuration directory path, defaults to '~/.config/paise2' if not set.
    """
    return os.environ.get(PAISE_CONFIG_DIR_ENV, DEFAULT_CONFIG_DIR)


def get_data_dir() -> str:
    """Get the data directory for PAISE2.

    Returns:
        Data directory path defaulting to '~/.local/share/paise2'.
    """
    return DEFAULT_DATA_DIR


def get_profiles_dir() -> Path:
    """Get the absolute path to the profiles directory.

    Returns:
        Absolute path to src/paise2/profiles directory.
    """
    # Get the directory containing this constants.py file
    current_dir = Path(__file__).parent
    # Navigate to the profiles directory
    return current_dir / "profiles"


def get_default_cache_path() -> str:
    """Get the default cache directory path.

    Returns:
        Default cache path within the data directory.
    """
    return f"{DEFAULT_DATA_DIR}/cache"


def get_default_state_db_path() -> str:
    """Get the default state database path.

    Returns:
        Default state database path within the data directory.
    """
    return f"{DEFAULT_DATA_DIR}/state.db"


def get_default_task_db_path() -> str:
    """Get the default task queue database path.

    Returns:
        Default task database path within the data directory.
    """
    return f"{DEFAULT_DATA_DIR}/tasks.db"
