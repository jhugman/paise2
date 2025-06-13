# ABOUTME: Test profile plugins - minimal test configuration provider
# ABOUTME: Provides basic test configuration for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import hookimpl


class TestConfigurationProvider(ConfigurationProvider):
    """Test configuration provider for minimal test settings."""

    def get_default_configuration(self) -> str:
        """Return minimal test configuration as YAML."""
        return """
app:
  name: PAISE2-Test
  version: 1.0
  debug: true

logging:
  level: DEBUG
  format: simple

test:
  enabled: true
  timeout: 5
"""

    def get_configuration_id(self) -> str:
        """Return configuration ID."""
        return "test_config"


@hookimpl
def register_configuration_provider(
    register: Callable[[ConfigurationProvider], None],
) -> None:
    """Register the test configuration provider."""
    register(TestConfigurationProvider())
