"""Tests for template loader utility."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.template_loader import (
    TEMPLATES_DIR,
    get_jinja_env,
    render_template,
)


class TestTemplateLoader:
    """Test cases for template loader."""

    def test_templates_dir_exists(self):
        """Test that templates directory exists."""
        assert TEMPLATES_DIR.exists()
        assert TEMPLATES_DIR.is_dir()

    def test_get_jinja_env_creates_environment(self):
        """Test that get_jinja_env creates a Jinja2 environment."""
        env = get_jinja_env()
        assert env is not None
        assert env.loader.searchpath == [str(TEMPLATES_DIR)]

    def test_get_jinja_env_singleton(self):
        """Test that get_jinja_env returns the same instance."""
        env1 = get_jinja_env()
        env2 = get_jinja_env()
        assert env1 is env2

    def test_render_template_system_prompt(self):
        """Test rendering the system prompt template."""
        content = render_template("summary/system_prompt.j2", {})
        assert isinstance(content, str)
        assert len(content) > 0
        assert "OSRS" in content or "RuneScape" in content
        assert "analyst" in content.lower()

    def test_render_template_user_prompt(self):
        """Test rendering the user prompt template with variables."""
        context = {
            "username": "TestPlayer",
            "day_overall_xp": "100,000",
            "day_top_skills_formatted": "Attack (50,000 XP), Defence (30,000 XP)",
            "day_levels_gained": 1,
            "day_boss_kills_formatted": "Zulrah (10 KC)",
            "day_boss_kills_total": 10,
            "week_overall_xp": "500,000",
            "week_top_skills_formatted": "Attack (200,000 XP), Defence (150,000 XP)",
            "week_levels_gained": 2,
            "week_boss_kills_formatted": "Zulrah (50 KC)",
            "week_boss_kills_total": 50,
        }

        content = render_template("summary/user_prompt.j2", context)

        assert isinstance(content, str)
        assert len(content) > 0
        assert "TestPlayer" in content
        assert "100,000" in content
        assert "500,000" in content
        assert "Attack" in content
        assert "Defence" in content
        assert "Last 24 hours" in content or "24 hours" in content
        assert "Last 7 days" in content or "7 days" in content

    def test_render_template_user_prompt_no_top_skills(self):
        """Test rendering user prompt when no top skills."""
        context = {
            "username": "TestPlayer",
            "day_overall_xp": "0",
            "day_top_skills_formatted": "None",
            "day_levels_gained": 0,
            "day_boss_kills": 0,
            "week_overall_xp": "0",
            "week_top_skills_formatted": "None",
            "week_levels_gained": 0,
            "week_boss_kills": 0,
        }

        content = render_template("summary/user_prompt.j2", context)

        assert "TestPlayer" in content
        assert "None" in content

    def test_render_template_missing_file(self):
        """Test that rendering a missing template raises an error."""
        with pytest.raises(Exception):  # FileNotFoundError or TemplateNotFound
            render_template("nonexistent/template.j2", {})

    def test_render_template_with_missing_variable(self):
        """Test rendering template with missing variable (should work but may show empty)."""
        # Missing some variables - Jinja2 will render empty strings for missing vars
        context = {
            "username": "TestPlayer",
        }

        content = render_template("summary/user_prompt.j2", context)
        assert "TestPlayer" in content
        # Other variables will be empty/undefined but template should still render

    def test_render_template_path_resolution(self):
        """Test that template paths are resolved correctly."""
        # Test that we can load templates from subdirectories
        content = render_template("summary/system_prompt.j2", {})
        assert len(content) > 0

    def test_template_loader_trim_blocks(self):
        """Test that Jinja2 trim_blocks is enabled (removes trailing newlines)."""
        env = get_jinja_env()
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True
