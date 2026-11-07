# 故障排查

只收集脱敏错误类型/服务错误码，不开启 SDK debug 或打印整个配置/环境变量。不要把网络错误自动升级成启动远程算力的授权。

| 现象 | 检查与下一步 |
|---|---|
| Python/boto3 缺失 | 使用 setup 打印的解释器，不混用 Windows、WSL 或系统 Python；离线环境需提前准备依赖 |
| 本地 doctor 成功、online 失败 | 前者没联网；检查实际 endpoint、VPN/网络、代理和证书 |
| DNS/连接超时 | 区分公网与内网域名、服务是否可达、出口策略；不要靠设公共读或关闭 TLS 解决 |
| TLS 验证失败 | 核对域名、系统时钟、CA 和组织代理；使用管理员提供的可信 CA，而非 verify=False |
| 403/AccessDenied | 核对账户、桶授权与操作权限；head/list/get/put 不等价。没有列桶权限不代表完全无权访问 |
| SignatureDoesNotMatch | 核对 endpoint 是否多拼了桶、签名 region、AK/SK 是否配对、临时 token/过期、系统时钟；不打印密钥逐字比较 |
| 404/NoSuchBucket/NoSuchKey | 检查区、大小写、profile prefix、对象 key；不能把所有404都归为文件不存在 |
| 301/重定向 | 从桶概览重新核对服务域名和 addressing style，不盲目把带桶地址填为服务 endpoint |
| Checksum/NotImplemented | 使用技能固定 SDK 版本及 when_required 配置；查具体兼容操作，不删除验证来掩盖真实损坏 |
| InvalidObjectState | 可能是归档/深冷对象，按官方恢复流程及用户授权处理，不把它当普通下载故障无限重试 |
| 上传默认被拒绝 | 工具先 head 防误覆盖；用户可能只有写权限没有 head 权限，需明确权限或改用已授权工具，不能把403当404 |
| 部分大文件失败 | 先确认远端大小/状态和本地源稳定性；可能遗留 multipart 碎片，获准后再清理 |
| 生成链接却打不开 | 内网可达性、签名参数是否完整、对象/凭据是否过期；生成成功不等于接收端下载成功 |

不要自动改已有密钥、桶权限、网络或软件环境。可以执行已授权范围内的明确修复；缺少信息时只询问影响下一步的非秘密项。
