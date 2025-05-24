# Telegram Channel Parser

A simple Python script to parse messages from Telegram channels and save them to JSON files.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Get your Telegram API credentials:
   - Go to https://my.telegram.org/auth
   - Log in with your phone number
   - Go to 'API development tools'
   - Create a new application
   - Copy the `api_id` and `api_hash`

3. Configure your credentials:
   - Copy the `.env` file and fill in your credentials:
     - `API_ID`: Your Telegram API ID
     - `API_HASH`: Your Telegram API hash
     - `PHONE`: Your phone number in international format (e.g., +1234567890)

4. Configure your channels and date range in `config.yaml`:

```yaml
channels:
  - "@channel1"
  - "@channel2"
start_date: "2024-01-01"
end_date: "2024-03-20"
```

## Usage

By default, the script reads configuration from `config.yaml`:

```bash
python telegram_parser.py
```

You can override any config value from the command line:

```bash
python telegram_parser.py --channels @news @tech --start-date 2024-02-01 --end-date 2024-03-01
```

Or use a different config file:

```bash
python telegram_parser.py --config my_config.yaml
```

### Arguments
- `--config`: Path to a YAML config file (default: `config.yaml`)
- `--channels`: Space-separated list of channel names to parse (e.g., @channel1 @channel2)
- `--start-date`: Start date in YYYY-MM-DD format
- `--end-date`: End date in YYYY-MM-DD format

## Output Format

The script creates a JSON file for each channel with the following structure:
```json
[
  {
    "id": 123456,
    "date": "2024-01-01T12:00:00",
    "message": "Message content",
    "views": 1000,
    "forwards": 50,
    "reactions": null
  },
  ...
]
```

## Notes

- The first time you run the script, you'll need to authenticate with Telegram
- Make sure you have access to the channels you're trying to parse
- The script respects Telegram's rate limits
- Messages are saved with UTF-8 encoding to properly handle non-Latin characters 