#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import subprocess
import os
import time
import sys
import re


def execute_command(cmd):
    """通用的执行命令函数，用于处理命令输出和错误"""
    print("[*] 执行: {}".format(' '.join(cmd)))
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, check=False)
        if result.returncode != 0 and result.stderr:
            print(f"[!] 命令 {cmd} 执行失败: {result.stderr.strip()}")
        return result
    except FileNotFoundError:
        print(f"[!] 致命错误: 未找到命令 '{cmd[0]}'. 请确保必要工具已安装并在 PATH 中.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] 执行命令 {cmd} 时发生意外错误: {e}")
        return None


def list_available_interfaces():

    """使用 ip link show 命令枚举物理网络接口并检查状态"""
    cmd = ["ip", "-o", "link", "show"]
    result = execute_command(cmd)
    ethernet_devices = {}

    if result and result.returncode == 0 and result.stdout:
        lines = result.stdout.strip().split('\n')
        print("[*] 解析 ip link show 输出...")

        for line in lines:
            match = re.search(r'^\d+:\s+(\w+):\s+<(.+)>\s+.+state\s+(\w+)', line)
            if match:
                device = match.group(1)
                flags = match.group(2).split(',')
                state = match.group(3)

                # 排除回环接口和非以太网接口
                if device != 'lo' and 'LOOPBACK' not in flags:
                    ethernet_devices[device] = {
                        'state': state,
                        'flags': flags
                    }
                    print(f"[*] 检测到: {device} (状态: {state})")

        if not ethernet_devices:
            print("[!] 未检测到任何可用的以太网接口。")
            sys.exit(1)

        print("\n[*] 尝试启动所有检测到的以太网设备...")
        for device, info in ethernet_devices.items():
            print(f"\n[*] 处理设备 '{device}'...")

            if info['state'].lower() != 'up':
                print(f"[*] 正在启动设备 '{device}'...")
                up_cmd = ["ip", "link", "set", device, "up"]
                up_result = execute_command(up_cmd)

                if up_result and up_result.returncode == 0:
                    print(f"[*] 接口 '{device}' 已成功执行启动操作")
                else:
                    print(f"[!] 启动接口 '{device}' 失败")
            else:
                print(f"[*] 接口 '{device}' 已经处于 UP 状态")

            # 重新检查设备状态
            check_cmd = ["ip", "-o", "link", "show", device]
            check_result = execute_command(check_cmd)
            if check_result and check_result.returncode == 0:
                new_state = re.search(r'state\s+(\w+)', check_result.stdout)
                if new_state:
                    new_state = new_state.group(1)
                    ethernet_devices[device]['state'] = new_state
                    print(f"[*] 接口 '{device}' 当前状态: {new_state}")
                else:
                    print(f"[!] 无法解析 '{device}' 的新状态")
            else:
                print(f"[!] 检查设备 '{device}' 状态失败")

        # 打印最终结果
        print("\n[*] 可用于 bonding 的物理网络接口 (最终状态)：")
        for i, (device, info) in enumerate(ethernet_devices.items(), 1):
            state = info['state']
            flags = ','.join(info['flags'])
            print(f"   {i}: {device} (状态: {state}, 标志: {flags})")

        return list(ethernet_devices.keys())

    else:
        print("[!] 严重错误: 无法使用 'ip link show' 获取设备列表。")
        if result and result.stderr:
            print(f"[!] 错误信息: {result.stderr.strip()}")
        print("[!] 请确保您有足够的权限执行此命令。")
        sys.exit(1)


def check_package(package_name):
    """
    检查软件包是否已安装。
    返回 True 如果软件包已安装，False 如果未安装。
    """
    print("[*] 正在检查软件包 '{}' 是否已安装...".format(package_name))
    check_cmd = ["rpm", "-q", package_name]
    result = execute_command(check_cmd)

    if result and result.returncode == 0:
        print("[*] 软件包 '{}' 已安装。".format(package_name))
        return True
    else:
        print("[!] 软件包 '{}' 未安装或检查出错。".format(package_name))
        return False


def netmask_to_cidr(netmask):

    try:
        return sum([bin(int(x)).count('1') for x in netmask.split('.')])
    except Exception as e:
        print(f"[!] 无效的子网掩码格式: {netmask} - {e}")
        return None


def network_manager_service(config_method):
    """
    根据用户选择的配置方式管理 NetworkManager 或 network 服务。
    启动所需的服务，停止并禁用另一个服务。
    """
    def service_exists(service_name):
        """检查服务是否存在"""
        check_cmd = ["systemctl", "list-unit-files", f"{service_name}.service"]
        result = execute_command(check_cmd)
        return result and result.returncode == 0 and service_name in result.stdout

    if config_method == 'NetworkManager':
        if service_exists("NetworkManager"):
            print("[*] 确保 NetworkManager 服务正在运行并已启用...")
            # 检查是否活跃
            is_active_cmd = ["systemctl", "is-active", "--quiet", "NetworkManager"]
            active_result = execute_command(is_active_cmd)
            if not active_result or active_result.returncode != 0:
                print("[*] NetworkManager 未运行，正在启动...")
                start_result = execute_command(["systemctl", "start", "NetworkManager"])
                if not start_result or start_result.returncode != 0:
                    print("[!] 启动 NetworkManager 失败，请检查日志！")
                    sys.exit(1)

            # 检查是否启用
            is_enabled_cmd = ["systemctl", "is-enabled", "--quiet", "NetworkManager"]
            enabled_result = execute_command(is_enabled_cmd)
            if not enabled_result or enabled_result.returncode != 0:
                print("[*] NetworkManager 未启用开机自启，正在启用...")
                execute_command(["systemctl", "enable", "NetworkManager"])
        else:
            print("[!] NetworkManager 服务不存在，请检查是否安装。")
            sys.exit(1)

        # 处理 network 服务
        if service_exists("network"):
            print("[*] 确保 network 服务已停止并已禁用...")
            # 检查是否活跃
            is_active_cmd_net = ["systemctl", "is-active", "--quiet", "network"]
            active_result_net = execute_command(is_active_cmd_net)
            if active_result_net and active_result_net.returncode == 0:
                print("[*] 正在停止 network 服务...")
                execute_command(["systemctl", "stop", "network"])

            # 检查是否启用（通过 chkconfig 和 systemctl）
            chk_exists_cmd = ["chkconfig", "--list", "network"]
            chk_exists_result = execute_command(chk_exists_cmd)
            if chk_exists_result and chk_exists_result.returncode == 0:
                if " on" in chk_exists_result.stdout:
                    print("[*] 正在禁用 network 服务开机自启 (chkconfig)...")
                    execute_command(["chkconfig", "--del", "network"])

            is_enabled_cmd_net = ["systemctl", "is-enabled", "--quiet", "network"]
            enabled_result_net = execute_command(is_enabled_cmd_net)
            if enabled_result_net and enabled_result_net.returncode == 0:
                print("[*] 正在禁用 network 服务开机自启 (systemctl)...")
                execute_command(["systemctl", "disable", "network"])
        else:
            print("[*] network 服务不存在，无需停止或禁用。")

    elif config_method == 'network-scripts':
        if service_exists("network"):
            print("[*] 确保 network 服务正在运行并已启用...")
            is_active_cmd_net = ["systemctl", "is-active", "--quiet", "network"]
            active_result_net = execute_command(is_active_cmd_net)
            if not active_result_net or active_result_net.returncode != 0:
                print("[*] network 服务未运行，正在启动...")
                start_result = execute_command(["systemctl", "start", "network"])
                if not start_result or start_result.returncode != 0:
                    print("[!] 启动 network 服务失败，请检查 network-scripts 包是否安装以及配置文件。")
                    sys.exit(1)

            chk_exists_cmd = ["chkconfig", "--list", "network"]
            chk_exists_result = execute_command(chk_exists_cmd)
            needs_enable = True
            if chk_exists_result and chk_exists_result.returncode == 0:
                if " on" in chk_exists_result.stdout:
                    needs_enable = False
            else:
                print("[*] network 服务未被 chkconfig 管理，尝试添加...")
                execute_command(["chkconfig", "--add", "network"])

            if needs_enable:
                print("[*] 正在启用 network 服务开机自启 (chkconfig network on)...")
                execute_command(["chkconfig", "network", "on"])
        else:
            print("[!] network 服务不存在，请检查是否安装 network-scripts 包。")
            sys.exit(1)

        # 处理 NetworkManager 服务
        if service_exists("NetworkManager"):
            print("[*] 确保 NetworkManager 服务已停止并已禁用...")
            # 检查是否活跃
            is_active_cmd_nm = ["systemctl", "is-active", "--quiet", "NetworkManager"]
            active_result_nm = execute_command(is_active_cmd_nm)
            if active_result_nm and active_result_nm.returncode == 0:  # Active
                print("[*] 正在停止 NetworkManager 服务...")
                execute_command(["systemctl", "stop", "NetworkManager"])
            # 检查是否启用
            is_enabled_cmd_nm = ["systemctl", "is-enabled", "--quiet", "NetworkManager"]
            enabled_result_nm = execute_command(is_enabled_cmd_nm)
            if enabled_result_nm and enabled_result_nm.returncode == 0:  # Enabled
                print("[*] 正在禁用 NetworkManager 开机自启...")
                execute_command(["systemctl", "disable", "NetworkManager"])
        else:
            print("[*] NetworkManager 服务不存在，无需停止或禁用。")


def configure_bonding(bond_name, slave1, slave2, ip, netmask, gw, bond_mode):

    cidr = netmask_to_cidr(netmask)
    if cidr is None:
        print("[!] 无法进行 NetworkManager 配置，因为子网掩码无效。")
        return False

    print(f"[*] 创建 bonding 连接 '{bond_name}'，模式: {bond_mode}")
    add_bond_cmd = [
        "nmcli", "connection", "add", "type", "bond", "ifname", bond_name,
        "mode", bond_mode, "con-name", bond_name
    ]
    bond_result = execute_command(add_bond_cmd)
    if not bond_result or bond_result.returncode != 0:
        print(f"[!] 创建 bonding 连接 '{bond_name}' 失败。")
        return False

    # 配置bond ip
    print(f"[*] 配置 bonding 连接 IP: {ip}/{cidr}, 网关: {gw}")
    execute_command(["nmcli", "connection", "modify", bond_name,
                     "ipv4.addresses", f"{ip}/{cidr}"])
    execute_command(["nmcli", "connection", "modify",
                     bond_name, "ipv4.gateway", gw])
    execute_command(["nmcli", "connection", "modify",
                     bond_name, "ipv4.method", "manual"])
    execute_command(["nmcli", "connection", "modify",
                     bond_name, "connection.autoconnect", "yes"])
    execute_command(["nmcli", "connection", "modify", bond_name,
                     "bond.options", f"mode={bond_mode},miimon=100"])

    # 配置slave端口
    print(f"[*] 添加 slave 接口 {slave1} 和 {slave2} 到 bond '{bond_name}'")
    add_slave1_cmd = [
        "nmcli", "connection", "add", "type", "ethernet", "ifname", slave1,
        "master", bond_name, "con-name", f"{slave1}-slave"
    ]
    slave1_result = execute_command(add_slave1_cmd)
    if not slave1_result or slave1_result.returncode != 0:
        print(f"[!] 添加 slave 连接 '{slave1}-slave' 失败。")
        # Consider cleanup or rollback here if needed
        return False

    add_slave2_cmd = [
        "nmcli", "connection", "add", "type", "ethernet", "ifname", slave2,
        "master", bond_name, "con-name", f"{slave2}-slave"
    ]
    slave2_result = execute_command(add_slave2_cmd)
    if not slave2_result or slave2_result.returncode != 0:
        print(f"[!] 添加 slave 连接 '{slave2}-slave' 失败。")
        return False

    # 激活链接
    print(f"[*] 重新加载 NetworkManager 连接并启动 bonding 接口")
    execute_command(["nmcli", "connection", "reload"])
    time.sleep(3)

    print(f"[*] 正在启动 bond 连接 '{bond_name}'...")
    up_bond_cmd = ["nmcli", "connection", "up", bond_name]
    up_bond_result = execute_command(up_bond_cmd)

    if not up_bond_result or up_bond_result.returncode != 0:
        print(f"[!] 启动 bond 连接 '{bond_name}' 失败。")
        print("[*] 尝试显式启动 slave 连接...")
        execute_command(["nmcli", "connection", "up", f"{slave1}-slave"])
        execute_command(["nmcli", "connection", "up", f"{slave2}-slave"])
        time.sleep(10)
        up_bond_result_retry = execute_command(up_bond_cmd)
        time.sleep(10)
        restart_bond_network_manager = execute_command(["systemctl", "restart", "NetworkManager"])
        time.sleep(10)
        if not up_bond_result_retry or up_bond_result_retry.returncode != 0 \
                or restart_bond_network_manager.returncode != 0:
            print(
                f"[!] 再次尝试启动 bond 连接 '{bond_name}' 仍然失败。请检查 'journalctl -u NetworkManager' 和 'nmcli device status'。")
            return False
    print(f"[*] Bond 连接 '{bond_name}' 应该已启动。")
    return True


def configure_network_script(bond_name, slave1, slave2, ip, netmask, gw, bond_mode):

    # 创建 network-scripts 配置文件
    print(f"[*] 使用 network-scripts 配置接口 {bond_name}，模式: {bond_mode}")
    config_dir = "/etc/sysconfig/network-scripts"
    mode_map = {
        "active-backup": "1",
        "balance-rr": "0",
        "balance-xor": "2",
        "broadcast": "3",
        "802.3ad": "4",  # LACP
        "balance-tlb": "5",
        "balance-alb": "6"
    }
    numeric_bond_mode = mode_map.get(bond_mode, "1")

    bond_conf = f"""TYPE=Bond
DEVICE={bond_name}
NAME={bond_name}
BONDING_MASTER=yes
ONBOOT=yes
BOOTPROTO=none
IPADDR={ip}
NETMASK={netmask}
GATEWAY={gw}
USERCTL=no
BONDING_OPTS="miimon=100 mode={numeric_bond_mode}"
"""
    slave1_conf = f"""TYPE=Ethernet
BOOTPROTO=none
DEVICE={slave1}
NAME={slave1}
ONBOOT=yes
MASTER={bond_name}
SLAVE=yes
USERCTL=no
"""
    slave2_conf = f"""TYPE=Ethernet
BOOTPROTO=none
DEVICE={slave2}
NAME={slave2}
ONBOOT=yes
MASTER={bond_name}
SLAVE=yes
USERCTL=no
"""

    print(f"[*] 正在写入新的配置文件到 {config_dir}")
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, f"ifcfg-{bond_name}"), 'w') as f:
            f.write(bond_conf)
        with open(os.path.join(config_dir, f"ifcfg-{slave1}"), 'w') as f:
            f.write(slave1_conf)
        with open(os.path.join(config_dir, f"ifcfg-{slave2}"), 'w') as f:
            f.write(slave2_conf)
        print("[*] 配置文件写入成功。")
    except IOError as e:
        print(f"[!] 写入配置文件时出错: {e}")
        print("[!] 请检查权限或磁盘空间。配置可能未生效。")
        return False  # Indicate failure

    # --- Restart network service ---
    print("[*] 正在重启 network 服务以应用配置...")
    restart_result = execute_command(["systemctl", "restart", "network"])
    if not restart_result or restart_result.returncode != 0:
        print("[!] 重启 network 服务失败。请检查 'systemctl status network' 或 'journalctl -xe'。")
        print("[!] 提示: 如果之前 NetworkManager 在管理这些网卡，可能需要手动 'ifdown' 这些接口或重启系统。")
        return False
    print("[*] network 服务已重启。")
    return True


def ping_gateway(gw):

    print(f"[*] 正在 ping 网关 {gw} (最多 4 次)...")
    ping_cmd = ["ping", "-c", "4", "-W", "1", gw]
    result = execute_command(ping_cmd)

    if result and result.returncode == 0:
        print(f"[*] 网关 {gw} 可达！网络配置似乎已成功应用。")
        return True
    else:
        print(f"[!] 警告: 无法连接到网关 {gw}。请检查 IP/子网掩码/网关设置、物理连接和防火墙。")
        return False


def get_valid_interface_input(prompt, available_interfaces, exclude_interface=None):

    while True:
        user_input = input(prompt).strip()
        if user_input in available_interfaces:
            if exclude_interface and user_input == exclude_interface:
                print(
                    f"[!] 错误: 不能选择与第一个 slave 接口 ({exclude_interface}) 相同的接口。")
            else:
                return user_input
        else:
            print(f"[!] 错误: 输入的接口 '{user_input}' 不在可用列表或格式无效。请从上面列出的接口中选择。")


def run():

    if os.geteuid() != 0:
        print("[!] 错误: 此脚本需要 root 权限执行。请使用 sudo 或以 root 用户身份运行。")
        sys.exit(1)

    print("--- Linux 双网卡绑定配置脚本 ---")

    available_interfaces = list_available_interfaces()
    if not available_interfaces:
        return

    bond_name = input("[?] 请输入双网卡绑定的名称 (例如: bond0): ").strip()
    if not bond_name or not re.match(r"^[a-zA-Z0-9_-]+$", bond_name):
        print("[!] 无效的绑定名称。请使用字母、数字、下划线或连字符。")
        sys.exit(1)

    print("\n[*] 请从以下可用接口中选择两个用于绑定:")
    for i, iface in enumerate(available_interfaces):
        print(f"   {i + 1}: {iface}")

    slave1 = get_valid_interface_input(
        f"[?] 请输入第一个网卡名 (从列表 {', '.join(available_interfaces)} 中选择): ",
        available_interfaces
    )
    slave2 = get_valid_interface_input(
        f"[?] 请输入第二个网卡名 (从列表 {', '.join(available_interfaces)} 中选择, 不能与 {slave1} 相同): ",
        available_interfaces,
        exclude_interface=slave1
    )

    ip = input("[?] 请输入 IP 地址 (例如: 192.168.1.100): ").strip()
    netmask = input("[?] 请输入子网掩码 (例如: 255.255.255.0): ").strip()
    gw = input("[?] 请输入网关地址 (例如: 192.168.1.1): ").strip()

    # --- Select bonding mode ---
    print("\n[*] 选择 bonding 模式:")
    modes = {
        '1': ("active-backup", "主备模式"),
        '2': ("balance-rr", "轮询模式"),
        '3': ("balance-xor", "XOR 策略"),
        '4': ("broadcast", "广播模式"),
        '5': ("802.3ad", "LACP / 动态链路聚合 (交换机需支持并配置)"),
        '6': ("balance-tlb", "发送负载均衡 (无需交换机配置)"),
        '7': ("balance-alb", "适配器负载均衡 (收发, 无需交换机配置)")
    }
    for key, (mode_val, desc) in modes.items():
        print(f"   {key}: {mode_val} ({desc})")

    bond_mode_choice = input("[?] 请输入模式编号 (默认 1 - active-backup): ").strip()
    bond_mode = modes.get(bond_mode_choice, modes['1'])[
        0]
    print(f"[*] 已选择模式: {bond_mode}")

    print("\n[*] 请选择网络配置方式:")
    print("   1: NetworkManager (推荐用于 RHEL 7/8/9 及更新版本)")
    print("   2: network-scripts (传统方式, RHEL 8/9 中已弃用, 可能需要安装 'network-scripts' 包)")
    config_method_choice = input("[?] 请输入配置方式编号 (默认 1): ").strip()

    if config_method_choice == '2':
        config_method = "network-scripts"
        required_package = "network-scripts"
    else:
        config_method = "NetworkManager"
        required_package = "NetworkManager"

    print(f"[*] 已选择配置方式: {config_method}")

    if required_package:
        print(f"[*] 检查 '{config_method}' 所需的软件包 '{required_package}'...")
        if not check_package(required_package):
            print(f"[!] 错误: 所需的软件包 '{required_package}' 未安装。")
            if config_method == "network-scripts":
                print(f"[!] '{required_package}' 是使用 'network-scripts' 配置所需的关键包。请手动安装后重试。")
                sys.exit(1)
            else:
                print("[!] NetworkManager 核心包缺失，系统网络可能无法正常工作。请先修复系统环境。")
                sys.exit(1)
        else:
            print(f"[*] 所需软件包 '{required_package}' 已存在。")

    network_manager_service(config_method)

    config_success = False
    if config_method == 'NetworkManager':
        print("\n[*] --- 开始使用 NetworkManager 配置 Bonding ---")
        config_success = configure_bonding(bond_name, slave1, slave2,
                                           ip, netmask, gw, bond_mode)
    elif config_method == 'network-scripts':
        print("\n[*] --- 开始使用 network-scripts 配置 Bonding ---")
        config_success = configure_network_script(
            bond_name, slave1, slave2, ip, netmask, gw, bond_mode)

    if config_success:
        print(f"\n[*] 配置过程已执行。现在尝试验证网关 {gw} 的可达性...")
        ping_success = ping_gateway(gw)
        if ping_success:
            print("\n[*] --- 配置成功完成 ---")
            print(f"[*] 接口 {bond_name} (模式: {bond_mode}) 应已配置并激活。")
            print(f"[*] IP: {ip}, 子网掩码: {netmask}, 网关: {gw}")
            print(f"[*] Slaves: {slave1}, {slave2}")
            print(f"[*] 管理方式: {config_method}")
            print(
                "[*] 建议运行 'ip addr show {}' 或 'nmcli device show {}' 查看最终状态。".format(bond_name, bond_name))
        else:
            pass
    else:
        print("\n[*] --- 配置过程中发生错误 ---")
        print("[!] 未能成功完成配置步骤。请查看上面的错误日志。")
        print("[!] 网络状态可能不一致，建议检查并手动修复。")

    print("\n[*] 脚本执行结束。")


def main():
    run()


if __name__ == '__main__':
    main()
