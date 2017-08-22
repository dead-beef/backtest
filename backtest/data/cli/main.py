from __future__ import print_function, absolute_import

from argparse import ArgumentParser

from . import plot, get


def create_argument_parser():
    parser = ArgumentParser()
    parsers = parser.add_subparsers(dest='command')

    plot.create_argument_parser(parsers.add_parser('plot'))
    get.create_argument_parser(parsers.add_parser('get'))

    return parser

def main():
    parser = create_argument_parser()
    args = parser.parse_args()
    if args.command == 'plot':
        plot.main(args)
    elif args.command == 'get':
        get.main(args)
    else:
        print('Invalid command "{0}"'.format(args.command))
        exit(1)
