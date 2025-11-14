# 🎯 JMComic QQ 机器人

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Android-lightgrey.svg)](README.md)
</div>

**平台状态说明：**
- ✅ **Windows系统**：已稳定可用
- 🧪 **Linux系统**：正在测试中，暂不推荐生产环境使用
- 🧪 **Android系统**：正在测试中，暂不推荐生产环境使用

> **注意**：Linux和Android平台的部署文档目前为测试版本，可能存在兼容性问题，请等待稳定版本发布后再进行部署。

> ✨ **智能漫画下载助手** - 基于 NapCat 的高性能 QQ 机器人，专为漫画爱好者设计

一个功能强大的 QQ 机器人，能够帮助用户轻松下载、管理和分享禁漫天堂的漫画内容。


### 🎯 核心功能
- 📥 **智能下载** - 通过漫画ID一键下载漫画内容
- 📤 **便捷发送** - 将已下载的漫画文件直接发送到QQ聊天
- 🔍 **状态监控** - 可查询下载进度和任务状态
- 📚 **内容管理** - 查看和管理已下载的漫画列表
- 📄 **格式转换** - 自动将图片转换为PDF格式，便于阅读
- 📱 **跨平台** - 支持Windows、Linux、Android

---

## 📦 Windows 部署

### 📋 环境要求

- 🪟 **Windows 10 或更高版本**
- 🐍 **Python >= 3.7**（推荐 Python 3.8+）
- 💾 **至少 4GB 可用存储空间**（根据下载漫画数量调整）
- 🌐 **稳定的网络连接**（支持代理配置）

### 🚀 部署步骤

#### 📥 第一步：获取项目文件

##### 1. 安装 Git（如未安装）
```bash
# 下载并安装 Git
# 访问 https://git-scm.com/downloads 下载Windows版Git
# 安装时选择"Use Git from the Windows Command Prompt"
# 验证安装：git --version
```

##### 2. 克隆项目到本地
```bash
# 创建项目文件夹
mkdir JMBot
cd JMBot

# 使用 Git 克隆项目
git clone https://github.com/AAA-huan/JM-QQ-Bot.git .
# 注意：使用.参数表示将代码克隆到当前JMBot目录，不会创建额外的子目录
```

#### ⚙️ 第二步：环境配置

##### 1. 安装 Python 环境
- 访问 [Python官网](https://www.python.org/downloads/) 下载最新版Python
- 安装时务必勾选「Add Python to PATH」选项
- 推荐安装 Python 3.8 或更高版本

##### 2. 创建虚拟环境
```bash
# 确保在JMBot项目文件夹内
# 鼠标右键打开powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
venv\Scripts\Activate

# 验证虚拟环境激活
python --version
pip --version
```

##### 3. 安装项目依赖
```bash
# 使用 pip 安装依赖（使用阿里云镜像加速）
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade
```

#### 🔧 第三步：配置机器人

##### 1. 复制配置文件
```bash
# 复制环境变量示例文件
copy .env.example .env

# 复制NapCat配置示例
copy napcat_config_example.yml napcat_config.yml

# 复制漫画下载配置示例
copy option_example.yml option.yml
```

##### 2. 编辑配置文件
打开 `.env` 文件，修改以下关键配置：

```ini
# ======================
# NapCat WebSocket 服务配置
# ======================
# WebSocket 服务地址 - 连接NapCat WebSocket服务的URL
# 把port替换为你实际的NapCat WebSocket服务端口
NAPCAT_WS_URL=ws://localhost:port/qq

# ======================
# 下载配置
# ======================
# 漫画下载存储路径 - 漫画文件下载的存储目录
MANGA_DOWNLOAD_PATH=./downloads

# ======================
# 安全配置
# ======================
# WebSocket服务令牌，与NapCat配置中的两个位置保持一致：
# - WebSocket服务配置部分的`token`字段
# - 中间件配置部分的`access-token`字段
# 
# 简化配置：只需设置NAPCAT_TOKEN一个字段即可
# 系统会自动将token添加到WebSocket连接URL中，无需手动添加
NAPCAT_TOKEN=""

# 为兼容原配置保留的令牌字段（优先级低于NAPCAT_TOKEN）
# 如果NAPCAT_TOKEN未设置，系统会尝试使用此值
ACCESS_TOKEN=
```

#### 四、配置 napcat_config.yml

打开`napcat_config.yml`文件进行配置


1. **配置 WebSocket 服务**
   ```yaml
   # WebSocket 服务配置
     - type: websocket-server
       # 监听地址（通常保持默认即可）
       host: 0.0.0.0
       # 监听端口（确保与.env文件中的NAPCAT_WS_URL端口一致）
       port: 8080
       # 路径（必须设置为/qq，与.env文件中的NAPCAT_WS_URL路径一致）
       path: /qq
       # 是否启用访问令牌（用于认证）
       # 此token需要与.env文件中的NAPCAT_TOKEN保持一致
       # 留空表示不启用Token验证
       token: "your_secure_token_here"
   ```

2. **配置中间件的访问令牌**
   ```yaml
   # 默认中间件配置
   default-middlewares &default:
     # 与.env文件中的NAPCAT_TOKEN或ACCESS_TOKEN保持一致
     # 留空表示不启用Token验证
     access-token: 'your_secure_token_here'
   ```

3. **重要配置说明**：
   - **端口一致性**：确保`port`值与`.env`文件中`NAPCAT_WS_URL`的端口部分一致
   - **路径设置**：`path`必须设置为`/qq`，这是机器人正常工作的必要条件
   - **Token一致性**：如果启用token验证，必须确保以下三个位置的token值完全相同：
     * `napcat_config.yml`中的WebSocket服务`token`字段
     * `napcat_config.yml`中的中间件`access-token`字段
     * `.env`文件中的`NAPCAT_TOKEN`或`ACCESS_TOKEN`字段
   - **禁用token验证**：如果不需要身份验证，请将所有token字段都留空（""或''）

#### 五、配置 NapCat

1. **安装 NapCat**
   - 下载并安装 NapCat：https://github.com/NapNeko/NapCatQQ
   - 启动 NapCat 并扫码登录 QQ 账号

2. **加载配置文件**
   - 启动NapCat时，确保它能够加载到您配置的`napcat_config.yml`文件
   - 您也可以通过NapCat的WebUI界面进行配置（WebUI地址可在NapCat启动面板查看）

3. **验证配置**
   - 访问 NapCat 的 WebUI
   - 检查「网络配置」→「WebSocket 服务端」中的设置是否与您在文件中配置的一致
   - 确认路径(path)为 `/qq`
   - 确认token值与.env文件中的配置一致（如果启用了验证）

#### 六、启动机器人

   ```bash
   # 进入项目目录
   cd JMBot
   
   # 启动机器人
   python bot.py

   # 停止机器人
   Ctrl+C
   ```

#### 🔄 七、常态化启动

##### 1. 启动 NapCat 服务
- 确保 NapCat 已正确安装并配置
- 启动 NapCat 服务

##### 2. 激活虚拟环境并启动机器人
```bash
# 进入项目目录
cd JMBot

# 激活虚拟环境
venv\Scripts\Activate

# 启动机器人
python bot.py
```

##### 3. 验证运行状态
- 检查任务管理器是否有 `python.exe` 进程
- 查看日志文件确认机器人正常运行

##### 4. 停止程序
```bash
# 方法一：通过任务管理器结束 python.exe 进程

# 方法二：使用 PowerShell 命令
   ctrl + C
```

### 🎯 使用方法

在QQ群或私聊中发送以下命令：

- `漫画帮助` - 查看所有可用命令
- `漫画下载 350234` - 下载指定ID的漫画
- `发送 350234` - 发送已下载的漫画文件
- `查询已下载漫画` - 查看已下载漫画列表

---

## ❓ 常见问题解答

### 🚨 启动与连接问题

#### 1. 机器人无法启动
**问题描述：** 启动机器人时出现错误或无法连接
**解决方案：**
- 检查 NapCat 是否正常运行
- 确认 `.env` 文件中的 `NAPCAT_WS_URL` 配置正确
- 检查防火墙设置，确保端口 `port` 未被阻止
- 查看日志文件获取详细错误信息

#### 2. WebSocket 连接失败
**问题描述：** 无法连接到 NapCat WebSocket 服务
**解决方案：**
- 确认 NapCat 服务已启动并监听正确端口
- 检查 `NAPCAT_WS_URL` 格式是否正确（ws://localhost:port/qq）
- 验证网络连接和防火墙设置
- 如果启用了token验证，请确保.env文件中的`NAPCAT_TOKEN`与NapCat配置中的token和access-token字段值完全一致
- 检查WebSocket路径是否正确设置为`/qq`

### 📥 下载相关问题

#### 3. 漫画下载失败
**问题描述：** 下载漫画时出现错误或下载中断
**解决方案：**
- 检查网络连接是否稳定
- 确认下载路径 `MANGA_DOWNLOAD_PATH` 有写入权限
- 检查磁盘空间是否充足
- 尝试调整 `thread_count` 参数（降低并发数）

#### 4. 下载速度过慢
**问题描述：** 下载速度不理想或频繁中断
**解决方案：**
- 调整 `thread_count` 增加并发下载数
- 配置代理服务器提高连接稳定性
- 检查网络带宽和服务器状态

### 💬 消息与通信问题

#### 5. 消息发送失败
**问题描述：** 机器人无法发送消息到QQ
**解决方案：**
- 确认 NapCat 与QQ客户端的连接正常
- 检查机器人是否被QQ群或好友屏蔽
- 查看 NapCat 日志确认消息发送状态

#### 6. 命令无响应
**问题描述：** 发送命令后机器人无反应
**解决方案：**
- 确认命令格式正确（如：`下载漫画 漫画ID`）
- 检查机器人是否在线且正常运行
- 查看日志文件排查错误信息

### ⚡ 性能与优化

#### 7. 性能优化建议
**问题描述：** 机器人运行缓慢或占用资源过高
**解决方案：**
- 调整 `thread_count` 参数控制并发下载数
- 设置合理的 `timeout` 值避免长时间等待
- 定期清理下载目录释放磁盘空间
- 考虑使用代理服务器提高下载稳定性

#### 8. 内存占用过高
**问题描述：** 机器人占用过多系统内存
**解决方案：**
- 限制同时下载的漫画数量
- 定期重启机器人释放内存
- 监控日志文件排查内存泄漏

---

## 🔧 故障排除

### 日志查看

- **Windows**: 查看命令行窗口输出
- **Linux**: `sudo journalctl -u JMBot -f`
- **Android**: Termux 终端输出

### 错误代码说明

- **WebSocket连接失败**: 检查 NapCat 状态和配置
- **下载失败**: 检查网络和漫画ID有效性
- **权限错误**: 检查文件和目录权限
- **存储空间不足**: 清理下载目录或调整存储路径

### 性能优化

1. **调整下载线程数**：在 `option.yml` 中修改 `thread_count`
2. **使用代理**：如有网络限制，配置代理服务器
3. **定期清理**：删除不再需要的漫画文件释放空间

---

### 如何贡献

1. **报告问题**
   - 在GitHub Issues中描述您遇到的问题
   - 提供详细的错误信息和复现步骤

2. **功能建议**
   - 提出新的功能想法或改进建议
   - 描述使用场景和预期效果

## 📄 许可证

本项目基于 MIT 许可证开源发布。

```
MIT License

Copyright (c) 2024 AAA-huan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ⚠️ 免责声明

本项目仅作为技术学习和研究用途，作者不对任何不当使用本工具造成的后果负责。请用户自行承担使用风险，并确保遵守所在国家或地区的相关法律法规。

**重要提示：**
- 请尊重版权，仅下载和使用您拥有合法权限的内容
- 请勿将本项目用于商业用途
- 请遵守您所在国家或地区的法律法规
- 使用本工具产生的任何后果由使用者自行承担