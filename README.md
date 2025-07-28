# 运维自动化工具集

> 自动化运维脚本集合，包含系统初始化、安全加固、虚拟机管理等功能

## 📦 安装依赖
```bash
# 安装Python3及pip
sudo apt install python3 python3-pip  # Debian/Ubuntu
sudo yum install python3 python3-pip  # CentOS/RHEL

# 安装Python依赖库
pip3 install pyvmomi  # vSphere操作依赖
```

## 📂 目录结构
```
.
├── python/                  # Python脚本主目录
│   ├── VMsoftware/          # 虚拟机相关操作
│   │   ├── init_system/     # 系统初始化配置
│   │   ├── package/         # 软件安装包资源
│   │   └── security/        # 安全加固脚本
│   └── vsphere/             # vSphere管理脚本
└── shell/                   # Shell脚本目录
```

## 🛠 核心功能模块

### vSphere管理 (`python/vsphere`)
- 集群配置/虚拟机管理/性能监控

### Utilities 方便自己的工具 (`Utilities/`)
- 批量ping

### 运维工具 (`shell/`)
- 服务配置/用户管理/健康检查

## ⏳ 版本历史
| 日期       | 版本 | 更新说明 |
|------------|------|----------|
| 2025-07-28 | v1.0 | 初始版本 |
