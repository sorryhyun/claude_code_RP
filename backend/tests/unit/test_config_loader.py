"""
Unit tests for config loader module.

Tests YAML configuration loading, caching, and hot-reloading.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from config.config_loader import (
    _config_cache,
    _get_cached_config,
    _get_file_mtime,
    _load_yaml_file,
    get_debug_config,
    get_memory_brain_prompt,
    get_tool_description,
)


class TestFileMtime:
    """Tests for _get_file_mtime function."""

    @pytest.mark.unit
    def test_get_file_mtime_existing_file(self):
        """Test getting modification time of existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                mtime = _get_file_mtime(tmp_path)
                assert mtime > 0
                assert isinstance(mtime, float)
            finally:
                tmp_path.unlink()

    @pytest.mark.unit
    def test_get_file_mtime_nonexistent_file(self):
        """Test getting modification time of nonexistent file returns 0."""
        mtime = _get_file_mtime(Path("/nonexistent/file.yaml"))
        assert mtime == 0.0


class TestLoadYamlFile:
    """Tests for _load_yaml_file function."""

    @pytest.mark.unit
    def test_load_yaml_file_valid(self):
        """Test loading valid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("key: value\nnumber: 42\n")
            tmp_path = Path(tmp.name)

        try:
            result = _load_yaml_file(tmp_path)
            assert result == {"key": "value", "number": 42}
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_load_yaml_file_empty(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("")
            tmp_path = Path(tmp.name)

        try:
            result = _load_yaml_file(tmp_path)
            assert result == {}
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_load_yaml_file_nonexistent(self):
        """Test loading nonexistent YAML file returns empty dict."""
        result = _load_yaml_file(Path("/nonexistent/file.yaml"))
        assert result == {}

    @pytest.mark.unit
    def test_load_yaml_file_nested_structure(self):
        """Test loading YAML file with nested structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("parent:\n  child1: value1\n  child2: value2\n")
            tmp_path = Path(tmp.name)

        try:
            result = _load_yaml_file(tmp_path)
            assert result == {"parent": {"child1": "value1", "child2": "value2"}}
        finally:
            tmp_path.unlink()


class TestCachedConfig:
    """Tests for _get_cached_config function."""

    def setup_method(self):
        """Clear cache before each test."""
        _config_cache.clear()

    @pytest.mark.unit
    def test_get_cached_config_first_load(self):
        """Test loading config for the first time (cache miss)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("test: value\n")
            tmp_path = Path(tmp.name)

        try:
            result = _get_cached_config(tmp_path)
            assert result == {"test": "value"}
            assert str(tmp_path) in _config_cache
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_cached_config_cache_hit(self):
        """Test loading config from cache (cache hit)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("test: value\n")
            tmp_path = Path(tmp.name)

        try:
            # First load
            result1 = _get_cached_config(tmp_path)
            # Second load (should hit cache)
            result2 = _get_cached_config(tmp_path)

            assert result1 == result2
            assert result2 == {"test": "value"}
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_cached_config_force_reload(self):
        """Test force reloading config bypasses cache."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("test: value1\n")
            tmp_path = Path(tmp.name)

        try:
            # First load
            result1 = _get_cached_config(tmp_path)
            assert result1 == {"test": "value1"}

            # Modify file
            with open(tmp_path, "w") as f:
                f.write("test: value2\n")

            # Force reload
            result2 = _get_cached_config(tmp_path, force_reload=True)
            assert result2 == {"test": "value2"}
        finally:
            tmp_path.unlink()


class TestGetDebugConfig:
    """Tests for get_debug_config function."""

    def setup_method(self):
        """Clear cache before each test."""
        _config_cache.clear()

    @pytest.mark.unit
    def test_get_debug_config_env_override_true(self, monkeypatch):
        """Test DEBUG_AGENTS environment variable overrides config."""
        # Create a temporary debug config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("debug:\n  enabled: false\n")
            tmp_path = Path(tmp.name)

        try:
            # Set environment variable
            monkeypatch.setenv("DEBUG_AGENTS", "true")

            # Patch the DEBUG_CONFIG path
            with patch("config.loaders.DEBUG_CONFIG", tmp_path):
                config = get_debug_config()
                assert config["debug"]["enabled"] is True
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_debug_config_env_override_false(self, monkeypatch):
        """Test DEBUG_AGENTS=false overrides config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("debug:\n  enabled: true\n")
            tmp_path = Path(tmp.name)

        try:
            monkeypatch.setenv("DEBUG_AGENTS", "false")

            with patch("config.loaders.DEBUG_CONFIG", tmp_path):
                config = get_debug_config()
                assert config["debug"]["enabled"] is False
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_debug_config_no_env_override(self, monkeypatch):
        """Test config is used when no environment variable is set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("debug:\n  enabled: true\n")
            tmp_path = Path(tmp.name)

        try:
            # Make sure env var is not set
            monkeypatch.delenv("DEBUG_AGENTS", raising=False)

            with patch("config.loaders.DEBUG_CONFIG", tmp_path):
                config = get_debug_config()
                assert config["debug"]["enabled"] is True
        finally:
            tmp_path.unlink()


class TestGetToolDescription:
    """Tests for get_tool_description function."""

    def setup_method(self):
        """Clear cache before each test."""
        _config_cache.clear()

    @pytest.mark.unit
    def test_get_tool_description_basic(self):
        """Test getting basic tool description."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("tools:\n  test_tool:\n    enabled: true\n    description: 'Test {agent_name}'\n")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.TOOLS_CONFIG", tmp_path):
                desc = get_tool_description("test_tool", agent_name="Alice")
                assert desc == "Test Alice"
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_tool_description_disabled_tool(self):
        """Test getting description of disabled tool returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("tools:\n  test_tool:\n    enabled: false\n    description: 'Test description'\n")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.TOOLS_CONFIG", tmp_path):
                desc = get_tool_description("test_tool")
                assert desc is None
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_tool_description_not_found(self):
        """Test getting description of nonexistent tool returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("tools:\n  other_tool:\n    enabled: true\n    description: 'Test'\n")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.TOOLS_CONFIG", tmp_path):
                desc = get_tool_description("nonexistent_tool")
                assert desc is None
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_tool_description_with_variables(self):
        """Test tool description with multiple template variables."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("tools:\n  test_tool:\n    enabled: true\n    description: '{agent_name} - {config_sections}'\n")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.TOOLS_CONFIG", tmp_path):
                desc = get_tool_description("test_tool", agent_name="Alice", config_sections="memory, background")
                assert desc == "Alice - memory, background"
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_tool_description_guidelines_tool(self):
        """Test getting guidelines tool description from separate file."""
        # Create tools config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("tools:\n  guidelines:\n    enabled: true\n")
            tools_path = Path(tmp.name)

        # Create guidelines config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("active_version: v1\nv1:\n  template: 'Guidelines for {agent_name}'\n")
            guidelines_path = Path(tmp.name)

        try:
            with (
                patch("config.loaders.TOOLS_CONFIG", tools_path),
                patch("config.loaders.GUIDELINES_CONFIG", guidelines_path),
            ):
                desc = get_tool_description("guidelines", agent_name="Alice")
                assert desc == "Guidelines for Alice"
        finally:
            tools_path.unlink()
            guidelines_path.unlink()


class TestGetMemoryBrainPrompt:
    """Tests for get_memory_brain_prompt function."""

    def setup_method(self):
        """Clear cache before each test."""
        _config_cache.clear()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_basic(self):
        """Test basic memory-brain prompt template substitution."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("""
memory_brain_prompt: |
  You are memory brain for {agent_name}.
  Max: {max_memories}
  Policy: {policy_section}
""")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                prompt = get_memory_brain_prompt(agent_name="TestAgent", max_memories=3, policy_section="Test policy")
                assert "TestAgent" in prompt
                assert "3" in prompt
                assert "Test policy" in prompt
                # Ensure placeholders are replaced
                assert "{agent_name}" not in prompt
                assert "{max_memories}" not in prompt
                assert "{policy_section}" not in prompt
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_missing_template(self):
        """Test that missing template returns empty string."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("active_version: v1\n")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                prompt = get_memory_brain_prompt(agent_name="TestAgent", max_memories=3, policy_section="Test")
                assert prompt == ""
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_empty_values(self):
        """Test memory-brain prompt with empty string values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("""
memory_brain_prompt: |
  Agent: {agent_name}
  Max: {max_memories}
  Policy: {policy_section}
""")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                prompt = get_memory_brain_prompt(agent_name="", max_memories=0, policy_section="")
                # Should still work with empty values
                assert "Agent: " in prompt
                assert "Max: 0" in prompt
                assert "Policy: " in prompt
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_special_characters(self):
        """Test memory-brain prompt with special characters in values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("""
memory_brain_prompt: |
  Name: {agent_name}
  Max: {max_memories}
""")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                prompt = get_memory_brain_prompt(agent_name="Dr. O'Brien (PhD)", max_memories=3, policy_section="Test")
                assert "Dr. O'Brien (PhD)" in prompt
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_korean_characters(self):
        """Test memory-brain prompt with Korean characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            tmp.write("""
memory_brain_prompt: |
  이름: {agent_name}
  최대: {max_memories}
  정책: {policy_section}
""")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                prompt = get_memory_brain_prompt(agent_name="프리렌", max_memories=3, policy_section="균형 잡힌 정책")
                assert "프리렌" in prompt
                assert "균형 잡힌 정책" in prompt
        finally:
            tmp_path.unlink()

    @pytest.mark.unit
    def test_get_memory_brain_prompt_multiline_values(self):
        """Test memory-brain prompt with multiline values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("""
memory_brain_prompt: |
  Agent: {agent_name}

  Max Memories: {max_memories}

  Policy:
  {policy_section}
""")
            tmp_path = Path(tmp.name)

        try:
            with patch("config.loaders.GUIDELINES_CONFIG", tmp_path):
                multiline_policy = "Line 1\nLine 2\nLine 3"

                prompt = get_memory_brain_prompt(
                    agent_name="TestAgent", max_memories=5, policy_section=multiline_policy
                )
                assert multiline_policy in prompt
        finally:
            tmp_path.unlink()
