#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from vsphere_performance import VspherePerformance as vspfm
from setup_cluster import get_cluster_content
from numpy import *
import sys


def get_cluster_performance(vcenter_instance, obj_cluster):
    
    cl_perfm_list = list()
    for cl_content in obj_cluster:
        cl_perfm_dict = dict()
        cl_perfm = vcenter_instance.get_performance_data(cl_content)
        cl_perfm_dict["cluster_name"] = cl_content.name
        for i in cl_perfm:
            cl_perfm_dict["period_time"] = i.sampleInfo
            cl_perfm_dict["collect_data"] = i.value
        cl_perfm_list.append(cl_perfm_dict)

    return cl_perfm_list


def proc_cluster_performance(perfm_content, days):

    perfm_data_list = list()
    for single_cluster_perfm in perfm_content:
        perfm_data_dict = dict()
        data_list = list()
        perfm_data_dict["cluster_name"] = single_cluster_perfm["cluster_name"]
        perfm_data_dict["cycle"] = days
        single_cluster_collect_data = single_cluster_perfm["collect_data"]
        if single_cluster_collect_data is not None:
            for i in single_cluster_collect_data:
                data_dict = dict() 
                data_dict["id"] = i.id.counterId
                data_dict["data"] = i.value
                data_list.append(data_dict)
            perfm_data_dict["mon_data"] = data_list
            perfm_data_list.append(perfm_data_dict)

    return perfm_data_list


def proc_cpu_mem_average(all_mon_data):

    cpu_mem_average_list = list()
    monitor_msg = {"cpu.usage.average": 2, 'mem.usage.average': 24}
    for monitor_msg_key, monitor_msg_value in monitor_msg.items():
        for mon_data in all_mon_data:
            for mon_msg in mon_data["mon_data"]:
                cpu_mem_average_dict = dict()
                cpu_mem_average_dict["cluster_name"] = mon_data["cluster_name"]
                cpu_mem_average_dict["cycle"] = mon_data["cycle"]
                for monid_key, mon_value in mon_msg.items():
                    if mon_value == monitor_msg_value:
                        cpu_mem_average_dict["mon_name"] = monitor_msg_key
                        cpu_mem_average_dict["max"] = str(max(mon_msg["data"]) / 100) + "%"
                        cpu_mem_average_dict["min"] = str(min(mon_msg["data"]) / 100) + "%"
                        cpu_mem_average_dict["ave"] = str(int("%d" % mean(mon_msg["data"])) / 100) + "%"
                        cpu_mem_average_dict["new"] = str(mon_msg["data"][-1] / 100) + "%"
                        cpu_mem_average_list.append(cpu_mem_average_dict)

    return cpu_mem_average_list


def proc_text(get_average):
    
    text_list = list()
    for single_count in range(0, len(get_average)):
        single_count_key = list(get_average[single_count].keys())
        single_count_values = list(get_average[single_count].values())
        if single_count == 0:
            for i in range(0, len(single_count_key)):
                if i != len(single_count_key) - 1:
                    text_list.append(single_count_key[i] + ",")
                else:
                    text_list.append(single_count_key[i] + "\n")

            for n in range(0, len(single_count_values)):
                if n != len(single_count_values) - 1:
                    text_list.append(str(single_count_values[n]) + ",")
                else:
                    text_list.append(str(single_count_values[n]) + "\n")
        else:
            for n in range(0, len(single_count_values)):
                if n != len(single_count_values) - 1:
                    text_list.append(str(single_count_values[n]) + ",")
                else:
                    text_list.append(str(single_count_values[n]) + "\n")

    return text_list


def write_text(vc_ip, cpumem_ave, days):

    filename = vc_ip + "_" + "cpumem_ave" + "_" + days + ".txt"
    with open("/Users/zhangcong/Desktop/" + filename, "w+") as count_files:
        count_files.writelines(cpumem_ave)

    for s_cm_a in cpumem_ave:
        print(s_cm_a, end="")

    return 0


def run():
    
    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    days = sys.argv[4]
    create_connect_obj = vspfm(ipaddress, user, passwd, days)
    cluster_content = get_cluster_content(create_connect_obj)
    all_data_msg = get_cluster_performance(create_connect_obj, cluster_content)
    all_mon_data = proc_cluster_performance(all_data_msg, days)
    get_average = proc_cpu_mem_average(all_mon_data)
    text_msg = proc_text(get_average)
    ret_value = write_text(ipaddress, text_msg, days)
    if ret_value == 0:
        print("Get data successfully...")
    else:
        print("Failed to get data...")


def main():
    run()


if __name__ == "__main__":
    main()
