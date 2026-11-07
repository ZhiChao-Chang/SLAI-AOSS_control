# 从 AOSS 下载到服务器或 AFS

适用场景：同学已从电脑上传数据，现在想让训练服务器直接下载；或者数据本来已在自己的 AOSS 桶。服务器端**不需要安装 Codex**，只需要工具、可达的 endpoint 和自己的凭据。

## 1. 确认在哪里执行

先问清目标服务器和目标目录，并确认用户本次希望在该服务器执行下载。不能只因电脑上有 AOSS 配置就自动连接某台 CCI/ACP，更不能启动、切换或重启实例。

- 本地终端：能访问电脑磁盘，不能把电脑路径当成服务器路径。
- 已登录服务器的终端：下载文件将落在服务器。
- AFS：需要该服务器**已经挂载**的真实目录；挂载点不一定是 `/mnt/afs`。

用户只是要方法时给出步骤。用户已明确授权目标服务器上的下载时，可在该范围内执行必要传输，不再重复询问同一授权。

## 2. 将工具放到服务器

尚未开源前可将分享 ZIP 复制到用户已登录的服务器，或通过已有的 SSH/scp 入口传输。不要假定服务器上有同学电脑的 skill 文件。将下面命令中的用户名、地址、端口、文件名换成实际值；这只是模板：

```text
# 在自己的电脑终端执行
scp -P SSH_PORT slai-aoss-skill.zip USER@SERVER:~/
# 随后用已有入口登录目标服务器
ssh -p SSH_PORT USER@SERVER
```

如果服务器已有本 skill 或已配置工具，直接复用本次获准使用的安装；不重复下载。

以下在**服务器终端**执行，`slai-aoss-skill.zip` 表示实际上传的 ZIP 文件名：

```sh
python3 -m zipfile -e ./slai-aoss-skill.zip ./aoss-toolkit
cd ./aoss-toolkit/slai-aoss
python3 scripts/setup.py
```

无需执行 `install_skill.py`，因为服务器不一定运行 Codex。setup 的联网下载仅准备工具，不启动计算作业。若服务器无法访问 PyPI，先在可联网且匹配 Python/平台的环境准备依赖 wheel，再按现有环境管理方式离线安装，不为下载依赖擅自修改服务器网络。

setup 会打印 Python 路径。默认 Linux 路径可以这样保存（自定义了配置根目录时按实际输出改）：

```sh
AOSS_PYTHON="$HOME/.config/slai-aoss/tool-venv/bin/python"
```

## 3. 在服务器配置自己的桶

电脑的环境变量、Windows 配置或本地 profile **不会自动出现在服务器**。同学可在服务器终端隐藏录入自己的 AK/SK，或使用本次任务的安全环境注入；不能指望另一个终端 export 自动传过去。不把密钥写进 SSH/scp 命令、聊天或共享脚本。

从控制台复制该桶适用于服务器网络的 endpoint。SenseCore 内网服务器一般优先使用桶的内网地址；在其他云或个人服务器则按可达性选择公网地址，不能将“任何服务器”都当成 SenseCore 内网。不要机械替换域名字符串，使用控制台的真实地址。

下面的 endpoint、桶名、前缀为示例，必须替换；`course-server` 与电脑上 `course` 可以用不同 endpoint，但桶与对象前缀应指向同一数据：

```sh
"$AOSS_PYTHON" scripts/aoss.py --profile course-server configure \
  --endpoint https://aoss-internal.cn-sh-01g.sensecoreapi-oss.cn \
  --bucket example-course-bucket --prefix my-course-work

"$AOSS_PYTHON" scripts/aoss.py --profile course-server doctor --online
"$AOSS_PYTHON" scripts/aoss.py --profile course-server list --prefix dataset/ --limit 20
```

配置命令会隐藏询问 AK、SK 和可选 token。不默认修改已有 profile；重配要明确 `--replace`。多人共用同一 Unix/root 账户时，600 权限无法隔离同账户其他使用者，应采用个人账户或自己的短期凭据/安全注入，不声称密钥对同账户其他人不可见。

## 4. 下载到服务器普通目录

工具默认不覆盖已有文件，先检查目录和磁盘空间：

```sh
mkdir -p "$HOME/data"
df -h "$HOME/data"
"$AOSS_PYTHON" scripts/aoss.py --profile course-server download \
  dataset/example.bin "$HOME/data/example.bin"
```

这里读取的是桶内 `my-course-work/dataset/example.bin`，不是电脑上的文件。数据传输方向为 **AOSS → 服务器**，不需要再经过同学电脑。工具会报告字节数、SHA-256；有可信期望哈希时可加 `--sha256 EXPECTED_HEX`。用户明确需要替换旧文件时才加 `--overwrite`。

## 5. 下载到已挂载的 AFS

先由用户指出自己的真实 AFS 目录，再检查该路径所属挂载和剩余空间。例如 `findmnt -T ACTUAL_AFS_DIRECTORY`、`df -h ACTUAL_AFS_DIRECTORY`。确认它确实属于已有 AFS 挂载，不能在未挂载的空 `/mnt/afs` 下写数据并声称已经持久化。

用用户实际目录替换下面变量值后执行，不把 `YOUR_DIRECTORY` 当作真实用户名：

```sh
AOSS_DEST='/mnt/afs/YOUR_DIRECTORY/data/example.bin'
"$AOSS_PYTHON" scripts/aoss.py --profile course-server download dataset/example.bin "$AOSS_DEST"
```

与普通下载同一命令，区别只是**目标所在文件系统**。技能不自行挂载 AFS，不创建或重启 CCI/ACP。

## 6. 整个目录或增量下载

SDK 小工具目前一次处理一个文件，不冒充递归同步工具。整个数据集按 [ADS 大批量传输](ads-cli.md) 检查服务器实际工具版本、源前缀、目标路径和覆盖行为，使用 cp 或 sync；可在终端先 dryrun。ADS 地址中的凭据有进程参数暴露限制，按该文档选择合适凭据方案，不把真实 AK/SK 命令发到聊天。

概念方向：

```text
服务器上的 ads-cli --https sync
  SRC = 自己的桶/指定前缀（服务器可达 endpoint）
  DST = 自己的服务器目录或已验证挂载的 AFS 目录
```

不附加 `--delete-src`/`--delete-dst`。结果报告实际传输/跳过/失败数量；不能把 sync 的大小/时间戳判断当作逐文件 SHA-256 验证。

## 7. 反向传回和断线

训练结果从服务器回 AOSS：在同一个服务器工具目录执行 `upload LOCAL_FILE results/FILE`，之后同学电脑用其公网 profile 下载同一个桶/前缀的对象。仍不需要公开桶。

长时间下载可以在用户已有的 tmux/screen 会话运行；这些工具是否安装以实际环境为准，不自动创建后台任务。若中断，先确认对象与本地结果状态，工具不承诺跨进程断点续传。生成临时链接只能改变认证方式，不能让内网域名变成公网可达。
