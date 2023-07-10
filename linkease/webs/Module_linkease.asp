<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
    <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta HTTP-EQUIV="Pragma" CONTENT="no-cache" />
    <meta HTTP-EQUIV="Expires" CONTENT="-1" />
    <link rel="shortcut icon" href="images/favicon.png" />
    <link rel="icon" href="images/favicon.png" />
    <title>软件中心 - 易有云（LinkEase）</title>
    <link rel="stylesheet" type="text/css" href="index_style.css" />
    <link rel="stylesheet" type="text/css" href="form_style.css" />
    <link rel="stylesheet" type="text/css" href="usp_style.css" />
    <link rel="stylesheet" type="text/css" href="ParentalControl.css">
    <link rel="stylesheet" type="text/css" href="css/element.css">
    <link rel="stylesheet" type="text/css" href="res/softcenter.css">
    <script language="JavaScript" type="text/javascript" src="/state.js"></script>
    <script language="JavaScript" type="text/javascript" src="/popup.js"></script>
    <script language="JavaScript" type="text/javascript" src="/validator.js"></script>
    <script language="JavaScript" type="text/javascript" src="/help.js"></script>
    <script language="JavaScript" type="text/javascript" src="/general.js"></script>
    <script type="text/javascript" src="/js/jquery.js"></script>
    <script type="text/javascript" src="/disk_functions.js"></script>
    <script language="JavaScript" type="text/javascript" src="/client_function.js"></script>
    <script type="text/javascript" src="/switcherplugin/jquery.iphone-switch.js"></script>
    <script type="text/javascript" src="/res/softcenter.js"></script>
    <style>
        .mask_bg {
            position: absolute;
            margin: auto;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 100;
            /*background-color: #FFF;*/
            background: url(images/popup_bg2.gif);
            background-repeat: repeat;
            filter: progid:DXImageTransform.Microsoft.Alpha(opacity=60);
            -moz-opacity: 0.6;
            display: none;
            /*visibility:hidden;*/
            overflow: hidden;
        }

        .mask_floder_bg {
            position: absolute;
            margin: auto;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 300;
            /*background-color: #FFF;*/
            background: url(images/popup_bg2.gif);
            background-repeat: repeat;
            filter: progid:DXImageTransform.Microsoft.Alpha(opacity=60);
            -moz-opacity: 0.6;
            display: none;
            /*visibility:hidden;*/
            overflow: hidden;
        }

        .folderClicked {
            color: #569AC7;
            font-size: 14px;
            cursor: text;
        }

        .lastfolderClicked {
            color: #FFFFFF;
            cursor: pointer;
        }

        .linkease_btn {
            border: 1px solid #222;
            background: linear-gradient(to bottom, #003333 0%, #000000 100%);
            /* W3C rogcss */
            font-size: 10pt;
            color: #fff;
            padding: 5px 5px;
            border-radius: 5px 5px 5px 5px;
            width: 16%;
        }

        .linkease_btn:hover {
            border: 1px solid #222;
            background: linear-gradient(to bottom, #27c9c9 0%, #279fd9 100%);
            /* W3C rogcss */
            font-size: 10pt;
            color: #fff;
            padding: 5px 5px;
            border-radius: 5px 5px 5px 5px;
            width: 16%;
        }

        .linkease_msg {
            margin: 10px;
        }
    </style>
    <script>
<% get_AiDisk_status(); %>
<% disk_pool_mapping_info(); %>
var PROTOCOL = "cifs";
        var _layer_order = "";
        var FromObject = "0";
        var lastClickedObj = 0;
        var disk_flag = 0;
        window.onresize = cal_panel_block;
        var nfsd_enable = '<% nvram_get("nfsd_enable"); %>';
        var nfsd_exportlist_array = '<% nvram_get("nfsd_exportlist"); %>';
        var noChange_status = 0;
        var _responseLen;
        var r_lan_ipaddr = "<% nvram_get(lan_ipaddr); %>"
        var params_check = ["linkease_enable","linkease_simple"];
        var params_input = [];
        var dbus = {}

        function init() {
            show_menu(menu_hook);
            get_dbus_data();
            get_status();
            //check_dir_path();
            //initial_dir();
        }

        function get_dbus_data() {
            $.ajax({
                type: "GET",
                url: "/_api/linkease",
                dataType: "json",
                async: false,
                success: function (data) {
                    dbus = data.result[0];
                    conf_to_obj();
                    generate_link();
                }
            });
        }

        function conf_to_obj() {
            for (var i = 0; i < params_input.length; i++) {
                if (dbus[params_input[i]]) {
                    E(params_input[i]).value = dbus[params_input[i]];
                }
            }
            // data from checkbox
            for (var i = 0; i < params_check.length; i++) {
                if (dbus[params_check[i]]) {
                    E(params_check[i]).checked = dbus[params_check[i]] == "1";
                }
            }
        }

        function save() {
            for (var i = 0; i < params_input.length; i++) {
                if (E(params_input[i])) {
                    dbus[params_input[i]] = E(params_input[i]).value
                }
            }
            for (var i = 0; i < params_check.length; i++) {
                dbus[params_check[i]] = E(params_check[i]).checked ? '1' : '0';
            }
            showLoading();
            push_data(dbus, 1);
        }

        function push_data(obj, arg) {
            var id = parseInt(Math.random() * 100000000);
            var postData = { "id": id, "method": "linkease_config.sh", "params": [arg], "fields": obj };
            $.ajax({
                url: "/_api/",
                cache: false,
                type: "POST",
                dataType: "json",
                data: JSON.stringify(postData),
                success: function (response) {
                    if (response.result == id) {
                        refreshpage();
                    }
                }
            });
        }

        function generate_link() {
            var webite = E("linkease_website");  //访问linkease
            var guide = E("linkease_guide");    //配置中心
            webite.href = "http://" + r_lan_ipaddr + ":8897";
            guide.href = "http://" + r_lan_ipaddr + ":8897/guide/index.html";
            if (dbus["linkease_enable"] != "1") {
                webite.style.display = "none";
                guide.style.display = "none";
            } else {
                webite.style.display = "";
                guide.style.display = "";
            }
        }
        function get_status() {
            var id = parseInt(Math.random() * 100000000);
            var postData = { "id": id, "method": "linkease_status.sh", "params": [1], "fields": "" };
            $.ajax({
                type: "POST",
                cache: false,
                url: "/_api/",
                data: JSON.stringify(postData),
                dataType: "json",
                success: function (response) {
                    E("status").innerHTML = response.result;
                    setTimeout("get_status();", 10000);
                },
                error: function () {
                    setTimeout("get_status();", 5000);
                }
            });
        }

        function menu_hook(title, tab) {
            tabtitle[tabtitle.length - 1] = new Array("", "LinkEase文件同步");
            tablink[tablink.length - 1] = new Array("", "Module_linkease.asp");
        }

        //--------------------------- dir function ---------------------------------------

        function initial_dir() {
            var __layer_order = "0_0";
            var url = "/getfoldertree.asp";
            var type = "General";
            url += "?motion=gettree&layer_order=" + __layer_order + "&t=" + Math.random();
            $.get(url, function (data) {
                initial_dir_status(data);
            });
        }

        function initial_dir_status(data) {
            if (data != "" && data.length != 2) {
                get_layer_items("0");
                eval("var default_dir=" + data);
            } else {
                //E("EditExports").style.display = "none";
                disk_flag = 1;
            }
        }

        function check_dir_path() {
            var dir_array = E('linkease_dir').value.split("/");
            if (dir_array[dir_array.length - 1].length > 21)
                E('linkease_dir').value = "/" + dir_array[1] + "/" + dir_array[2] + "/" + dir_array[dir_array.length - 1].substring(0, 18) + "...";
        }

        function get_disk_tree() {
            if (disk_flag == 1) {
                alert('<#no_usb_found#>');
                return false;
            }
            cal_panel_block();
            $("#folderTree_panel").fadeIn(300);
            get_layer_items("0");
        }

        function get_layer_items(layer_order) {
            $.ajax({
                url: '/gettree.asp?layer_order=' + layer_order,
                dataType: 'script',
                error: function (xhr) {
                    ;
                },
                success: function () {
                    get_tree_items(treeitems);
                }
            });
        }

        function get_tree_items(treeitems) {
            document.aidiskForm.test_flag.value = 0;
            this.isLoading = 1;
            var array_temp = new Array();
            var array_temp_split = new Array();
            for (var j = 0; j < treeitems.length; j++) { // To hide folder 'Download2'
                array_temp_split[j] = treeitems[j].split("#");
                if (array_temp_split[j][0].match(/^asusware$/)) {
                    continue;
                }
                array_temp.push(treeitems[j]);
            }
            this.Items = array_temp;
            if (this.Items && this.Items.length >= 0) {
                BuildTree();
            }
        }

        function BuildTree() {
            var ItemText, ItemSub, ItemIcon;
            var vertline, isSubTree;
            var layer;
            var short_ItemText = "";
            var shown_ItemText = "";
            var ItemBarCode = "";
            var TempObject = "";
            for (var i = 0; i < this.Items.length; ++i) {
                this.Items[i] = this.Items[i].split("#");
                var Item_size = 0;
                Item_size = this.Items[i].length;
                if (Item_size > 3) {
                    var temp_array = new Array(3);
                    temp_array[2] = this.Items[i][Item_size - 1];
                    temp_array[1] = this.Items[i][Item_size - 2];
                    temp_array[0] = "";
                    for (var j = 0; j < Item_size - 2; ++j) {
                        if (j != 0)
                            temp_array[0] += "#";
                        temp_array[0] += this.Items[i][j];
                    }
                    this.Items[i] = temp_array;
                }
                ItemText = (this.Items[i][0]).replace(/^[\s]+/gi, "").replace(/[\s]+$/gi, "");
                ItemBarCode = this.FromObject + "_" + (this.Items[i][1]).replace(/^[\s]+/gi, "").replace(/[\s]+$/gi, "");
                ItemSub = parseInt((this.Items[i][2]).replace(/^[\s]+/gi, "").replace(/[\s]+$/gi, ""));
                layer = get_layer(ItemBarCode.substring(1));
                if (layer == 3) {
                    if (ItemText.length > 21)
                        short_ItemText = ItemText.substring(0, 30) + "...";
                    else
                        short_ItemText = ItemText;
                } else
                    short_ItemText = ItemText;
                shown_ItemText = showhtmlspace(short_ItemText);
                if (layer == 1)
                    ItemIcon = 'disk';
                else if (layer == 2)
                    ItemIcon = 'part';
                else
                    ItemIcon = 'folders';
                SubClick = ' onclick="GetFolderItem(this, ';
                if (ItemSub <= 0) {
                    SubClick += '0);"';
                    isSubTree = 'n';
                } else {
                    SubClick += '1);"';
                    isSubTree = 's';
                }
                if (i == this.Items.length - 1) {
                    vertline = '';
                    isSubTree += '1';
                } else {
                    vertline = ' background="/images/Tree/vert_line.gif"';
                    isSubTree += '0';
                }
                if (layer == 2 && isSubTree == 'n1') { // Uee to rebuild folder tree if disk without folder, Jieming add at 2012/08/29
                    document.aidiskForm.test_flag.value = 1;
                }
                TempObject += '<table class="tree_table" id="bug_test">';
                TempObject += '<tr>';
                // the line in the front.
                TempObject += '<td class="vert_line">';
                TempObject += '<img id="a' + ItemBarCode + '" onclick=\'E("d' + ItemBarCode + '").onclick();\' class="FdRead" src="/images/Tree/vert_line_' + isSubTree + '0.gif">';
                TempObject += '</td>';
                if (layer == 3) {
                    /*a: connect_line b: harddisc+name  c:harddisc  d:name e: next layer forder*/
                    TempObject += '<td>';
                    TempObject += '<img id="c' + ItemBarCode + '" onclick=\'E("d' + ItemBarCode + '").onclick();\' src="/images/New_ui/advancesetting/' + ItemIcon + '.png">';
                    TempObject += '</td>';
                    TempObject += '<td>';
                    TempObject += '<span id="d' + ItemBarCode + '"' + SubClick + ' title="' + ItemText + '">' + shown_ItemText + '</span>\n';
                    TempObject += '</td>';
                } else if (layer == 2) {
                    TempObject += '<td>';
                    TempObject += '<table class="tree_table">';
                    TempObject += '<tr>';
                    TempObject += '<td class="vert_line">';
                    TempObject += '<img id="c' + ItemBarCode + '" onclick=\'E("d' + ItemBarCode + '").onclick();\' src="/images/New_ui/advancesetting/' + ItemIcon + '.png">';
                    TempObject += '</td>';
                    TempObject += '<td class="FdText">';
                    TempObject += '<span id="d' + ItemBarCode + '"' + SubClick + ' title="' + ItemText + '">' + shown_ItemText + '</span>';
                    TempObject += '</td>';
                    TempObject += '<td></td>';
                    TempObject += '</tr>';
                    TempObject += '</table>';
                    TempObject += '</td>';
                    TempObject += '</tr>';
                    TempObject += '<tr><td></td>';
                    TempObject += '<td colspan=2><div id="e' + ItemBarCode + '" ></div></td>';
                } else {
                    /*a: connect_line b: harddisc+name  c:harddisc  d:name e: next layer forder*/
                    TempObject += '<td>';
                    TempObject += '<table><tr><td>';
                    TempObject += '<img id="c' + ItemBarCode + '" onclick=\'E("d' + ItemBarCode + '").onclick();\' src="/images/New_ui/advancesetting/' + ItemIcon + '.png">';
                    TempObject += '</td><td>';
                    TempObject += '<span id="d' + ItemBarCode + '"' + SubClick + ' title="' + ItemText + '">' + shown_ItemText + '</span>';
                    TempObject += '</td></tr></table>';
                    TempObject += '</td>';
                    TempObject += '</tr>';
                    TempObject += '<tr><td></td>';
                    TempObject += '<td><div id="e' + ItemBarCode + '" ></div></td>';
                }
                TempObject += '</tr>';
            }
            TempObject += '</table>';
            E("e" + this.FromObject).innerHTML = TempObject;
        }

        function get_layer(barcode) {
            var tmp, layer;
            layer = 0;
            while (barcode.indexOf('_') != -1) {
                barcode = barcode.substring(barcode.indexOf('_'), barcode.length);
                ++layer;
                barcode = barcode.substring(1);
            }
            return layer;
        }

        function build_array(obj, layer) {
            var path_temp = "/mnt";
            var layer2_path = "";
            var layer3_path = "";
            if (obj.id.length > 6) {
                if (layer == 3) {
                    layer3_path = "/" + obj.title;
                    while (layer3_path.indexOf("&nbsp;") != -1)
                        layer3_path = layer3_path.replace("&nbsp;", " ");
                    if (obj.id.length > 8)
                        layer2_path = "/" + E(obj.id.substring(0, obj.id.length - 3)).innerHTML;
                    else
                        layer2_path = "/" + E(obj.id.substring(0, obj.id.length - 2)).innerHTML;
                    while (layer2_path.indexOf("&nbsp;") != -1)
                        layer2_path = layer2_path.replace("&nbsp;", " ");
                }
            }
            if (obj.id.length > 4 && obj.id.length <= 6) {
                if (layer == 2) {
                    layer2_path = "/" + obj.title;
                    while (layer2_path.indexOf("&nbsp;") != -1)
                        layer2_path = layer2_path.replace("&nbsp;", " ");
                }
            }
            path_temp = path_temp + layer2_path + layer3_path;
            return path_temp;
        }

        function GetFolderItem(selectedObj, haveSubTree) {
            var barcode, layer = 0;
            showClickedObj(selectedObj);
            barcode = selectedObj.id.substring(1);
            layer = get_layer(barcode);
            if (layer == 0)
                alert("Machine: Wrong");
            else if (layer == 1) {
                // chose Disk
                setSelectedDiskOrder(selectedObj.id);
                path_directory = build_array(selectedObj, layer);
                E('createFolderBtn').className = "createFolderBtn";
                E('deleteFolderBtn').className = "deleteFolderBtn";
                E('modifyFolderBtn').className = "modifyFolderBtn";
                E('createFolderBtn').onclick = function () { };
                E('deleteFolderBtn').onclick = function () { };
                E('modifyFolderBtn').onclick = function () { };
            } else if (layer == 2) {
                // chose Partition
                setSelectedPoolOrder(selectedObj.id);
                path_directory = build_array(selectedObj, layer);
                E('createFolderBtn').className = "createFolderBtn_add";
                E('deleteFolderBtn').className = "deleteFolderBtn";
                E('modifyFolderBtn').className = "modifyFolderBtn";
                E('createFolderBtn').onclick = function () {
                    popupWindow('OverlayMask', '/aidisk/popCreateFolder.asp');
                };
                E('deleteFolderBtn').onclick = function () { };
                E('modifyFolderBtn').onclick = function () { };
                document.aidiskForm.layer_order.disabled = "disabled";
                document.aidiskForm.layer_order.value = barcode;
            } else if (layer == 3) {
                // chose Shared-Folder
                setSelectedFolderOrder(selectedObj.id);
                path_directory = build_array(selectedObj, layer);
                E('createFolderBtn').className = "createFolderBtn";
                E('deleteFolderBtn').className = "deleteFolderBtn_add";
                E('modifyFolderBtn').className = "modifyFolderBtn_add";
                E('createFolderBtn').onclick = function () { };
                E('deleteFolderBtn').onclick = function () {
                    popupWindow('OverlayMask', '/aidisk/popDeleteFolder.asp');
                };
                E('modifyFolderBtn').onclick = function () {
                    popupWindow('OverlayMask', '/aidisk/popModifyFolder.asp');
                };
                document.aidiskForm.layer_order.disabled = "disabled";
                document.aidiskForm.layer_order.value = barcode;
            }
            if (haveSubTree)
                GetTree(barcode, 1);
        }

        function showClickedObj(clickedObj) {
            if (this.lastClickedObj != 0)
                this.lastClickedObj.className = "lastfolderClicked"; //this className set in AiDisk_style.css
            clickedObj.className = "folderClicked";
            this.lastClickedObj = clickedObj;
        }

        function GetTree(layer_order, v) {
            if (layer_order == "0") {
                this.FromObject = layer_order;
                E('d' + layer_order).innerHTML = '<span class="FdWait">. . . . . . . . . .</span>';
                setTimeout('get_layer_items("' + layer_order + '", "gettree")', 1);
                return;
            }
            if (E('a' + layer_order).className == "FdRead") {
                E('a' + layer_order).className = "FdOpen";
                E('a' + layer_order).src = "/images/Tree/vert_line_s" + v + "1.gif";
                this.FromObject = layer_order;
                E('e' + layer_order).innerHTML = '<img src="/images/Tree/folder_wait.gif">';
                setTimeout('get_layer_items("' + layer_order + '", "gettree")', 1);
            } else if (E('a' + layer_order).className == "FdOpen") {
                E('a' + layer_order).className = "FdClose";
                E('a' + layer_order).src = "/images/Tree/vert_line_s" + v + "0.gif";
                E('e' + layer_order).style.position = "absolute";
                E('e' + layer_order).style.visibility = "hidden";
            } else if (E('a' + layer_order).className == "FdClose") {
                E('a' + layer_order).className = "FdOpen";
                E('a' + layer_order).src = "/images/Tree/vert_line_s" + v + "1.gif";
                E('e' + layer_order).style.position = "";
                E('e' + layer_order).style.visibility = "";
            } else {
                alert("Error when show the folder-tree!");
            }
        }

        function cancel_folderTree() {
            this.FromObject = "0";
            $("#folderTree_panel").fadeOut(300);
        }

        function confirm_folderTree() {
            E('linkease_dir').value = path_directory;
            this.FromObject = "0";
            $("#folderTree_panel").fadeOut(300);
        }

        function cal_panel_block() {
            var blockmarginLeft;
            if (window.innerWidth)
                winWidth = window.innerWidth;
            else if ((document.body) && (document.body.clientWidth))
                winWidth = document.body.clientWidth;
            if (document.documentElement && document.documentElement.clientHeight && document.documentElement.clientWidth) {
                winWidth = document.documentElement.clientWidth;
            }
            if (winWidth > 1050) {
                winPadding = (winWidth - 1050) / 2;
                winWidth = 1105;
                blockmarginLeft = (winWidth * 0.25) + winPadding;
            } else if (winWidth <= 1050) {
                blockmarginLeft = (winWidth) * 0.25 + document.body.scrollLeft;
            }
            E("folderTree_panel").style.marginLeft = blockmarginLeft + "px";
        }

    </script>
</head>

<body onload="init();">
    <div id="TopBanner"></div>
    <div id="DM_mask" class="mask_bg"></div>
    <div id="folderTree_panel" class="panel_folder">
        <table>
            <tr>
                <td>
                    <div class="machineName"
                        style="width:200px;font-family:Microsoft JhengHei;font-size:12pt;font-weight:bolder; margin-top:15px;margin-left:30px;">
                        选择下载目录</div>
                </td>
                <td>
                    <div style="width:240px;margin-top:17px;margin-left:125px;">
                        <table>
                            <tr>
                                <td>
                                    <div id="createFolderBtn" class="createFolderBtn" title="<#AddFolderTitle#>"></div>
                                </td>
                                <td>
                                    <div id="deleteFolderBtn" class="deleteFolderBtn" title="<#DelFolderTitle#>"></div>
                                </td>
                                <td>
                                    <div id="modifyFolderBtn" class="modifyFolderBtn" title="<#ModFolderTitle#>"></div>
                                </td>
                            <tr>
                        </table>
                    </div>
                </td>
            </tr>
        </table>
        <div id="e0" class="folder_tree"></div>
        <div style="background-image:url(images/Tree/bg_02.png);background-repeat:no-repeat;height:90px;">
            <input class="button_gen" type="button" style="margin-left:27%;margin-top:18px;"
                onclick="cancel_folderTree();" value="取消">
            <input class="button_gen" type="button" onclick="confirm_folderTree();" value="确认">
        </div>
    </div>
    <div id="DM_mask_floder" class="mask_floder_bg"></div>
    <!-- floder tree-->
    <div id="Loading" class="popup_bg"></div>
    <iframe name="hidden_frame" id="hidden_frame" src="" width="0" height="0" frameborder="0"></iframe>
    <form method="post" name="aidiskForm" action="" target="hidden_frame">
        <input type="hidden" name="motion" id="motion" value="">
        <input type="hidden" name="layer_order" id="layer_order" value="">
        <input type="hidden" name="test_flag" value="" disabled="disabled">
        <input type="hidden" name="protocol" id="protocol" value="">
    </form>
    <input type="hidden" name="current_page" value="Module_linkease.asp">
    <input type="hidden" name="next_page" value="Module_linkease.asp">
    <input type="hidden" name="group_id" value="">
    <input type="hidden" name="modified" value="0">
    <input type="hidden" name="action_mode" value="">
    <input type="hidden" name="action_script" value="">
    <input type="hidden" name="action_wait" value="8">
    <input type="hidden" name="first_time" value="">
    <input type="hidden" name="preferred_lang" id="preferred_lang" value="<% nvram_get("preferred_lang"); %>">
    <input type="hidden" name="SystemCmd" onkeydown="onSubmitCtrl(this, ' Refresh ')" value="">
    <input type="hidden" name="firmver" value="<% nvram_get("firmver"); %>">
    <table class="content" align="center" cellpadding="0" cellspacing="0">
        <tr>
            <td width="17">&nbsp;</td>
            <td valign="top" width="202">
                <div id="mainMenu"></div>
                <div id="subMenu"></div>
            </td>
            <td valign="top">
                <div id="tabMenu" class="submenuBlock"></div>
                <table width="98%" border="0" align="left" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="left" valign="top">
                            <table width="760px" border="0" cellpadding="5" cellspacing="0" bordercolor="#6b8fa3"
                                class="FormTitle" id="FormTitle">
                                <tr>
                                    <td bgcolor="#4D595D" colspan="3" valign="top">
                                        <div>&nbsp;</div>
                                        <div class="formfonttitle">易有云（LinkEase）远程文件管理，家庭相册备份</div>
                                        <div style="float:right; width:15px; height:25px;margin-top:-20px">
                                            <img id="return_btn" onclick="reload_Soft_Center();" align="right"
                                                style="cursor:pointer;position:absolute;margin-left:-30px;margin-top:-25px;"
                                                title="返回软件中心" src="/images/backprev.png"
                                                onMouseOver="this.src='/images/backprevclick.png'"
                                                onMouseOut="this.src='/images/backprev.png'"></img>
                                        </div>
                                        <div style="margin:0px 0 10px 5px;" class="splitLine"></div>
                                        <div class="SimpleNote">
                                            <li>支持 Windows、macOS、iOS、安卓、电视、NAS、路由器等平台。轻松实现文件互传、相册备份、文件同步，确保数据不丢失！</li>
                                            <li><i>相关文档：</i><a href="https://doc.linkease.com/zh/guide/linkease/install/device/koolcenter_merlin.html" target="_blank"><em><u>[使用教程]</u></em></a></li>
											<li><i>交流反馈：</i><a href="https://pd.qq.com/s/cr5pja9bu" target="_blank"><em><u>[加入QQ频道]</u></em></a></li>													
											<li><i>关于我们：</i><a href="https://www.linkease.com/about/" target="_blank"><em><u>[易有云]</u></em></a></li>													
                                        </div>
                                        <table width="100%" border="1" align="center" cellpadding="4" cellspacing="0"
                                            bordercolor="#6b8fa3" class="FormTable">
                                            <thead>
                                                <tr>
                                                    <td colspan="2">LinkEase - 高级设置</td>
                                                </tr>
                                            </thead>
                                            <tr id="switch_tr">
                                                <th>
                                                    <label>开关</label>
                                                </th>
                                                <td colspan="2">
                                                    <div class="switch_field" style="display:table-cell;float: left;">
                                                        <label for="linkease_enable">
                                                            <input id="linkease_enable" class="switch" type="checkbox"
                                                                style="display: none;">
                                                            <div class="switch_container">
                                                                <div class="switch_bar"></div>
                                                                <div class="switch_circle transition_style">
                                                                    <div></div>
                                                                </div>
                                                            </div>
                                                        </label>
                                                    </div>
                                                </td>
                                            </tr>
											<tr>
                                                <th>
                                                    <label>精简版（内存小于512M推荐）</label>
                                                </th>
                                                <td colspan="2">
                                                    <div class="switch_field" style="display:table-cell;float: left;">
                                                        <label for="linkease_simple">
                                                            <input id="linkease_simple" class="switch" type="checkbox"
                                                                style="display: none;">
                                                            <div class="switch_container">
                                                                <div class="switch_bar"></div>
                                                                <div class="switch_circle transition_style">
                                                                    <div></div>
                                                                </div>
                                                            </div>
                                                        </label>
                                                    </div>
                                                </td>
                                            </tr>
                                            <tr id="linkease_status">
                                                <th>运行状态</th>
                                                <td><span id="status">获取中...</span></td>
                                            </tr>
                                            <tr id="rule_update_switch">
                                                <th>管理/帮助</th>
                                                <td id="linkease_pre">
                                                    <a type="button" id="linkease_guide" class="linkease_btn"
                                                        target="_blank">配置中心</a>
                                                    <a type="button" id="linkease_website" class="linkease_btn" href=""
                                                        target="_blank">访问易有云</a>
                                                </td>
                                            </tr>
                                        </table>
                                        <div class="linkease_msg">
                                            <i>使用流程：</i>
                                            <div class="linkease_msg_info">
                                                <li>注册帐号：下载易有云客户端注册帐号。<a href="https://www.linkease.com/download/" target="_blank"><em><u>[点我全平台下载]</u></em></a></li>
                                                <li>启动插件：打开上方开关按钮后点击提交。</li>
												<li>先插入移动硬盘，并推荐格式化为 EXT3/EXT4 的文件分区，更多请查看<a href="https://doc.linkease.com/zh/guide/linkease/install/device/koolcenter_merlin.html" target="_blank"><em><u>[使用教程]</u></em></a>。</li>
                                                <li>绑定设备：</li>
												  <ul>方式一：点击上方"配置中心"按钮，进入易有云的配置页面，并登录您的易有云账号。</ul>
												  <ul>方式二：使用易有云APP进行扫描局域网设备并绑定。</ul>
                                                <li>配置网盘：登录后进入配置界面，设置网盘名称和网盘位置。</li>
                                                <li>绑定成功：确保配置无误后点击确定，成功后会提示已绑定。</li>
                                                <li>至此，您可使用易有云的APP或电脑客户端，选择绑定的设备并使用。</li>
                                            </div>
                                        </div>
                                        <div style="margin:30px 0 10px 5px;" class="splitLine"></div>
                                        <div id="warning" style="font-size:14px;margin:20px auto;"></div>
                                        <div class="apply_gen">
                                            <input class="button_gen" id="cmdBtn" onClick="save()" type="button"
                                                value="提交" />
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
            <td width="10" align="center" valign="top"></td>
        </tr>
    </table>
    <div id="footer"></div>
    <div id="OverlayMask" class="popup_bg">
        <div align="center">
            <iframe src="" frameborder="0" scrolling="no" id="popupframe" width="400" height="400"
                allowtransparency="true" style="margin-top:150px;"></iframe>
        </div>
    </div>
</body>

</html>
