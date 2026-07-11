#!/bin/sh

desktop_pid="$(pidof linkease-desktop)"
apptunnel_pid="$(pidof apptunnel-client)"
health_url="http://127.0.0.1:19290/apps/api/v1/health"

if [ -z "$desktop_pid" ] && [ -z "$apptunnel_pid" ]; then
	echo "LinkEase full 未运行"
	exit 0
fi

if [ -z "$desktop_pid" ]; then
	echo "【警告】：LinkEase full 主服务未运行，apptunnel-client 运行中"
	exit 0
fi

if [ -z "$apptunnel_pid" ]; then
	echo "【警告】：LinkEase full 主服务运行中，旧版8897入口未运行"
	exit 0
fi

if command -v curl >/dev/null 2>&1; then
	if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
		echo "LinkEase full 运行正常，/apps/ 与8897入口已启动"
	else
		echo "LinkEase full 进程运行中，/apps/ 健康检查未就绪"
	fi
else
	echo "LinkEase full 进程运行中，未找到curl，跳过/apps/健康检查"
fi
