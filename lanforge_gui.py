import os
import sys

# Safe stdout/stderr redirection for Windows --noconsole binaries
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from gui.app import LANForgeApp

def main():
    app = LANForgeApp()
    app.mainloop()

if __name__ == "__main__":
    main()
