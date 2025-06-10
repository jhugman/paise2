# ABOUTME: Tests for configuration diffing and state management functionality
# ABOUTME: Covers ConfigurationDiffer, EnhancedMergedConfiguration, and diff calculation


from paise2.config.diffing import ConfigurationDiffer, EnhancedMergedConfiguration
from paise2.plugins.core.interfaces import ConfigurationDiff


class TestConfigurationDiffer:
    """Test configuration diff calculation."""

    def test_calculate_diff_added(self):
        """Test detecting added configuration."""
        old_config = {"plugin_a": {"setting1": "value1"}}
        new_config = {
            "plugin_a": {"setting1": "value1"},
            "plugin_b": {"setting2": "value2"},
        }

        diff = ConfigurationDiffer.calculate_diff(old_config, new_config)

        assert "plugin_b" in diff.added
        assert diff.added["plugin_b"]["setting2"] == "value2"
        assert "plugin_a" in diff.unchanged

    def test_calculate_diff_removed(self):
        """Test detecting removed configuration."""
        old_config = {
            "plugin_a": {"setting1": "value1"},
            "plugin_b": {"setting2": "value2"},
        }
        new_config = {"plugin_a": {"setting1": "value1"}}

        diff = ConfigurationDiffer.calculate_diff(old_config, new_config)

        assert "plugin_b" in diff.removed
        assert diff.removed["plugin_b"]["setting2"] == "value2"
        assert "plugin_a" in diff.unchanged

    def test_calculate_diff_modified(self):
        """Test detecting modified configuration."""
        old_config = {"plugin_a": {"setting1": "old_value"}}
        new_config = {"plugin_a": {"setting1": "new_value"}}

        diff = ConfigurationDiffer.calculate_diff(old_config, new_config)

        # With the new approach, modifications appear in both added and removed
        assert "plugin_a" in diff.added
        assert diff.added["plugin_a"]["setting1"] == "new_value"
        assert "plugin_a" in diff.removed
        assert diff.removed["plugin_a"]["setting1"] == "old_value"
        # Modified section should be empty (kept for backwards compatibility)
        assert len(diff.modified) == 0

    def test_calculate_diff_nested_changes(self):
        """Test detecting changes in nested configuration."""
        old_config = {
            "plugin_a": {
                "section1": {"setting1": "value1"},
                "section2": {"setting2": "value2"},
            }
        }
        new_config = {
            "plugin_a": {
                "section1": {"setting1": "new_value1"},
                "section2": {"setting2": "value2"},
                "section3": {"setting3": "value3"},
            }
        }

        diff = ConfigurationDiffer.calculate_diff(old_config, new_config)

        # With new approach: changes appear in added/removed, new sections in added
        assert "plugin_a" in diff.added
        assert diff.added["plugin_a"]["section1"]["setting1"] == "new_value1"
        assert diff.added["plugin_a"]["section3"]["setting3"] == "value3"

        assert "plugin_a" in diff.removed
        assert diff.removed["plugin_a"]["section1"]["setting1"] == "value1"

        assert "plugin_a" in diff.unchanged
        assert diff.unchanged["plugin_a"]["section2"]["setting2"] == "value2"

    def test_calculate_diff_no_changes(self):
        """Test when there are no changes."""
        config = {"plugin_a": {"setting1": "value1"}}

        diff = ConfigurationDiffer.calculate_diff(config, config)

        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.modified) == 0
        assert "plugin_a" in diff.unchanged

    def test_has_path_changed_positive(self):
        """Test detecting path changes."""
        diff = ConfigurationDiff(
            added={
                "plugin_a": {"new_setting": "value"},
                "plugin_b": {"old_setting": "new"},
            },
            removed={"plugin_b": {"old_setting": "old"}},
            modified={},  # Empty with new approach
            unchanged={},
        )

        assert ConfigurationDiffer.has_path_changed(diff, "plugin_a.new_setting")
        assert ConfigurationDiffer.has_path_changed(diff, "plugin_b.old_setting")

    def test_has_path_changed_negative(self):
        """Test when path hasn't changed."""
        diff = ConfigurationDiff(
            added={"plugin_a": {"new_setting": "value"}},
            removed={},
            modified={},
            unchanged={"plugin_b": {"setting": "value"}},
        )

        assert not ConfigurationDiffer.has_path_changed(diff, "plugin_b.setting")
        assert not ConfigurationDiffer.has_path_changed(diff, "plugin_c.setting")

    def test_values_equal_different_types(self):
        """Test value equality with different types."""
        assert ConfigurationDiffer._values_equal("123", 123) is False  # noqa: SLF001
        assert ConfigurationDiffer._values_equal(True, "true") is False  # noqa: SLF001
        assert ConfigurationDiffer._values_equal([1, 2, 3], [1, 2, 3]) is True  # noqa: SLF001

    def test_get_path_value_from_diff_dict(self):
        """Test retrieving values from diff dictionary using dotted paths."""
        diff_dict = {"plugin_a": {"section1": {"setting1": "value1"}}}

        result = ConfigurationDiffer.get_path_value_from_diff_dict(
            diff_dict, ["plugin_a", "section1", "setting1"]
        )
        assert result == "value1"

        result = ConfigurationDiffer.get_path_value_from_diff_dict(
            diff_dict, ["plugin_a", "nonexistent"], "default"
        )
        assert result == "default"


class TestEnhancedMergedConfiguration:
    """Test enhanced configuration with diff support."""

    def test_enhanced_configuration_basic_access(self):
        """Test basic configuration access."""
        config_data = {
            "plugin_a": {"setting1": "value1"},
            "plugin_b": {"setting2": "value2"},
        }

        config = EnhancedMergedConfiguration(config_data)

        assert config.get("plugin_a.setting1") == "value1"
        assert config.get("plugin_b.setting2") == "value2"
        assert config.get("nonexistent", "default") == "default"

    def test_enhanced_configuration_with_diff(self):
        """Test configuration with diff information."""
        config_data = {
            "plugin_a": {"setting1": "new_value"},
            "plugin_b": {"setting2": "value2"},
        }

        diff = ConfigurationDiff(
            added={
                "plugin_a": {"setting1": "new_value"},
                "plugin_b": {"setting2": "value2"},
            },
            removed={"plugin_a": {"setting1": "old_value"}},
            modified={},  # Empty with new approach
            unchanged={},
        )

        config = EnhancedMergedConfiguration(config_data, diff)

        # Test has_changed
        assert config.has_changed("plugin_a.setting1")
        assert not config.has_changed("plugin_c.setting3")

        # Test addition
        assert config.addition("plugin_b.setting2") == "value2"
        assert config.addition("nonexistent") is None

        # Test removal
        assert config.removal("plugin_a.setting1") == "old_value"

        # Test diff property
        assert config.last_diff == diff

    def test_enhanced_configuration_no_diff(self):
        """Test configuration without diff information."""
        config_data = {"plugin_a": {"setting1": "value1"}}

        config = EnhancedMergedConfiguration(config_data)

        assert not config.has_changed("plugin_a.setting1")
        assert config.addition("plugin_a.setting1") is None
        assert config.removal("plugin_a.setting1") is None
        assert config.last_diff is None

    def test_enhanced_configuration_get_section(self):
        """Test getting entire configuration sections."""
        config_data = {
            "plugin_a": {"setting1": "value1", "setting2": "value2"},
            "plugin_b": {"setting3": "value3"},
        }

        config = EnhancedMergedConfiguration(config_data)

        section = config.get_section("plugin_a")
        assert section["setting1"] == "value1"
        assert section["setting2"] == "value2"

        empty_section = config.get_section("nonexistent")
        assert empty_section == {}

    def test_enhanced_configuration_removal_access(self):
        """Test accessing removed configuration values."""
        config_data = {"plugin_a": {"setting1": "value1"}}

        diff = ConfigurationDiff(
            added={},
            removed={"plugin_b": {"removed_setting": "removed_value"}},
            modified={},
            unchanged={"plugin_a": {"setting1": "value1"}},
        )

        config = EnhancedMergedConfiguration(config_data, diff)

        assert config.removal("plugin_b.removed_setting") == "removed_value"
        assert config.removal("nonexistent", "default") == "default"

    def test_enhanced_configuration_complex_path_changes(self):
        """Test complex nested path changes."""
        config_data = {
            "plugin_a": {
                "section1": {"setting1": "new_value"},
                "section2": {"setting2": "value2"},
            }
        }

        diff = ConfigurationDiff(
            added={
                "plugin_a": {
                    "section1": {"setting1": "new_value"},
                    "section2": {"setting2": "value2"}
                }
            },
            removed={
                "plugin_a": {
                    "section1": {"setting1": "old_value"}
                }
            },
            modified={},  # Empty with new approach
            unchanged={},
        )

        config = EnhancedMergedConfiguration(config_data, diff)

        # These should detect changes
        assert config.has_changed("plugin_a.section1.setting1")
        assert config.has_changed("plugin_a.section2.setting2")

        # These should not detect changes (not in the diff)
        assert not config.has_changed("plugin_a.section3.setting3")
        assert not config.has_changed("plugin_b.section1.setting1")
