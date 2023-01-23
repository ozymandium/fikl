from fikl import Decision

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Path to YAML with configuration")
    parser.add_argument("output", help="Path to HTML output")
    return parser.parse_args()


def main(args: argparse.Namespace):
    decision = Decision.from_yaml(args.config)
    decision.to_html(args.output)


if __name__ == "__main__":
    main(parse_args())
