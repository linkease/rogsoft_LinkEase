#! /bin/sh
source /koolshare/scripts/base.sh

linkease_status=`pidof link-ease`
linkease_pid=`ps | grep -w link-ease | grep -v grep | awk '{print $1}'`
linkease_info=`/koolshare/bin/link-ease simplifyInfo|awk '{print $2}'`
linkease_ver=`echo ${linkease_info} | awk 'NR==3'`
linkease_simple=`echo ${linkease_info} | awk 'NR==1'`
if [ "$linkease_simple" = "YES" ]; then
  linkease_msg="精简版"
else
  linkease_msg="完整版"
fi
if [ -n "$linkease_status" ];then
    http_response  "进程运行正常！是${linkease_msg}，版本号：${linkease_ver}（PID：${linkease_pid}）"
else
    http_response  "【警告】：进程未运行！版本：${linkease_ver}"
fi
