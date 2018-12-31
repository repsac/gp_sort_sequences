import os
import shutil
import argparse
from datetime import datetime

DEFAULT_INTERVAL = 5


def sort_sequences(paths,
                   destination,
                   interval=DEFAULT_INTERVAL,
                   dryrun=False):
    raw_files = _parse_raw_files(paths)
    sorted_raws = _sort_raw_files(raw_files, interval)
    _move_raws(sorted_raws, destination, dryrun)


def _move_raws(sorted_raws, destination, dryrun):
    count = 1
    for each in sorted_raws:
        if not each:
            continue

        if len(each) == 1:
            set_folder = 'single'
        else:
            set_folder = 'seq%d' % count
            count += 1

        set_folder = os.path.join(destination, set_folder)

        if not os.path.exists(set_folder):
            if dryrun:
                print("DRYRUN: creating path '%s'" % set_folder)
            else:
                os.makedirs(set_folder)

        for fi in each:
            if dryrun:
                print("DRYRUN: Moving %s > %s" % (fi, set_folder))
            else:
                shutil.move(fi, set_folder)


def _sort_raw_files(raw_files, interval):
    sorted_raws = [[]]
    for index, rf in enumerate(raw_files):
        sorted_raws[-1].append(rf)

        try:
            next_rf = raw_files[index+1]
        except IndexError:
            break

        this_date = datetime.fromtimestamp(os.path.getmtime(rf))
        next_date = datetime.fromtimestamp(os.path.getmtime(next_rf))

        diff = next_date - this_date
        if not interval-1 <= diff.seconds <= interval+1:
            sorted_raws.append([])

    return sorted_raws


def _parse_raw_files(paths):
    raw_files = []
    for path in paths:
        for root, dirs, files in os.walk(path):
            for fi in files:
                if fi.endswith('.GPR'):
                    raw_files.append(os.path.join(root, fi))
    return raw_files


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    parser.add_argument('-i', '--interval', default=DEFAULT_INTERVAL, type=int)
    parser.add_argument('-d', '--destination', required=True)
    parser.add_argument('-n', '--dryrun', action='store_true')

    args = parser.parse_args()
    sort_sequences(args.paths, args.destination,
                   interval=args.interval,
                   dryrun=args.dryrun)


if __name__ == '__main__':
    _main()
