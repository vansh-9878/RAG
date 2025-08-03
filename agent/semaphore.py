from threading import Semaphore, Lock
import itertools
from typing import List, Tuple
import os
from dotenv import load_dotenv
load_dotenv()

class APIKeyLoadBalancer:
    def __init__(self, api_keys: List[str], concurrency_limit_per_key: int = 25):
        """
        Initialize load balancer with multiple API keys
        
        Args:
            api_keys: List of API keys to distribute requests across
            concurrency_limit_per_key: Maximum concurrent requests per API key
        """
        self.api_keys = api_keys
        self.concurrency_limit_per_key = concurrency_limit_per_key
        
        # Create a semaphore for each API key
        self.semaphores = {
            api_key: Semaphore(concurrency_limit_per_key) 
            for api_key in api_keys
        }
        
        # Round-robin iterator for load balancing
        self.key_iterator = itertools.cycle(api_keys)
        self.iterator_lock = Lock()
    
    def get_next_api_key(self) -> str:
        """Get the next API key in round-robin fashion"""
        with self.iterator_lock:
            return next(self.key_iterator)
    
    def acquire_semaphore(self, api_key: str) -> bool:
        """
        Acquire semaphore for specific API key
        
        Args:
            api_key: The API key to acquire semaphore for
            
        Returns:
            True if acquired successfully, False otherwise
        """
        return self.semaphores[api_key].acquire(blocking=False)
    
    def acquire_any_available(self) -> Tuple[str, bool]:
        """
        Try to acquire semaphore for any available API key
        Starting with the next one in round-robin order
        
        Returns:
            Tuple of (api_key, success) where success indicates if acquisition was successful
        """
        starting_key = self.get_next_api_key()
        
        # Try the round-robin selected key first
        if self.acquire_semaphore(starting_key):
            return starting_key, True
        
        # If that fails, try all other keys
        for api_key in self.api_keys:
            if api_key != starting_key and self.acquire_semaphore(api_key):
                return api_key, True
        
        # If no semaphore is available, wait for the round-robin selected key
        self.semaphores[starting_key].acquire()
        return starting_key, True
    
    def release_semaphore(self, api_key: str):
        """Release semaphore for specific API key"""
        self.semaphores[api_key].release()
    
    def get_available_slots(self, api_key: str) -> int:
        """Get number of available slots for specific API key"""
        return self.semaphores[api_key]._value


# Default configuration - you can modify this array with your API keys
GEMINI_API_KEYS = [
    os.getenv("k1"),os.getenv("k2"),os.getenv("k3")
]

GEMINI_CONCURRENCY_LIMIT_PER_KEY = 25

# Initialize the load balancer
gemini_load_balancer = APIKeyLoadBalancer(
    api_keys=GEMINI_API_KEYS,
    concurrency_limit_per_key=GEMINI_CONCURRENCY_LIMIT_PER_KEY
)

# Legacy compatibility - keep the old semaphore for backward compatibility
GEMINI_CONCURRENCY_LIMIT = 25
gemini_semaphore = Semaphore(GEMINI_CONCURRENCY_LIMIT)
