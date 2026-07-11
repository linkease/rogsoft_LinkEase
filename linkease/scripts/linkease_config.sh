#!/bin/sh
eval `dbus export linkease`
eval `dbus export betterapps`
source /koolshare/scripts/base.sh
alias echo_date='echo $(date +%Y年%m月%d日\ %X):'

DESKTOP_BIN=/koolshare/bin/linkease-desktop
APPTUNNEL_BIN=/koolshare/bin/apptunnel-client
DESKTOP_PID_FILE=/var/run/linkease-desktop.pid
APPTUNNEL_PID_FILE=/var/run/linkease-apptunnel.pid
DESKTOP_PORT=19290
APPTUNNEL_PORT=8897
LINKEASE_LOCAL_API=/var/run/linkease.sock
APP_DIR=/koolshare/linkease
APPS_PORT_FORWARD="http://127.0.0.1:${DESKTOP_PORT}"

export SERVER_HOST=0.0.0.0
export SERVER_PORT=${DESKTOP_PORT}
export SERVER_MODE=release
export SERVER_BASE_PATH=/apps/
export LINKEASE_EDITION=router-lite
export KAIPLUS_ENABLED=1
export KAIPLUS_BIN=${APP_DIR}/kaiplus/bin/kaiplus_bin
export KAIPLUS_STATIC_DIR=${APP_DIR}/kaiplus/www
export KAIPLUS_DEFAULTS_DIR=${APP_DIR}/kaiplus/defaults
export KAIPLUS_SYSTEM_ROLE=asusgo
export KAIPLUS_BASE_PATH=/apps/kaiplus/
export KAIPLUS_ADDR=127.0.0.1:19291
export KAIPLUS_PROXY_TARGET=http://127.0.0.1:19291
export KAIPLUS_WORKSPACE_TOOL_BINARY=${APP_DIR}/kaiplus/helpers/kaiplus_workspace_tool
export KAIPLUS_WORKSPACE_TOOL_INSTALL_DIR=${APP_DIR}/kaiplus/helpers
export REASONIX_CREDENTIALS_STORE=file

read_persisted_data_disk(){
	persisted_config=${APP_DIR}/data/bootstrap/system/data-root.json
	[ -f "$persisted_config" ] || return 0
	persisted_data_disk="$(sed -n 's/.*"selectedDisk"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$persisted_config" | head -n 1)"
	if [ -n "$persisted_data_disk" ] && [ -d "$persisted_data_disk" ]; then
		resolved_data_disk="$persisted_data_disk"
	fi
}

persist_migrated_betterapps_disk(){
	[ -n "$resolved_data_disk" ] || return 0
	[ -n "$migrated_from_betterapps" ] || return 0
	[ -n "$linkease_data_disk" ] && return 0
	dbus set linkease_data_disk="$resolved_data_disk" >/dev/null 2>&1
}

resolve_linkease_data_disk(){
	resolved_data_disk=""
	migrated_from_betterapps=""

	if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then
		resolved_data_disk="$linkease_data_disk"
		return 0
	fi

	if [ -n "$linkease_data_root_parent" ] && [ -d "$linkease_data_root_parent" ]; then
		resolved_data_disk="$linkease_data_root_parent"
		return 0
	fi

	case "$linkease_data_root" in
	*/.linkease_data)
		resolved_data_disk="${linkease_data_root%/.linkease_data}"
		if [ -n "$resolved_data_disk" ] && [ -d "$resolved_data_disk" ]; then
			return 0
		fi
		resolved_data_disk=""
		;;
	esac

	if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then
		resolved_data_disk="$betterapps_data_disk"
		migrated_from_betterapps=1
		return 0
	fi

	if [ -n "$betterapps_data_root_parent" ] && [ -d "$betterapps_data_root_parent" ]; then
		resolved_data_disk="$betterapps_data_root_parent"
		migrated_from_betterapps=1
		return 0
	fi

	case "$betterapps_data_root" in
	*/.linkease_data)
		resolved_data_disk="${betterapps_data_root%/.linkease_data}"
		if [ -n "$resolved_data_disk" ] && [ -d "$resolved_data_disk" ]; then
			migrated_from_betterapps=1
			return 0
		fi
		resolved_data_disk=""
		;;
	esac

	read_persisted_data_disk
	return 0
}

configure_data_paths(){
	resolve_linkease_data_disk
	persist_migrated_betterapps_disk

	if [ -n "$resolved_data_disk" ]; then
		export LINKEASE_BOOTSTRAP_FALLBACK=0
		export LINKEASE_DATA_DISK="$resolved_data_disk"
		export LINKEASE_DATA_ROOT=${LINKEASE_DATA_DISK}/.linkease_data
		export LINKEASE_RECYCLE_ROOT=${LINKEASE_DATA_DISK}/.linkease_recycle
	else
		export LINKEASE_BOOTSTRAP_FALLBACK=1
		export LINKEASE_DATA_DISK=
		export LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap
		export LINKEASE_RECYCLE_ROOT=
	fi

	export USER_DATA_PATH=${LINKEASE_DATA_ROOT}/users/admin
	export SYSTEM_DATA_PATH=${LINKEASE_DATA_ROOT}/system
	export TEMP_PATH=${LINKEASE_DATA_ROOT}/tmp
	export KAIPLUS_HOME=${LINKEASE_DATA_ROOT}/kaiplus
}

configure_data_paths

ensure_dirs(){
	if [ "$LINKEASE_BOOTSTRAP_FALLBACK" = "1" ]; then
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH" "$KAIPLUS_HOME"
	else
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH" "$KAIPLUS_HOME" "$LINKEASE_RECYCLE_ROOT"
	fi
}

schedule_httpd_restart(){
	(sleep 3; service restart_httpd >/dev/null 2>&1) &
}

ensure_apps_forward(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	[ "$current_forward" = "$APPS_PORT_FORWARD" ] && return 0
	nvram set apps_port_forward="$APPS_PORT_FORWARD" >/dev/null 2>&1 || return 1
	nvram commit >/dev/null 2>&1 || return 1
	logger "[软件中心]: 初始化LinkEase访问入口，稍后重启httpd！"
	schedule_httpd_restart
}

start_desktop(){
	start-stop-daemon -S -q -b -m -p $DESKTOP_PID_FILE -x $DESKTOP_BIN
}

start_apptunnel(){
	start-stop-daemon -S -q -b -m -p $APPTUNNEL_PID_FILE -x $APPTUNNEL_BIN -- --deviceAddr :$APPTUNNEL_PORT --localApi $LINKEASE_LOCAL_API
}

start_ee(){
	ensure_dirs || return 1
	ensure_apps_forward || return 1
	kill_ee
	start_desktop
	start_apptunnel
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

kill_ee(){
	killall link-ease >/dev/null 2>&1
	killall linkease-desktop >/dev/null 2>&1
	killall apptunnel-client >/dev/null 2>&1
	killall kaiplus_bin >/dev/null 2>&1
	rm -f $DESKTOP_PID_FILE $APPTUNNEL_PID_FILE >/dev/null 2>&1
}

clean_iptables_port(){
	while iptables -D INPUT -p tcp --dport $1 -j ACCEPT >/dev/null 2>&1; do
		:
	done
}

load_iptables(){
	clean_iptables_port ${DESKTOP_PORT}
	clean_iptables_port ${APPTUNNEL_PORT}
	iptables -t filter -I INPUT -p tcp --dport ${DESKTOP_PORT} -j ACCEPT >/dev/null 2>&1
	iptables -t filter -I INPUT -p tcp --dport ${APPTUNNEL_PORT} -j ACCEPT >/dev/null 2>&1
}

del_iptables(){
	clean_iptables_port ${DESKTOP_PORT}
	clean_iptables_port ${APPTUNNEL_PORT}
}

#=========================================================
case $ACTION in
start)
	if [ "$linkease_enable" == "1" ];then
		logger "[软件中心]: 启动LinkEase插件！"
		kill_ee
		start_ee
		load_iptables
	else
		logger "[软件中心]: LinkEase插件未开启，不启动！"
	fi
	;;
start_nat)
	load_iptables
	;;
*)
	if [ "$linkease_enable" == "1" ];then
		kill_ee
		start_ee
		load_iptables
		http_response "$1"
	else
		kill_ee
		del_iptables
		http_response "$1"
	fi
	;;
esac
