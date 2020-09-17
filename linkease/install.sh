#!/bin/sh
source /koolshare/scripts/base.sh
alias echo_date='echo 【$(TZ=UTC-8 date -R +%Y年%m月%d日\ %X)】:'
DIR=$(cd $(dirname $0); pwd)
MODEL=$(nvram get productid)
module=linkease

# 获取固件类型
_get_type() {
	local FWTYPE=$(nvram get extendno|grep koolshare)
	if [ -d "/koolshare" ];then
		if [ -n $FWTYPE ];then
			echo "koolshare官改固件"
		else
			echo "koolshare梅林改版固件"
		fi
	else
		if [ "$(uname -o|grep Merlin)" ];then
			echo "梅林原版固件"
		else
			echo "华硕官方固件"
		fi
	fi
}

exit_install(){
	local state=$1
	case $state in
		1)
			echo_date "本插件适用于适用于【koolshare 梅林改/官改 hnd/axhnd/axhnd.675x】固件平台，你的固件平台不能安装！！！"
			echo_date "本插件支持机型/平台：https://github.com/koolshare/rogsoft#rogsoft"
			echo_date "退出安装！"
			rm -rf /tmp/${module}* >/dev/null 2>&1
			exit 1
			;;
		0|*)
			rm -rf /tmp/${module}* >/dev/null 2>&1
			exit 0
			;;
	esac
}

# 判断路由架构和平台
case $(uname -m) in
	aarch64)
		if [ "$(uname -o|grep Merlin)" -a -d "/koolshare" ];then
			echo_date 机型：$MODEL $(_get_type) 符合安装要求，开始安装插件！
		else
			exit_install 1
		fi
		;;
	armv7l)
		if [ "$MODEL" == "TUF-AX3000" -o "$MODEL" == "RT-AX82U" -o "$MODEL" == "RT-AX95Q" -o "$MODEL" == "RT-AX56_XD4" ] && [ -d "/koolshare" ];then
			echo_date 机型：$MODEL $(_get_type) 符合安装要求，开始安装插件！
		else
			exit_install 1
		fi
		;;
	*)
		exit_install 1
	;;
esac

ROG_86U=0
EXT_NU=$(nvram get extendno)
EXT_NU=${EXT_NU%_*}

if [ -n "$(nvram get extendno | grep koolshare)" -a "$(nvram get productid)" == "RT-AC86U" -a "${EXT_NU}" -lt "81918" ];then
	ROG_86U=1
fi

# 判断固件需要什么UI
if [ "$MODEL" == "GT-AC5300" -o "$MODEL" == "GT-AX11000" -o "$ROG_86U" == "1" ];then
	# 官改固件，骚红皮肤
	ROG=1
fi

if [ "$MODEL" == "TUF-AX3000" ];then
	# 官改固件，橙色皮肤
	TUF=1
fi

# stop linkease first
enable=`dbus get linkease_enable`
if [ "$enable" == "1" ];then
	killall	link-ease > /dev/null 2>&1
fi

rm -rf /koolshare/init.d/*linkease.sh
cp -rf /tmp/linkease/bin/* /koolshare/bin/
cp -rf /tmp/linkease/scripts/* /koolshare/scripts/
cp -rf /tmp/linkease/webs/* /koolshare/webs/
cp -rf /tmp/linkease/res/* /koolshare/res/
cp -rf /tmp/linkease/uninstall.sh /koolshare/scripts/uninstall_linkease.sh
if [ "$ROG" == "1" ];then
	continue
else
	if [ "$TUF" == "1" ];then
		sed -i 's/3e030d/3e2902/g;s/91071f/92650F/g;s/680516/D0982C/g;s/cf0a2c/c58813/g;s/700618/74500b/g;s/530412/92650F/g' /koolshare/webs/Module_${module}.asp >/dev/null 2>&1
	else
		sed -i '/rogcss/d' /koolshare/webs/Module_${module}.asp >/dev/null 2>&1
	fi
fi
chmod +x /koolshare/bin/link-ease
chmod +x /koolshare/scripts/*
[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh

# 离线安装用
dbus set linkease_version="$(cat $DIR/version)"
dbus set softcenter_module_linkease_version="$(cat $DIR/version)"
dbus set softcenter_module_linkease_description="易有云2.0 （LinkEase） 手机相册同步，PC 双向同步！"
dbus set softcenter_module_linkease_install="1"
dbus set softcenter_module_linkease_name="linkease"
dbus set softcenter_module_linkease_title="易有云2.0"

# re-enable linkease
if [ "$enable" == "1" ];then
	sh /koolshare/scripts/linkease_config.sh start
fi

# 完成
echo_date "易有云2.0 插件安装完毕！"
exit_install
