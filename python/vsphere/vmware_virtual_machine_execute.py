#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   vmware_virtual_machine_execute.py
@Time    :   2025/05/10
@Author  :   suknna 
通过vmtools在目标虚拟机内部执行命令
'''

from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
import ssl
import sys
import time
import re
import os
import requests
requests.packages.urllib3.disable_warnings()

def log_result(vm_name, exit_code, log_file):
    """记录执行结果到日志文件"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} | {vm_name} | ExitCode: {exit_code}\n")

def read_vm_list(file_path):
    """从文件读取虚拟机列表"""
    with open(file_path, 'r') as f:
        vms = list(set(line.strip() for line in f if line.strip()))
    return vms

def connect_vcenter(host, user, password):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False  # 必须先禁用主机名验证
    context.verify_mode = ssl.CERT_NONE
    try:
        service_instance = SmartConnect(
            host=host, user=user, pwd=password, port=443, sslContext=context
        )
        print("连接成功!")
        return service_instance
    except Exception as e:
        print(f"连接失败: {e}")
        raise

def get_vm_by_name(content, vm_name):
    """通过名称获取虚拟机对象"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    for vm in container.view:
        if vm.name == vm_name:
            return vm
    return None

def upload_file_to_vm(si, vm, auth, local_path, remote_dir="C:\\Windows\\"):
    """通过GuestFileManager上传文件到虚拟机"""
    guest_file_manager = si.content.guestOperationsManager.fileManager
    
    # 创建目录（如果不存在）
    try:
        guest_file_manager.MakeDirectoryInGuest(vm, auth, remote_dir, createParentDirectories=True)
    except vim.fault.FileAlreadyExists:
        pass  # 目录已存在，继续执行
    
    # 上传文件
    try:
        remote_path = f"{remote_dir}{os.path.basename(local_path)}"
        file_size = os.path.getsize(local_path)
        upload_url = guest_file_manager.InitiateFileTransferToGuest(
            vm, auth, 
            remote_path,
            fileAttributes=vim.vm.guest.FileManager.FileAttributes(),
            fileSize=file_size,
            overwrite=True
        )
        
        # 使用requests上传文件内容
        with open(local_path, 'rb') as f:
            response = requests.put(upload_url, data=f, verify=False)
        return response.status_code == 200
    except Exception as e:
        print(f"文件上传失败: {e}")
        return False

def execute_binary(guest_manager, vm, auth, binary_path):
    """在虚拟机内执行二进制程序"""
    spec = vim.vm.guest.ProcessManager.ProgramSpec(
        programPath=binary_path,
        arguments=""
    )
    pid = guest_manager.StartProgramInGuest(vm, auth, spec)
    return pid

def execute_powershell_script(guest_manager, vm, auth, script, si):
    """在虚拟机内执行PowerShell脚本"""
    try:
        # 检查VMware Tools状态
        tools_status = vm.guest.toolsStatus
        if tools_status in ('toolsNotInstalled', 'toolsNotRunning'):
            raise SystemExit("VMwareTools未安装或未运行")

        # 创建命令规范
        spec = vim.vm.guest.ProcessManager.ProgramSpec(
            programPath="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            arguments=f"-Command \"{script}\""
        )

        # 启动程序
        pid = guest_manager.StartProgramInGuest(vm, auth, spec)
        print(f"程序已启动，PID: {pid}")

        # 监控程序状态
        if pid > 0:
            print(f"程序已提交，PID: {pid}")
            pid_exitcode = guest_manager.ListProcessesInGuest(vm, auth, [pid]).pop().exitCode
            
            # 检查非数字状态码
            while re.match('[^0-9]+', str(pid_exitcode)):
                print(f"程序运行中，PID: {pid}")
                time.sleep(5)
                pid_exitcode = guest_manager.ListProcessesInGuest(vm, auth, [pid]).pop().exitCode
                
                if pid_exitcode == 0:
                    print(f"程序 {pid} 执行成功")
                    break
                elif re.match('[1-9]+', str(pid_exitcode)):
                    print(f"错误: 程序 {pid} 执行失败")
                    print(f"提示: 可在虚拟机 {vm.summary.guest.ipAddress} 上调试")
                    print("进程详细信息:")
                    print(guest_manager.ListProcessesInGuest(vm, auth, [pid]))
                    break

        # 不再获取标准输出和错误输出，直接返回状态码
        return pid_exitcode, "", ""

    except vmodl.MethodFault as error:
        print(f"VMware API错误: {error.msg}")
        sys.exit(1)
    except Exception as e:
        print(f"执行命令失败: {e}")
        sys.exit(1)

def main():
    # 配置参数
    vcenter_host = "192.168.200.10"  # vCenter/ESXi IP
    vcenter_user = "admin1@localhost"
    vcenter_pass = "Security123"
    guest_user = "Administrator"  # 虚拟机本地管理员账户
    guest_pass = "1112222333"
    vm_list_file = "vm_info.txt"
    success_log = "success.log"
    error_log = "error.log"

    # 读取虚拟机列表
    try:
        vm_names = read_vm_list(vm_list_file)
        print(f"共发现 {len(vm_names)} 台待处理虚拟机")
    except Exception as e:
        print(f"读取虚拟机列表失败: {e}")
        sys.exit(1)

    # 1. 连接到vCenter
    try:
        si = connect_vcenter(vcenter_host, vcenter_user, vcenter_pass)
        content = si.RetrieveContent()
    except Exception as e:
        print(f"vCenter连接失败: {e}")
        sys.exit(1)

    for vm_name in vm_names:
        print(f"\n{'='*30} 开始处理 {vm_name} {'='*30}")
        
        # 获取虚拟机对象
        vm = get_vm_by_name(content, vm_name)
        if not vm:
            print(f"虚拟机不存在: {vm_name}")
            log_result(vm_name, "NOT_FOUND", error_log)
            continue

        try:
            # 准备认证信息
            auth = vim.vm.guest.NamePasswordAuthentication(
                username=guest_user, password=guest_pass
            )

            # 上传并执行二进制文件
            binary_name = "cmdserver_uninstall_amd64.exe"
            local_binary = os.path.join(os.getcwd(), binary_name)
            remote_binary = f"C:\\Windows\\{binary_name}"
            
            if not os.path.exists(local_binary):
                print(f"本地二进制文件不存在: {local_binary}")
                log_result(vm_name, "MISSING_BINARY", error_log)
                continue
                
            if not upload_file_to_vm(si, vm, auth, local_binary):
                print("文件上传失败")
                log_result(vm_name, "UPLOAD_FAILED", error_log)
                continue

            # 执行二进制文件
            guest_manager = si.content.guestOperationsManager.processManager
            pid = execute_binary(guest_manager, vm, auth, remote_binary)
            print(f"程序已启动，PID: {pid}")
            
            # 监控执行状态
            start_time = time.time()
            timeout = 600
            exit_code = None
            while time.time() - start_time < timeout:
                processes = guest_manager.ListProcessesInGuest(vm, auth, [pid])
                if processes and processes[0].exitCode is not None:
                    exit_code = processes[0].exitCode
                    break
                time.sleep(2)
            
            if exit_code is None:
                print(f"程序执行超时(PID: {pid})")
                log_result(vm_name, "TIMEOUT", error_log)
                continue

            print(f"程序执行完成，退出码: {exit_code}")
            if exit_code == 0:
                log_result(vm_name, exit_code, success_log)
                print(f"✅ {vm_name} 卸载成功")
            else:
                log_result(vm_name, exit_code, error_log)
                print(f"❌ {vm_name} 卸载失败，错误码: {exit_code}")

        except Exception as e:
            print(f"处理异常: {e}")
            log_result(vm_name, str(e), error_log)

    Disconnect(si)

if __name__ == "__main__":
    main()
