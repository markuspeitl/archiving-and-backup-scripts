import os
from os.path import isdir, isfile, exists, expanduser, join
from datetime import date
import argparse
import sys

# target_dir = "/backups"


def get_squash_backup_base_cmd(source_dir, backups_dir=None, compression_lvl=17):

    if (not backups_dir):
        backups_dir = "/backups"

    if (backups_dir and not exists(backups_dir)):
        os.makedirs(backups_dir, exist_ok=True)

    if (not exists(source_dir)):
        raise Exception("Source dir does not exist")

    fs_source_path_label = source_dir.replace('/', '-')

    today = date.today()
    today_date_string = today.strftime("%d-%m-%Y")

    comp_algo = "zstd"
    block_size = "256k"

    settings_string = f"c_{comp_algo}-b_{block_size}-l_{compression_lvl}"

    full_backup_name = 'squash' + fs_source_path_label + "-" + today_date_string + "-" + settings_string + '.img'

    if (full_backup_name[0] == '-'):
        full_backup_name = full_backup_name[1:]

    target_path = join(backups_dir, full_backup_name)

    cmd = [
        'sudo',
        'mksquashfs',
        source_dir,
        target_path,
        '-comp', comp_algo,
        "-Xcompression-level", str(compression_lvl),
        "-b", block_size,
        "-mem", "1200M",
        "-info", "-progress",
        "-noappend"
    ]

    return cmd


def get_filter_options(filters_arg):

    if (not filters_arg):
        return []

    cmd = ['-regex']

    for filter in filters_arg:
        cmd.append('-e')
        cmd.append(f"'{filter}'")

    return cmd


"""
def mk_squashfs_archive(source_dir, exclude_regex_filters=[], compression_level=17):
    backup_cmd = get_squash_backup_base_cmd(source_dir, None, compression_level)
    filter_options = get_filter_options(exclude_regex_filters)

    full_cmd_args = backup_cmd + filter_options
    full_cmd = " ".join(full_cmd_args)

    print(full_cmd)
    # os.system(full_cmd)
"""


def print_cmd_args(args, vertical=True):

    cmd = ' '.join(args)
    if (vertical):
        cmd = '\n'.join(args)

    print(cmd)


def mk_squashfs_archive(source_dir, options):
    backup_cmd = get_squash_backup_base_cmd(source_dir, backups_dir=options.backups_dir, compression_lvl=options.compression_level)
    filter_options = get_filter_options(options.exclude_regex_filters)

    full_cmd_args = backup_cmd + filter_options
    full_cmd = " ".join(full_cmd_args)

    # print(full_cmd)

    print_cmd_args(full_cmd_args)

    if (not options.dry_run):
        print(full_cmd)
        # os.system(full_cmd)


# https://stackoverflow.com/questions/57304278/how-to-use-mksquashfs-regex
# https://askubuntu.com/questions/628585/mksquashfs-not-excluding-file


def get_universal_excludes():
    return [
        '\.cache',
        '.*\.cache\/.*',
        '.*\.cache\/.*',
        '.*cache\/.*',
        '.*\/logs\/.*',
        '.+/node_modules',
        'node_modules/*',
    ]


def get_home_excludes_expressions():
    return [
        '^\.nvm',
        '^\.npm',
        '^\.vscode-server',
        '^.*.img',
        '.+/dist',
        'dist/*'
    ] + get_universal_excludes()


def get_sys_excludes_expressions():
    return [
        # Contains device nodes that appear as files, however they do not really exist and are a representation of the system connected devices/device drivers, for programs to communicate with
        '^dev',
        # Maily for letting programs or the system mount non permanent/removable media here (usb flash storage, drives, cdrom)
        '^media',
        # Contains information about the system and its devices (can be printed out by using 'cat' on the filedescriptor), is a newer place for some stuff that historically was in /proc, also for kernel state changes, but more strictly structured than /proc
        '^sys',
        # Contains the initramfs image and the bootloader, might make sense to back this up for making the squashfs image bootable or backing up the specific kernel with the system (just for data and configs however this is not needed)
        '^boot',
        # Place for (partly) corrupted files to be placed if they are detected in a filsystem check run fschk
        'lost+found',
        # Place for the user to mount partitions or devices example: network shares are mounted here, or for the os, but mainly more permanent things then like internal data drives
        'mnt',
        # Provides information about running processes, kernel status, files for changing kernel states
        'proc',
        # Temporary directory for application to place data in, data is not guaranteed to persist after reboot
        'tmp',
        # Link to /var/run, containes data used by applications at runtime tmpfs in RAM #https://askubuntu.com/questions/169495/what-are-run-lock-and-run-shm-used-for
        '/run',
        'var/run',
        # Related to /run, /run/lock contains lock files indicating that a shared resource is in use by a process (handling of access conflicts)
        'var/lock',
        # Package manager state backups?
        '^var/backups',
        # Temporary cache files of applications (usually keeping something on disk so it does not need to be downloaded checked every time)
        'var/cache',
        # Application logs - can get quite big (might be useful to back up on really critical servers for the sake of analysis and security)
        'var/log',
        # Temporary files
        'var/tmp',
        # variable state data that should persist (might make sense to back up when trying to run backed up applications)
        'var/lib',
        # Data thats awaiting processing (printer queue, pending cronjobs), outgoing mail
        'var/spool'

    ] + get_universal_excludes()

# What does get backed up (without symlinks)
# -home (optional) -> better though is a dedicated backup for user data
# opt - Potentially contains data if an application was installed to there (third party or seperate software)
# root - Usually not big, nice to have, but usually does not contain much of interest unless work was done in/with the root user (if you can create a user to do sysadmin stuff, otherwise backing your root user up is useful)
# usr /bin /include /share /local /include - Binaries, libraries and shared headers for installed and self built applications, python packages, desktop files
# boot - Might contain boot configurations, probably only makes sense to back up when trying to make the backup bootable
# etc - System wide configurations of applications (good idea to back up if anything was changed)
# (mnt) - if anything is mounted here that should also be backed up this could be included, however a dedicated backup would be better
# srv - Sometimes used to store server data, web pages, apache server configurations on -> so if there is something on there we want to back it up
# var/lib - Package managers use it to store lists to sources, data generated by applications https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s08.html basically data that needs persistance and needed for running/resuming an application from the last state
# var/lib/flatpak is where your flatpak applications are stored -- /var/snap where your snap packages are
# var/?? - Some databases like mysql postgresql hold their data somwhere in var (then you want to back up those var locations -> might be an issue though if there is a write while backing up)
# var/ might contain "databases, web pages, crontabs, log files, and DNS zone files" https://www.redhat.com/sysadmin/backup-dirs

# Pure data
# -home
# (-root) if changed
# etc
# srv

# Pure applications
# (/boot) should it be bootable?
# /usr -- applications and libraries --- # /bin / lib  +++ just symbolic links to /usr

# for /var it is best to manually go through the dirs and check once more which ones are important
# /var/lib
# /var/snap
# /var/mail
# /var/local
# (/var/backups)
# opt - if you installed anything to there


def get_sys_excludes_nohome_expressions():
    return get_sys_excludes_expressions() + ['^home']


def add_to_exclude_expressions(options, add_expr_list):
    if (not options.exclude_regex_filters):
        options.exclude_regex_filters = []

    options.exclude_regex_filters += add_expr_list


def backup_home_norepo(options):
    current_user_home = os.path.expanduser('~')
    add_to_exclude_expressions(options, get_home_excludes_expressions() + ['^repos'])

    mk_squashfs_archive(current_user_home, options)


def backup_home(options):
    current_user_home = os.path.expanduser('~')
    add_to_exclude_expressions(options, get_home_excludes_expressions())

    mk_squashfs_archive(current_user_home, options)


def backup_sys_nohome(options):
    add_to_exclude_expressions(options, get_sys_excludes_expressions())
    mk_squashfs_archive('/', options)


def main():
    parser = argparse.ArgumentParser(
        description="Manage the dotfiles and configuration backups to a git repository and install the .dotfiles in new systems by symlinking"
    )

    parser.add_argument('-dry', '--dry_run', action="store_true", help="Do not commit any changes to the system, only print what would be changed")
    # parser.add_argument('-v', '--verbose', action="store_true", help="Verbose logging")
    # parser.add_argument('-d', '--debug', action="store_true", help="Debug logging")

    parser.add_argument('source_path_or_target', help="Source directory to back up - or name of the preconfigured backup target")
    parser.add_argument('-f', '--exclude_regex_filters', '--regex_filters', '--filters', nargs='+', help="Posix regular expression filters to exclude from mksquashfs")
    parser.add_argument('-b', '--backups_dir', '--target_dir', help="", default="/backups")
    parser.add_argument('-c', '--compression_level', '--compression', type=int, help="Compression level [1,22]", default=17)

    args = parser.parse_args()

    if ('/' not in args.source_path_or_target):
        target_name = args.source_path_or_target

        if (target_name == 'home_no_repo' or target_name == 'homenorepo'):
            backup_home_norepo(args)
        elif (target_name == 'home'):
            backup_home(args)
        elif (target_name == 'sys_no_home' or target_name == 'sysnohome' or target_name == 'sys'):
            backup_sys_nohome(args)

    else:
        mk_squashfs_archive(args.source_path_or_target, args)


if __name__ == '__main__':
    sys.exit(main())
