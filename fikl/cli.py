from fikl.decision import Decision

import argparse
import logging
import sys
import traceback

import ipdb


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Path to YAML with configuration")
    parser.add_argument("-d", "--data", required=True, help="Path to CSV with scores")
    parser.add_argument("-o", "--output", required=True, help="Path to HTML output")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def exception_handler(exception_type, exception, tb):
    """print the stack trace and drop into ipython shell on exception"""
    traceback.print_exception(exception_type, exception, tb)
    ipdb.post_mortem(tb)


def main():
    args = parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        # also drop into an ipython debugging shell on exception
        sys.excepthook = exception_handler
    else:
        logging.basicConfig(level=logging.INFO)

    decision = Decision(config_path=args.config, data_path=args.data)
    decision.to_html(args.output)


if __name__ == "__main__":
    main()
