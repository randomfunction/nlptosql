import time
import logging
import concurrent.futures
from typing import Callable, Any

# 1. Setup simple, clear logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nlptosql")

# 2. Simple Metrics Tracker
class MetricsTracker:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_duration = 0.0

    def record_request(self, success: bool, duration: float):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_duration += duration

    def get_stats(self) -> dict:
        avg_time = self.total_duration / self.total_requests if self.total_requests > 0 else 0
        return {
            "total_requests": self.total_requests,
            "success": self.successful_requests,
            "failure": self.failed_requests,
            "avg_response_time_sec": round(avg_time, 3)
        }

metrics = MetricsTracker()

# 3. Retry and Timeout Logic for LLM calls
def retry_with_timeout(func: Callable, max_retries: int = 2, timeout_sec: int = 15) -> Any:
    """Executes a function with a timeout limit, failing over via simple retries."""
    for attempt in range(1, max_retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func)
                # Enforce timeout limit
                return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            logger.warning(f"Attempt {attempt}: LLM Request timed out after {timeout_sec}s.")
            if attempt == max_retries:
                raise TimeoutError("LLM Request failed after max retries due to timeout.")
        except Exception as e:
            logger.error(f"Attempt {attempt}: LLM Execution Failed -> {str(e)}")
            if attempt == max_retries:
                raise e
            time.sleep(1) # Base cooldown
