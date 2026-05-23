"""Quick test to run database_setup and capture output to file."""
import sys
import io

# Redirect all output to a file
log_file = open('setup_log.txt', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

try:
    from database_setup import create_database
    result = create_database()
    print(f"\nResult: {result}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    log_file.close()
