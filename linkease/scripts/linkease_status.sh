#! /bin/sh
source /koolshare/scripts/base.sh

linkease_status=`pidof link-ease`
linkease_pid=`ps | grep -w link-ease | grep -v grep | awk '{print $1}'`
#linkease_info=`/koolshare/bin/linkease -vv`
linkease_ver=`echo ${linkease_info} | awk '{print $1}'`
linkease_rid=`echo ${linkease_info} | awk '{print $2}'`
if [ -n "$linkease_status" ];then
    http_response  "进程运行正常！版本：${linkease_ver} 路由器ID：${linkease_rid} （PID：$linkease_pid）"
else
    http_response  "【警告】：进程未运行！版本：${linkease_ver} 路由器ID：${linkease_rid}"
fi
