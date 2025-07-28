#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from vsphere_get_content import VsphereContent as vspc
import datetime
import re
import sys


def decide_ipv4(ip_str):

    re_ip = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
    re_ip_value = re_ip.match(ip_str)
    if re_ip_value:
        return True
    else:
        return False


def sizeof_fmt(num):
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def time_fmt(times):
    get_time = datetime.datetime.strftime(times, "%Y-%m-%d %H:%M:%S")
    return get_time


def proc_vms_content(obj_vms):

    cl_vm_content_list = list()
    for single_vm in obj_vms:
        single_vm_content_dict = dict()
        single_vm_config = single_vm.config
        single_vm_runtime = single_vm.runtime
        single_vm_config_hardware = single_vm_config.hardware
        single_vm_guest = single_vm.guest
        single_vm_sum_conf = single_vm.summary.config
        single_vm_sum_quickStats = single_vm.summary.quickStats

        # 获取虚拟机状态
        single_vm_content_dict["phy_host_name"] = single_vm_runtime.host.name
        single_vm_content_dict["connectStat"] = single_vm_runtime.connectionState
        single_vm_powerState = single_vm_runtime.powerState
        single_vm_content_dict["powerState"] = single_vm_powerState
        single_vm_content_dict["integration"] = single_vm_runtime.consolidationNeeded
        single_vm_content_dict["memoryHotAdd"] = single_vm_config.memoryHotAddEnabled
        single_vm_content_dict["cpuHotAdd"] = single_vm_config.cpuHotAddEnabled
        single_vm_content_dict["cpuHotRemove"] = single_vm_config.cpuHotRemoveEnabled
        single_vm_content_dict["uptime"] = single_vm_sum_quickStats.uptimeSeconds
        single_vm_content_dict["overallStatus"] = single_vm.summary.overallStatus

        # 获取虚拟配置信息
        single_vm_content_dict["display_name"] = single_vm_config.name
        single_vm_content_dict["os_release"] = single_vm_config.guestFullName
        single_vm_content_dict["hard_version"] = single_vm_config.version
        single_vm_content_dict["guest_uuid"] = single_vm_config.uuid

        # 获取虚拟机硬件配置
        single_vm_config_hardware_numCPU = single_vm_config_hardware.numCPU
        single_vm_content_dict["numCPU"] = single_vm_config_hardware_numCPU
        single_vm_config_hardware_memoryMB = single_vm_config_hardware.memoryMB
        single_vm_content_dict["memoryMB"] = single_vm_config_hardware_memoryMB
        single_vm_content_dict["numEthernetCards"] = single_vm_sum_conf.numEthernetCards
        single_vm_content_dict["numVirtualDisks"] = single_vm_sum_conf.numVirtualDisks

        for vm_datastore in single_vm_config.datastoreUrl:
            vm_datastore_dict = dict()
            vmdisk_content_list = list()
            vm_datastore_dict["datastore_name"] = vm_datastore.name
            vm_datastore_dict["datastore_url"] = vm_datastore.url
            single_vm_config_hardware_device = single_vm_config_hardware.device
            for vmdisk in single_vm_config_hardware_device:
                vmdisk_dict = dict()
                if vmdisk._wsdlName == "VirtualDisk":
                    vmdisk_dict["vmdisk_name"] = vmdisk.deviceInfo.label
                    vmdisk_cap = int(vmdisk.deviceInfo.summary.split(" ")[0].replace(",", "")) * 1024
                    vmdisk_dict["vmdisk_capacity"] = sizeof_fmt(vmdisk_cap)
                    vmdisk_content_list.append(vmdisk_dict)
                vm_datastore_dict["vmdisk_content"] = vmdisk_content_list
            single_vm_content_dict["vmdisk"] = vm_datastore_dict

        single_vm_content_dict["toolsStatus"] = single_vm_guest.toolsStatus
        single_vm_content_dict["toolsVersionStatus"] = single_vm_guest.toolsVersionStatus2
        single_vm_content_dict["toolsRunningStatus"] = single_vm_guest.toolsRunningStatus
        single_vm_content_dict["toolsVersion"] = single_vm_guest.toolsVersion

        cl_vm_content_list.append(single_vm_content_dict)

    return cl_vm_content_list


def get_vms_connect(create_connect):

    cl_vms_content_list = list()
    vms = create_connect.get_virtualmachine()
    for vms_c in vms:
        cl_vms_content_dict = dict()
        vms_v = vms_c["virtualmachine"]
        if vms_v is not None:
            cl_vms_content_dict["cluster_name"] = vms_c["cluster_name"]
            cl_vms_c = proc_vms_content(vms_v)
            cl_vms_content_dict["vms_content"] = cl_vms_c
        else:
            cl_vms_content_dict["cluster_name"] = vms_c["cluster_name"]
            cl_vms_content_dict["vms_content"] = "Null"

        cl_vms_content_list.append(cl_vms_content_dict)

    return cl_vms_content_list


def proc_text(all_vms_msg):

    text_list = list()
    text_list.append("cluster_name,phy_host_name,display_name,guest_uuid,os_release,hard_version,memoryHotAdd,"
                     "cpuHotAdd,cpuHotRemove,connectStat,powerState,integration,uptime,overallStatus,numCPU,memory,"
                     "numEthernetCards,numVirtualDisks,datastore_name,datastore_url,vmdisk_name,vmdisk_capacity,"
                     "toolsStatus,toolsRunningStatus,toolsVersionStatus,toolsVersion" + "\n")

    for vms_msg in all_vms_msg:
        for single_vm_msg in vms_msg["vms_content"]:
            text_list.append(vms_msg["cluster_name"] + ",")
            text_list.append(single_vm_msg["phy_host_name"] + ",")
            text_list.append(single_vm_msg["display_name"] + ",")
            text_list.append(single_vm_msg["guest_uuid"] + ",")
            text_list.append(single_vm_msg["os_release"] + ",")
            text_list.append(single_vm_msg["hard_version"] + ",")
            text_list.append(str(single_vm_msg["memoryHotAdd"]) + ",")
            text_list.append(str(single_vm_msg["cpuHotAdd"]) + ",")
            text_list.append(str(single_vm_msg["cpuHotRemove"]) + ",")

            text_list.append(single_vm_msg["connectStat"] + ",")
            text_list.append(single_vm_msg["powerState"] + ",")
            text_list.append(str(single_vm_msg["integration"]) + ",")
            system_uptime = "%d" % (single_vm_msg["uptime"] / 60 / 24)
            text_list.append(str(system_uptime) + ",")

            text_list.append(str(single_vm_msg["numCPU"]) + ",")
            text_list.append(str(single_vm_msg["memoryMB"]) + ",")
            text_list.append(str(single_vm_msg["numEthernetCards"]) + ",")
            text_list.append(str(single_vm_msg["numVirtualDisks"]) + ",")

            text_list.append(single_vm_msg["vmdisk"]["datastore_name"] + ",")
            text_list.append(single_vm_msg["vmdisk"]["datastore_url"] + ",")
            for n in range(0, len(single_vm_msg["vmdisk"]["vmdisk_content"])):
                text_list.append(single_vm_msg["vmdisk"]["vmdisk_content"][n]["vmdisk_name"] + ":")
                text_list.append(single_vm_msg["vmdisk"]["vmdisk_content"][n]["vmdisk_capacity"])
                if n == (len(single_vm_msg["vmdisk"]["vmdisk_content"]) - 1):
                    text_list.append(",")
                else:
                    text_list.append(";")
            text_list.append(str(single_vm_msg["toolsStatus"]) + ",")
            text_list.append(single_vm_msg["toolsRunningStatus"] + ",")
            text_list.append(single_vm_msg["toolsVersionStatus"] + ",")
            text_list.append(single_vm_msg["toolsVersion"] + "\n")

    return text_list


def write_text(vc_ip, file_content):

    filename = vc_ip + "_" + "vmcontent" + ".txt"
    with open("/Users/zhangcong/Desktop/" + filename, "w+") as vm_files:
        vm_files.writelines(file_content)

    for vmc in file_content:
        print(vmc, end="")

    return 0


def run():
    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    create_connect_obj = vspc(ipaddress, user, passwd)
    all_vms_msg = get_vms_connect(create_connect_obj)
    proc_files = proc_text(all_vms_msg)
    ret_value = write_text(ipaddress, proc_files)
    if ret_value == 0:
        print("Get data successfully...")
    else:
        print("Failed to get data...")


def main():
    run()


if __name__ == "__main__":
    main()
