#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import ssl
import atexit
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


class VsphereContent(object):

    def __init__(self, ipaddress, user, passwd):
        self.ipaddress = ipaddress
        self.user = user
        self.passwd = passwd

    def server_connect(self):

        try:
            local_certificate_ssl = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            local_certificate_ssl.verify_mode = ssl.CERT_NONE
            self.service_instance = SmartConnect(host=self.ipaddress,
                                                 user=self.user,
                                                 pwd=self.passwd,
                                                 port=443,
                                                 sslContext=local_certificate_ssl)
            atexit.register(Disconnect, self.service_instance)

        except IOError as io_error:
            print(io_error)

        if not self.service_instance:
            raise SystemExit("Unable to connect to host with supplied credentials.")

        return self.service_instance

    def get_vcenter_object(self):

        vcenter_content = self.server_connect().RetrieveContent()
        return vcenter_content

    def get_datacenter(self):

        obj_datacenter = self.get_vcenter_object()
        datacenter_content = obj_datacenter.viewManager.CreateContainerView(obj_datacenter.rootFolder, [vim.Datacenter],
                                                                            True)
        datacenter_inventory = datacenter_content.view

        return datacenter_inventory

    def get_cluster(self):

        cluster_list = list()
        datacenter_values = self.get_datacenter()
        for datacenter_value in datacenter_values:
            if datacenter_value is None:
                continue
            else:
                cluster_list.append(datacenter_value.hostFolder.childEntity)

        return cluster_list

    def get_physical_host(self):

        cl_physical_host_list = list()
        for obj_cluster in self.get_cluster():
            for cluster_content in obj_cluster:
                cl_phy_host = dict()
                cl_phy_host["cluster_name"] = cluster_content.name
                phy_hosts_len = len(cluster_content.host)
                if phy_hosts_len == 0:
                    cl_phy_host["phy_hosts"] = None
                else:
                    cl_phy_host["phy_hosts"] = cluster_content.host

                cl_physical_host_list.append(cl_phy_host)

        return cl_physical_host_list

    def get_phy_network(self):

        phy_network_list = list()
        phy_host_nework = self.get_physical_host()
        for vhost_list in phy_host_nework:
            if vhost_list["phy_hosts"] is not None:
                vhost_content = vhost_list["phy_hosts"]
                for vhost_nm in vhost_content:
                    phy_nework_dict = dict()
                    try:
                        for vhost_nt in vhost_nm.config.network.pnic:
                            phy_nework_card_dict = dict()
                            nt_device = vhost_nt.device
                            if nt_device.startswith("vmnic"):
                                phy_nework_dict["phy_host_name"] = vhost_nm.name
                                phy_nework_dict[nt_device] = phy_nework_card_dict
                                phy_nework_card_dict["pci"] = vhost_nt.pci
                                phy_nework_card_dict["mac"] = vhost_nt.mac
                                phy_nework_card_dict["driver"] = vhost_nt.driver
                                if vhost_nt.linkSpeed is not None:
                                    phy_nework_card_dict["connect"] = "linked"
                                    phy_nework_card_dict["duplex"] = vhost_nt.linkSpeed.duplex
                                    phy_nework_card_dict["speedMb"] = vhost_nt.linkSpeed.speedMb
                                else:
                                    phy_nework_card_dict["connect"] = "Unlinked"

                    except Exception as phy_host_error:
                        print("{0} connect error, {1}".format(vhost_nm.name, phy_host_error))

                    phy_network_list.append(phy_nework_dict)
            else:
                pass

        return phy_network_list

    def get_vswitch(self):

        cl_vhost_vswitch_list = list()
        cl_vhost_vswitch = self.get_physical_host()
        for vhost_list in cl_vhost_vswitch:
            if vhost_list["phy_hosts"] is not None:
                vhost_content = vhost_list["phy_hosts"]
                for vhost_nm in vhost_content:
                    cl_vhost_vswitch_dict = dict()
                    vswitch_content = list()
                    try:
                        for vhost_vswitch in vhost_nm.config.network.vswitch:
                            single_vhost_vswitch_dict = dict()
                            cl_vhost_vswitch_dict["phy_host_name"] = vhost_nm.name
                            single_vhost_vswitch_dict["vswitch_name"] = vhost_vswitch.name
                            single_vhost_vswitch_dict["vswitch_mtu"] = vhost_vswitch.mtu
                            single_vhost_vswitch_dict["vswitch_numPortsAvailable"] = vhost_vswitch.numPortsAvailable
                            single_vhost_vswitch_dict["vswitch_numPorts"] = vhost_vswitch.numPorts
                            single_vhost_vswitch_dict["vswitch_phy_nic"] = vhost_vswitch.pnic
                            single_vhost_vswitch_dict["vswitch_portgroup"] = vhost_vswitch.portgroup
                            vswitch_content.append(single_vhost_vswitch_dict)
                            cl_vhost_vswitch_dict["vswitch_content"] = vswitch_content

                    except Exception as phy_host_error:
                        print("{0} connect error, {1}".format(vhost_nm.name, phy_host_error))
                    cl_vhost_vswitch_list.append(cl_vhost_vswitch_dict)

        return cl_vhost_vswitch_list

    def get_dvs(self):

        obj_dvs = self.get_vcenter_object()
        dvs_content = obj_dvs.viewManager.CreateContainerView(obj_dvs.rootFolder, [vim.DistributedVirtualSwitch], True)
        dvs_inventory = dvs_content.view

        return dvs_inventory

    def get_datastore(self):

        cl_datastore_list = list()
        for obj_datastore in self.get_cluster():
            for cluster_datastore in obj_datastore:
                cl_datastore_dict = dict()
                if len(cluster_datastore.datastore) != 0:
                    cl_datastore_dict["cluster_name"] = cluster_datastore.name
                    cl_datastore_dict["datastore"] = cluster_datastore.datastore
                else:
                    cl_datastore_dict["cluster_name"] = cluster_datastore.name
                    cl_datastore_dict["datastore"] = None

                cl_datastore_list.append(cl_datastore_dict)

        return cl_datastore_list

    def get_virtualmachine(self):

        cl_vhost_vm_list = list()
        phy_hosts_list = self.get_physical_host()
        for vhost_list in phy_hosts_list:
            if vhost_list["phy_hosts"] is not None:
                vhost_content = vhost_list["phy_hosts"]
                for vhost_n in vhost_content:
                    single_vm_dict = dict()
                    single_vm_dict["cluster_name"] = vhost_list["cluster_name"]
                    single_vm_dict["vhost_name"] = vhost_n.name
                    if len(vhost_n.vm) != 0:
                        single_vm_dict["virtualmachine"] = vhost_n.vm
                        cl_vhost_vm_list.append(single_vm_dict)
                    else:
                        single_vm_dict["virtualmachine"] = None
                        cl_vhost_vm_list.append(single_vm_dict)
            else:
                pass

        return cl_vhost_vm_list


def main():
    run = VsphereContent(ipaddress="132.79.2.43", user="administrator@vsphere.local", passwd="Root@123")
    # print(run.get_dvs())
    for i in run.get_dvs():
        # print(dir(i))
        # print(i.name)
        print(i.summary.productInfo.vendor)

if __name__ == "__main__":
    main()
