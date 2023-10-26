#!/usr/bin/env python3

import os
from os.path import isdir, isfile, exists


# mksquashfs ./chroot chroot_gzip9_default.squashfs -noappend -comp gzip


# More infos for compression algorithms:
# https://dev.to/cookiebinary/comparing-compression-methods-on-linux-gzip-bzip2-xz-and-zstd-3idd

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

# Default (128k -- 131072bytes) - block sizes between 4K and 1M are supported
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
    if (not is_valid_compression_set(compression_set)):
        return None

    options = []
    options.append('-comp')
    options.append(compression_set['type'])
    options.append('-b')
    options.append(compression_set['type'])

    return ""


def is_valid_compression_set(compression_set):
    if ('type' not in compression_set):
        raise Exception('A type of compression algorythm to use with mksquashfs is required')

    if ('block_size' not in compression_set):
        raise Exception('Block size is required')

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

# mksquashfs(source_dir_path, '/home/pmarkus/target_squash_archive.img', compression_set, run_options)


result = {
    'time': 0,
    'target': 'target.img',
    'target_size': 0,
    'src': "",
    'src_size': 0
}

bench_inf0 = {
    'label': "",
    'before_s': 0,
    'after_s': 0,
    'time': 0
}

# Results taken from https://gist.github.com/baryluk/70a99b5f26df4671378dd05afef97fce
prev_results = [
    {
        'label': 'gzip_128k',
        'time': 168.0,
        'after_s': 9248616448
    },
    {
        'label': 'xz_128k',
        'time': 376.0,
        'after_s': 7822753792
    },
    {
        'label': 'xz_128k_x86',
        'time': 781.0,
        'after_s': 7701307392
    },
    {
        'label': 'xz_32k',
        'time': 336.0,
        'after_s': 8517169152
    },
    {
        'label': 'zstd_128k_x15',
        'time': 215.0,
        'after_s': 8553738240
    },
    {
        'label': 'zstd_32k_x15',
        'time': 159.0,
        'after_s': 9148821504
    },
    {
        'label': 'zstd_32k_x22',
        'time': 650.0,
        'after_s': 9059016704
    },
    {
        'label': 'zstd_128k_x22',
        'time': 934.0,
        'after_s': 8473190400
    },
    {
        'label': 'lzo_32k_x9',
        'time': 180.0,
        'after_s': 10710016000
    },
    {
        'label': 'lz4_32k',
        'time': 21.0,
        'after_s': 13007339520
    },
    {
        'label': 'lz4_32k_HC',
        'time': 121.0,
        'after_s': 11628195840
    }
]

for result in prev_results:
    result['before_s'] = 26566785410

for result in prev_results:
    result['ratio'] = round(result['after_s'] / result['before_s'], 2)


for result in prev_results:
    result['size_reduction_per_second'] = round(((1.0 - result['ratio']) / result['time']) * 1000.0, 3)


time_table = sorted(prev_results, key=lambda result: result['time'])
size_table = sorted(prev_results, key=lambda result: result['ratio'])
size_reduction_per_second_table = sorted(prev_results, key=lambda result: result['size_reduction_per_second'])
# size_table = sorted(lambda result: result['after_s'], prev_results)


def pretty_table(results, selected_keys):
    from prettytable import PrettyTable
    results_table = PrettyTable(selected_keys)

    for result in results:
        selected_fields = []
        for key in selected_keys:
            selected_fields.append(result[key])
        results_table.add_row(selected_fields)

    print(results_table)


def ugly_print(results, selected_keys):
    print(selected_keys)

    for result in results:
        selected_fields = []

        for key in selected_keys:
            selected_fields.append(result[key])

        print(selected_fields)


print("Timetable:")
pretty_table(time_table, ['label', 'time', 'ratio', 'size_reduction_per_second'])
print("Sizetable:")
pretty_table(size_table, ['label', 'time', 'ratio', 'size_reduction_per_second'])

print("Ratio reduction per second:")
pretty_table(size_reduction_per_second_table, ['label', 'time', 'ratio', 'size_reduction_per_second'])


# Conclusions for algorithms:
# Discussion of the results of https://dev.to/cookiebinary/comparing-compression-methods-on-linux-gzip-bzip2-xz-and-zstd-3idd and the other results here
# - xz has the strongest compression, but is slow
# - zstd is a little better than gzip, bzi2 compression on 'normal' preset and on strong preset it is a bit weaker than xz (but only needs around half the time)
# interestingly on 'normal' preset it is quite a bit faster than gzip.
# According to the 'size_reduction_per_second' metric calculated above it is the third strongest when combining compression speed with ratio (only after lz4)

# Different compression tiers based on requirements:
# 1. For very low compression scenarios lz4 is the fastest
# 2. Then for the next tier zstd (32k, x15) and gzip (128k) perform very similar (both outperforming lzo)
# 3. Mid compression, zstd seems to outperform bzip2 in speed
# 4. In the high compression rate it starts with a strong dropoff in compression speed - here zstd and xz compression perform similar, although zstd is faster on similar results
# 5. If you have the computing resources and time nothing beats 'xz', as it can still reach a better ratio than zstd

# 1. For high volume and day to day use LZ4, GZIP, ZSTD (low)
# 2. For backup and creating archives that need to be opened somtimes and/or on low powered machines use ZSTD (decompression is also good with that)
# 3. For archiving, when storage/retrieval time does not matter as much, maybe storage is limite use XZ


# Block sizes (32k ... 128k ... 256k >> 1-2M):
# - Bigger block sizes mean better compression ratio, but slower speed
# (block size is probably in which sized chunks compression is performed, therefore if a couple of files fit into a block, similar or redundant information between files can be removed
# though i have not found exact infomation yet)
# - Bigger blocks increase RAM usage during compression
# - When a file is smaller than the block size, the whole block needs to be decompressed to access the file

# https://engineering.fb.com/2018/12/19/core-infra/zstandard/
# At facebook they are using 256k block sizes for squashfs images with Zstd
# Though it is best to take claims of the creator and large businesses that have bias with a grain of salt.

# https://en.wikipedia.org/wiki/Zstd
# Debian and Arch switched their packaging to zstd.
# 0.8% bigger packages on arch but more than 10x faster decompression
# Seems to be a generally very good pick for semi permanent archiving

# For normal usage for archives/compression outside of a squashfs image
# https://www.systutorials.com/docs/linux/man/1-zstd/
