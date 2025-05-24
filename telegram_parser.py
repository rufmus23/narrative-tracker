import os
import json
import argparse
import atexit
import signal
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv
import yaml
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Telegram API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')

class TelegramParser:
    def __init__(self):
        self.session_file = 'telegram_session'
        self.client = None
        self._setup_cleanup_handlers()
        
    def _setup_cleanup_handlers(self):
        """Setup handlers for proper cleanup on exit"""
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print("\nReceived termination signal. Cleaning up...")
        self._cleanup()
        exit(0)
        
    def _cleanup(self):
        """Cleanup resources"""
        if self.client and self.client.is_connected():
            print("\nCleaning up and closing connection...")
            try:
                # Create a new event loop for cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.client.disconnect())
                loop.close()
                print("Connection closed.")
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
        
    async def connect(self):
        """Connect to Telegram"""
        print("Connecting to Telegram...")
        try:
            self.client = TelegramClient(self.session_file, API_ID, API_HASH)
            await self.client.connect()
            
            # Only start if not already authorized
            if not await self.client.is_user_authorized():
                print("First time login - authentication required")
                await self.client.start(phone=PHONE)
                print("Authentication successful!")
            else:
                print("Using existing session")
            
            print("Connected successfully!")
        except Exception as e:
            print(f"Error connecting to Telegram: {str(e)}")
            raise

    def _format_reactions(self, reactions):
        """Format reactions into a JSON-serializable format"""
        if not reactions:
            return None
        try:
            return {
                'count': reactions.count,
                'reactions': [
                    {
                        'emoji': reaction.emoji,
                        'count': reaction.count
                    } for reaction in reactions.results
                ] if hasattr(reactions, 'results') else None
            }
        except Exception:
            return None
        
    async def parse_channel(self, channel_name, start_date, end_date):
        """Parse messages from a channel within date range"""
        if not self.client or not self.client.is_connected():
            raise Exception("Client is not connected")
            
        print(f"\nParsing channel: {channel_name}")
        channel = await self.client.get_entity(channel_name)
        
        # Convert dates to datetime objects if they're strings and make them timezone-aware
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
        messages = []
        offset_id = 0
        total_messages = 0
        total_count_limit = 0  # No limit
        
        # First, get total message count for progress bar
        print("Fetching message history...")
        while True:
            try:
                history = await self.client(GetHistoryRequest(
                    peer=channel,
                    offset_id=offset_id,
                    offset_date=end_date,  # Only fetch messages up to end_date
                    add_offset=0,
                    limit=100,
                    max_id=0,
                    min_id=0,  # We'll filter by date instead of ID
                    hash=0
                ))
                
                if not history.messages:
                    break
                    
                # Filter messages by start_date before adding them
                for message in history.messages:
                    message_date = message.date
                    if message_date.tzinfo is None:
                        message_date = message_date.replace(tzinfo=timezone.utc)
                    
                    if message_date >= start_date:
                        messages.append(message)
                
                offset_id = history.messages[-1].id
                total_messages = len(messages)
                
                # If we've gone past our start_date, we can stop fetching
                if history.messages[-1].date < start_date:
                    break
                
                if total_count_limit != 0 and total_messages >= total_count_limit:
                    break
            except Exception as e:
                print(f"Error fetching messages: {str(e)}")
                break
        
        print(f"Found {total_messages} messages within date range")
        
        # Format messages
        formatted_messages = []
        for message in tqdm(messages, desc="Processing messages"):
            try:
                message_data = {
                    'id': message.id,
                    'date': message.date.isoformat(),
                    'message': message.message,
                    'views': getattr(message, 'views', None),
                    'forwards': getattr(message, 'forwards', None),
                    'reactions': self._format_reactions(getattr(message, 'reactions', None))
                }
                formatted_messages.append(message_data)
            except Exception as e:
                print(f"Error processing message {message.id}: {str(e)}")
                continue
        
        print(f"Successfully processed {len(formatted_messages)} messages")
        return formatted_messages
    
    async def save_to_json(self, channel_name, messages):
        """Save messages to a JSON file"""
        filename = f"data/{channel_name.replace('@', '')}_messages.json"
        print(f"\nSaving messages to {filename}...")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved {len(messages)} messages to {filename}")
        except Exception as e:
            print(f"Error saving to {filename}: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()

def load_config(config_path="config.yaml"):
    """Load configuration from a YAML file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config file: {str(e)}")
        raise

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Parse Telegram channel messages')
    parser.add_argument('--config', default="config.yaml",
                        help='Path to config YAML file (default: config.yaml)')
    parser.add_argument('--channels', nargs='+',
                        help='List of channel names to parse (e.g., @channel1 @channel2)')
    parser.add_argument('--start-date',
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date',
                        help='End date in YYYY-MM-DD format')
    return parser.parse_args()

async def main():
    parser = None
    try:
        args = parse_args()
        config = load_config(args.config)

        # Allow command-line overrides
        channels = args.channels if args.channels else config.get("channels", [])
        start_date = args.start_date if args.start_date else config.get("start_date")
        end_date = args.end_date if args.end_date else config.get("end_date")

        if not channels or not start_date or not end_date:
            print("Channels, start_date, and end_date must be specified in config or as arguments.")
            return

        parser = TelegramParser()
        await parser.connect()

        print(f"\nStarting to parse {len(channels)} channels...")
        for channel in channels:
            try:
                messages = await parser.parse_channel(channel, start_date, end_date)
                await parser.save_to_json(channel, messages)
            except Exception as e:
                print(f"Error parsing channel {channel}: {str(e)}")
                continue

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if parser:
            await parser.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 