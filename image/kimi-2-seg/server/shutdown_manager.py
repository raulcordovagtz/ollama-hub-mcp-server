import time
import os
import psutil
import torch
import threading

class ShutdownManager:
    def __init__(self, idle_timeout_minutes, vram_threshold_mb):
        self.idle_timeout = idle_timeout_minutes * 60
        self.vram_threshold = vram_threshold_mb
        self.last_request_time = time.time()
        self.running = False
        self.monitor_thread = None

    def update_activity(self):
        self.last_request_time = time.time()

    def start_monitor(self):
        # We need this to run in background, but the prompt example just showed the class logic.
        # Since I am integrating into FastAPI, I need to run 'monitor' loop.
        # The prompt `monitor` method has a `while True`. I should probably run this in a thread or task.
        # I will keep the exact logic but wrap it to be non-blocking for startup if called directly,
        # OR just provide the method as requested and let server.py call it in background task.
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor, daemon=True)
        self.monitor_thread.start()

    def monitor(self):
        import logging
        logger = logging.getLogger(__name__)
        while self.running:
            time.sleep(30)
            idle_time = time.time() - self.last_request_time
            vram_used = self.get_vram_usage()
            
            logger.info(f"Monitor check: idle_time={idle_time:.1f}s, vram={vram_used:.1f}MB, timeout={self.idle_timeout}s, threshold={self.vram_threshold}MB")

            if idle_time > self.idle_timeout:
                logger.warning(f"Shutdown triggered: idle_time={idle_time:.1f}s > {self.idle_timeout}s")
                self.shutdown("inactivity")
            elif vram_used > self.vram_threshold:
                logger.warning(f"Shutdown triggered: vram={vram_used:.1f}MB > {self.vram_threshold}MB")
                self.shutdown("vram threshold exceeded")

    def get_vram_usage(self):
        try:
            return torch.mps.current_allocated_memory() / (1024 * 1024)
        except Exception:
            # Fallback or 0 if not MPS
            if torch.cuda.is_available():
                 return torch.cuda.memory_allocated() / (1024 * 1024)
            return 0

    def shutdown(self, reason="inactivity"):
        message = f"Inference server shutting down due to {reason}."
        print(f"Auto-kill triggered: {message}")
        # Audio alert for Mac
        os.system(f'say "{message}" &')
        time.sleep(2) # Give a moment for audio to start
        os._exit(0)

    def stop(self):
        self.running = False
