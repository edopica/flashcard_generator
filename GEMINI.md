# Project: Flashcard Generator

A Python-based utility for automatically generating Anki flashcards from PDF documents using the Gemini API.

## Project Overview

The **Flashcard Generator** automates the workflow of extracting examinable facts from educational materials (PDFs, slides) and converting them into high-quality, MathJax-formatted Anki cards.

### Core Technologies
- **Python 3.13+**: Primary programming language.
- **Google GenAI SDK**: Interfaces with Gemini models for content extraction and structuring.
- **genanki**: Generates `.apkg` files for Anki.
- **AnkiConnect**: Optional integration for direct upload to a running Anki instance.
- **uv**: Dependency management and project isolation.

### Architecture
- `main.py`: The central entry point that coordinates file processing and deck uploading.
- `src/flash_gen.py`: Logic for communicating with Gemini, handling PDF bytes, and parsing structured JSON responses.
- `src/anki_uploader.py`: Logic for creating `genanki` models/decks and performing HTTP requests to AnkiConnect. Uses deterministic SHA-256 hashing for model/deck IDs to prevent database pollution.
- `src/utils.py`: Helper functions for configuration loading and tracking processed files to avoid duplicates. Includes fallback default configurations for global execution.
- `src/math_prompt.md`: The system prompt defining the AI's behavior, formatting rules (MathJax), and data schema. Bundled with the module.

## Building and Running

### Prerequisites
1.  **Python 3.13** and **uv** must be installed.
2.  Set the `GEMINI_API_KEY` environment variable.
3.  (Optional) Have Anki open with the [AnkiConnect](https://ankiweb.net/shared/info/2055079234) plugin installed for automatic uploads.

### Installation
To install the script as a global command line tool:
```bash
uv tool install --editable .
```

### Common Commands
- **Run the full pipeline from any directory:**
  ```bash
  fgen
  ```
- **Skip PDF generation and only upload an existing JSON:**
  ```bash
  fgen --flashcards cards.json
  ```
- **Reprocess all files in the current directory (ignore cache):**
  ```bash
  fgen --no-skip
  ```

## Development Conventions

### Data Modeling
- The project uses **Pydantic** (`src/flash_gen.py`) to define the structure of flashcards (`Flashcard`, `FlashcardDeck`). This ensures strict JSON schema validation when interacting with Gemini.
- Flashcards follow a specific schema: `front`, `back`, `extra`, and `tags`.

### Source of Truth
- **Prompts**: `src/math_prompt.md` is the "brain" of the generator. Changes to card style, MathJax usage, or extraction logic should be made there.
- **Configuration**: The tool runs with built-in sensible defaults. To override configuration (e.g. models, URLs), place a `.fgen.json` or `variables.json` in the directory where you are running the `fgen` command.

### File Tracking
- Processed PDFs are tracked in a `processed_files.json` created in the current working directory to prevent redundant API calls.

### Logging
- Uses standard Python `logging`. Output is directed to the console, providing visibility into API responses and upload status.

## Directory Structure
- `src/`: Core logic modules and packaged system prompts.
- `files/`: (Legacy/Test) Input PDFs, generated JSON, and output `.apkg` decks.
- `reviews/`: Documentation of major updates and bugfixes.
