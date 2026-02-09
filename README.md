# Subcleaner
Subcleaner is a python3 script for cleaning and removing ads from .srt subtitle files.
The script is more sophisticated than a simple search and delete per line and includes:

**Ad Removal Features:**
- Uses different regex profiles for different languages
- Once ad-blocks are identified, they get removed and remaining blocks are re-indexed
- Can fix overlapping subtitles

**Advanced Text Cleaning Features:**
- Remove subtitles for the deaf and hard of hearing (SDH) patterns (speaker labels, sound descriptions, and effects at line start)
- Remove speaker labels explicitly (e.g., "JOHN:", "MARY:")
- Remove music note characters (♪)
- Remove line breaks within cues
- Merge consecutive identical cues
- Convert fully uppercase text to sentence case
- Remove dialog markers (leading hyphens)
- Remove or preserve specific formatting tags (italic, bold, font)
- Remove text between delimiters (curly braces, parentheses, square brackets, asterisks, hashtags) - anywhere in text
- Custom character/pattern removal

Can clean entire libraries in recursive mode and works well with [Bazarr](https://github.com/morpheus65535/bazarr) 
directly installed or as a container from the [linuxserver/bazarr](https://hub.docker.com/r/linuxserver/bazarr) image.

# Installing
Cloning and running with python3 should work.

```cd /opt```

```git clone https://github.com/KBlixt/subcleaner.git```

```cd subcleaner```

Install the default config simply by running the script once or copy the default config into
the script root directory.

```python3 ./subcleaner.py -h```

With the subcleaner.conf file installed you can modify the settings within it.
the config file contains instructions what each of the settings does.

## Configuration

### Text Cleaning Options
The script includes advanced text cleaning features that can be configured in the `subcleaner.conf` file under the `[TEXT_CLEANING]` section. All text cleaning options are disabled by default to preserve existing behavior.

**Available text cleaning options:**

**SDH and Speaker/Content Patterns:**
- `remove_sdh` - Remove SDH (Subtitles for Deaf/Hard-of-hearing) patterns: speaker labels like `[JOHN]`, `(SPEAKER)`, and sound descriptions like `(doorbell ringing)` **at the start of lines**. This targets common SDH formatting patterns.
- `remove_speaker_labels` - Remove explicit speaker name labels like "JOHN:" or "MARY:" at the beginning of lines (uppercase names followed by colons). More specific than generic bracket removal.
- `remove_music_notes` - Remove cues containing music note characters (♪) and mark them for deletion

**Text Formatting and Content:
- `remove_formatting_tags` - Remove HTML-style tags like `<i>`, `<b>`, `<font>`, `<span>` (with options to preserve specific tags)
- `remove_line_breaks` - Join multi-line cues into single lines
- `remove_dialog_markers` - Remove leading hyphens and dashes (`-`, `–`, `—`) used as dialog markers at line starts
- `convert_uppercase_to_lowercase` - Convert all-caps text to sentence case
- `merge_identical_cues` - Combine consecutive identical subtitle cues

**General Delimiter Removal (removes anywhere in text, not just line starts):**
- `remove_text_in_square_brackets` - Remove ALL text between `[ ]` anywhere (duplicate with SDH if you only want line-start removal)
- `remove_text_in_parentheses` - Remove ALL text between `( )` anywhere (duplicate with SDH if you only want line-start removal)
- `remove_text_in_curly_braces` - Remove text between `{ }` anywhere
- `remove_text_in_asterisks` - Remove text between `* *` anywhere
- `remove_text_in_hashtags` - Remove text between `# #` anywhere

**Other:**
- `custom_chars_to_remove` - Remove lines containing specific characters or patterns (JSON array format)

**Note on SDH vs Bracket Removal:** If you enable `remove_sdh`, you may not need `remove_text_in_square_brackets` and `remove_text_in_parentheses` since SDH already handles common `[SPEAKER]` and `(SPEAKER)` patterns at line starts. The bracket removal options are more aggressive and remove brackets anywhere in the text.

## Bazarr
Unlock the scripts full potential by running it after downloading a subtitle from 
[Bazarr](https://github.com/morpheus65535/bazarr). Enable custom post-processing and use
the command:

```python3 /opt/subcleaner/subcleaner.py "{{subtitles}}" -s``` (note the quotation)

It should work 
right out the gate provided the paths and permissions are set up correctly.

in the bazarr log it should confirm that the script ran successfully or give you 
an error message that tells you what's wrong. if nothing is output then you've probably 
set the script path wrong.

## Docker

If you run Bazarr in a docker container, as you should,
make sure the Bazarr container have access to the script directory. Either
mount /opt/subcleaner directly into the container as a volume or install the script inside 
the Bazarr config directory.

I have verified that this works on the [linuxserver/bazarr](https://hub.docker.com/r/linuxserver/bazarr) image.

# Languages:
The script have a few language profiles included by default:

- English
- Spanish
- Portuguese
- Dutch
- Indonesian
- Swedish

If you want to run the script against any other language you'll have to either create a profile for it
or disable the requirement in the subcleaner.conf file. It's recommended to create
a language profile. read the README in the regex_profiles directory for more info and guidance.

### If you make a useful regex profile for a non-default language, PLEASE let me know! 
I'll review it and add it to the included default profiles. And it'll help out others that use 
that language in the future! :)

__________________


# Thank you :)
Please, If you find any issues or have any questions feel free to 
open an issue or discussion.

__________________
###### Future (possibly):

* Automatic subtitle deletion if language don't match label.

* better ui for confirming/reverting deletion of ads.

* ASS support?

