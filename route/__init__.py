"""CLI for performing routing operations using an online routing service.
"""
import csv
import sys
import argparse
import logging
import pkg_resources
from .common import load_config
from . import operations as ops


def get_version():
    """Returns the version details for the package.
    """
    packages = pkg_resources.require("Route")
    return packages[0].version


def _configure_logger():
    """Configure the root logger.
    """
    logging.basicConfig(level=logging.DEBUG)


_configure_logger()
log = logging.getLogger(__name__)


def main():
    # load app config
    load_config()

    # parse provided cli args
    parser = argparse.ArgumentParser(prog="routr", description=__doc__)
    parser.set_defaults(func=ops.compute)
    arg = parser.add_argument

    arg("source", type=argparse.FileType("r"), help=\
        "path to csv file with coordinates for origin and destination points")
    arg("-o", "--output", type=argparse.FileType("w"), default=sys.stdout,
        help="location to write output. default to standard output")

    try:
        args = parser.parse_args(sys.argv[1:])
        args.func(args)
    except Exception as ex:
        log.exception(ex)
