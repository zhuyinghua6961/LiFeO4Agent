"""
Track database build progress over time.
"""

import time
import sys
from chromadb_manager import ChromaDBManager

EXPECTED_TOTAL = 794180
last_count = 0
last_time = time.time()

print("Tracking database build progress...")
print("Press Ctrl+C to stop")
print()

try:
    while True:
        db_manager = ChromaDBManager("./chroma_chunks_v2")
        collection = db_manager.get_collection("literature_chunks_v2")
        
        if collection:
            current_count = collection.count()
            current_time = time.time()
            
            # Calculate rate since last check
            if last_count > 0:
                chunks_added = current_count - last_count
                time_elapsed = current_time - last_time
                rate = chunks_added / time_elapsed if time_elapsed > 0 else 0
                
                # Estimate remaining time
                remaining = EXPECTED_TOTAL - current_count
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_hours = eta_seconds / 3600
                
                progress_pct = (current_count / EXPECTED_TOTAL) * 100
                
                print(f"[{time.strftime('%H:%M:%S')}] "
                      f"Chunks: {current_count:,}/{EXPECTED_TOTAL:,} ({progress_pct:.2f}%) | "
                      f"Rate: {rate:.1f} chunks/s | "
                      f"ETA: {eta_hours:.2f}h", flush=True)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Initial count: {current_count:,}", flush=True)
            
            last_count = current_count
            last_time = current_time
        else:
            print("Collection not found yet...", flush=True)
        
        time.sleep(30)  # Check every 30 seconds
        
except KeyboardInterrupt:
    print("\nStopped tracking.")
