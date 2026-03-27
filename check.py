import traceback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import main
    print("SUCCESS: main imported without errors")
except Exception as e:
    with open('crash.txt', 'w') as f:
        f.write(traceback.format_exc())
    print("FAILED: check crash.txt")
