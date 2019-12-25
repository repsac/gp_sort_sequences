# gp_sort_sequences
Python script for sorting out sequences from GoPro time lapses

Given one or more source folders, search for all JPG and GPR files from a
GOPRO's source folder. The media will be sorted into `/SEQ000/<EXT>`
subfolders under the specified output path.

```
<OUTPUT>/SEQ001/JPG/G*.JPG
<OUTPUT>/SEQ001/GPR/G*.GPR
<OUTPUT>/SEQ002/JPG/G*.JPG
<OUTPUT>/SEQ002/GPR/G*.GPR
```

**IMPORTANT**
This script does not try to process time-lapse movies, only image sequences.

The `--movie` option will generate a 30fps movie from the JPG files only, and
be created in the sequence root.

`<OUTPUT>/SEQ001/SEQ001.MP4`

Command line usage:
```shell
# execute on a specified directory (output uses $PWD)
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
```