# GPV (graisse-prompt-versioning)

CLI utility for prompt versioning where the prompt is assembled from jinja2 sub-prompt template files. Relies on a local SQLite database.

**Sub-prompt file naming:** The prefix of each filename defines the order in which sub-prompts are concatenated to generate the prompt. Use zero-padded numeric prefixes (e.g. `01`, `02`, `03`...) so that files sort correctly in directory listings. For example, `01_intro.j2`, `02_body.j2`, `03_outro.j2` will be assembled in that order. The segment after the first underscore determines the sub-prompt type (e.g. `01_intro_section.j2` has type `intro_section`).

**Working directory:** The current working directory (CWD) matters when invoking gpv. You must run gpv from the directory containing `.gpv`. When `gpv commit` is invoked with explicit paths (including absolute paths), the `.gpv` file in the CWD is used—not the `.gpv` in the target file's directory.

## Installation

```bash
pip install -e .
```

## Setup

1. Create a `.gpv` file in your project directory containing the absolute path to your SQLite database.
2. Run `gpv init` to create the database and schema.

### Example

The `example/` directory contains sample `.j2` files and a `.gpv.example` template. To try GPV:

```bash
cd example
cp .gpv.example .gpv
# Edit .gpv and set the path to your database (e.g. /absolute/path/to/example/gpv.db)
gpv init
gpv commit -m "Initial commit"
gpv info
gpv prompt
```

## Commands

- `gpv init` - Create database and schema
- `gpv commit -m "message"` - Commit all .j2 files in CWD
- `gpv commit -m "message" path1.j2 path2.j2` - Commit specified files
- `gpv commit -branch parent_pk path.j2 -m "message"` - Commit with branch versioning
- `gpv uncommit` - Revert to previous master
- `gpv info` - Print current master prompt details
- `gpv prompt` - Print concatenated sub-prompts
- `gpv prompt -key pk` - Print sub-prompts for specified master
- `gpv extract` - Create .j2 files from current master
