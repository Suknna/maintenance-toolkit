#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from vsphere_get_content import VsphereContent as vspc
import sys


def get_cluster_content(server_instance):
    
    cluster_content_list = list()
    cluster_content = server_instance.get_cluster()
    for single_cluster in cluster_content:
        for cluster in single_cluster:
            cluster_content_list.append(cluster)

    return cluster_content_list


def proc_cluster_content(cluster_msg):
    
    proc_cluster_list = list()
    for pr_cluster in cluster_msg:
        proc_cluster_dict = dict()

        proc_cluster_dict["cluster_name"] = pr_cluster.name
        proc_cluster_dict["config_status"] = pr_cluster.configStatus
        proc_cluster_dict["runing_status"] = pr_cluster.overallStatus

        # 获取集群详细信息
        cluster_summary = pr_cluster.summary
        proc_cluster_dict["numCpuCores"] = cluster_summary.numCpuCores
        proc_cluster_dict["numCpuThreads"] = cluster_summary.numCpuThreads
        proc_cluster_dict["numHosts"] = cluster_summary.numHosts
        proc_cluster_dict["numEffectiveHosts"] = cluster_summary.numEffectiveHosts
        proc_cluster_dict["numVmotions"] = cluster_summary.numVmotions
        proc_cluster_dict["numStorage"] = len(pr_cluster.datastore) - cluster_summary.numHosts
        proc_cluster_dict["numNetwork"] = len(pr_cluster.network)
        proc_cluster_dict["poweroffVM"] = cluster_summary.usageSummary.poweredOffVmCount
        proc_cluster_dict["totalVM"] = cluster_summary.usageSummary.totalVmCount

        # 获取集群资源使用情况
        cluster_resource_usage = pr_cluster.GetResourceUsage()
        cluster_cpu_used = cluster_resource_usage.cpuUsedMHz
        proc_cluster_dict["cpuUsed(MHz)"] = cluster_cpu_used
        cluster_cpu_total = cluster_resource_usage.cpuCapacityMHz
        proc_cluster_dict["cpuCapacity(MHz)"] = cluster_cpu_total
        cluster_mem_used = cluster_resource_usage.memUsedMB
        proc_cluster_dict["memUsed(MB)"] = cluster_mem_used
        cluster_mem_total = cluster_resource_usage.memCapacityMB
        proc_cluster_dict["memCapacity(MB)"] = cluster_mem_total
        cluster_storage_used = cluster_resource_usage.storageUsedMB
        proc_cluster_dict["storageUsed(MB)"] = cluster_storage_used
        cluster_storage_total = cluster_resource_usage.storageCapacityMB
        proc_cluster_dict["storageCapacity(MB)"] = cluster_storage_total

        if cluster_cpu_total != 0 or cluster_mem_total != 0:
            proc_cluster_dict["cpu_usage"] = "%.2f" % (cluster_cpu_used / cluster_cpu_total * 100) + "%"
            proc_cluster_dict["mem_usage"] = "%.2f" % (cluster_mem_used / cluster_mem_total * 100) + "%"
        else:
            proc_cluster_dict["cpu_usage"] = "Null"
            proc_cluster_dict["mem_usage"] = "Null"

        if cluster_storage_total != 0:
            proc_cluster_dict["storage_usage"] = "%.2f" % (cluster_storage_used / cluster_storage_total * 100) + "%"
        else:
            proc_cluster_dict["storage_usage"] = "Null"

        # vsphere DRS推荐优化配置
        cluster_drs_recommand = pr_cluster.drsRecommendation
        if len(cluster_drs_recommand) == 0:
            proc_cluster_dict["drs_recommand"] = "Null"
        else:
            proc_cluster_dict["drs_recommand"] = len(cluster_drs_recommand)

        proc_cluster_list.append(proc_cluster_dict)

    return proc_cluster_list


def proc_text(content_list):

    text_list = list()
    for single_cluster in range(0, len(content_list)):
        single_cluster_key = list(content_list[single_cluster].keys())
        single_cluster_values = list(content_list[single_cluster].values())
        if single_cluster == 0:
            for i in range(0, len(single_cluster_key)):
                if i != len(single_cluster_key) - 1:
                    text_list.append(single_cluster_key[i] + ",")
                else:
                    text_list.append(single_cluster_key[i] + "\n")
            for n in range(0, len(single_cluster_values)):
                if n != len(single_cluster_values) - 1:
                    text_list.append(str(single_cluster_values[n]) + ",")
                else:
                    text_list.append(str(single_cluster_values[n]) + "\n")
        else:
            for n in range(0, len(single_cluster_values)):
                if n != len(single_cluster_values) - 1:
                    text_list.append(str(single_cluster_values[n]) + ",")
                else:
                    text_list.append(str(single_cluster_values[n]) + "\n")
    return text_list


def write_text(vc_ip, file_content):

    filename = vc_ip + "_" + "cluster" + ".txt"
    with open("/home/BJCYiaos/vsphere_inspection/reports/" + filename, "w+") as cl_files:
        cl_files.writelines(file_content)

    for cluster_c in file_content:
        print(cluster_c, end="")

    return 0


def run():

    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    create_connect_obj = vspc(ipaddress, user, passwd)
    cluster_msg = get_cluster_content(create_connect_obj)
    all_cluster_msg = proc_cluster_content(cluster_msg)
    text_msg = proc_text(all_cluster_msg)
    ret_value = write_text(ipaddress, text_msg)
    if ret_value == 0:
        print("Get data successfully...")
    else:
        print("Failed to get data...")


def main():
    run()


if __name__ == "__main__":
    main()
