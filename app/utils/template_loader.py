"""Template loading and rendering utilities."""

import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Get the project root directory (parent of app/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Initialize Jinja2 environment
_jinja_env: Environment | None = None


def get_jinja_env() -> Environment:
    """
    Get or create the Jinja2 environment.

    Returns:
        Environment: Configured Jinja2 environment
    """
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info(
            f"Initialized Jinja2 environment with templates dir: {TEMPLATES_DIR}"
        )
    return _jinja_env


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        template_path: Path to template file relative to templates directory
        context: Dictionary of variables to pass to template

    Returns:
        str: Rendered template content

    Raises:
        FileNotFoundError: If template file doesn't exist
        Exception: If template rendering fails
    """
    env = get_jinja_env()
    try:
        template = env.get_template(template_path)
        return template.render(**context)
    except Exception as e:
        logger.error(
            f"Error rendering template {template_path}: {e}", exc_info=True
        )
        raise
