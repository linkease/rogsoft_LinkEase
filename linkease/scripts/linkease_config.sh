#!/bin/sh
eval `dbus export linkease`
eval `dbus export betterapps`
source /koolshare/scripts/base.sh
alias echo_date='echo $(date +%Y年%m月%d日\ %X):'

FULL_BIN=/koolshare/bin/linkease-full
FULL_PID_FILE=/var/run/linkease-full.pid
FULL_MIN_MEM_KB=900000
DESKTOP_PORT=19290
APP_DIR=/koolshare/linkease
APPS_PORT_FORWARD="http://127.0.0.1:${DESKTOP_PORT}"
LEGACY_BIN=/koolshare/bin/link-ease
LINKEASE_ACTIVE_EDITION=

export SERVER_HOST=0.0.0.0
export SERVER_PORT=${DESKTOP_PORT}
export SERVER_MODE=release
export SERVER_BASE_PATH=/apps/
export LINKEASE_EDITION=nas-full
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

is_usb_jffs_running(){
	local resolved_jffs
	resolved_jffs="$(readlink -f /jffs 2>/dev/null)"
	case "$resolved_jffs" in
		/tmp/mnt/*|/mnt/*|/media/*)
			return 0
			;;
	esac

	awk '$2 == "/jffs" { print $1 }' /proc/mounts 2>/dev/null | tail -n 1 | grep -Eq '^(/dev/sd|/dev/mapper/|/tmp/mnt/|/mnt/|/media/)'
}

usb2jffs_is_enabled(){
	[ "$(dbus get usb2jffs_enable 2>/dev/null)" = "1" ] && return 0
	[ "$(dbus get usb2jffs_mount 2>/dev/null)" = "1" ] && return 0
	is_usb_jffs_running
}

detect_usb2jffs_ready(){
	if usb2jffs_is_enabled && is_usb_jffs_running; then
		linkease_usb2jffs_ready=1
		dbus set linkease_usb2jffs_ready=1 >/dev/null 2>&1
		dbus set linkease_usb2jffs_hint="" >/dev/null 2>&1
		return 0
	fi

	linkease_usb2jffs_ready=0
	dbus set linkease_usb2jffs_ready=0 >/dev/null 2>&1
	dbus set linkease_usb2jffs_hint="LinkEase Full 需要开启并启用 usb2jffs 后使用。" >/dev/null 2>&1
	return 1
}

mem_total_kb(){
	awk '/^MemTotal:/ { print $2; exit }' /proc/meminfo 2>/dev/null
}

full_memory_ready(){
	local mem_kb
	mem_kb="$(mem_total_kb)"
	[ -n "$mem_kb" ] && [ "$mem_kb" -ge "$FULL_MIN_MEM_KB" ] 2>/dev/null
}

default_standard_gomemlimit(){
	local mem_kb
	mem_kb="$(mem_total_kb)"
	case "$mem_kb" in
		''|*[!0-9]*) echo 128MiB; return 0 ;;
	esac
	if [ "$mem_kb" -le 524288 ] 2>/dev/null; then
		echo 128MiB
	elif [ "$mem_kb" -le 1048576 ] 2>/dev/null; then
		echo 192MiB
	else
		echo 384MiB
	fi
}

default_full_gomemlimit(){
	local mem_kb
	mem_kb="$(mem_total_kb)"
	case "$mem_kb" in
		''|*[!0-9]*) echo 256MiB; return 0 ;;
	esac
	if [ "$mem_kb" -le 1048576 ] 2>/dev/null; then
		echo 256MiB
	else
		echo 384MiB
	fi
}

apply_go_memory_limits(){
	if [ "$LINKEASE_ACTIVE_EDITION" = "full" ]; then
		export GOMEMLIMIT="${linkease_full_gomemlimit:-$(default_full_gomemlimit)}"
	else
		export GOMEMLIMIT="${linkease_gomemlimit:-$(default_standard_gomemlimit)}"
	fi
	export GOGC="${linkease_gogc:-50}"
}

detect_full_runtime_support(){
	local ARCH
	ARCH=$(uname -m)
	case "${ARCH}" in
		arm*|aarch64|arm64)
			if ! full_memory_ready; then
				linkease_full_supported=0
				dbus set linkease_full_supported=0 >/dev/null 2>&1
				dbus set linkease_full_support_hint="LinkEase Full 需要 1GB 以上内存，当前设备可继续使用标准版。" >/dev/null 2>&1
			elif detect_usb2jffs_ready; then
				linkease_full_supported=1
				dbus set linkease_full_supported=1 >/dev/null 2>&1
				dbus set linkease_full_support_hint="" >/dev/null 2>&1
			else
				linkease_full_supported=0
				dbus set linkease_full_supported=0 >/dev/null 2>&1
				dbus set linkease_full_support_hint="LinkEase Full 需要开启并启用 usb2jffs 后使用。" >/dev/null 2>&1
			fi
			;;
		*)
			linkease_usb2jffs_ready=0
			linkease_full_supported=0
			dbus set linkease_usb2jffs_ready=0 >/dev/null 2>&1
			dbus set linkease_full_supported=0 >/dev/null 2>&1
			dbus set linkease_full_support_hint="LinkEase Full 支持 ARM32/ARM64，当前设备可继续使用标准版，或单独安装 LinkEaseLite。" >/dev/null 2>&1
			;;
	esac
}

normalize_linkease_edition(){
	case "$linkease_edition" in
		standard|full)
			if [ "$linkease_edition" = "full" ] && [ "$linkease_full_supported" != "1" ]; then
				echo standard
			else
				echo "$linkease_edition"
			fi
			;;
		*) echo standard ;;
	esac
}

persist_active_edition(){
	LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"
	dbus set linkease_edition="$LINKEASE_ACTIVE_EDITION" >/dev/null 2>&1
	dbus set linkease_simple=0 >/dev/null 2>&1
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

detect_full_runtime_support
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
	curl -fsS --connect-timeout 2 "$1" 2>/dev/null || wget -qO- -T 2 "$1" 2>/dev/null
}

httpd_proxy_capable(){
	[ -x /usr/sbin/httpd ] && /usr/sbin/httpd -C proxy >/dev/null 2>&1
}

httpd_proxy_running(){
	ps | grep '[h]ttpd-proxy' >/dev/null 2>&1
}

set_apps_proxy_state(){
	proxy_capable="$1"
	proxy_running="$2"
	proxy_backend="$3"
	proxy_hint="$4"

	dbus set linkease_httpd_proxy_capable="$proxy_capable" >/dev/null 2>&1
	dbus set linkease_httpd_proxy_running="$proxy_running" >/dev/null 2>&1
	dbus set linkease_httpd_proxy_backend="$proxy_backend" >/dev/null 2>&1
	if [ "$proxy_running" = "1" ]; then
		dbus set linkease_apps_proxy_supported=1 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="" >/dev/null 2>&1
	else
		dbus set linkease_apps_proxy_supported=0 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="$proxy_hint" >/dev/null 2>&1
	fi
}

detect_apps_proxy_state(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	proxy_backend="$current_forward"
	proxy_capable=0
	proxy_running=0
	proxy_hint=""

	if httpd_proxy_capable; then
		proxy_capable=1
	fi
	if httpd_proxy_running; then
		proxy_running=1
	fi

	if [ "$proxy_capable" != "1" ]; then
		proxy_hint="当前系统 httpd 不支持 /apps/ 反向代理，已使用${DESKTOP_PORT}端口直连，建议升级系统到最新版本。"
	elif [ "$proxy_running" != "1" ]; then
		proxy_hint="当前系统 httpd proxy 未运行，已使用${DESKTOP_PORT}端口直连；正在初始化 /apps/ 入口，可稍后刷新。"
	fi

	set_apps_proxy_state "$proxy_capable" "$proxy_running" "$proxy_backend" "$proxy_hint"
}

wait_httpd_proxy_running(){
	for i in 1 2 3 4 5 6 7 8 9 10; do
		httpd_proxy_running && return 0
		sleep 1
	done
	return 1
}

ensure_apps_forward(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	if ! httpd_proxy_capable; then
		detect_apps_proxy_state
		return 0
	fi

	if [ "$current_forward" != "$APPS_PORT_FORWARD" ]; then
		if nvram set apps_port_forward="$APPS_PORT_FORWARD" >/dev/null 2>&1 && nvram commit >/dev/null 2>&1; then
			logger "[软件中心]: 初始化LinkEase访问入口，稍后重启httpd！"
			schedule_httpd_restart
		fi
	elif ! httpd_proxy_running; then
		logger "[软件中心]: LinkEase /apps/反向代理未运行，稍后重启httpd！"
		schedule_httpd_restart
	fi

	wait_httpd_proxy_running >/dev/null 2>&1
	detect_apps_proxy_state
	return 0
}

start_full_binary(){
	start-stop-daemon -S -q -b -m -p $FULL_PID_FILE -x $FULL_BIN
}

stop_linkeaselite_runtime(){
	killall linkease-lite >/dev/null 2>&1
	dbus set linkeaselite_enable=0 >/dev/null 2>&1
}

start_standard(){
	ensure_dirs || return 1
	kill_ee
	stop_linkeaselite_runtime
	apply_go_memory_limits
	ulimit -v unlimited 2>/dev/null || true
	start-stop-daemon -S -q -b -x $LEGACY_BIN
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_full(){
	ensure_dirs || return 1
	ensure_apps_forward || return 1
	kill_ee
	stop_linkeaselite_runtime
	apply_go_memory_limits
	ulimit -v unlimited 2>/dev/null || true
	start_full_binary
	detect_apps_proxy_state
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_active_edition(){
	case "$LINKEASE_ACTIVE_EDITION" in
		standard)
			start_standard
			;;
		full)
			start_full
			;;
	esac
}

kill_ee(){
	killall link-ease >/dev/null 2>&1
	killall linkease-full >/dev/null 2>&1
	killall linkease-desktop >/dev/null 2>&1
	killall apptunnel-client >/dev/null 2>&1
	rm -f $FULL_PID_FILE /var/run/linkease-desktop.pid /var/run/linkease-apptunnel.pid >/dev/null 2>&1
}

clean_iptables_port(){
	while iptables -D INPUT -p tcp --dport $1 -j ACCEPT >/dev/null 2>&1; do
		:
	done
}

load_iptables(){
	clean_iptables_port ${DESKTOP_PORT}
	if [ "$LINKEASE_ACTIVE_EDITION" = "full" ]; then
		iptables -t filter -I INPUT -p tcp --dport ${DESKTOP_PORT} -j ACCEPT >/dev/null 2>&1
	fi
}

del_iptables(){
	clean_iptables_port ${DESKTOP_PORT}
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
