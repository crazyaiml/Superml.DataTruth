"""
Prompt Management

Loads and formats prompts from markdown files.
"""

from pathlib import Path
from typing import Dict, Optional

from src.config import settings


class PromptManager:
    """Manages loading and formatting of prompt templates."""

    def __init__(self, prompts_dir: Path | str = "prompts") -> None:
        """
        Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, name: str) -> str:
        """
        Load a prompt from file.

        Args:
            name: Prompt name (without .md extension)

        Returns:
            Prompt content

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if name in self._cache:
            return self._cache[name]

        prompt_file = self.prompts_dir / f"{name}.prompt.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, "r") as f:
            content = f.read()

        self._cache[name] = content
        return content

    def format_prompt(self, template: str, **kwargs: str) -> str:
        """
        Format a prompt template with variables.

        Args:
            template: Prompt template string
            **kwargs: Variables to format into prompt

        Returns:
            Formatted prompt
        """
        return template.format(**kwargs)

    def load_and_format(self, prompt_name: str, **kwargs: str) -> str:
        """
        Load and format a prompt with variables.

        Args:
            prompt_name: Prompt name
            **kwargs: Variables to format into prompt

        Returns:
            Formatted prompt
        """
        template = self.load_prompt(prompt_name)
        return self.format_prompt(template, **kwargs)

    def get_available_prompts(self) -> list[str]:
        """
        Get list of available prompt names.

        Returns:
            List of prompt names (without .prompt.md extension)
        """
        prompts = []
        for file in self.prompts_dir.glob("*.prompt.md"):
            prompts.append(file.stem.replace(".prompt", ""))
        return sorted(prompts)

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()


# Global prompt manager
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """
    Get global prompt manager instance.

    Returns:
        PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def load_prompt(name: str) -> str:
    """
    Load a prompt by name.

    Args:
        name: Prompt name

    Returns:
        Prompt content
    """
    return get_prompt_manager().load_prompt(name)


def format_prompt(name: str, **kwargs: str) -> str:
    """
    Load and format a prompt.

    Args:
        name: Prompt name
        **kwargs: Format variables

    Returns:
        Formatted prompt
    """
    return get_prompt_manager().load_and_format(name, **kwargs)
