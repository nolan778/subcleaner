import logging
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

import libs
from libs.subcleaner import languages

logger = logging.getLogger(__name__)


class TextCleaningConfig:
    """Configuration for text cleaning operations."""
    
    def __init__(self, cfg: ConfigParser):
        """Initialize text cleaning configuration from ConfigParser."""
        # Get TEXT_CLEANING section or use defaults
        if 'TEXT_CLEANING' not in cfg:
            # Create default section
            cfg.add_section('TEXT_CLEANING')
        
        section = cfg['TEXT_CLEANING']
        
        # General cleaning options
        self.remove_sdh = section.getboolean('remove_sdh', False)
        self.remove_speaker_labels = section.getboolean('remove_speaker_labels', False)
        self.remove_music_notes = section.getboolean('remove_music_notes', False)
        self.remove_line_breaks = section.getboolean('remove_line_breaks', False)
        self.merge_identical_cues = section.getboolean('merge_identical_cues', False)
        self.convert_uppercase_to_lowercase = section.getboolean('convert_uppercase_to_lowercase', False)
        self.remove_dialog_markers = section.getboolean('remove_dialog_markers', False)
        
        # Text formatting options
        self.remove_formatting_tags = section.getboolean('remove_formatting_tags', False)
        self.preserve_italic_tags = section.getboolean('preserve_italic_tags', True)
        self.preserve_bold_tags = section.getboolean('preserve_bold_tags', True)
        self.preserve_font_tags = section.getboolean('preserve_font_tags', True)
        
        # Text between delimiters
        self.remove_text_in_curly_braces = section.getboolean('remove_text_in_curly_braces', False)
        self.remove_text_in_parentheses = section.getboolean('remove_text_in_parentheses', False)
        self.remove_text_in_square_brackets = section.getboolean('remove_text_in_square_brackets', False)
        self.remove_text_in_asterisks = section.getboolean('remove_text_in_asterisks', False)
        self.remove_text_in_hashtags = section.getboolean('remove_text_in_hashtags', False)
        
        # Custom character filtering
        custom_chars_str = section.get('custom_chars_to_remove', '[]')
        # Parse custom characters/patterns from JSON array format
        # Examples:
        #   [] removes nothing (feature disabled)
        #   ["j\""] removes lines containing j" anywhere in the line
        import json
        try:
            self.custom_chars_to_remove = json.loads(custom_chars_str)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Invalid JSON format for custom_chars_to_remove: {custom_chars_str}. Using empty list.")
            self.custom_chars_to_remove = []

home_dir = Path(libs.__file__).parent.parent
try:
    home_dir = home_dir.relative_to(Path.cwd())
except ValueError:
    pass
regex_dir = home_dir.joinpath("regex_profiles")

# for migrating old installations:
if home_dir.joinpath("regex").exists():
    for path in home_dir.joinpath("regex").iterdir():
        new_file = regex_dir.joinpath(path.name)
        if not new_file.exists():
            path.rename(new_file)
        path.unlink()
    home_dir.joinpath("regex").rmdir()

default_regex_dir = regex_dir.joinpath("default")
script_file = home_dir.joinpath('subcleaner.py')

log_file: Path
use_default_regex: bool
fix_overlaps: bool
relative_base: Path
default_language: Optional[str]
config_file = home_dir.joinpath("subcleaner.conf")

if not config_file.is_file():
    config_file.write_text(home_dir.joinpath("default_config", "subcleaner.conf").read_text())

cfg = ConfigParser()
cfg.read(str(config_file), encoding="UTF-8")

use_default_regex = cfg['SETTINGS'].getboolean("use_defaults", True)

sections = cfg.sections()

log_dir = Path(cfg["SETTINGS"].get("log_dir", "logs/"))
if not log_dir.is_absolute():
    log_dir = home_dir.joinpath(log_dir)
if not log_dir.exists():
    log_dir.mkdir()
if not log_dir.is_dir():
    raise ValueError(f"log directory: {log_dir} is not a directory")
log_file = log_dir.joinpath("subcleaner.log")

relative_base = Path(cfg['SETTINGS'].get("relative_path_base", "."))
if not relative_base.is_absolute():
    relative_base = Path.cwd().joinpath(relative_base)
relative_base = relative_base.resolve()

fix_overlaps = cfg['SETTINGS'].getboolean("fix_overlaps", True)

default_language = cfg['SETTINGS'].get("default_language", "")
if default_language in ["blank", "Blank", "", "empty", "Empty"]:
    default_language = None
if default_language:
    if not languages.is_language(default_language):
        logger.error("Config error: default language code must be a valid ISO:639 language. Exiting")
        exit(1)

use_english_on_all = cfg['SETTINGS'].getboolean("use_english_on_all", False)
require_language_profile = cfg['SETTINGS'].getboolean("require_language_profile", True)
# Initialize text cleaning configuration
text_cleaning = TextCleaningConfig(cfg)