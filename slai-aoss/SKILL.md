---
name: slai-aoss
description: 配置和使用 SLAI 所用的 SenseCore 大装置 AOSS 对象存储，指导安装工具、配置个人账户、验证连接、上传下载文件和生成临时分享链接。用户提到 AOSS、ads-cli 或大装置对象存储时使用；不用于 Amazon OpenSearch Serverless，也不管理 CCI/ACP 算力。
---

# SLAI AOSS 对象存储

面向已经配有 SLAI 资源的河套学生。默认用户已有学校配置的平台账户和资源，直接引导查找自己的连接信息，不从申请账户、购买资源或联系管理员开始。分享包不附带个人凭据、桶或算力入口。SLAI 使用的是 SenseCore 的 S3 兼容对象存储；不是本地磁盘或 AFS。

默认中文交流。相对路径均相对于本技能实际安装目录，不假定作者的用户名或项目目录。

## 首次配置

阅读 [首次配置](references/setup.md)。确认 Windows、macOS、Linux 或 WSL；Windows 与 WSL 的 Python、路径及配置分别处理。

先确认操作发生在同学电脑还是服务器。一步步引导用户在**商汤大装置平台**的控制台定位自己的**服务 endpoint**、桶名、公网/内网地址及 AK/SK 管理入口；只在聊天收集非秘密项。不会找不等于没有资源。不能根据 CCI/ACP 可用区猜桶的 endpoint。签名 region 未知时按文档默认值开始，遇到签名错误再核对。

用户只问配置时先配置和检查依赖；获准后只读验证。不自动购买资源、创建桶、设公共读、上传测试文件或启动服务器。现有授权范围内的普通上传下载直接完成，不反复询问。

凭据由用户在自己的终端通过隐藏输入配置，或经本次进程的 AOSS_ACCESS_KEY_ID / AOSS_SECRET_ACCESS_KEY 注入。不要让用户在聊天发送 AK/SK，不打印、不搜索无关账户密钥。

默认使用 scripts/aoss.py（boto3）：密钥不进入参数或 URI。依赖由 scripts/setup.py 安装到用户专用虚拟环境，不修改系统 Python。配置保存到 ~/.config/slai-aoss/，与技能目录分离，不得分享。

```sh
python scripts/setup.py
# 将 PY 替换为 setup 输出的解释器路径；示例 endpoint/桶须换成自己的
PY scripts/aoss.py --profile course configure --endpoint https://aoss.cn-sh-01g.sensecoreapi-oss.cn --bucket example-course-bucket
PY scripts/aoss.py --profile course doctor
PY scripts/aoss.py --profile course doctor --online
```

让用户自行在终端完成隐藏输入，Codex 不代填密码提示；已有环境变量可用 --env-only，见配置文档。

## 操作路由

- 文件列举、属性、上传、下载、临时链接：[操作说明](references/operations.md)。
- 服务器下载、AOSS 到服务器/AFS、电脑上传后服务器取回：[服务器端下载完整流程](references/server-download.md)。服务器无需安装或运行 Codex，工具和凭据须在执行下载的服务器环境配置。
- 大目录、数据集、增量同步、指定 ADS：[ads-cli](references/ads-cli.md)。先读实际版本帮助，不将 sync 当作内容哈希校验，不自动启用删除选项。
- 权限、签名、归档及网络错误：[故障排查](references/troubleshooting.md)。
- 上游资料和维护范围：[来源](references/sources.md)。

## 执行与结果

- HTTPS、证书校验默认开启，不以 insecure 绕过错误。内网域名只能在相应网络访问，不能因此擅自启动 CCI。
- 只处理指定桶/对象/前缀。传输授权不包含删除、ACL 修改、对外公开、创建资源或启动远程计算。
- 输出字节数与验证方式；multipart ETag 不等于 SHA-256。高价值文件可获准后往返下载比对哈希。
- 不记录 AK/SK、Authorization 或签名 URL。presign 默认写私密文件，不自动公开；临时链接本身是访问凭证。
- 超时后先确认对象状态，不无限重传。大文件中断可能遗留 multipart 碎片，清理另需授权。
- 不把离线测试、依赖安装或成功生成链接称为用户账户已连通/文件已取回。

## 开发验证

python scripts/test_aoss.py 使用临时目录和模拟客户端，不访问真实桶。真实服务验证需用户自己的配置及本次授权。
