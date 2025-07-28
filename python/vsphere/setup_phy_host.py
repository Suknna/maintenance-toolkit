#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from vsphere_get_content import VsphereContent as vspc
import datetime
import sys


def sizeof_fmt(num):
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def proc_phy_host(obj_phy_hosts):
    proc_phy_hosts_list = list()
    for hosts in obj_phy_hosts:
        proc_phy_hosts_dict = dict()
        host_sum = hosts.summary
        host_runtime = host_sum.runtime
        proc_phy_hosts_dict["hostname"] = hosts.name
        host_runtime_connectionState = host_runtime.connectionState
        proc_phy_hosts_dict["server_ip"] = host_sum.config.name
        proc_phy_hosts_dict["overallStatus"] = host_sum.overallStatus
        proc_phy_hosts_dict["connect_status"] = host_runtime_connectionState
        proc_phy_hosts_dict["power_status"] = host_runtime.powerState
        proc_phy_hosts_dict["MaintenanceMode"] = host_runtime.inMaintenanceMode
        host_runtime_bootTime = host_runtime.bootTime
        proc_phy_hosts_dict["boot_time"] = datetime.datetime.strftime(host_runtime_bootTime, "%Y-%m-%d %H:%M:%S")
        host_hardware = host_sum.hardware
        proc_phy_hosts_dict["vendor"] = host_hardware.vendor
        proc_phy_hosts_dict["model"] = host_hardware.model
        proc_phy_hosts_dict["cpuModel"] = host_hardware.cpuModel
        host_hardware_cpuMhz = host_hardware.cpuMhz
        host_hardware_numCpuPkgs = host_hardware.numCpuPkgs
        proc_phy_hosts_dict["numCpuPkgs"] = host_hardware_numCpuPkgs
        host_hardware_numCpuCores = host_hardware.numCpuCores
        proc_phy_hosts_dict["numCpuCores"] = host_hardware_numCpuCores
        proc_phy_hosts_dict["numCpuThreads"] = host_hardware.numCpuThreads
        proc_phy_hosts_dict["cpuMhz_total"] = host_hardware_cpuMhz * host_hardware_numCpuCores
        host_hardware_memorySize = host_hardware.memorySize
        proc_phy_hosts_dict["memorySize"] = sizeof_fmt(host_hardware_memorySize)
        host_config = host_sum.config.product
        proc_phy_hosts_dict["soft_version"] = host_config.fullName
        host_quickStats = host_sum.quickStats
        if host_runtime_connectionState == "connected":
            proc_phy_hosts_dict["vcenter_ip"] = host_sum.managementServerIp
            host_uptime = host_quickStats.uptime
            host_uptime_day = host_uptime / 60 / 60 / 24
            proc_phy_hosts_dict["uptime_day"] = "%d" % host_uptime_day
            host_quickStats_overallCpuUsage = host_quickStats.overallCpuUsage
            host_quickStats_overallMemoryUsage = host_quickStats.overallMemoryUsage
            host_cpu_usage_percentage = int(host_quickStats_overallCpuUsage) / \
                                        (host_hardware_cpuMhz * host_hardware_numCpuCores) * 100
            host_mem_usage_percentage = (int(host_quickStats_overallMemoryUsage) /
                                         (int(host_hardware_memorySize) / 1024 / 1024)) * 100
            proc_phy_hosts_dict["cpu_usage_percentage"] = "%.2f" % host_cpu_usage_percentage + "%"
            proc_phy_hosts_dict["mem_usage_percentage"] = "%.2f" % host_mem_usage_percentage + "%"
        else:
            proc_phy_hosts_dict["connect_status"] = host_runtime_connectionState
            proc_phy_hosts_dict["vcenter_ip"] = None
            proc_phy_hosts_dict["uptime_day"] = None
            proc_phy_hosts_dict["cpu_usage_percentage"] = None
            proc_phy_hosts_dict["mem_usage_percentage"] = None

        proc_phy_hosts_list.append(proc_phy_hosts_dict)

    return proc_phy_hosts_list


def get_phy_hosts(obj_phy_hosts):
    cl_phy_hosts_statistics_list = list()
    cl_phy_hosts = obj_phy_hosts.get_physical_host()
    for phy_hosts_msg in cl_phy_hosts:
        cl_phy_hosts_statistics_dict = dict()
        phy_hosts_content = phy_hosts_msg["phy_hosts"]
        if phy_hosts_content is not None:
            cl_phy_hosts_content = proc_phy_host(phy_hosts_content)
            cl_phy_hosts_statistics_dict["cluster_name"] = phy_hosts_msg["cluster_name"]
            cl_phy_hosts_statistics_dict["phy_hosts_msg"] = cl_phy_hosts_content

            cl_phy_hosts_statistics_list.append(cl_phy_hosts_statistics_dict)

    return cl_phy_hosts_statistics_list


def proc_text(all_hosts_msg):
    text_list = list()
    if len(all_hosts_msg) != 0:
        text_list.append("cluster_name,hostname,server_ip,vcenter_ip,overallStatus,connect_status,power_status,"
                         "maintenancemode,boot_time,vendor,model,cpuModel,cpuMhz_total,numCpuPkgs,numCpuCores,"
                         "numCpuThreads,""memorySize,soft_version,uptime_day,cpu_usage_percentage,mem_usage_percentage" + "\n")
        for hosts_msg in all_hosts_msg:
            for hosts_c in hosts_msg["phy_hosts_msg"]:
                text_list.append(hosts_msg["cluster_name"] + ",")
                text_list.append(hosts_c["hostname"] + ",")
                text_list.append(str(hosts_c["server_ip"]) + ",")
                text_list.append(str(hosts_c["vcenter_ip"]) + ",")
                text_list.append(hosts_c["overallStatus"] + ",")
                text_list.append(hosts_c["connect_status"] + ",")
                text_list.append(hosts_c["power_status"] + ",")
                text_list.append(str(hosts_c["MaintenanceMode"]) + ",")
                text_list.append(hosts_c["boot_time"] + ",")
                text_list.append(hosts_c["vendor"] + ",")
                text_list.append(hosts_c["model"] + ",")
                text_list.append(hosts_c["cpuModel"] + ",")
                text_list.append(str(hosts_c["cpuMhz_total"]) + ",")
                text_list.append(str(hosts_c["numCpuPkgs"]) + ",")
                text_list.append(str(hosts_c["numCpuCores"]) + ",")
                text_list.append(str(hosts_c["numCpuThreads"]) + ",")
                text_list.append(str(hosts_c["memorySize"]) + ",")
                text_list.append(hosts_c["soft_version"] + ",")
                text_list.append(str(hosts_c["uptime_day"]) + ",")
                text_list.append(str(hosts_c["cpu_usage_percentage"]) + ",")
                text_list.append(str(hosts_c["mem_usage_percentage"]) + "\n")

    return text_list


def write_text(vc_ip, hosts_content):

    filename = vc_ip + "_" + "hosts_content" + ".txt"
    with open("/Users/zhangcong/Desktop/" + filename, "w+") as phy_hosts_file:
        phy_hosts_file.writelines(hosts_content)

    for hostc in hosts_content:
        print(hostc, end="")

    return 0


def run():
    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    create_connect_obj = vspc(ipaddress, user, passwd)
    all_phy_hosts_msg = get_phy_hosts(create_connect_obj)
    proc_files = proc_text(all_phy_hosts_msg)
    ret_value = write_text(ipaddress, proc_files)
    if ret_value == 0:
        print("Get data successfully...")
    else:
        print("Failed to get data...")


def main():
    run()


if __name__ == "__main__":
    main()
