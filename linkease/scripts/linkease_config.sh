#!/bin/sh
eval `dbus export linkease`
source /koolshare/scripts/base.sh
alias echo_date='echo $(date +%Y年%m月%d日\ %X):'

BIN=/koolshare/bin/link-ease
PID_FILE=/var/run/link-ease.pid

if_use_simple_version(){
  linkease_info=`/koolshare/bin/link-ease simplifyInfo|awk '{print $2}'`
  is_simple=`echo "${linkease_info}" | sed -n '1p'`
  memory=`echo "${linkease_info}" | sed -n '2p'`
  #echo "simple is: $is_simple"
  #echo "memory is: $memory"
  if [ "$is_simple" = "NO" ] && [ $memory -lt 400 ]; then
    echo "Change to simplify version, downloading"
    wget -q -t 2 -T 20 --dns-timeout=15 --no-check-certificate https://fw0.koolcenter.com/binary/LinkEase/AutoUpgrade/linkease.arm0 -O /tmp/linkease.arm0
    if [ "$?" != "0" ]; then
      wget -q -t 2 -T 20 --dns-timeout=15 --no-check-certificate https://fw.koolcenter.com/binary/LinkEase/AutoUpgrade/linkease.arm0 -O /tmp/linkease.arm0
    fi
    if [ "$?" = "0" ]; then
			echo "Download OK"
      chmod 755 /tmp/linkease.arm0
      is_simple=`/tmp/linkease.arm0 simplifyInfo | awk '{print $2}' | sed -n '1p'`
      if [ "$is_simple" = "YES" ]; then
				echo "Changing binary"
        cp /tmp/linkease.arm0 $BIN
        rm /tmp/linkease.arm0
      fi
    fi
  fi
}

start_ee(){
  if_use_simple_version

	start-stop-daemon -S -q	-b -m -p $PID_FILE -x $BIN
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

kill_ee(){
	killall	link-ease > /dev/null 2>&1
}

load_iptables(){
	iptables -S | grep "8897" | sed 's/-A/iptables -D/g' > clean.sh && chmod 777 clean.sh && ./clean.sh && rm clean.sh > /dev/null 2>&1
	iptables -t	filter -I INPUT -p tcp --dport 8897 -j ACCEPT > /dev/null 2>&1
}

del_iptables(){
	iptables -S | grep "8897" | sed 's/-A/iptables -D/g' > clean.sh && chmod 777 clean.sh && ./clean.sh && rm clean.sh > /dev/null 2>&1
}

#=========================================================
case $ACTION in
start)
	if [ "$linkease_enable" == "1" ];then
		logger "[软件中心]: 启动linkease插件！"
		kill_ee
		start_ee
		load_iptables
	else
		logger "[软件中心]: linkease插件未开启，不启动！"
	fi
	;;
start_nat)
		load_iptables
	;;
*)
	if [ "$linkease_enable" == "1" ];then
		kill_ee
		start_ee
		load_iptables
		http_response "$1"
	else
		kill_ee
		del_iptables
		http_response "$1"
	fi
	;;
esac

