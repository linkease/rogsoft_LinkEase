#!/bin/sh
eval `dbus export linkease`
source /koolshare/scripts/base.sh

normalize_linkease_edition(){
	case "$linkease_edition" in
		standard|full|lite) echo "$linkease_edition" ;;
		*) [ "$linkease_simple" = "1" ] && echo lite || echo standard ;;
	esac
}

LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"

legacy_pid="$(pidof link-ease)"
full_pid="$(pidof linkease-full)"
DESKTOP_PORT=19290
health_url="http://127.0.0.1:19290/apps/api/v1/health"

fetch_url(){
	curl -fsS --connect-timeout 2 "$1" 2>/dev/null || wget -qO- -T 2 "$1" 2>/dev/null
}

httpd_proxy_capable(){
	[ -x /usr/sbin/httpd ] && /usr/sbin/httpd -C proxy >/dev/null 2>&1
}

httpd_proxy_running(){
	ps | grep '[h]ttpd-proxy' >/dev/null 2>&1
}

detect_apps_proxy_state(){
	linkease_httpd_proxy_backend="$(nvram get apps_port_forward 2>/dev/null)"
	linkease_httpd_proxy_capable=0
	linkease_httpd_proxy_running=0
	linkease_apps_proxy_hint=""

	if httpd_proxy_capable; then
		linkease_httpd_proxy_capable=1
	fi
	if httpd_proxy_running; then
		linkease_httpd_proxy_running=1
	fi

	if [ "$linkease_httpd_proxy_capable" != "1" ]; then
		linkease_apps_proxy_hint="当前系统 httpd 不支持 /apps/ 反向代理，已使用${DESKTOP_PORT}端口直连，建议升级系统到最新版本。"
	elif [ "$linkease_httpd_proxy_running" != "1" ]; then
		linkease_apps_proxy_hint="当前系统 httpd proxy 未运行，已使用${DESKTOP_PORT}端口直连；正在初始化 /apps/ 入口，可稍后刷新。"
	fi

	dbus set linkease_httpd_proxy_capable="$linkease_httpd_proxy_capable" >/dev/null 2>&1
	dbus set linkease_httpd_proxy_running="$linkease_httpd_proxy_running" >/dev/null 2>&1
	dbus set linkease_httpd_proxy_backend="$linkease_httpd_proxy_backend" >/dev/null 2>&1
	if [ "$linkease_httpd_proxy_running" = "1" ]; then
		dbus set linkease_apps_proxy_supported=1 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="" >/dev/null 2>&1
	else
		dbus set linkease_apps_proxy_supported=0 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="$linkease_apps_proxy_hint" >/dev/null 2>&1
	fi
}

case "$LINKEASE_ACTIVE_EDITION" in
	standard)
		if [ -n "$legacy_pid" ]; then
			http_response "LinkEase Standard 运行正常"
		else
			http_response "LinkEase Standard 未运行"
		fi
		;;
	lite)
		if [ -n "$legacy_pid" ]; then
			http_response "LinkEase Lite 运行正常"
		else
			http_response "LinkEase Lite 未运行"
		fi
		;;
	full)
		detect_apps_proxy_state
		if [ -z "$full_pid" ]; then
			http_response "LinkEase Full 未运行"
			exit 0
		fi
		if fetch_url "$health_url" >/dev/null 2>&1; then
			if [ "$linkease_httpd_proxy_running" = "1" ]; then
				status_msg="LinkEase Full 运行正常，/apps/ 入口已启动"
			elif [ "$linkease_httpd_proxy_capable" = "1" ]; then
				status_msg="LinkEase Full 运行正常，当前系统 httpd proxy 未运行，已使用19290端口直连"
			else
				status_msg="LinkEase Full 运行正常，当前系统 httpd 不支持 /apps/ 反向代理，已使用19290端口直连，建议升级系统"
			fi
		else
			status_msg="LinkEase Full 进程运行中，/apps/ 健康检查未就绪"
		fi
		http_response "$status_msg"
		;;
esac
