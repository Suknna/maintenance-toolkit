#!/bin/bash

# OpenSSH升级脚本
# 更新时间：20250722
# 作者：Suknna

# 脚本配置
# openssh包名
OPENSSH_PATH="openssh-10.0p2.tar"
# openssh包解压后的目录
OPENSSH_DECOM_DIR="openssh-10.0p1"
# 工作目录
WORKER_DIR=$(pwd)

# 此处往下不要乱动!!!!!
echo "
+-----------------------------------------------------------------------+
注意:
    前置检查1和2如果失败请按照“Linux虚拟机模板”excel文档的中进行配置yum安装对应软件包
    前置检查3和4如果失败请按照“Linux虚拟机模板”excel文档中进行编译安装
    对应软件安装后继续执行脚本即可

安装信息:
    OpenSSH软件包位置: $OPENSSH_PATH
    OpenSSH软件包解压后的目录: $OPENSSH_DECOM_DIR
    升级过程中工作目录: $WORKER_DIR
    当前sshd服务状态: $(systemctl is-active sshd)
+-----------------------------------------------------------------------+

确认无误后脚本将在10秒后开始执行
"

for ((i=10; i>=1; i--)); do
    echo -n "."
    sleep 1
done
echo ""

echo "前置检查..."

echo "检查项1: 验证基础命令..."
command -v gcc >/dev/null || { echo "错误: gcc命令不存在 参考修复命令: yum install -y gcc gcc-c++*"; exit 1; }
command -v tar >/dev/null || { echo "错误: tar命令不存在 参考修复命令: yum install -y tar"; exit 1; }
command -v make >/dev/null || { echo "错误: make命令不存在 参考修复命令: yum install -y make"; exit 1; }
command -v strings >/dev/null || { echo "错误: strings命令不存在 参考修复命令: yum install -y binutils"; exit 1; }
echo "基础命令无问题"

echo "检查项2: 验证RPM开发包..."
rpm -q pam-devel >/dev/null || { echo "错误: pam-devel包未安装 参考修复命令: yum install -y pam-devel"; exit 1; }
echo "RPM开发包正常"

echo "检查项3: 验证OpenSSL版本..."
# 这种办法是获取机器内部动态链接库的环境变量，根据变量中的路径去读取二进制文件内容获取ssl版本。和configure配置过程中的检测方式一致。
openssl_ver=$(ldd `which openssl` | grep -E "libssl|libcrypto"  | awk -F " " '{print $3}' | xargs -i strings {} | grep -E "^OpenSSL\s+")
if ! echo "$openssl_ver" | grep -Eq '(1.1.1|3.)'; then
  echo "错误: OpenSSL版本不符合要求(需1.1.1或3.x.x), 请升级openssl"
  echo $openssl_ver
  exit 1
fi
echo "OpenSSL版本符合要求"

echo "检查项4: 验证zlib..."
gcc -E - <<<'#include <zlib.h>' >/dev/null 2>&1 || {
  echo "错误: zlib不存在, 请安装zlib"
  exit 1
}
echo "zlib存在"

echo "开始OpenSSH升级流程..."

echo "步骤1: 切换到 $WORKER_DIR 工作目录"
# 判断工作目录是否存在
if [ -d $WORKER_DIR ];then
    cd $WORKER_DIR || {
        echo "错误: 无法切换到 $WORKER_DIR 目录"
        exit 1
    }
else
    echo "工作目录不存在 $WORKER_DIR !"
    exit 1
fi

echo "步骤2: 解压$OPENSSH_PATH "
tar_command=""
case "$OPENSSH_PATH" in
    *.tar.gz)
        tar_command="tar zxvf"
        ;;
    *.tar)
        tar_command="tar xvf"
        ;;
    *)
        echo "无法解压文件, 未知的文件类型: $OPENSSH_PATH "
        exit 1
        ;;
esac

# 检查压缩包是否存在
if [ ! -f $OPENSSH_PATH ];then
    echo "错误: OpenSSH软件包不存在 $(pwd)/$OPENSSH_PATH "
    exit 1
fi

if tar_info=$($tar_command "$OPENSSH_PATH" 2>&1); then
    echo "解压完成"
else
    echo "错误: $OPENSSH_PATH 解压失败"
    echo "详细信息: $tar_info"
    exit 1
fi

echo "步骤3: 进入 $OPENSSH_DECOM_DIR 目录"
cd $OPENSSH_DECOM_DIR || {
    echo "错误: 无法进入$OPENSSH_DECOM_DIR\目录"
    exit 1
}

echo "步骤4: 执行configure..."
configure_info=$(./configure --prefix=/usr --sysconfdir=/etc/ssh --with-pam --with-md5-passwords --mandir=/usr/share/man 2>&1)
if [ $? -ne 0 ]; then
    echo "错误: configure执行失败"
    echo "$configure_info" | tail -10
    exit 1
fi
echo "configure完成"

echo "步骤5: 执行make编译..."
make_info=$(make 2>&1)
if [ $? -ne 0 ]; then
    echo "错误: make编译失败"
    echo "$make_info"
    exit 1
fi
echo "make编译完成"

echo "步骤6: 校验sshd配置文件..."
config_check_info=$(./sshd -t 2>&1)
if [ $? -ne 0 ]; then
    echo "错误: sshd配置校验失败"
    echo "$config_check_info"
    exit 1
fi
echo "配置文件检查完成"

echo "步骤7: 备份ssh配置文件"
sshd_config_bak_path="/opt/sshd_config_$(date +%Y-%m-%d)"
back_ssh_config_info=$(cp -rvf /etc/ssh/sshd_config $sshd_config_bak_path )
if [ $? -ne 0 ]; then
    echo "错误: 无法备份sshd配置文件"
    echo $back_ssh_config_info
    exit 1
fi
echo "配置文件备份完成, 备份目录: $sshd_config_bak_path "

echo "步骤8: 执行make install安装..."
make_install_info=$(make install 2>&1)
if [ $? -ne 0 ]; then
    echo "错误: make install安装失败"
    echo "$make_install_info"
    exit 1
fi
echo "make install安装完成"

echo "步骤9: 重启sshd服务..."
init_system=$(ps -p 1 -o comm=)
case "$init_system" in
    systemd)
        echo "检测到 systemd，使用 systemctl 重启 sshd..."
        systemctl restart sshd
        systemctl status sshd --no-pager
        ;;
    init)
        echo "检测到 SysV init，使用 service 重启 sshd..."
        if [ -f /etc/init.d/sshd ]; then
            service sshd restart
            service sshd status
        else
            echo "错误：未找到 /etc/init.d/sshd，请检查服务名称！" >&2
            exit 1
        fi
        ;;
     *)
        echo "错误：未知的初始化系统 '$init_system'，无法重启 sshd！" >&2
        exit 1
        ;;
esac

echo "步骤10: 清理环境"
cd $WORKER_DIR || {
    echo "OpenSSH升级操作已完成。但是无法回到工作目录 $WORKER_DIR 请手动清理 $WORKER_DIR/$OPENSSH_PATH 和 $WORKER_DIR/$OPENSSH_DECOM_DIR "
    exit 0
}
remove_OpenSSH_info=$(rm -rf $OPENSSH_DECOM_DIR 2>&1)
if [ $? -ne 0 ];then
    echo "OpenSSH升级操作已完成。但是删除 $OPENSSH_DECOM_DIR 失败, 请手动清理"
    echo $remove_OpenSSH_info
    exit 0
fi

remove_OpenSSH_Package=$(rm -rvf $OPENSSH_PATH )
if [ $? -ne 0 ];then
    echo "OpenSSH升级操作已完成。但是删除 $OPENSSH_PATH 失败, 请手动清理"
    echo $remove_OpenSSH_Package
    exit 0
fi
# 删除脚本本身
remove_shell_info=$(rm -rvf $0)
if [ $? -ne 0 ];then
    echo "OpenSSH升级操作已完成。但是删除脚本失败, 请手动清理"
    echo $remove_shell_info
    exit 0
fi
echo "OpenSSH升级流程完成"
cd $WORKER_DIR
exit 0
