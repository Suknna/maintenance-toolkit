#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 导入Python 2/3 兼容性模块
from __future__ import print_function
import os
import sys
import shutil
import time
import subprocess

# --- 配置区 ---

# 目标配置文件路径
CONFIG_FILE_PATH = '/etc/logrotate.d/syslog'

# 要写入的新配置文件内容
NEW_CONFIG_CONTENT = """/var/log/cron
/var/log/maillog
/var/log/messages
/var/log/secure
/var/log/spooler
{
    # 每天轮替
    daily

    # 保留180份旧日志
    rotate 180

    # 当文件大小超过200MB时也进行轮替
    size 200M

    # 压缩轮替后的日志文件
    compress

    # 延迟压缩，直到下一次轮替时再压缩
    delaycompress

    # 如果日志文件不存在，忽略并且不报错
    missingok

    # 如果日志文件为空，则不进行轮替
    notifempty

    # 针对列出的所有日志文件，postrotate脚本只执行一次
    sharedscripts

    # 在轮替之后执行的脚本
    postrotate
        # 通知 rsyslog 服务重新加载，以便它向新的空日志文件中写入
        /usr/bin/systemctl restart rsyslog.service > /dev/null 2>&1 || true
    endscript
}
"""

# --- 脚本核心逻辑 ---


def check_root_privileges():
    """检查脚本是否以root权限运行"""
    if os.geteuid() != 0:
        print("错误：此脚本需要root权限才能修改系统文件和重启服务。")
        print("请尝试使用 'sudo python {0}' 来运行。".format(sys.argv[0]))
        sys.exit(1)


def run_command(command):
    """
    执行一个shell命令并返回其输出。
    在Python 2和3中兼容。
    """
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        if sys.version_info[0] == 3:
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1


def get_service_manager():
    """
    判断系统使用的是 systemctl 还是 service。
    """
    try:
        stdout, _, returncode = run_command("ps -p 1 -o comm=")
        if returncode == 0 and 'systemd' in stdout.strip():
            print("检测到 systemd，将使用 'systemctl' 命令。")
            return 'systemctl'
    except Exception:
        pass

    print("未检测到 systemd，将使用 'service' 命令。")
    return 'service'


def get_syslog_service_name(manager_cmd):
    """
    判断日志服务是 rsyslog, syslog-ng还是 syslog。
    *** 已增强此函数以提高兼容性 ***
    """
    # 检查顺序：rsyslog > syslog-ng > syslog
    services_to_check = ['rsyslog', 'syslog-ng', 'syslog']

    for service in services_to_check:
        found = False
        if manager_cmd == 'systemctl':
            # 对于 systemd，is-active 是最可靠的方法
            check_cmd = "{0} is-active --quiet {1}".format(
                manager_cmd, service)
            _, _, returncode = run_command(check_cmd)
            if returncode == 0:
                found = True
        else:
            # 对于非 systemd (SysVinit)
            # 方法1: 尝试 'service status'，这可以检查正在运行的服务
            check_cmd = "{0} {1} status ".format(manager_cmd, service)
            _, _, returncode = run_command(check_cmd)
            if returncode == 0:
                found = True
            else:
                # 方法2 (更可靠): 检查 /etc/init.d/ 中是否存在服务脚本
                initd_path = "/etc/init.d/{0}".format(service)
                if os.path.exists(initd_path):
                    print("信息: 通过检查 '{0}' 路径确认服务存在。".format(initd_path))
                    found = True

        if found:
            print("检测到活动的或已安装的日志服务: '{0}'".format(service))
            return service

    print("错误：无法在系统中找到 'rsyslog', 'syslog-ng' 或 'syslog' 服务。")
    print("请确认您的系统已安装并启用了其中一种日志服务。")
    sys.exit(1)


def main():
    """主执行函数"""
    # 0. 权限检查
    print("--- 步骤 0: 检查运行权限 ---")
    check_root_privileges()
    print("权限检查通过，以root身份运行。\n")

    # 1. 判断系统和服务
    print("--- 步骤 1: 检测系统环境 ---")
    service_manager = get_service_manager()
    syslog_service = get_syslog_service_name(service_manager)
    print("检测完成。\n")

    # 2. 备份文件
    print("--- 步骤 2: 备份原始配置文件 ---")
    if os.path.exists(CONFIG_FILE_PATH):
        timestamp = time.strftime('%Y%m%d%H%M%S')
        backup_path = "{0}.bak_{1}".format(CONFIG_FILE_PATH, timestamp)
        try:
            shutil.copy2(CONFIG_FILE_PATH, backup_path)
            print("成功: '{0}' 已备份至 '{1}'".format(CONFIG_FILE_PATH, backup_path))
        except Exception as e:
            print("错误: 备份文件失败。原因: {0}".format(e))
            sys.exit(1)
    else:
        print("警告: 配置文件 '{0}' 不存在，跳过备份步骤。".format(CONFIG_FILE_PATH))
    print("备份完成。\n")

    # 3. 替换内容并检查权限
    print("--- 步骤 3: 写入新配置并设置权限 ---")
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(NEW_CONFIG_CONTENT)
        print("成功: 新内容已写入 '{0}'".format(CONFIG_FILE_PATH))
        os.chmod(CONFIG_FILE_PATH, 0o644)
        print("成功: 文件权限已设置为 644。")
    except Exception as e:
        print("错误: 写入文件或设置权限失败。原因: {0}".format(e))
        sys.exit(1)
    print("配置更新完成。\n")

    # 4. 重启服务
    print("--- 步骤 4: 重启日志服务 ---")
    restart_command = ""
    if service_manager == 'systemctl':
        restart_command = "systemctl restart {0}".format(syslog_service)
    else:
        restart_command = "service {0} restart".format(syslog_service)
    print("执行命令: '{0}'".format(restart_command))

    stdout, stderr, returncode = run_command(restart_command)
    if returncode == 0 or (stderr and ("ok" in stderr.lower() or "started" in stderr.lower())):
        # 增加对返回信息中关键字的判断，因为某些service脚本即使成功也可能返回非0值
        print("成功: '{0}' 服务已重启。".format(syslog_service))
    else:
        print("错误: 服务重启失败。")
        print("返回码: {0}".format(returncode))
        print("STDOUT: \n{0}".format(stdout))
        print("STDERR: \n{0}".format(stderr))
        sys.exit(1)

    print("\n所有操作已成功完成！")


if __name__ == '__main__':
    main()
