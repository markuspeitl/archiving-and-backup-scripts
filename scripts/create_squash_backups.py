import re
import os
from os.path import isdir, isfile, exists, expanduser, join
from datetime import date
import argparse
import sys

# target_dir = "/backups"
mount_images_dir = '/mnt'

def get_squash_backup_base_cmd(source_dir, backups_dir=None, compression_lvl=17, label_prefix=""):

    if (not backups_dir):
        backups_dir = "/backups"

    if (backups_dir and not exists(backups_dir)):
        os.makedirs(backups_dir, exist_ok=True)

    if (not exists(source_dir)):
        raise Exception(f"Source dir {source_dir} does not exist")


    fs_source_path_label = source_dir.replace('/', '-')
    if(source_dir.strip() == "/"):
        fs_source_path_label = "system"

    if(label_prefix != ""):
        label_prefix = label_prefix +  '__'


    today = date.today()
    today_date_string = today.strftime("%d-%m-%Y")

    comp_algo = "zstd"
    block_size = "256k"

    settings_string = f"c_{comp_algo}-b_{block_size}-l_{compression_lvl}"

    full_backup_name = label_prefix + fs_source_path_label + "-" + today_date_string + "-" + settings_string + '.squash.img'

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

    backup_cmd, target_image_path = get_squash_backup_base_cmd(source_dir, backups_dir=backup_dir, compression_lvl=options.compression_level, label_prefix=options.label_prefix)

    target_image_name = os.path.basename(target_image_path)
    options.exclude_regex_filters.append(f"... {str(target_image_name)}")

    filter_options = get_filter_options(options.exclude_regex_filters)

    full_cmd_args = backup_cmd + filter_options
    full_cmd = " ".join(full_cmd_args)

    # print(full_cmd)

    print_cmd_args(full_cmd_args)
    print("\n" + full_cmd)

    if (options.dry_run):
        return None

    os.system(full_cmd)

    print("Ran command:")
    print("\n" + full_cmd)

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
        #NO BACKUP
        
        # Contains device nodes that appear as files, however they do not really exist and are a representation of the system connected devices/device drivers, for programs to communicate with
        'dev',
        # Maily for letting programs or the system mount non permanent/removable media here (usb flash storage, drives, cdrom)
        'media',
        # Contains information about the system and its devices (can be printed out by using 'cat' on the filedescriptor), is a newer place for some stuff that historically was in /proc, also for kernel state changes, but more strictly structured than /proc
        'sys',
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
        # Temporary files
        'var/tmp',
        
        #POSSIBLE BACKUP

        # Contains the initramfs image and the bootloader, might make sense to back this up for making the squashfs image bootable or backing up the specific kernel with the system (just for data and configs however this is not needed)
        'boot',
        # Package manager state backups?
        'var/backups',
        # Temporary cache files of applications (usually keeping something on disk so it does not need to be downloaded checked every time)
        'var/cache',
        # Application logs - can get quite big (might be useful to back up on really critical servers for the sake of analysis and security)
        'var/log',
        'var/logs',
        # variable state data that should persist (might make sense to back up when trying to run backed up applications)
        #'var/lib',
        # Data thats awaiting processing (printer queue, pending cronjobs), outgoing mail
        'var/spool'

    ] + get_universal_excludes()

def get_sys_data_excludes():
    return [
        #System wide installed applications, binaries, libraries, headers - Can be restored by reinstalling with package manager
        'usr/bin',
        'usr/lib',
        'usr/lib64',
        'usr/libx32',
        'usr/sbin',
        'usr/src',
        'usr/games',
        'usr/include',
        'usr/lib32',
        'usr/libexec',
        'usr/share',
        # Links to /usr
        'bin',
        'lib',
        'lib64',
        'libx32',
        'sbin',
        'lib32',
        #The actual .snap packages that represent a readlonly filesystem that is mounted to system when using (and application the gets a chroot/pivotroot for that mount) -- Can be restored deterministically when pinning version
        'var/lib/snapd/snaps',
        'var/lib/snapd',
        #Where the snaps are actually mounted into the system (they are mounted reasonly so the snap has to store its data elsewhere /var/snap for variable system wide data /home/user/snap for user specific data )
        'snap',
        #optional
        'usr/local',
        # User data ~/.var/app, flatpak iself conf ~/.local/share/flatpak, system-wide configuration are somewhere in var/lib/flatpak
        # For flatpaks it really depends as apart from userdata everything is in one place (but there are also system configurations)
        # Example in /var/lib/flatpak/app/com.vscodium.codium/.../files there is a /bin and /lib dir for the application execution -> then there is also /etc holding system wide conf -> then there is /share where i do not know if it is supposed to represent /usr/share or more like /var/lib
        'var/lib/flatpak',
        'var/lib/apt',
        'var/lib/dpkg',
        'var/lib/dkms',
        # Docker containers are supposed to hold not persistent changeable data themselves and images should be stored somewhere else (dockerhub, built with dockerfile)
        'var/lib/docker/!(*volumes*)',
    ]

def get_home_data_excludes():
    return [
        'AppImage',
        #'apps',
        'apps/REAPER',
        #Really nice build of obs with good plugins and stuff
        #Don't exclude config directory as it contains obs profiles and scenes
        'apps/obs_portable_29_1_3/!(*config*)',
        'apps/Godot_v4_0_2',
        '.cache',
        '.conda',
        '.condarc',
        '.dbus',
        '.deno',
        '.dmrc',
        '.dotfiles_manager_backup',
        '.dotnet',
        '.fonts.conf',
        '.gem',
        '.gnome',
        '.java',
        '.lesshst',
        '.log',
        'lost+found',
        'lowerbind',
        #Python virtual environments should not be permanenet (easy to recreate with file)
        'miniconda3',
        '.mono',
        '.muse-hub'
        '.npm',
        'nuget',
        '.nv',
        '.nvm',
        '.omnisharp',
        'Paradox Interactive_work',
        '.pki',
        '.plastic4',
        '.shutter',
        '.ssr',
        '.toguaudioline',
        #Probably only hub and editor not projects
        'Unity',
        '.zynaddsubfx-bank-cache.xml',
        '.zcompdump*',
        '.xsession-errors*',
        '.Xauthority',
        #Mostly just extensions (can be easily restored from settings sync)
        '.vscode',
        '.vscode-oss',
        #Same as with other stuff that stores data with the binaries, if it took some time to craft and optimize back up
        #Note that saves and app configurations are stored withing the wine prefixes (so depending on what is done with wine this can be backed up)
        '.wine',
        #Probably rendered proxies from Davinci Resolve
        'Videos/CacheClip',
        #Files for testing what type of files can be imported under linux (which is not many)
        'Videos/capability-test-files',
        'Videos/Resolve Project Backups',
        #Repos should always be stored on git repository (and data somewhere where it is backed up)
        'repos'
        #I guess digikam photo organization or something like that
        'Pictures/*db',
        '.nvidia-settings-rc',
        #For now as there is only one dir under it right now
        'Music',
        'Games',
        #Locations of davinci resolve seem to be just bad ports from windows
        'Documents/BlackmagicDesign',
        'recordingprojects',
        #There should be nothing but temporary files in Downloads, if not then it is time to organize
        'Downloads',
        #The problem with Vcode ist that it or its extensions use the .config directory for all data (apart from the extensions under ~)
        '.config/Code/Cache*',
        '.config/Code/Crash*',
        '.config/Code/Service Worker',
        '.config/Code/User/workspaceStorage',
        '.config/Code/User/globalStorage',
        '.config/Code/User/History',
        #This is already well backed up
        '.config/joplin-desktop',
        #Plugins and reaper config stored here
        #~/.config/REAPER,
        #Probably the wrong location to place saves
        # Interesting with native version of .steam, rimworld (linux native) is located at ~/.steam/debian-installation/steamapps/common/RimWorld/
        # However the Saves, the mods and the mod configurations are at "~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios"
        # Another one of these situation where you do not want ".config/unity3d/Ludeon Studio" in your main backup, but still to have it
        # as it takes effort to configure mods together so they are compatible
        '.config/unity3d/cache',
        '.config/unity3d/Ludeon Studios',
        #'.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios/Saves',
        '.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios/Saves',
        'temp-south-america-presentation',
        #Trash bin
        '.local/share/Trash',
        #File indexer cache
        '.local/share/baloo',
        #qtwebengine browser cache of qutebrowser (dir however also contains browsing history, which is useful to back up when moving to a new desktop machine)
        '.local/share/qutebrowser/webengine'
        #Synthesizer
        '.local/share/vital',
        '.local/share/gem',
        #Contains flatpaks that were installed for the local user (instead of system /var/lib/flatpak)
        '.local/share/flatpak',
        #Applications/binaries/libs installed for user (some binaries for local python packages land here, and other things like that)
        '.local/bin',
        '.local/lib',
        # It generally user specific flatpak application data that lands in .var/app
        # For browser this can be data for installed extensions
        '.var/app/com.valvesoftware.Steam'
        '.var/app/com.github.micahflee.torbrowser-launcher'
        #I do not have any particular wine settings
        '.var/app/org.winehq.Wine'
        '.var/app/net.lutris.Lutris'
        '.var/app/net.supertuxkart.SuperTuxKart'
        #Unless this is the main browser than it might make sense
        '.var/app/org.mozilla.firefox'
        

    ]

#.var, snap, .steam

#- Videos: -> Backup Videos (and Videos of Downloads)
#- Pictures: (Currently not very big so fine to back up with other stuff)
#- ~/Music/sound-of-light: Should have one backup somewhere -- only one (music best stored somewhere from where it can be redownloaded unless it is your own or you carefully curated a playlist)
#- ~/Games/starsector: although this should not be in the main backup there should be a copy somewhere as it took a bit of work to configure all the mods
#the same with Rimwold at??
# - recordingprojects: NEEDS SOME BACKUP: Definetely its own backup (probably best to do a backup for large media files/ or media projects in general)
# - temp-south-america-presentation NEEDS SOME BACKUP: if not already backed up

# ~/.local/share/DaVinciResolve seems to contain actual configs and settings of resolve (while not placing anything in the actual config dir .config)


#.config: dirs that are bigger than 10MB do something wrong


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
    add_to_exclude_expressions(options, get_sys_excludes_expressions() + ['home'])
    return mk_squashfs_archive('/', options)


def backup_sys_data_nohome(options):
    add_to_exclude_expressions(options, get_sys_excludes_expressions() + get_sys_data_excludes() + ['home'])
    return mk_squashfs_archive('/', options)

def create_data_backups(options):
    #1. Create one data backup for each user (back up configuration/setting files and user data, but no application binaries, libs or runtime data)

    #2. Create sys backup mainly for /etc, /srv, /usr/local/share, /usr/local/etc , maybe usr/local + a dpkg list + flatpak list + snap list
    # Optional: /usr/local -> libs and binaries built by sysadmin (not from dist pkg manager), usr/local/share, usr/share (readonly) (architecture-independent shareable text files)
    #https://www.ibm.com/docs/en/aix/7.1?topic=tree-usrshare-directory
    print("test")
    #Data backup for sys:
        # etc - system wide configurations (important) - bootloader conf, sshd conf, firewall, device mount locations (fstab)
        # /var/snap - proably not important but to be on the safe side, containes runtime persistant variable state data for snaps
        # /var/mail
        # /var/ -- databases if they are stored here somewhere, basically any data written by an application that does not go into a used specific dir, lands here
        # /var/logs -- if logs have any significance in this case
        
        # no /usr/ or /usr/local
        # no /usr/share, /usr/local/share (data that is readonly and shareable between architectures) --> would be just the same when reinstalling the application again (.desktop files, etc.) (static files not dependant on arch like ARM, x86, .etc)
        # no /usr/{bin, lib, games, include, src, etc.} mainly executables, binaries, libraries and headers sources, but can be installed again via package manager
        # /usr/local is the only location in /usr/ which would make sense to back up, only if it contains an application that is difficult to build and configure (then maybe)
        # /boot similar to /usr/local if there is a custom build kernel or initramfs on there, however usually this is managed by the package manager, and some bootloaders grub2 store their configuration in /etc/ which makes this directory easily rebuildable on a common distro
        # no root - unless changed in any way by sysadmin
        # /snap might have some data??
        # /var for the most part this is persistant runtime applications data - only really useful when trying to restore an application to that state, by copying (without going through the package manager)

target_mapper = {
    'home_no_repo': backup_home_norepo,
    'homenorepo': backup_home_norepo,
    'home': backup_home,
    'sys_no_home': backup_sys_nohome,
    'sysnohome': backup_sys_nohome,
    'sys_data_no_home': backup_sys_data_nohome,
    'sysdatanohome': backup_sys_data_nohome
}

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

    print(f"sudo mount {image_path} {mount_dir}")
    os.system(f"sudo mkdir -p {mount_dir} && sudo mount {image_path} {mount_dir}")

    os.system(f"du -h -d 1 {mount_dir}")

    return mount_dir


def umount_mount(mount_point):

    if (not exists(mount_point)):
        raise Exception(f"Can not unmount point at '{mount_point}' the path does not exist")

    print(f"sudo umount -l {mount_point}")
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
    parser.add_argument('-pre', '--label_prefix', help="Label prefix for the resulting file (is set automatically to target)", default="")

    args = parser.parse_args()

    if ('/' not in args.source_path_or_target):
        target_name = args.source_path_or_target

        if(target_name in target_mapper):
            args.label_prefix = target_name
            target_mapper[target_name](args)
    else:
        mk_squashfs_archive(args.source_path_or_target, args)

    # return mk_squashfs_archive(join(current_user_home, 'wireguard'), options)


if __name__ == '__main__':
    sys.exit(main())
