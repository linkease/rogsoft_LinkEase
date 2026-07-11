#!/bin/sh
source /koolshare/scripts/base.sh

cd /tmp
killall link-ease > /dev/null 2>&1
killall linkease-desktop > /dev/null 2>&1
killall apptunnel-client > /dev/null 2>&1
killall kaiplus_bin > /dev/null 2>&1

rm -rf /koolshare/init.d/*linkease.sh
rm -rf /koolshare/init.d/*LinkEase.sh
rm -rf /koolshare/bin/link-ease
rm -rf /koolshare/bin/linkease-desktop
rm -rf /koolshare/bin/apptunnel-client
rm -rf /koolshare/bin/linkease-plugins
rm -rf /koolshare/bin/linkease-media
rm -rf /koolshare/bin/heif-converter
rm -rf /koolshare/linkease
rm -rf /koolshare/res/icon-linkease.png
rm -rf /koolshare/res/icon-LinkEase.png
rm -rf /koolshare/scripts/linkease*.sh
rm -rf /koolshare/scripts/LinkEase*.sh
rm -rf /koolshare/webs/Module_linkease.asp
rm -rf /koolshare/webs/Module_LinkEase.asp
rm -rf /koolshare/scripts/uninstall_linkease.sh
rm -rf /koolshare/scripts/uninstall_LinkEase.sh
rm -rf /tmp/linkease*
rm -rf /tmp/LinkEase*

rm -rf /koolshare/init.d/*betterapps.sh
rm -rf /koolshare/init.d/*BetterApps.sh
rm -rf /koolshare/bin/betterapps
rm -rf /koolshare/bin/BetterApps
rm -rf /koolshare/bin/betterapps-plugins
rm -rf /koolshare/bin/BetterApps-plugins
rm -rf /koolshare/betterapps
rm -rf /koolshare/res/icon-betterapps.png
rm -rf /koolshare/res/icon-BetterApps.png
rm -rf /koolshare/scripts/betterapps*.sh
rm -rf /koolshare/scripts/BetterApps*.sh
rm -rf /koolshare/webs/Module_betterapps.asp
rm -rf /koolshare/webs/Module_BetterApps.asp
rm -rf /koolshare/scripts/uninstall_betterapps.sh
rm -rf /koolshare/scripts/uninstall_BetterApps.sh
rm -rf /tmp/betterapps*
rm -rf /tmp/BetterApps*

dbus remove betterapps_enable
dbus remove BetterApps_enable
dbus remove softcenter_module_betterapps_install
dbus remove softcenter_module_betterapps_version
dbus remove softcenter_module_betterapps_name
dbus remove softcenter_module_betterapps_title
dbus remove softcenter_module_betterapps_description
dbus remove softcenter_module_BetterApps_install
dbus remove softcenter_module_BetterApps_version
dbus remove softcenter_module_BetterApps_name
dbus remove softcenter_module_BetterApps_title
dbus remove softcenter_module_BetterApps_description

dbus remove linkease_enable
dbus remove softcenter_module_linkease_install
dbus remove softcenter_module_linkease_version
dbus remove softcenter_module_linkease_name
dbus remove softcenter_module_linkease_title
dbus remove softcenter_module_linkease_description
