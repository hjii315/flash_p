# flash_proto

## Requirements
- Python 3.10+
- `OPENAI_API_KEY` environment variable

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python -m flash_proto
```

You will be prompted for:
- Input/Output
- Success criteria
- Constraints

Outputs are saved to:
- SQLite: `flash_proto.sqlite3`
- Files: `runs/<session_id>/...`
