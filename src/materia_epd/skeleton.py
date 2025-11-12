import sys
import argparse


def main(args):
    parser = argparse.ArgumentParser(description="MaterIA CLI")
    # Add real options/commands here later
    parser.add_argument("--version", action="store_true", help="Show version")
    parsed = parser.parse_args(args)

    if parsed.version:
        print("MaterIA CLI version 0.1.0")  # or import from your package


def run():
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
