import re
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
        raise Exception(f"Source dir {source_dir} does not exist")

    fs_source_path_label = source_dir.replace('/', '-')

    today = date.today()
    today_date_string = today.strftime("%d-%m-%Y")

    comp_algo = "zstd"
    block_size = "256k"

    settings_string = f"c_{comp_algo}-b_{block_size}-l_{compression_lvl}"

    full_backup_name = 'squash' + fs_source_path_label + "-" + today_date_string + "-" + settings_string + '.squash.img'

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

    return cmd, target_path


def get_filter_options(filters_arg):

    if (not filters_arg):
        return []

    #cmd = ['-regex']
    cmd = ['-wildcards']

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

    backup_dir = options.backups_dir

    if (options.use_current_working_dir):
        current_directory = os.getcwd()
        backup_dir = current_directory

    if (options.sub_source_path):
        source_dir = join(source_dir, options.sub_source_path)

    backup_cmd, target_image_path = get_squash_backup_base_cmd(source_dir, backups_dir=backup_dir, compression_lvl=options.compression_level)

    target_image_name = os.path.basename(target_image_path)
    options.exclude_regex_filters.append(f".+/{str(re.escape(target_image_name))}")

    filter_options = get_filter_options(options.exclude_regex_filters)

    full_cmd_args = backup_cmd + filter_options
    full_cmd = " ".join(full_cmd_args)

    # print(full_cmd)

    print_cmd_args(full_cmd_args)
    print("\n" + full_cmd)

    if (options.dry_run):
        return None

    os.system(full_cmd)

    if (options.no_verify):
        return target_image_path

    if (not exists(target_image_path) or not verify_squashfs(target_image_path)):
        print(f"Verification of {target_image_path} failed, please check if the image is valid manually or create the archive/image again")
        return None

    print(f"Verification of {target_image_path} was successful")

    return target_image_path

# https://stackoverflow.com/questions/57304278/how-to-use-mksquashfs-regex
# https://askubuntu.com/questions/628585/mksquashfs-not-excluding-file


#Apperantly they need to be POSIX regular expressions otherwise it wont work:
#https://en.wikibooks.org/wiki/Regular_Expressions/POSIX_Basic_Regular_Expressions
def get_universal_excludes():
    return [
        '.cache',
        '... .cache',
        'cache',
        '... cache',
        'logs',
        '... logs',
        '*.log',
        '... *.log',
        'node_modules',
        '... node_modules',
        '... *.squash.img',
        #'^node\_modules',
        #'.*/node\_modules',
        #'^node_modules',
        #'.*/node_modules',
        #'.*/node_modules/.*',
        #'.+\.squash\.img',
        #'^repos/PowerMindMapReloaded/client/node_modules/.*',
        #'.*/.*/.*/node_modules/.*'
        #'.*.*.*node_modules.*.*',
        #'^repos/PowerMindMapReloaded/client/node_modules',
        #'^repos/PowerMindMapReloaded/client/node_modules/.*',
        
        #'.*repos/PowerMindMapReloaded/client/node_modules/.*',
        #'.*PowerMindMapReloaded/client/node_modules/.*',
    ]


def get_home_excludes_expressions():
    return [
        '.nvm',
        '.npm',
        '.vscode-server',
        'dist',
        '... dist',

        # Depends: contains user specific application data of snaps, can be important "application settings, profiles" or not so much "browser cache - images, cached pages, etc." for example with /snap/firefox
        # Probably there that it does not interfere with system apps on ~/.config or ~/.local or flatpak apps on ~/.var/app
        # '^snap'
        # Depends: Contains per application data for flatpak apps contains (app data, user configurations, settings , caches + temp data) this is because flatpaks are only installed for a user and not for the system therefore all app data lands in ~
        # Very similar to apps on ~/snap
        # '^\.var/apps'
    ] + get_universal_excludes()


def get_sys_excludes_expressions():
    return [
        # Contains device nodes that appear as files, however they do not really exist and are a representation of the system connected devices/device drivers, for programs to communicate with
        'dev',
        # Maily for letting programs or the system mount non permanent/removable media here (usb flash storage, drives, cdrom)
        'media',
        # Contains information about the system and its devices (can be printed out by using 'cat' on the filedescriptor), is a newer place for some stuff that historically was in /proc, also for kernel state changes, but more strictly structured than /proc
        'sys',
        # Contains the initramfs image and the bootloader, might make sense to back this up for making the squashfs image bootable or backing up the specific kernel with the system (just for data and configs however this is not needed)
        'boot',
        # Place for (partly) corrupted files to be placed if they are detected in a filsystem check run fschk
        'lost+found',
        # Place for the user to mount partitions or devices example: network shares are mounted here, or for the os, but mainly more permanent things then like internal data drives
        'mnt',
        # Provides information about running processes, kernel status, files for changing kernel states
        'proc',
        # Temporary directory for application to place data in, data is not guaranteed to persist after reboot
        'tmp',
        # Link to /var/run, containes data used by applications at runtime tmpfs in RAM #https://askubuntu.com/questions/169495/what-are-run-lock-and-run-shm-used-for
        'run',
        'var/run',
        # Related to /run, /run/lock contains lock files indicating that a shared resource is in use by a process (handling of access conflicts)
        'var/lock',
        # Package manager state backups?
        'var/backups',
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
    return get_sys_excludes_expressions() + ['home']


def add_to_exclude_expressions(options, add_expr_list):
    if (not options.exclude_regex_filters):
        options.exclude_regex_filters = []

    options.exclude_regex_filters += add_expr_list


def backup_home_norepo(options):
    current_user_home = os.path.expanduser('~')
    add_to_exclude_expressions(options, get_home_excludes_expressions() + ['repos'])

    return mk_squashfs_archive(current_user_home, options)


def backup_home(options):
    current_user_home = os.path.expanduser('~')
    add_to_exclude_expressions(options, get_home_excludes_expressions())

    return mk_squashfs_archive(current_user_home, options)


def backup_sys_nohome(options):
    add_to_exclude_expressions(options, get_sys_excludes_expressions())
    return mk_squashfs_archive('/', options)


mount_images_dir = '/mnt'
# Note that this does not work with the mksquashfs '-nopad' option, as the resulting image is not mountable


def mount_squashfs_image(image_path, label):

    if (not exists(image_path)):
        raise Exception(f"Can not mount image to system, image at path '{image_path}' does not exist")

    if (os.stat(image_path).st_size <= 0):
        raise Exception(f"Can not mount image to system, image at path '{image_path}' is empty")

    if (not label or len(label) <= 0):
        raise Exception(f"Label of mount point has to be non empty")

    mount_dir = join(mount_images_dir, label)
    # os.makedirs(mount_dir)
    # os.system(f"sudo mkdir -p {mount_dir} && sudo umount -l {mount_dir} && sudo mount {image_path} {mount_dir}")
    os.system(f"sudo mkdir -p {mount_dir} && sudo mount {image_path} {mount_dir}")
    return mount_dir


def umount_mount(mount_point):

    if (not exists(mount_point)):
        raise Exception(f"Can not unmount point at '{mount_point}' the path does not exist")

    os.system(f"sudo umount -l {mount_point}")
    os.system(f"sudo rm -d {mount_point}")


def umount_labeled(mount_label):
    mount_dir = join(mount_images_dir, mount_label)
    umount_mount(mount_dir)


def dir_tree_has_files(directory):
    if (not directory or not exists(directory)):
        return False

    print("\nFiles in image: ")
    print("\n".join(os.listdir(directory)))
    print("\n")

    for file in os.scandir(directory):
        if (isfile(file)):
            return True

    return False


def verify_squashfs(image_path):

    import uuid
    random_uuid_string = str(uuid.uuid4())
    print(random_uuid_string)

    try:
        mounted_dir_path = mount_squashfs_image(image_path, random_uuid_string)

        has_files = dir_tree_has_files(mounted_dir_path)

        if (os.stat(image_path).st_size >= 0):
            file_size = str(int(os.stat(image_path).st_size / pow(10, 3)))
            print(f"The image has a file size of {file_size}kB")

    except Exception as err:
        umount_mount(mounted_dir_path)
        raise err

    umount_mount(mounted_dir_path)

    return has_files


def main():
    parser = argparse.ArgumentParser(
        description="Create squashfs images for backing up/ archiving the data on a system"
    )

    parser.add_argument('-dry', '--dry_run', action="store_true", help="Do not commit any changes to the system, only print what would be changed")
    # parser.add_argument('-v', '--verbose', action="store_true", help="Verbose logging")
    # parser.add_argument('-d', '--debug', action="store_true", help="Debug logging")

    parser.add_argument('source_path_or_target', help="Source directory to back up - or name of the preconfigured backup target")
    parser.add_argument('-f', '--exclude_regex_filters', '--regex_filters', '--filters', nargs='+', help="Posix regular expression filters to exclude from mksquashfs")
    parser.add_argument('-b', '--backups_dir', '--target_dir', help="The directory to store the resulting squashfs images to", default="/backups")
    parser.add_argument('-cwd', '--use_current_working_dir', "--use_cwd", action="store_true", help="Use the current directory from which this script was called to store the image")
    parser.add_argument('-c', '--compression_level', '--compression', type=int, help="Compression level [1,22]", default=17)
    parser.add_argument('-nv', '--no_verify', "--skip_verify", action="store_true", help="Do not verify that the resulting image is mountable and readable after creating it")
    parser.add_argument('-sub', '--sub_source_path', '--sub_source', help="Sub path of the source path to use for making an image instead (Mainly for debugging as it can break some excludes regexp)", default=None)

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

    # return mk_squashfs_archive(join(current_user_home, 'wireguard'), options)


if __name__ == '__main__':
    sys.exit(main())
