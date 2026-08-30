import sys
import os
import time
from datetime import datetime

# Import scripts
import extract_flight_data
import process_flight_data

def main():
    start_time = time.time()
    today = datetime.now()

    # Step 1: Dunamic API pull across booking window buckets
    print(f"== Extracting flight data ==")
    print(f"\n[Step 1/2]: Triggering flight data acquisition")
     
    try:
        extract_flight_data.main()
    except Exception as e:
        print(f"Error during flight data extraction: {e}")
        sys.exit(1)

    # Step 2: Data processing and transformation
    print(f"\n[Step 2/2]: Triggering flight data processing")
    
    try: 
        process_flight_data.main()
    except Exception as e:
        print(f"Error during flight data processing: {e}")
        sys.exit(1)

    elapsed = round(time.time() - start_time, 2)
    print(f"\nFlight data extraction and processing completed in {elapsed} seconds.")

if __name__ == "__main__":
    main()
         

     