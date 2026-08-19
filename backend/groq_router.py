import time
from datetime import datetime, timedelta
import logging
from groq import Groq, RateLimitError
from config import GROQ_API_KEYS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GroqRouter")

class GroqKeyManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        # Tracks cooldown expiration: { "key": datetime_it_becomes_available }
        self.cooldowns = {key: None for key in api_keys}
        self.current_key_idx = 0
        
        # Initialize clients lazily to save resources
        self.clients = {}

    def _get_client(self, api_key):
        if api_key not in self.clients:
            self.clients[api_key] = Groq(api_key=api_key)
        return self.clients[api_key]

    def _get_available_key(self):
        start_idx = self.current_key_idx
        now = datetime.now()
        
        # Look for the first key that is not on cooldown
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_idx]
            cooldown_expiry = self.cooldowns[key]
            
            if cooldown_expiry is None or now > cooldown_expiry:
                # Key is available! Clear cooldown if it had one.
                self.cooldowns[key] = None
                return key
            
            # Move to next key
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            
        # If we loop through everything and all are on cooldown, we have exhausted all daily limits.
        raise Exception("ALL Groq API keys are currently exhausted/on cooldown!")

    def chat_completion(self, *args, **kwargs):
        """
        Mimics client.chat.completions.create but with automatic failover.
        Will retry across different keys if rate limits are hit.
        """
        keys_tried = 0
        max_retries = len(self.api_keys)
        
        while keys_tried < max_retries:
            try:
                active_key = self._get_available_key()
                client = self._get_client(active_key)
                
                # Execute the API call
                response = client.chat.completions.create(*args, **kwargs)
                return response
                
            except RateLimitError as e:
                logger.warning(f"RateLimitError on key {active_key[:10]}... Putting on 24hr cooldown.")
                # Put the exhausted key on a 24 hour cooldown
                self.cooldowns[active_key] = datetime.now() + timedelta(hours=24)
                
                # Move to the next key immediately for the retry
                self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                keys_tried += 1
                
            except Exception as e:
                # If it's a 400 error about a decommissioned model or something else, 
                # we don't necessarily want to burn the key, but we can't succeed.
                err_msg = str(e).lower()
                if "rate limit" in err_msg or "quota" in err_msg or "429" in err_msg:
                    logger.warning(f"Quota/Limit Error on key {active_key[:10]}... Putting on 24hr cooldown.")
                    self.cooldowns[active_key] = datetime.now() + timedelta(hours=24)
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                    keys_tried += 1
                else:
                    # Bubble up unrelated errors (like 404 Model Not Found)
                    raise e
                    
        raise Exception("Failed to get chat completion. All available keys hit rate limits during retry.")

# Singleton instance for the application to import
groq_router = GroqKeyManager(GROQ_API_KEYS)
