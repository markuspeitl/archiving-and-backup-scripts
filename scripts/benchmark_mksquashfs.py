
import os
from os.path import isdir, isfile, exists


# mksquashfs ./chroot chroot_gzip9_default.squashfs -noappend -comp gzip


# Data according to https://gist.github.com/baryluk/70a99b5f26df4671378dd05afef97fce

import os
orig_file_size_bytes = 26566785410

# gzip (default)/xz/lzo/lz4/zstd
comp_algorithms = ['gzip', 'xz', 'lzo', 'lz4', 'zstd']

# vscode: search words and quote them
# ([a-zA-Z0-9]+)
# replace
# '$1'

# Compression filters can improve compression of executable data eg. binaries and executables (https://www.kernel.org/doc/html/latest/staging/xz.html)
# because of this it is probably that the filters names here are for instruction sets / cpu architectures
xz_comp_filters = ['x86', 'arm', 'armthumb', 'powerpc', 'sparc', 'ia64']

# Rules: must be less than the block size and bigger than 8192bytes - examples 75%, 50%, 37.5%, 25%, or 32K, 16K, 8K
xz_dictionary_sizes = [0.2, 0.4, 0.6, 0.8, 1.0]

# Default (128k) - block sizes between 4K and 1M are supported
block_sizes_k_bytes = [4, 8, 16, 32, 64, 128, 256, 512, 1024]


def list_to_percent(float_list):
    return list(map(lambda dec_point: int(round(dec_point * 100)), float_list))


comp_algorithms = {
    'gzip': {
        '-Xcompression-level': range(1, 9 + 1),
        '-Xwindows-size': range(8, 15 + 1),
        '-Xstrategy': ['default', 'filtered', 'huffman_only', 'run_length_encoded', 'fixed']
    },
    'lzo': {
        '-Xalgorithm': ['lzo1x_1', 'lzo1x_1_11', 'lzo1x_1_12', 'lzo1x_1_15', 'lzo1x_999'],
        '-Xcompression-level': range(1, 9 + 1)
    },
    'lz4': {
        '-Xhc': [True, False]
    },
    'xz': {
        '-Xbcj': xz_comp_filters,
        '-Xdict-size': list_to_percent(xz_dictionary_sizes)
    },
    'zstd': {
        '-Xcompression-level': range(1, 22 + 1)
    },
}

options = "-info -progress -noappend"

# Filesystem not mounted to a multiple of 4k creates an unmountable FS (to retrieve the data unsquashfs needs to be used)
optiona_options = "-nopad"


compression_prio_levels = range(1, 10 + 1)
speed_prio_levels = range(1, 10 + 1)

squash_runs = []


# https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
def get_dir_size(path):

    if (not os.path.isdir(path)):
        return None

    return int(sum(file.stat().st_size for file in os.scandir(path) if file.is_file()))


def compression_set_to_options(compression_set):

    return ""


def is_valid_compression_set(compression_set):
    return True


def mksquashfs(source_dir, target_file, compression_set, option_list):

    if (not exists(source_dir) or not isdir(source_dir)):
        raise Exception('Error source directory of squashing operation does not exist or is not a directory')

    target_dir = os.path.dirname(target_file)

    if (not exists(target_dir) or not isdir(target_dir)):
        raise Exception('Error parent directory of target file/image of the squashed fs does not exist or is not a directory')

    if (not is_valid_compression_set(compression_set)):
        raise Exception('Error compression set has invalid options or settings')

    cmd_args = []
    cmd_args.append('mksquashfs')
    cmd_args.append(source_dir)
    cmd_args.append(target_file)
    cmd_args += compression_set_to_options(compression_set)
    cmd_args += option_list

    mksquash_cmd = " ".join(cmd_args)
    print(mksquash_cmd)
    # os.system(mksquash_cmd)

    if (not exists(target_file)):
        raise Exception('Error squashed images does not exist after mksquashfs operation')

    return target_file


compression_set = {
    'type': 'xz',
    'block_size': 128,
    '-Xdict-size': 0.5
}

run_options = ['-noappend', '-info', '-progress', '-wildcards']

source_dir_path = '/home/pmarkus'

# Note that without considering the excludes of mksquashfs the compression ratio that results from this is not accurate
orig_dir_size_bytes = get_dir_size(source_dir_path)

mksquashfs(source_dir_path, '/home/pmarkus/target_squash_archive.img', compression_set, run_options)
