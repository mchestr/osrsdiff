# Templates Directory

This directory contains Jinja2 templates used for generating prompts and other text content.

## Structure

- `summary/` - Templates for player summary generation
  - `system_prompt.j2` - System prompt for OpenAI API (no variables)
  - `user_prompt.j2` - User prompt template with player progress data

## Template Variables

### `summary/system_prompt.j2`

No variables required. This template defines the system role and instructions for the AI model.

### `summary/user_prompt.j2`

The user prompt template accepts the following variables:

**Player Information:**
- `username` - Player username (string)

**Last 24 Hours Data:**
- `day_overall_xp` - Overall XP gained (formatted string with commas, e.g., "100,000")
- `day_top_skills_formatted` - Top skills by XP (formatted string, e.g., "Attack (50,000 XP), Defence (30,000 XP)")
- `day_levels_gained` - Total levels gained (integer)
- `day_boss_kills_formatted` - Boss kills with names (formatted string, e.g., "Zulrah (10 KC), Vorkath (5 KC)")
- `day_boss_kills_total` - Total boss kills (integer, used internally but not displayed in template)

**Last 7 Days Data:**
- `week_overall_xp` - Overall XP gained (formatted string with commas, e.g., "500,000")
- `week_top_skills_formatted` - Top skills by XP (formatted string, e.g., "Attack (200,000 XP), Defence (150,000 XP)")
- `week_levels_gained` - Total levels gained (integer)
- `week_boss_kills_formatted` - Boss kills with names (formatted string, e.g., "Zulrah (100 KC), Vorkath (50 KC)")
- `week_boss_kills_total` - Total boss kills (integer, used internally but not displayed in template)

**Output Format:**
The template instructs the AI to return JSON in the format:
```json
{
  "summary": "Concise 1-2 sentence overview",
  "points": ["Point 1 with specific numbers", "Point 2 with specific numbers", "Point 3 with specific numbers"]
}
```

## Usage

Templates are loaded using the `app.utils.template_loader` module:

```python
from app.utils.template_loader import render_template

# System prompt (no variables)
system_prompt = render_template("summary/system_prompt.j2", {})

# User prompt (with player data)
user_prompt = render_template("summary/user_prompt.j2", {
    "username": "PlayerName",
    "day_overall_xp": "100,000",
    "day_top_skills_formatted": "Attack (50,000 XP), Defence (30,000 XP)",
    "day_levels_gained": 1,
    "day_boss_kills_formatted": "Zulrah (10 KC), Vorkath (5 KC)",
    "week_overall_xp": "500,000",
    "week_top_skills_formatted": "Attack (200,000 XP), Defence (150,000 XP)",
    "week_levels_gained": 2,
    "week_boss_kills_formatted": "Zulrah (100 KC), Vorkath (50 KC)",
})
```

## Template Guidelines

The prompts are designed to generate data-driven summaries:

- **System Prompt**: Defines the AI's role as a data analyst focused on factual, number-driven summaries
- **User Prompt**: Provides structured data and clear instructions to avoid vague qualifiers

**Key Writing Rules:**
- Lead with numbers and metrics
- Avoid weasel words: "significant", "impressive", "notable", etc.
- Use exact values: "1.27M XP" not "over a million XP"
- Include specific boss names and kill counts
- Compare day vs week activity when relevant

## Editing Templates

Templates use Jinja2 syntax. Common features:

- Variables: `{{ variable_name }}`
- Conditionals: `{% if condition %}...{% endif %}`
- Loops: `{% for item in items %}...{% endfor %}`

See [Jinja2 documentation](https://jinja.palletsprojects.com/) for more details.
