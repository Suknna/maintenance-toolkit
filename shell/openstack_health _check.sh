#!/bin/bash
# Openstack服务健康检查
# 更新时间：20250722
# 作者：Suknna

# OpenStack集群登陆环境变量
export OS_PROJECT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=rrrtttt123
export OS_AUTH_URL=http://keystone-api.openstack.svc.cluster.local:5000/v3
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2

export OS_ENDPOINT_TYPE=internalURL
export CINDER_ENDPOINT_TYPE=internalURL
export OS_AUTH_TYPE=password
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_REGION_NAME=RegionOne
export OS_INTERFACE=internal

# check keystone service
if `openstack token issue > /dev/null 2>&1 `;then
    echo -e "\e[32mKeystone services is Ok\e[0m"
else
    echo -e "\e[31mKeystone services not Ok\e[0m"
    return 0
fi

# check nova service
if nova_cmd_result=`nova service-list 2>&1`;then
    result=`echo "$nova_cmd_result" | sed 's/  *//g' | awk -F "|" 'NR > 2 && NF > 1 && $0 !~ /^[-+| ]+$/ && ($6 != "enabled" || $7 != "up") {print $2,$3}'`
    if [ -z "$result" ];then
        echo -e "\e[32mNova services is Ok\e[0m"
    else
        echo -e "\e[31mNova services not Ok\e[0m"
        echo "Problematic services:"
        echo "$nova_cmd_result"
    fi
else
    echo -e "\e[31mNova service api abnormal\e[0m"
fi

# check glance service 
if `glance image-list > /dev/null 2>&1`;then
    echo -e "\e[32mGlance services is Ok\e[0m"
else
    echo -e "\e[31mGlance services not Ok\e[0m"
fi

#check cinder service
