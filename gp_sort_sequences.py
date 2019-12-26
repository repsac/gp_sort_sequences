# MIT License
#
# Copyright (c) 2019 Ed Caspersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# allcopies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Given one or more source folders, search for all JPG and GPR files from a
GOPRO's source folder. The media will be sorted into /SEQ000/<EXT>
subfolders under the specified destination path.

<DESTINATION>/SEQ001/JPG/G*.JPG
<DESTINATION>/SEQ001/GPR/G*.GPR
<DESTINATION>/SEQ002/JPG/G*.JPG
<DESTINATION>/SEQ002/GPR/G*.GPR

*IMPORTANT*
This script does not try to process time-lapse movies, only image sequences.

The --movie option will generate a 30fps movie from the JPG files only, and
be created in the sequence root.

<DESTINATION>/SEQ001/SEQ001.MP4

==== COMMAND LINE USAGE ====
# execute on a specified directory (destination defaults to $PWD)
> python -m gp_sort_sequeces <path to root folder>

# execute on more than one root directory (all sorted data will be treated as
# on and put in one destination folder)
> python -m gp_sort_sequeces <path to folder1> <path to folder2>

# specifiy the destination (path must already exist)
> python -m gp_sort_sequeces <path to root folder> -d <destination>

# enable additional verbosity
> python -m gp_sort_sequeces <path to root folder> -d <destination> -v

# generate a movie file from the JPG (non-raw) sequence files
> python -m gp_sort_sequeces <path to root folder> -d <destination> -m

# run the unit tests
> python -m gp_sort_sequeces -u -v
"""
import os
import sys
import shutil
import argparse
from itertools import groupby
from operator import itemgetter
from subprocess import Popen


# One probably should not overwrite these constants
__VERBOSE = False
__DRYRUN = False

# The image sequence formats created by GoPro. This script does
# not try to process time-lapse movies, only image sequences.
# To avoid breaking logic in this script, keep the non-raw (JPG)
# file in the first index.
IMG_SEQUENCE_EXTENSIONS = ('JPG', 'GPR')

# Change the prefix (before"{" to fit your needs)
SEQUENCE_FOLDER = 'SEQ{:>03d}'

# Feel free to edit these as need be to fit your workflow
FPS = 30
MOVIE_WIDTH = 1920
MOVIE_EXTENSION = 'MP4'

# If this string is changed you must ensure that the format()
# parameters are satisfied in _build_command()
FFMPEG = 'ffmpeg -r {fps:d} -f image2 -start_number {start_number} -i '\
         '{input_file} -vf "scale={movie_width}:-1" -vcodec libx264 '\
         '-crf 25 -pix_fmt yuv420p -y {output_file}'


def sort_sequences(root_directory,
                   destination_directory,
                   dryrun=False,
                   verbose=False,
                   movie=False):
    """
    Given one or more source folders, search for all JPG and GPR files from a
    GOPRO's source folder. All images belonging to the same sequence will
    be organized under a <SEQ000> folder, and be organized by file type.

    :param root_directory: accepts either a single string or a list of strings
                        as the root folder(s) to search for image sequences
    :param destination_directory: destination for the sorted image sequences
    :param dryrun: optional dryrun (no files will be moved or created)
    :param verbose: optional verbosity, leave off if you like it quiet
    :param movie: optional feature to create a preview movie from JPG files
    :rtype: {}
    :returns: {
        <sequence folder path>: {
            <EXTENSION>: [<media>, ...]
        }
    }
    """

    def set_params(x, y):
        global __VERBOSE
        __VERBOSE = x
        global __DRYRUN
        __DRYRUN = y

    set_params(verbose, dryrun)

    if not isinstance(root_directory, list):
        root_directory = [root_directory]
    
    try:
        file_mapping = _map_sequence_files(root_directory)
        sorted_files = _sort_sequence_files(file_mapping, destination_directory)
        if movie:
            movies = _generate_movie(sorted_files)
            for sequence in movies:
                sorted_files[sequence].update(movies[sequence])
    except:
        set_params(False, False)
        raise

    set_params(False, False)
    return sorted_files


def _build_command(sequence, name, ext):
    """
    Build out the command used to create a preview movie file
    """
    basename, file_ext = os.path.splitext(name)
    input_file = '{root}%{seq:03d}d{ext}'.format(
        root=basename[0],
        seq=len(basename[1:]),
        ext=file_ext)
    input_file = os.path.join(sequence, ext, input_file)
    output_file = '{}.{}'.format(os.path.basename(sequence),
                                 MOVIE_EXTENSION)
    output_file = os.path.join(sequence, output_file)
    cmd = FFMPEG.format(fps=FPS,
                        input_file=input_file,
                        output_file=output_file,
                        start_number=basename[1:],
                        movie_width=MOVIE_WIDTH)
    return cmd, output_file


def _generate_movie(sorted_files):
    """
    Create a movie clips, from JPG files, for each sequence
    """
    global __DRYRUN

    movies = {}
    for sequence in sorted_files:
        for ext in sorted_files[sequence]:
            # we aren't going to try and generate clips from raw media
            if ext.upper() != IMG_SEQUENCE_EXTENSIONS[0]:
                continue
            name = sorted_files[sequence][ext][0]
            cmd, output_file = _build_command(sequence, name, ext)

            movies.setdefault(sequence, {}).setdefault(
                MOVIE_EXTENSION, []).append(output_file)

            if __DRYRUN:
                _print("Running command: {}".format(cmd))
                continue          

            proc = Popen(cmd)
            proc.wait()
            if proc.returncode != 0:
                message = "Failed to run command: {}".format(cmd)
                print(message, file=sys.stderr)
    return movies


def _sort_sequence_files(file_mapping, destination_directory):
    """
    Sort the sequences into their own <sequence>/<extension folders
    """
    seq_counter = 1
    sorted_files = {}

    keys = [*file_mapping]
    keys.sort()
    for k, g in groupby(enumerate(keys), lambda ix : ix[0] - ix[1]):
        seq_name = SEQUENCE_FOLDER.format(seq_counter)
        seq_folder_path = os.path.join(destination_directory, seq_name)
        sorted_files.update({seq_folder_path: {}})
        _mkdir(seq_folder_path)
        manifest = list(map(itemgetter(1), g))

        for key in manifest:
            for ext, path in file_mapping[key].items():
                ext_path = os.path.join(seq_folder_path, ext)
                _mkdir(ext_path)
                _move(path, ext_path)
                sorted_files[seq_folder_path].setdefault(
                    ext, []
                ).append(os.path.basename(path))

        for key, value in sorted_files[seq_folder_path].items():
            ext_path = os.path.join(seq_folder_path, key)
            _print("Moved {} files to {}".format(len(value), ext_path))
        seq_counter += 1
    return sorted_files


def _map_sequence_files(root_directory):
    """
    Create a mapping associating the GPR and JPG files with
    their corresponding integer identifier.

    {
        30067: ['../G0030067.JPG',
                '../G0030067.GPR']
    }
    """
    file_mapping = {}
    for each_folder in root_directory:
        for root, dirs, files in os.walk(each_folder):
            for fi in files:
                name, ext = os.path.splitext(fi)
                key = int(name[1:])
                file_mapping.setdefault(key, {}).update({
                    ext[1:]: os.path.join(root, fi)
                })
    return file_mapping


def _move(src, dst):
    global __DRYRUN
    if not __DRYRUN:
        shutil.move(src, dst)


def _print(message):
    global __DRYRUN
    global __VERBOSE
    if __VERBOSE:
        if __DRYRUN:
            message = "[DRYRUN] {}".format(message)
        print(message)


def _mkdir(path):
    global __DRYRUN
    if not os.path.exists(path) and not __DRYRUN:
        os.mkdir(path)
        _print("Created '{}'".format(path))


def _unittest(args):
    import tempfile
    from random import randint
    from pathlib import Path

    first_frame = '00001'
    folders = [[]]
    # fat32 will cause sequences (commonly over 1000) to be
    # broken out to multiple folders. this logic attempts to
    # emulate this behavior from GoPro cameras
    counter = 1000

    def set_sequence(first_frame):
        frame_tokens = [x for x in str(first_frame)]
        frame_tokens[0] = str(int(frame_tokens[0]) + 1)
        first_frame = int(''.join(frame_tokens))
        last_frame = randint(first_frame+500, first_frame+1000)
        return (first_frame, last_frame)

    while len(folders) < 6:
        first_frame, last_frame = set_sequence(first_frame)
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
        _mkdir(folder_paths[-1])
        for filename in folder:
            # even if shooting in RAW (GPR) the GoPro still creates a
            # JPG file, we emulate that here
            for ext in IMG_SEQUENCE_EXTENSIONS:
                name = 'G{}.{}'.format(filename, ext)
                Path(os.path.join(folder_paths[-1], name)).touch()

    for index, folder_path in enumerate(folder_paths):
        files = os.listdir(folder_path)
        if index+1 == len(folder_paths):
            break
        assert len(files) == 2000, "Incorrect number of files in {}".format(
            folder_path)
    
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
                    if ext not in IMG_SEQUENCE_EXTENSIONS:
                        continue
                    data.append(int(os.path.splitext(fname)[0][1:]))

                if not data:
                    continue

                message = "Sequence {}/{} is NOT sequential".format(sequence,
                                                                    ext)
                result = sorted(data) == list(range(min(data), max(data)+1))
                assert result, message
    
    destination_directory = tempfile.mkdtemp()
    try:
        results = sort_sequences(tmp_root, destination_directory,
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
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument('paths', nargs='*',
                        default=[os.getcwd()],
                        help="Specify one or more root paths to search")
    parser.add_argument('-d', '--destination',
                        default=os.getcwd(),
                        help="Specify the destination path (must already exist)")
    parser.add_argument('-u', '--unittest',
                        action='store_true',
                        help="Perform the unittests")
    parser.add_argument('-n', '--dryrun',
                        action='store_true',
                        help=("Runs the script but does not move files or "
                              "generate any movie files."))
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Enables verbose feedback")
    parser.add_argument('-m', '--movie',
                        action='store_true',
                        help="Generates a movie file from the JPG sequence(s)")

    args = parser.parse_args()

    if args.unittest:
        _unittest(args)
    else:
        sort_sequences(args.paths,
                       args.destination,
                       dryrun=args.dryrun,
                       verbose=args.verbose,
                       movie=args.movie)


if __name__ == '__main__':
    _main()