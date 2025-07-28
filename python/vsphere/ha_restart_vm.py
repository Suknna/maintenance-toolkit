#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# 用于检测集群内因节点宕机发生重启的虚拟机

from pyVmomi import vim
from datetime import datetime
from vsphere_get_content import VsphereContent as vspc
import sys
import json

def get_events(serviceinst):

    event_manager = serviceinst.content.eventManager
    filter_spec = vim.event.EventFilterSpec()

    # 设置实体过滤器
    entity_spec = vim.event.EventFilterSpec.ByEntity()
    entity_spec.recursion = "all"

    # 设置事件id
    filter_spec.eventTypeId = ["com.vmware.vc.ha.VmRestartedByHAEvent"]
    # 创建事件收集器
    collector = event_manager.QueryEvent(filter_spec)
    return collector


def convert_time_cst(time_str):

    dt_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone()
    standard_time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
    return standard_time_str


def format_event(events_info):

    event_dict = {}

    for event in events_info:

        cluster_name = event.computeResource.name
        host_name = event.host.name
        vm_name = event.vm.name

        # # 如果 computeResource 不存在，创建一个新的条目
        if cluster_name not in event_dict:
            event_dict[cluster_name] = []

        # 添加子字典
        event_dict[cluster_name].append({
            "physical_machine": host_name,
            "display_name": vm_name,
            "address": str(vm_name.split("_")[-1]),
            "createdTime": convert_time_cst(str(event.createdTime)),
            "fullFormattedMessage": event.fullFormattedMessage
        })
    return event_dict


def run():
    ipaddress = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    create_connect_obj = vspc(ipaddress, user, passwd)
    connect_vcenter = vspc.server_connect(create_connect_obj)
    cluster_evn = format_event(get_events(connect_vcenter))
    print(json.dumps(cluster_evn, indent=4))


def main():
    run()


if __name__ == '__main__':
    main()
