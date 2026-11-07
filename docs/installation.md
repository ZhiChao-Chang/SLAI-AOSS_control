# 安装指南

[← 返回项目首页](../README.md)

## 交给 Codex 安装

将这段发给实际运行在自己电脑上的 Codex：

```text
请安装并使用这个仓库中的 slai-aoss skill，引导我配置商汤大装置平台 AOSS：
https://github.com/ZhiChao-Chang/SLAI-AOSS_control/tree/main/slai-aoss
```

Codex 可以使用内置的 `$skill-installer` 从仓库下载 `slai-aoss/`。安装后未识别到技能时，再重新打开会话。[OpenAI 官方安装说明](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use)

之后直接说：

```text
使用 $slai-aoss 帮我找到自己的桶和 endpoint，并先做只读连接验证。
```

默认面向已有学校资源的河套学生。Codex 会引导打开**商汤大装置平台**，核对账号、空间与区域，查找桶概览和 AccessKey 管理入口。AK/SK 由用户在自己的终端隐藏录入，不发到聊天。

## 备用：手动安装

仅在 Codex 无法直接安装时使用。先获取源码：

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

安装器默认放到 `~/.codex/skills/slai-aoss/`，设置 `CODEX_HOME` 时使用对应的 skills 目录。若当前 Codex 使用 `~/.agents/skills/` 等其他目录，通过 `--skills-dir` 指定。例如：

```sh
python3 install_skill.py --skills-dir ~/.agents/skills
```

Windows 与 WSL 是不同执行环境，应安装到真正运行 Codex 的环境。也可手动复制完整的 `slai-aoss/`，不要只复制 `SKILL.md` 或多套一层目录。

安装器只复制技能，不安装 SDK、不联网、不配置凭据、不访问存储桶。工具执行需要 Python 3.10+，首次使用时由 [配置流程](../slai-aoss/references/setup.md) 引导安装专用依赖环境。

## 更新

让 Codex 按当前仓库内容更新即可。手动安装时，默认不会覆盖已有同名 skill；明确更新可执行：

```sh
git pull
python3 install_skill.py --replace
```

旧版备份到 skills 目录之外的 `skill-backups/`，避免同时被发现。`--skills-dir` 等选项与首次安装时保持一致。

## 配置与服务器使用

凭据默认放在个人 `~/.config/slai-aoss/`，不在 skill 或本仓库中。Windows 的文件权限位不等同于 ACL，需使用自己的私有目录。不要把配置、`.aws`、环境文件或私密下载链接发到 GitHub。

服务器不需要安装 Codex。只在执行下载的服务器环境准备工具和自己的凭据，按 [服务器流程](../slai-aoss/references/server-download.md) 选择可达 endpoint，再下载到目标目录或已挂载 AFS。本地环境变量不会自动出现在服务器。

## 验证安装

技能工具提供无网络测试；用 setup 输出的 Python 执行：

```sh
PY slai-aoss/scripts/test_aoss.py
```

`PY` 代表实际解释器路径，不是命令名。真实连接需按配置文档执行只读验证；离线测试通过不代表你的账户已经连通。

仓库内的 [SHA256SUMS](../SHA256SUMS) 可校验源文件。分享仓库链接即可，不需要复制自己的配置目录。
