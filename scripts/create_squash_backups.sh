#!/usr/bin/env bash

get_squash_backup_base(){
	SOURCE_DIR="$1"
	TARGET_DIR="/backups"
	
	if [ -z "$SOURCE_DIR" ]; then
		SOURCE_DIR="$HOME"
	fi
	
	DAY_TODAY=$(date +"%d-%m-%Y")
	TARGET_LABEL=$(echo $SOURCE_DIR | sed "s+/+-+g")
	
	printf "%s %s %s %s %s %s %s %s %s" \
	"sudo mksquashfs" \
	"\"$SOURCE_DIR\"" \
	"\"$TARGET_DIR/msrv$TARGET_LABEL-$DAY_TODAY.img\"" \
	"-comp zstd" \
	"-Xcompression-level 17" \
	"-b 256k" \
	"-mem 1200M" \
	"-info -progress" \
	"-noappend"
}

#home_norepo_excludes(){

backup_home_norepo(){
	#TARGET_HOME="$1"
	TARGET_DIR="/backups"
	
	BASE_CK_CMD=$(get_squash_backup_base "$1")
	
    cd "$1"

	eval "$BASE_CK_CMD" \
	-wildcards \
    -e '... common'
}

#-e 'firefox' \
#-e 'chromium' \

export get_squash_backup_base
export backup_home_norepo

: "
eval \"$BASE_CK_CMD\" \
	-wildcards \
	-e '.cache' \
	-e '.nvm' \
	-e '.npm' \
	-e '.vscode-server' \
	-e 'repos' \
	-e '\.\.\. logs/\*' \
	-e '\.\.\. .cache/\*' \
    -e '\*.img'
"