import difflib
import re
import logging
from typing import List, Dict
from libs.subcleaner.subtitle import Subtitle
from libs.subcleaner.settings import config

logger = logging.getLogger(__name__)

# Global statistics for text cleaning
text_cleaning_stats: Dict[str, int] = {}


def reset_stats() -> None:
    """Reset text cleaning statistics."""
    global text_cleaning_stats
    text_cleaning_stats = {
        'music_notes_removed': 0,
        'sdh_cleaned': 0,
        'speaker_labels_removed': 0,
        'line_breaks_removed': 0,
        'dialog_markers_removed': 0,
        'formatting_tags_removed': 0,
        'curly_braces_cleaned': 0,
        'parentheses_cleaned': 0,
        'square_brackets_cleaned': 0,
        'asterisks_cleaned': 0,
        'hashtags_cleaned': 0,
        'uppercase_converted': 0,
        'cues_merged': 0,
        'custom_chars_removed': 0,
    }


def get_stats() -> Dict[str, int]:
    """Get current text cleaning statistics."""
    return text_cleaning_stats.copy()


def clean_text(subtitle: Subtitle) -> None:
    """Apply all configured text cleaning operations to subtitle blocks."""
    if not subtitle.blocks:
        return
    
    for block in subtitle.blocks:
        # Check for custom characters that indicate lines to remove
        if config.text_cleaning.custom_chars_to_remove and _contains_custom_chars(block.content):
            # Mark block for deletion if it contains custom characters
            subtitle.ad(block)
            block.hints.append("contains_custom_char")
            text_cleaning_stats['custom_chars_removed'] += 1
            continue
        
        if config.text_cleaning.remove_music_notes and _contains_music_note(block.content):
            # Mark block for deletion if it contains music notes
            subtitle.ad(block)
            block.hints.append("contains_music_note")
            text_cleaning_stats['music_notes_removed'] += 1
            continue
        
        original_content = block.content
        
        # Apply text cleaning operations in carefully ordered sequence
        # IMPORTANT: Remove formatting tags FIRST (before SDH, speaker labels, etc.)
        # This ensures that patterns like <font>[SPEAKER]</font> can be properly matched and removed.
        # If we skip tag removal first, the patterns inside tags won't be recognized.
        if config.text_cleaning.remove_formatting_tags:
            cleaned = _remove_formatting_tags(block.content)
            if cleaned != block.content:
                text_cleaning_stats['formatting_tags_removed'] += 1
            block.content = cleaned
        
        # Now that tags are removed, pattern-matching operations work correctly
        if config.text_cleaning.remove_sdh:
            cleaned = _remove_sdh(block.content)
            if cleaned != block.content:
                text_cleaning_stats['sdh_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_speaker_labels:
            cleaned = _remove_speaker_labels(block.content)
            if cleaned != block.content:
                text_cleaning_stats['speaker_labels_removed'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_dialog_markers:
            cleaned = _remove_dialog_markers(block.content)
            if cleaned != block.content:
                text_cleaning_stats['dialog_markers_removed'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_line_breaks:
            if '\n' in block.content:
                text_cleaning_stats['line_breaks_removed'] += 1
            block.content = _remove_line_breaks(block.content)
        
        if config.text_cleaning.remove_text_in_curly_braces:
            cleaned = _remove_text_between_delimiters(block.content, '{', '}')
            if cleaned != block.content:
                text_cleaning_stats['curly_braces_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_text_in_parentheses:
            cleaned = _remove_text_between_delimiters(block.content, '(', ')')
            if cleaned != block.content:
                text_cleaning_stats['parentheses_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_text_in_square_brackets:
            cleaned = _remove_text_between_delimiters(block.content, '[', ']')
            if cleaned != block.content:
                text_cleaning_stats['square_brackets_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_text_in_asterisks:
            cleaned = _remove_text_between_delimiters(block.content, '*', '*')
            if cleaned != block.content:
                text_cleaning_stats['asterisks_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.remove_text_in_hashtags:
            cleaned = _remove_text_between_delimiters(block.content, '#', '#')
            if cleaned != block.content:
                text_cleaning_stats['hashtags_cleaned'] += 1
            block.content = cleaned
        
        if config.text_cleaning.convert_uppercase_to_lowercase:
            cleaned = _convert_uppercase_to_lowercase(block.content)
            if cleaned != block.content:
                text_cleaning_stats['uppercase_converted'] += 1
            block.content = cleaned
        
        # Clean up extra whitespace
        block.content = block.content.strip()
        
        # Update clean_content for matching algorithms
        if block.content != original_content:
            diff = _build_unified_diff(original_content, block.content)
            if diff:
                subtitle.add_text_cleaning_diff(block, diff)
            block.clean_content = re.sub("[\\s.,:_-]", "", block.content)


def merge_identical_consecutive_cues(subtitle: Subtitle) -> None:
    """Merge consecutive cues with identical content."""
    if not subtitle.blocks or len(subtitle.blocks) < 2:
        return
    
    blocks_to_remove = []
    i = 0
    while i < len(subtitle.blocks) - 1:
        current_block = subtitle.blocks[i]
        next_block = subtitle.blocks[i + 1]
        
        # Check if content is identical
        if current_block.content == next_block.content:
            # Merge: extend current block's end time to next block's end time
            current_block.end_time = next_block.end_time
            blocks_to_remove.append(next_block)
            # Don't increment i, check if next block is also identical to current
        else:
            i += 1
    
    # Remove merged blocks
    for block in blocks_to_remove:
        subtitle.blocks.remove(block)
    
    # Track number of cues merged
    if blocks_to_remove:
        text_cleaning_stats['cues_merged'] += len(blocks_to_remove)
    
    # Reindex blocks
    subtitle.reindex()


def _contains_music_note(text: str) -> bool:
    """Check if text contains music note character (♪)."""
    return '♪' in text


def _contains_custom_chars(text: str) -> bool:
    """Check if text contains any of the configured custom characters/patterns to remove.
    
    Supports both individual characters and multi-character patterns.
    If a pattern is more than one character, it's matched as an exact substring.
    """
    if not config.text_cleaning.custom_chars_to_remove:
        return False
    for char_or_pattern in config.text_cleaning.custom_chars_to_remove:
        if char_or_pattern in text:
            return True
    return False


def _remove_sdh(text: str) -> str:
    """Remove SDH (Subtitles for the Deaf and Hard of hearing) patterns.
    
    Common patterns:
    - [SPEAKER]: Speaker name in square brackets
    - (SPEAKER): Speaker name in parentheses
    - *SPEAKER*: Speaker name in asterisks
    - SPEAKER:: Double colon at end
    """
    # Remove patterns like [SPEAKER] or [SPEAKER:] at the start of line
    text = re.sub(r'^\s*\[[^\]]*\]', '', text, flags=re.MULTILINE)
    
    # Remove patterns like (SPEAKER) or (SPEAKER:) at the start of line
    text = re.sub(r'^\s*\([^\)]*\)', '', text, flags=re.MULTILINE)
    
    # Remove patterns like *SPEAKER* or *SPEAKER:* at the start of line
    text = re.sub(r'^\s*\*[^\*]+\*', '', text, flags=re.MULTILINE)
    
    # Remove common SDH abbreviations and sounds in parentheses at the start of a line
    # Pattern like (doorbell ringing), (music playing), etc.
    text = re.sub(r'^\s*\([^)]*(?:ringing|playing|sounds?|music|knocking|door|phone|alarm|beeping|buzzing|creaking|footsteps?|silence|pounding)\s*[^)]*\)', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    return text.strip()


def _remove_speaker_labels(text: str) -> str:
    """Remove speaker labels at the beginning of lines.
    
    Matches patterns like:
    - JOHN: Hello
    - MARY: How are you
    - BOB: (multiple lines)
    
    Only removes if the speaker name is in uppercase followed by a colon.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Pattern: start of line, optional whitespace, uppercase word(s), colon
        match = re.match(r'^\s*([A-Z][A-Z\s]*?):\s*', line)
        if match:
            # Only remove if the speaker name is one or more uppercase words
            speaker = match.group(1).strip()
            # Check if it's actually a speaker label (uppercase, usually short)
            if speaker.isupper() and len(speaker.split()) <= 3:
                # Remove the speaker label
                remaining = line[match.end():]
                cleaned_lines.append(remaining)
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def _remove_line_breaks(text: str) -> str:
    """Remove all line breaks within a cue, joining lines with a space."""
    # Replace newlines with space
    text = text.replace('\n', ' ')
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _remove_formatting_tags(text: str) -> str:
    """Remove HTML-style formatting tags from text.
    
    Preserves:
    - <i></i> italic tags (if preserve_italic_tags is True)
    - <b></b> bold tags (if preserve_bold_tags is True)
    - <font></font> and similar (if preserve_font_tags is True)
    
    Removes all other tags.
    """
    preserved_tags = []
    
    if config.text_cleaning.preserve_italic_tags:
        preserved_tags.append('i')
    
    if config.text_cleaning.preserve_bold_tags:
        preserved_tags.append('b')
    
    if config.text_cleaning.preserve_font_tags:
        preserved_tags.extend(['font', 'span', 'color'])
    
    # Build regex pattern for tags to preserve
    preserve_pattern = '|'.join(re.escape(tag) for tag in preserved_tags)
    
    if preserve_pattern:
        # Remove all tags except the preserved ones
        # This pattern removes < > with content, except for preserved tags
        text = re.sub(f'<(?!/?({preserve_pattern})\\b)[^>]*>', '', text, flags=re.IGNORECASE)
    else:
        # Remove all tags
        text = re.sub(r'<[^>]*>', '', text)
    
    return text


def _remove_text_between_delimiters(text: str, open_delim: str, close_delim: str) -> str:
    """Remove all text between two delimiters (including delimiters).
    
    Args:
        text: The text to clean
        open_delim: Opening delimiter
        close_delim: Closing delimiter
    
    Examples:
        _remove_text_between_delimiters("Hello {world}", '{', '}') -> "Hello "
        _remove_text_between_delimiters("Hello (world)", '(', ')') -> "Hello "
    """
    # Escape delimiters for regex
    escaped_open = re.escape(open_delim)
    escaped_close = re.escape(close_delim)
    
    # For matching delimiters, use a lazy match
    pattern = f'{escaped_open}.*?{escaped_close}'
    text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # Clean up extra whitespace but preserve line breaks
    lines = text.split('\n')
    cleaned_lines = [re.sub(r' +', ' ', line).strip() for line in lines]
    # Remove empty lines created by the removal
    cleaned_lines = [line for line in cleaned_lines if line]
    return '\n'.join(cleaned_lines)


def _remove_dialog_markers(text: str) -> str:
    """Remove leading hyphens used as dialog markers.
    
    Removes "-", "–" (en-dash), or "—" (em-dash) only at the start of a line (per-line basis).
    Preserves dashes within sentences and other content.
    
    Example:
        "- Hello\n- World" -> "Hello\nWorld"
        "— Hello\n— World" -> "Hello\nWorld"
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Match leading hyphen/dash (-, –, or —) with optional whitespace
        # \p{Dash} would work with regex library but re module doesn't support it
        # So we explicitly include: hyphen-minus (-), en-dash (–), em-dash (—)
        match = re.match(r'^\s*[-–—]\s*', line)
        if match:
            # Remove the leading dash and the space after it
            cleaned_line = line[match.end():]
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def _convert_uppercase_to_lowercase(text: str) -> str:
    """Convert fully uppercase text to lowercase (sentence case).
    
    Only converts if most of the text is uppercase.
    This prevents converting intentional all-caps words.
    """
    # Count uppercase letters
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 2:
        return text
    
    uppercase_count = sum(1 for c in letters if c.isupper())
    uppercase_ratio = uppercase_count / len(letters)
    
    # Convert to lowercase if at least 70% is uppercase
    if uppercase_ratio >= 0.7:
        # Convert first character to uppercase, rest to lowercase
        text_lower = text.lower()
        if text_lower:
            text_lower = text_lower[0].upper() + text_lower[1:]
        return text_lower
    
    return text


def _build_unified_diff(before: str, after: str) -> str:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    diff_lines = list(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="before",
        tofile="after",
        lineterm="",
        n=0,
    ))
    if not diff_lines:
        return ""
    if len(diff_lines) >= 2 and diff_lines[0].startswith("---") and diff_lines[1].startswith("+++"):
        diff_lines = diff_lines[2:]
    return "\n".join(diff_lines)
