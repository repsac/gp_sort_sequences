import os
import shutil
import tempfile
from random import randint
from pathlib import Path
import gp_sort_sequences


def _set_sequence(first_frame):
    frame_tokens = [x for x in str(first_frame)]
    frame_tokens[0] = str(int(frame_tokens[0]) + 1)
    first_frame = int(''.join(frame_tokens))
    last_frame = randint(first_frame+500, first_frame+1000)
    return (first_frame, last_frame)


def cleanup(paths):
    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)


def test_results(results):
    assert len(results) != 0, "No media was found for testing"
    for sequence in results:
        for ext in results[sequence]:
            data = []

            for fname in results[sequence][ext]:
                message = "Extensions mismatched {} != {}".format(ext,
                                                                    fname)
                assert fname.endswith(ext), message

                # we only want to do sequential testing on image file
                # that are generated from non-movie time-lapses
                if ext not in gp_sort_sequences.IMG_SEQUENCE_EXTENSIONS:
                    continue
                data.append(int(os.path.splitext(fname)[0][1:]))

            if not data:
                continue

            message = "Sequence {}/{} is NOT sequential".format(sequence,
                                                                ext)
            result = sorted(data) == list(range(min(data), max(data)+1))
            assert result, message


def _unittest(args):
    first_frame = '00001'
    folders = [[]]
    # fat32 will cause sequences (commonly over 1000) to be
    # broken out to multiple folders. this logic attempts to
    # emulate this behavior from GoPro cameras
    counter = 1000
    while len(folders) < 6:
        first_frame, last_frame = _set_sequence(first_frame)
        for frame in range(first_frame, last_frame):
            if counter == 0:
                counter = 1000
                folders.append([])
            folders[-1].append('{:>07d}'.format(frame))
            counter -= 1
        first_frame = last_frame
    
    tmp_root = tempfile.mkdtemp()
    folder_paths = []
    for index, folder in enumerate(folders):
        folder_name = '{:<03d}GOPRO'.format(index+1)
        folder_paths.append(os.path.join(tmp_root, folder_name))
        gp_sort_sequences._mkdir(folder_paths[-1])
        for filename in folder:
            # even if shooting in RAW (GPR) the GoPro still creates a
            # JPG file, we emulate that here
            for ext in gp_sort_sequences.IMG_SEQUENCE_EXTENSIONS:
                name = 'G{}.{}'.format(filename, ext)
                Path(os.path.join(folder_paths[-1], name)).touch()

    for index, folder_path in enumerate(folder_paths):
        files = os.listdir(folder_path)
        if index+1 == len(folder_paths):
            break
        assert len(files) == 2000, "Incorrect number of files in {}".format(
            folder_path)
    
    destination_directory = tempfile.mkdtemp()
    try:
        results = gp_sort_sequences.sort_sequences(
            tmp_root,
            destination_directory,
            verbose=args.verbose,
            dryrun=True if args.movie else args.dryrun,
            movie=args.movie)
        test_results(results)
    except:
        cleanup([tmp_root, destination_directory])
        raise
    else:
        cleanup([tmp_root, destination_directory])


def _main():
    args = gp_sort_sequences._parse_args()
    _unittest(args)


if __name__ == '__main__':
    _main()