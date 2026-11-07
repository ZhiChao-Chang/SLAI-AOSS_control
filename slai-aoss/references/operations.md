# 文件操作

下列命令在**当前终端所在机器**执行。要下载到训练服务器或 AFS，先按 [服务器端流程](server-download.md) 在目标环境准备工具、凭据和目录；无需服务器也运行 Codex。

`PY` 替换为 setup 打印的 Python 路径；所有对象参数是相对于已配置 prefix 的 key。先确认当前 profile，避免把数据发到别人的桶。普通已授权传输无需重复确认。

```sh
# 最多显示20项；--prefix 是当前配置前缀下的子前缀
PY scripts/aoss.py --profile course list --prefix dataset/ --limit 20
PY scripts/aoss.py --profile course head dataset/example.bin

# 单个文件上传，默认遇到已有对象就停止
PY scripts/aoss.py --profile course upload ./example.bin dataset/example.bin --sha256

# 下载到新文件，默认不覆盖；若对象有 sha256 元数据会校验它
PY scripts/aoss.py --profile course download dataset/example.bin ./downloaded-example.bin

# 明确覆盖已有对象或本地文件时，给对应命令加 --overwrite
```

SDK 工具支持 multipart 大文件传输，但目录需要另见 [ADS](ads-cli.md)。上传前 head 是防误覆盖检查，不是对并发写入的原子锁；多人同时写共享桶时用自己的唯一前缀，或按平台版本策略处理。

### 完整性与结果解释

- 上传默认核对远端字节数。`--sha256` 计算本地哈希并写对象元数据；这是上传方声明，不是远端内容的独立校验。
- 下载计算 SHA-256，并与对象元数据或显式 `--sha256 EXPECTED_HEX` 比较。已知哈希应来自可信来源。
- 高价值文件按用户授权往返下载，比较原文件与下载文件的 SHA-256。不要把 ETag 当哈希算法保证，multipart ETag 尤其不是 SHA-256。
- 下载使用临时文件，校验后才发布。默认 no-replace 使用同文件系统硬链接；FAT/某些共享盘不支持时换普通本地文件系统，不要自动转为覆盖。
- 上传期间原文件不要修改；远端对象在下载期间也可能被别人替换，需要强一致版本标识时与管理员确认平台能力。
- 网络失败时报告错误类型，先 head 目标确认状态。不能把未确认上传说成成功，也不盲目整批重试。

### 私有临时分享

只在用户确实请求分享指定对象时运行：

```sh
PY scripts/aoss.py --profile course presign dataset/example.bin --expires 3600 --output ./private-download-link.txt
```

链接写入默认不覆盖的私密文件，不打印到运行日志。默认1小时；工具限制不超过32400秒，临时凭据可能更早失效。签名在本地生成，head 只检查对象可读元信息，并不验证接收者网络或实际下载。

生成内网 endpoint 链接不会使它能从公网访问。不要删掉签名参数后声称私有对象可匿名下载；不改变桶 ACL。向用户展示或发送链接时注意它本身就是凭据，不自动发到群聊或外部服务。

### 不提供的管理能力

此工具不创建/删除桶、不删除对象、不改ACL、不购买配额、不启动CCI/ACP。上述操作不是普通传输的附带步骤；确有需求时按本次授权和官方工具单独处理。
