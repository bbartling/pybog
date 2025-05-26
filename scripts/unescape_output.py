# scripts/
from xml.sax.saxutils import unescape
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python unescape_output.py <escaped_output.txt>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        raw = f.read()

    print("\n=== Unescaped Output ===\n")
    print(unescape(raw))