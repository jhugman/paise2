# ABOUTME: Profile-specific wiring for content source lifecycle management
# ABOUTME: Registers the ContentSourceLifecycleAction in the app profile

from __future__ import annotations

# Re-export for backwards compatibility and profile-specific customization
from paise2.plugins.providers.lifecycle import ContentSourceLifecycleAction

__all__ = ["ContentSourceLifecycleAction"]
