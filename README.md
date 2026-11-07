# SLAI-AOSS_control

面向河套学生的 **商汤大装置平台 AOSS 对象存储 Codex Skill**。

引导同学找到自己的桶、endpoint 和 AccessKey，完成本地配置，再进行文件上传、下载和校验。也包含服务器直接从 AOSS 下载到本地目录或已挂载 AFS 的完整步骤。

这是学生使用的非官方工具，不代表 SLAI 或商汤官方产品；不附带共享账号、密钥或资源。默认同学已有学校配置的资源，不要求另行注册或购买。

## 直接交给 Codex 安装（推荐）

**不用自己下载 ZIP、解压或运行安装脚本。** 把下面这段直接发给自己电脑上的 Codex：

```text
请安装这个 GitHub 仓库中的 slai-aoss skill：
https://github.com/ZhiChao-Chang/SLAI-AOSS_control
技能目录是 slai-aoss。
安装完成后告诉我，再引导我找到商汤大装置平台上自己的桶和 endpoint。
AK/SK 让我在本机终端隐藏输入，不发到聊天；先做只读连接验证。
```

也可把技能目录的直接链接交给 Codex：
<https://github.com/ZhiChao-Chang/SLAI-AOSS_control/tree/main/slai-aoss>

Codex 可以使用内置的 `$skill-installer` 从 GitHub 安装。安装后未识别到技能时，再重新打开会话。接着发送：

```text
使用 $slai-aoss 帮我配置商汤大装置平台的 AOSS。
```

安装和工具准备由 Codex 引导完成；同学只需找到自己的资源信息，并在本机终端录入自己的凭据。[OpenAI 官方技能安装说明](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use)

<details>
<summary>备用：手动安装（Codex 无法直接下载安装时再看）</summary>

下载本仓库 ZIP 并完整解压，或：

```sh
git clone https://github.com/ZhiChao-Chang/SLAI-AOSS_control.git
cd SLAI-AOSS_control
```

Windows PowerShell：

```powershell
py -3 install_skill.py
```

macOS / Linux / WSL：

```sh
python3 install_skill.py
```

安装器将 `slai-aoss/` 放到当前用户的 `~/.codex/skills/slai-aoss/`，或 `$CODEX_HOME/skills/`。已有同名 skill 时默认停止，明确更新可加 `--replace`（自动备份旧版）。Windows 和 WSL 的安装位置是分开的，需安装到实际运行 Codex 的环境。

安装器本身不联网、不装工具依赖、不配置凭据、不访问桶。需要 Python 3.10+ 执行技能工具。


安装器默认使用 `~/.codex/skills/`；若当前 Codex 实际使用 `~/.agents/skills/` 等其他位置，可加 `--skills-dir` 指定对应目录。推荐优先让 Codex 根据自身环境安装，而不是同学手动判断。

</details>

## 如何引导首次使用

1. 确认操作发生在自己的电脑还是服务器。
2. 打开**商汤大装置平台**，核对自己的账号、资源空间和区域。
3. 进入对象存储/AOSS，打开自己桶的概览，找到桶名及公网/内网 endpoint。
4. 从头像菜单进入 AccessKey 管理。AK/SK 是对象存储凭据，不是模型 API key；同学在自己的终端隐藏录入，不发到聊天。
5. 先检查本地配置，再做指定桶/前缀的只读请求；之后按同学实际指令上传或下载。

找不到桶时先检查账号、区域和资源空间，不把“不会找配置”当成没有资源。

## 使用示例

```text
使用 $slai-aoss 列出 course profile 下的 results/，最多20项。
使用 $slai-aoss 上传我指定的文件，默认不覆盖已有对象。
使用 $slai-aoss 下载指定对象，并按可信 SHA-256 校验。
使用 $slai-aoss 教我把 AOSS 数据下载到服务器，说明每条命令在哪台机器执行。
使用 $slai-aoss 规划目录增量同步，先确认方向，不删除数据。
```

## 服务器端也能下载

服务器**不需要运行 Codex**。把工具放到服务器，在服务器配置自己的凭据及可达 endpoint，然后直接下载到服务器目录或已经挂载的 AFS；数据不必经过个人电脑中转。

详见 [服务器下载完整流程](slai-aoss/references/server-download.md)。本地环境变量不会自动继承到服务器；也不能把未挂载的 `/mnt/afs` 当成持久存储。

## 文档

- [完整中文安装与分享说明](安装与分享说明.txt)
- [Skill 入口](slai-aoss/SKILL.md)
- [找到配置与安装工具](slai-aoss/references/setup.md)
- [文件上传、下载、校验和临时链接](slai-aoss/references/operations.md)
- [服务器与 AFS 下载](slai-aoss/references/server-download.md)
- [ADS 目录和增量同步](slai-aoss/references/ads-cli.md)
- [故障排查](slai-aoss/references/troubleshooting.md)
- [官方资料与适用范围](slai-aoss/references/sources.md)

## 凭据与操作边界

- 凭据默认保存在个人 `~/.config/slai-aoss/`，与 skill 和仓库分离。不要把这个目录、`.aws`、环境文件或签名链接提交 GitHub。
- 默认 SDK 路线不把密钥放进命令参数。ADS 的某些版本使用含凭据 URI，进程参数暴露限制见对应文档。
- 默认 HTTPS，上传下载默认防误覆盖；不会自动删除对象、公开桶或启动 CCI/ACP。
- 预签名 URL 本身是临时访问凭证，不默认打印到日志或公开。
- 上传后的字节数验证和写入 SHA-256 元数据，不等于对远端内容做独立校验。SDK 小工具一次处理一个文件，目录传输按 ADS 指引。

## 验证范围

在 Linux 验证了工具首次安装、技能安装/更新及 **15 项无网络测试**，包括实际 boto3 配置与模拟请求、分页、防误覆盖、损坏下载拒绝发布和私密链接输出。Windows/macOS 提供安装指引，但没有宣称已做全平台实测。

```sh
# 在 skill 目录中执行，先安装专用 SDK 环境
cd slai-aoss
python3 scripts/setup.py
# 用 setup 输出的 Python 路径替换 PY
PY scripts/test_aoss.py
```

测试使用临时目录与模拟客户端，不读取真实账户或访问真实存储桶。安装成功不等于账户已连通；各自配置后仍需只读验证。

## 许可证

[MIT License](LICENSE)。依赖软件遵循各自许可证；不分发厂商工具二进制或课程账户资料。
