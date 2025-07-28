import subprocess

def ping_host(host):
    """Ping单个主机并返回是否连通"""
    try:
        result = subprocess.run(['ping', '-c', '5', host], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              timeout=5)
        return result.returncode == 0
    except:
        return False

def ping_all(hosts_str):
    """Ping多个主机并打印结果"""
    hosts = hosts_str.splitlines()
    for host in hosts:
        host = host.strip()
        if host:  # 跳过空行
            status = "通" if ping_host(host) else "不通"
            print(f"{host}: {status}")

if __name__ == "__main__":
    # 示例用法 - 用户可以替换为自己的IP列表
    sample_ips = """
192.168.24.66
192.168.24.67
192.168.24.68
192.168.24.69
192.168.24.70
192.168.24.71
192.168.24.72
192.168.24.73
192.168.24.74
192.168.24.75
192.168.24.140
192.168.24.141
192.168.24.142
192.168.24.143
192.168.24.144
192.168.24.145
192.168.24.146
192.168.24.147
192.168.24.148
192.168.24.149"""
    ping_all(sample_ips)
