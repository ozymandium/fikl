from fikl import Decision

import argparse
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Path to YAML with configuration")
    parser.add_argument("output", help="Path to HTML output")
    parser.add_argument("-d", "--debug", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    decision = Decision.from_yaml(args.config)
    decision.to_html(args.output)


if __name__ == "__main__":
    main()
