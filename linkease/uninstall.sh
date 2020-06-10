#!/bin/sh
eval `dbus export linkease_`
source /koolshare/scripts/base.sh

cd /tmp
killall	link-ease > /dev/null 2>&1

rm -rf /koolshare/init.d/*linkease.sh
rm -rf /koolshare/bin/link-ease
rm -rf /koolshare/res/icon-linkease.png
rm -rf /koolshare/scripts/linkease*.sh
rm -rf /koolshare/webs/Module_linkease.asp
rm -rf /koolshare/scripts/uninstall_linkease.sh
rm -rf /tmp/linkease*
