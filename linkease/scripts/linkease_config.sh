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
LEGACY_BIN=/koolshare/bin/link-ease
LINKEASE_ACTIVE_EDITION=

export SERVER_HOST=0.0.0.0
export SERVER_PORT=${DESKTOP_PORT}
export SERVER_MODE=release
export SERVER_BASE_PATH=/apps/
export LINKEASE_EDITION=router-lite
export KAIPLUS_ENABLED=0
KAIPLUS_PROXY_TARGET=""

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

normalize_linkease_edition(){
	case "$linkease_edition" in
		standard|full|lite)
			if [ "$linkease_edition" = "full" ] && [ "$linkease_full_supported" != "1" ]; then
				echo standard
			else
				echo "$linkease_edition"
			fi
			;;
		*) [ "$linkease_simple" = "1" ] && echo lite || echo standard ;;
	esac
}

persist_active_edition(){
	LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"
	dbus set linkease_edition="$LINKEASE_ACTIVE_EDITION" >/dev/null 2>&1
	if [ "$LINKEASE_ACTIVE_EDITION" = "lite" ]; then
		dbus set linkease_simple=1 >/dev/null 2>&1
	else
		dbus set linkease_simple=0 >/dev/null 2>&1
	fi
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
}

persist_active_edition
configure_data_paths

normalize_kaiplus_port(){
	kaiplus_port=8189
	case "$1" in
		''|*[!0-9]*) echo "$kaiplus_port"; return 0 ;;
	esac
	if [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65535 ] 2>/dev/null; then
		echo "$1"
	else
		echo "$kaiplus_port"
	fi
}

resolve_kaiplus_proxy_target(){
	KAIPLUS_PROXY_TARGET=""
	[ -x /koolshare/scripts/kaiplus_config.sh ] || return 0
	[ -x /koolshare/bin/kaiplus_bin ] || return 0

	kaiplus_port="$(dbus get kaiplus_port 2>/dev/null)"
	kaiplus_port="$(normalize_kaiplus_port "$kaiplus_port")"
	KAIPLUS_PROXY_TARGET="http://127.0.0.1:${kaiplus_port}"
	export KAIPLUS_PROXY_TARGET="${KAIPLUS_PROXY_TARGET}"
}

resolve_kaiplus_proxy_target

ensure_dirs(){
	if [ "$LINKEASE_BOOTSTRAP_FALLBACK" = "1" ]; then
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH"
	else
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH" "$LINKEASE_RECYCLE_ROOT"
	fi
}

schedule_httpd_restart(){
	(sleep 3; service restart_httpd >/dev/null 2>&1) &
}

fetch_url(){
	if command -v curl >/dev/null 2>&1; then
		curl -fsS --connect-timeout 2 "$1"
		return $?
	fi
	if command -v wget >/dev/null 2>&1; then
		wget -qO- -T 2 "$1"
		return $?
	fi
	return 1
}

ensure_apps_forward(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	if [ "$current_forward" != "$APPS_PORT_FORWARD" ]; then
		if nvram set apps_port_forward="$APPS_PORT_FORWARD" >/dev/null 2>&1 && nvram commit >/dev/null 2>&1; then
			logger "[软件中心]: 初始化LinkEase访问入口，稍后重启httpd！"
			schedule_httpd_restart
		fi
	fi
	return 0
}

verify_apps_forward(){
	apps_health_url="http://127.0.0.1/apps/api/v1/health"
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
		if fetch_url "$apps_health_url" >/dev/null 2>&1; then
			dbus set linkease_apps_proxy_supported=1 >/dev/null 2>&1
			dbus set linkease_apps_proxy_hint="" >/dev/null 2>&1
			return 0
		fi
		sleep 1
	done
	dbus set linkease_apps_proxy_supported=0 >/dev/null 2>&1
	dbus set linkease_apps_proxy_hint="当前系统 httpd 不支持 /apps/ 反向代理，已使用${DESKTOP_PORT}端口直连，建议升级系统到最新版本。" >/dev/null 2>&1
	return 0
}

start_desktop(){
	start-stop-daemon -S -q -b -m -p $DESKTOP_PID_FILE -x $DESKTOP_BIN
}

start_apptunnel(){
	start-stop-daemon -S -q -b -m -p $APPTUNNEL_PID_FILE -x $APPTUNNEL_BIN -- --deviceAddr :$APPTUNNEL_PORT --localApi $LINKEASE_LOCAL_API
}

start_standard(){
	ensure_dirs || return 1
	kill_ee
	start-stop-daemon -S -q -b -x $LEGACY_BIN
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_full(){
	ensure_dirs || return 1
	ensure_apps_forward || return 1
	kill_ee
	start_desktop
	start_apptunnel
	verify_apps_forward
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_lite(){
	export LINKEASE_SIMPLE=1
	start_standard
}

start_active_edition(){
	case "$LINKEASE_ACTIVE_EDITION" in
		standard)
			start_standard
			;;
		full)
			start_full
			;;
		lite)
			start_lite
			;;
	esac
}

kill_ee(){
	killall link-ease >/dev/null 2>&1
	killall linkease-desktop >/dev/null 2>&1
	killall apptunnel-client >/dev/null 2>&1
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
	if [ "$LINKEASE_ACTIVE_EDITION" = "full" ]; then
		iptables -t filter -I INPUT -p tcp --dport ${DESKTOP_PORT} -j ACCEPT >/dev/null 2>&1
	fi
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
		start_active_edition
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
		start_active_edition
		load_iptables
		http_response "$1"
	else
		kill_ee
		del_iptables
		http_response "$1"
	fi
	;;
esac
