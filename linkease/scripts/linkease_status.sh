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
desktop_pid="$(pidof linkease-desktop)"
apptunnel_pid="$(pidof apptunnel-client)"
health_url="http://127.0.0.1:19290/apps/api/v1/health"

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
		if [ -z "$desktop_pid" ] && [ -z "$apptunnel_pid" ]; then
			http_response "LinkEase Full 未运行"
			exit 0
		fi
		if [ -z "$desktop_pid" ]; then
			http_response "【警告】：LinkEase Full 主服务未运行，apptunnel-client 运行中"
			exit 0
		fi
		if [ -z "$apptunnel_pid" ]; then
			http_response "【警告】：LinkEase Full 主服务运行中，旧版8897入口未运行"
			exit 0
		fi
		if command -v curl >/dev/null 2>&1; then
			if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
				if [ "$linkease_apps_proxy_supported" = "1" ]; then
					status_msg="LinkEase Full 运行正常，/apps/ 与8897入口已启动"
				else
					status_msg="LinkEase Full 运行正常，当前系统未启用 /apps/ 反向代理，建议升级系统"
				fi
			else
				status_msg="LinkEase Full 进程运行中，/apps/ 健康检查未就绪"
			fi
		else
			status_msg="LinkEase Full 进程运行中，未找到curl，跳过/apps/健康检查"
		fi
		http_response "$status_msg"
		;;
esac
