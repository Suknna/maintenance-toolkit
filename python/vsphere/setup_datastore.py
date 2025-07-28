#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from vsphere_get_content import VsphereContent as vspc
import sys


def sizeof_fmt(num):
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def proc_datastore_content(obj_datastore):
    cl_datastore_list = list()
    for datastore_n in obj_datastore:
        cl_datastore_dict = dict()
        if len(datastore_n.host) > 1:
            cl_summary = datastore_n.summary
            cl_vol_name = cl_summary.name
            cl_datastore_dict["vol_name"] = cl_vol_name
            cl_capacity = cl_summary.capacity
            cl_datastore_dict["Capacity"] = sizeof_fmt(cl_capacity)
            cl_freespace = cl_summary.freeSpace
            cl_datastore_dict["Freespace"] = sizeof_fmt(cl_freespace)
            cl_uncommitted = cl_summary.uncommitted if cl_summary.uncommitted else 0
            cl_datastore_dict["Uncommitted"] = sizeof_fmt(cl_uncommitted)
            cl_provisioned = cl_capacity - cl_freespace + cl_uncommitted
            cl_datastore_dict["Provisioned"] = sizeof_fmt(cl_provisioned)
            cl_overp = cl_provisioned - cl_capacity
            cl_overp_pct = "%.2f" % ((cl_overp * 100) / cl_capacity) if cl_capacity else 0
            if cl_overp > 0:
                cl_datastore_dict["Over-provisioned"] = "{0}/{1}%".format(sizeof_fmt(cl_overp), cl_overp_pct)
            else:
                cl_datastore_dict["Over-provisioned"] = None
            cl_vhosts_num = len(datastore_n.host)
            cl_datastore_dict["Host_num"] = cl_vhosts_num
            cl_vm_num = len(datastore_n.vm)
            cl_datastore_dict["Vm_num"] = cl_vm_num
            cl_datastore_list.append(cl_datastore_dict)

    return cl_datastore_list


def get_datastore_connect(create_connect):
    cl_datastore_content_list = list()
    datastore = create_connect.get_datastore()
    for datastore_c in datastore:
        cl_datastore_content_dict = dict()
        datastore_s = datastore_c["datastore"]
        if datastore_s is not None:
            cl_das_c = proc_datastore_content(datastore_s)
            cl_datastore_content_dict["cluster_name"] = datastore_c["cluster_name"]
            cl_datastore_content_dict["datastore"] = cl_das_c
        cl_datastore_content_list.append(cl_datastore_content_dict)
    return cl_datastore_content_list


def proc_text(all_datastore_msg):
    text_list = list()
    if len(all_datastore_msg) != 0:
        text_list.append("cluster_name,datastore_name,Capacity,Freespace,Uncommitted,Provisioned,"
                               "Over-provisioned,Host_num,Vm_num" + "\n")
        for proc_data in all_datastore_msg:
            for data_ct in proc_data["datastore"]:
                text_list.append(proc_data["cluster_name"] + ",")
                text_list.append(data_ct["vol_name"] + ",")
                text_list.append(data_ct["Capacity"] + ",")
                text_list.append(data_ct["Freespace"] + ",")
                text_list.append(data_ct["Uncommitted"] + ",")
                text_list.append(data_ct["Provisioned"] + ",")
                if data_ct["Over-provisioned"] is None:
                    text_list.append("Normal" + ",")
                else:
                    text_list.append(data_ct["Over-provisioned"] + ",")
                text_list.append(str(data_ct["Host_num"]) + ",")
                text_list.append(str(data_ct["Vm_num"]) + "\n")
    else:
        print("There is no stored information that can be analyzed and processed")

    return text_list


def write_text(vc_ip, datastore_content):

    filename = vc_ip + "_" + "datastore" + ".txt"
    with open("/Users/zhangcong/Desktop/" + filename, "w+") as datastore_file:
        datastore_file.writelines(datastore_content)

    for dsc in datastore_content:
        print(dsc, end="")

    return 0


def run():
    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    create_connect_obj = vspc(ipaddress, user, passwd)
    all_datastore_msg = get_datastore_connect(create_connect_obj)
    proc_files = proc_text(all_datastore_msg)
    ret_value = write_text(ipaddress, proc_files)
    if ret_value == 0:
        print("Get data successfully...")
    else:
        print("Failed to get data...")


def main():
    run()


if __name__ == "__main__":
    main()
