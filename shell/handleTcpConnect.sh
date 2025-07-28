#!/bin/bash
# 作者：王涣琦 Suknna
# 作用：定期采集连接数从执行的时间往前倒15分钟
# 备注：如果脚本输出-1表示从文件中获取采集数失败，-2表示/tmp/checktcpconnect.log不存在。


if [ -f /tmp/checktcpconnect.log ];then
    data=$(cat /tmp/checktcpconnect.log | grep -E "$(date +%Y-%m-%d) 10:5[5-9]:|$(date +%Y-%m-%d) 10:[6-9][0-9]:|$(date +%Y-%m-%d) 11:0[0-9]:|$(date +%Y-%m-%d) 11:10:|$(date +%Y-%m-%d) 14:5[0-5]|$(date +%Y-%m-%d) 15:0[0-9]" | awk -F ":" '{print $4}' | sort -n | tail -n 1 2>&1) || {
        echo -1
    }
    echo $data
else 
    echo -2
fi
