import os
import sys

# Ensure root directory and gui directory are in sys.path
cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(cur_dir)
for p in (cur_dir, root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app import LANForgeApp
except ImportError:
    from gui.app import LANForgeApp

def main():
    app = LANForgeApp()
    app.mainloop()

if __name__ == "__main__":
    main()
