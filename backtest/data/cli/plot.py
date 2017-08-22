from __future__ import print_function

from datetime import datetime

from backtest.data import FileDataSource


def create_argument_parser(parser):
    parser.add_argument('-i', '--info', action='store_true',
                        help='print metadata and exit')
    parser.add_argument('-d', '--dataset', nargs='+', default=None,
                        help='select datasets (default: all)')
    parser.add_argument('-p', '--price', nargs='+',
                        help='select prices (default: all)',
                        choices=FileDataSource.CANDLE_VALUES,
                        default=FileDataSource.CANDLE_VALUES)
    parser.add_argument('file')
    return parser

def plot(args, src):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    start = src.start_time
    step = src.tick_size
    date_formatter = FuncFormatter(
        lambda x, _: datetime.fromtimestamp((int(start + x * step)))
    )

    fig, ax = plt.subplots()
    ax.xaxis.set_major_formatter(date_formatter)
    ax.set_xlim(0, src.get_max_ticks() - 1)
    fig.autofmt_xdate()

    plt.title(args.file)
    plt.xlabel('time')
    plt.ylabel('price')
    plots = []
    for dataset in args.dataset:
        plots.extend(
            plt.plot(
                src.data[dataset][:, src.CANDLE[price]],
                label='{0}_{1}'.format(dataset, price)
            )[0]
            for price in args.price
        )
    plt.legend(handles=plots)
    plt.show()


def main(args):
    src = FileDataSource(args.file)

    if args.info:
        end_time = src.start_time + src.tick_size * (src.get_max_ticks() - 1)
        print('start    ', datetime.fromtimestamp(src.start_time).ctime())
        print('end      ', datetime.fromtimestamp(end_time).ctime())
        print('interval ', datetime.fromtimestamp(src.tick_size).time())
        print('datasets ', ' '.join(src.datasets()))
        exit(0)

    if args.dataset is None:
        args.dataset = src.datasets()
    else:
        for dataset in args.dataset:
            if dataset not in src:
                print('no dataset', dataset, 'in', args.file)
                exit(1)

    plot(args, src)
