# 首次配置

## 引导河套同学找到自己的配置

默认河套同学已经有学校提供的商汤大装置平台账户和资源。不要先问是否购买、要求重新注册或将“不会找配置”转成“找管理员”。直接引导操作；界面菜单名可能更新，以当前控制台为准。

1. 打开同学平常使用的**商汤大装置平台**，用自己的账户登录。
2. 检查页面当前账号、资源空间/项目和区域选择器，进入“对象存储 / AOSS”。这一步和 CCI/ACP 实例列表不同。
3. 在桶列表找到自己的桶或课程分配给自己的桶，打开桶概览/详情，记录**桶名**、服务/访问域名，以及公网、内网对应项。不要仅根据计算实例所在区域猜地址。
4. 点击头像/账户菜单中的“AccessKey访问密钥 / 访问密钥”入口，查找自己的 AK/SK。登录密码和模型 API key 都不能代替它。SK 往往只在创建时显示；已有安全保存的配对凭据就使用它，不能从 AK 推算 SK。确实没有可用的配对密钥时，再引导在自己的密钥页面创建新的配对密钥，不删除或轮换正在被其他工作使用的密钥。
5. Codex 只询问 endpoint、桶、前缀等非秘密项，让同学自己在终端隐藏录入 AK/SK；不要把控制台密钥页截图或秘密值发到聊天。

若桶列表看似空，先核对当前空间、区域和登录账号。出现实际拒绝访问时，再定位是哪一个桶、哪个操作和哪项授权出了问题；不把它预设为“所有同学都需要申请资源”。资源已存在不代表任意同学可使用他人的密钥或桶。

从桶概览复制服务 endpoint、桶名、所在网络。服务 endpoint 类似 `https://aoss.cn-sh-01g.sensecoreapi-oss.cn`；桶域名是 `https://example-course-bucket.aoss.cn-sh-01g.sensecoreapi-oss.cn`。SDK 工具填前者并单独填桶名，不能两次包含桶名。

- 普通个人电脑通常用公网 endpoint；课程 VPN/网络政策仍需满足。
- 内网域名通常带 `aoss-internal`，要在可达的网络执行；内网有桶不代表笔记本可以直接访问。
- 示例中的可用区不是固定值，一律以用户控制台为准。不要把 `cn-sh-01g` 直接当成 SDK 签名 region。
- SDK 签名默认 `us-east-1` 是可调整的兼容初值，不是用户桶真实 region 的断言。管理员提供签名 region 时按其值设置。
- 默认 virtual-hosted addressing；管理员明确给 path-style 要求时用 `--addressing-style path`。

## 安装依赖

需 Python 3.10+。在已安装 skill 的目录运行；路径包含空格时加引号。

Linux/macOS/WSL：

```sh
python3 scripts/setup.py
```

Windows PowerShell：

```powershell
py -3 scripts/setup.py
```

setup 建立独立虚拟环境，安装 `requirements.txt`，打印工具解释器路径。不要用 sudo pip，不改系统 Python。Python 有 venv 但缺少 ensurepip/pip 时，setup 自动从 PyPI 获取固定的 pip 25.3 wheel，核对其与 PyPI HTTPS 元数据的 SHA-256 后，仅在这个虚拟环境安装。该核对依赖 PyPI 与 HTTPS，不声称是独立签名验证。若连 venv 模块也没有，需按发行版安装 venv 组件；Windows 没有 Python 时先安装 Python 3.10+，WSL 内用 Linux 解释器。

后文用 `PY` 表示 setup 打印的真实解释器路径。运行时换成该路径；PowerShell 对带引号路径加 `&`，例如：

```powershell
& "$HOME\.config\slai-aoss\tool-venv\Scripts\python.exe" scripts/aoss.py --help
```

## 用户自行录入凭据

先与用户确认 endpoint、桶和前缀，不在聊天收 AK/SK。让用户在自己终端执行（示例必须替换）：

```sh
PY scripts/aoss.py --profile course configure --endpoint https://aoss.cn-sh-01g.sensecoreapi-oss.cn --bucket example-course-bucket --prefix my-course-work
```

终端依次隐藏询问 AK、SK、可选 session token。录入不会访问云端。长期 AK/SK 的 token 留空；临时凭据应填写配套 token，并注意有效期。

文件写入 `~/.config/slai-aoss/profiles/course.json`（非秘密连接信息）和 `~/.config/slai-aoss/credentials/course.json`（秘密）。POSIX 用 600/700；Windows 的 mode 位不等价于 ACL，用户需确保文件在自己的私有用户目录、未被共享或同步到公共位置。两者均不写入 skill，不放入 Git 或分享包。

再次配置默认不覆盖；用户明确更换自己的 profile 时才用 `--replace`。多个桶用不同 `--profile`。

已有安全环境注入时：

```sh
PY scripts/aoss.py --profile course configure --endpoint https://aoss.cn-sh-01g.sensecoreapi-oss.cn --bucket example-course-bucket --env-only
```

执行进程必须能看见 `AOSS_ACCESS_KEY_ID`、`AOSS_SECRET_ACCESS_KEY`，临时凭据再加 `AOSS_SESSION_TOKEN`。不要把值写在命令历史里；不要以“已在另一个终端 export”推断当前 Codex 子进程已继承它。`AOSS_CONFIG_HOME` 可改变配置根目录。助手不应读取密钥内容来证明变量存在。

## 验证

```sh
PY scripts/aoss.py --profile course doctor
PY scripts/aoss.py --profile course doctor --online
```

第一条仅验证本地配置和凭据是否可读，不访问网络。第二条只调用一次指定桶/前缀的 list（最多一项）；不是全账户列桶，也不写文件。没有 ListBucket 权限但允许已知对象读取时：

```sh
PY scripts/aoss.py --profile course doctor --online --key existing-file.txt
```

列举成功不代表拥有上传权限，head 成功也不证明可以下载归档内容。只有用户要求测试写入时才创建随机测试对象，并往返验证；不得为了“测试”将桶设为公共读。是否清理测试对象按用户指令。

下一步：在自己电脑操作见 [文件操作](operations.md)；要把桶内文件下载到服务器或 AFS，按 [服务器完整流程](server-download.md) 在服务器环境另做配置。
