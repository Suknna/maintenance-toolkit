#!/bin/bash
# 重制用户密码适用红帽系列: RHEL、CentOS、Rocky、fedora、kylin、UOS、OpenEuler

#定义用户名
USERNAME="prometheus"
#定义用户密码
PASSWD="ROOT@!@#"
# 定义需要检查的文件列表
FILES=("/etc/passwd" "/etc/group" "/etc/shadow" "/etc/gshadow")

# 前置检查
command -v expect >/dev/null || { echo "错误: expect命令不存在 参考修复命令: yum install -y expect"; exit 1; }

# 设置当前shell环境变量
export LANG=C

# 1. 检查文件是否被加锁(i属性)
for file in "${FILES[@]}"; do
    if lsattr "$file" 2>/dev/null | grep -q "i"; then
        echo "$file 已被加锁(i属性)，正在解锁..."
        # 2. 解锁文件
        chattr -i "$file"
        if [ $? -eq 0 ]; then
            echo "$file 解锁成功"
        else
            echo "$file 解锁失败"
            exit 1
        fi
    else
        echo "$file 未被加锁"
    fi
done

# 3. 重置用户密码
# 检查用户是否存在
if ! id -u "$USERNAME" >/dev/null 2>&1; then
    echo "错误: 用户 $USERNAME 不存在"
    exit 1
fi

expect << EOF
spawn passwd $USERNAME
expect {
    "New password:" {
        send "$PASSWD\r"
        exp_continue
    }
    "Retype new password:" {
        send "$PASSWD\r"
        exp_continue
    }
    "passwd: all authentication tokens updated successfully." {
        exit 0
    }
    "BAD PASSWORD:" {
        send_user "错误: 密码不符合复杂度要求\n"
        exit 1
    }
    timeout {
        send_user "错误: 密码修改超时\n"
        exit 1
    }
    eof {
        exit 0
    }
}
EOF

if [ $? -eq 0 ]; then
    echo "密码修改成功"
else
    echo "密码修改失败"
    exit 1
fi

echo "所有操作已完成"
exit 0
