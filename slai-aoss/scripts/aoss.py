#!/usr/bin/env python3
"""AOSS via the official S3 SDK. Never put secrets in arguments or object URIs."""
from __future__ import annotations
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit


class UserError(Exception):
    pass


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def profile_paths(profile):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', profile):
        raise UserError('profile 只允许字母、数字、下划线和短横线，最多64字符。')
    root = Path(os.environ.get('AOSS_CONFIG_HOME', str(Path.home() / '.config/slai-aoss'))).expanduser()
    return root / 'profiles' / (profile + '.json'), root / 'credentials' / (profile + '.json')


def private_write(path, value, replace=False):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise UserError('拒绝向符号链接写入配置或私密链接。')
    if not replace:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(value)
        return
    fd, tmp = tempfile.mkstemp(prefix='.aoss-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(value)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def validate_config(raw):
    endpoint = raw.get('endpoint', '').strip().rstrip('/')
    u = urlsplit(endpoint)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:
        raise UserError('endpoint 必须为 HTTPS 服务地址，不含密钥、桶路径、对象路径或查询参数。')
    bucket = raw.get('bucket', '').strip()
    if not bucket or '/' in bucket or '\\' in bucket or any(c.isspace() for c in bucket):
        raise UserError('请填控制台中的桶名，不要填写整个 URL。')
    if u.hostname.startswith(bucket + '.'):
        raise UserError('这里需要不带桶名的服务 endpoint，避免重复拼接桶名。')
    style = raw.get('addressing_style', 'virtual')
    if style not in ('virtual', 'path'):
        raise UserError('addressing_style 必须为 virtual 或 path。')
    region = raw.get('region', 'us-east-1').strip()
    if not region:
        raise UserError('签名 region 不能为空。')
    prefix = raw.get('prefix', '').strip('/')
    mode = raw.get('credential_mode', 'local')
    if mode not in ('local', 'environment'):
        raise UserError('credential_mode 必须为 local 或 environment。')
    return dict(endpoint=endpoint, bucket=bucket, region=region, addressing_style=style,
                prefix=prefix, credential_mode=mode)


def load_config(profile):
    path, _ = profile_paths(profile)
    if not path.is_file():
        raise UserError('尚未配置这个 profile，先执行 configure。')
    return validate_config(json.loads(path.read_text(encoding='utf-8')))


def credentials(profile, env_only=False):
    ak, sk, token = (os.environ.get(k, '') for k in
                     ('AOSS_ACCESS_KEY_ID', 'AOSS_SECRET_ACCESS_KEY', 'AOSS_SESSION_TOKEN'))
    if ak or sk or token:
        if not ak or not sk:
            raise UserError('环境凭据不完整，需要同时设置 AOSS_ACCESS_KEY_ID 和 AOSS_SECRET_ACCESS_KEY。')
        return dict(access_key=ak, secret_key=sk, session_token=token)
    if env_only:
        raise UserError('本 profile 为 env-only，当前进程没有 AOSS 环境凭据。')
    _, path = profile_paths(profile)
    if not path.is_file():
        raise UserError('没有本 profile 的凭据，请在自己的终端 configure 或注入 AOSS 环境变量。')
    if path.is_symlink():
        raise UserError('凭据文件不能是符号链接。')
    if os.name == 'posix' and path.stat().st_mode & 0o077:
        raise UserError('凭据文件权限过宽，请在自己的终端将该文件设为 chmod 600。')
    c = json.loads(path.read_text(encoding='utf-8'))
    if not c.get('access_key') or not c.get('secret_key'):
        raise UserError('凭据文件不完整。')
    return c


def client(profile, config):
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise UserError('缺少 boto3；先运行 scripts/setup.py 并使用它输出的 Python。')
    c = credentials(profile, config['credential_mode'] == 'environment')
    return boto3.client('s3', endpoint_url=config['endpoint'], region_name=config['region'],
                        aws_access_key_id=c['access_key'], aws_secret_access_key=c['secret_key'],
                        aws_session_token=c.get('session_token') or None,
                        config=Config(signature_version='s3v4',
                                      s3={'addressing_style': config['addressing_style']},
                                      connect_timeout=10, read_timeout=60,
                                      retries={'mode': 'standard', 'total_max_attempts': 3},
                                      request_checksum_calculation='when_required',
                                      response_checksum_validation='when_required'))


def object_key(c, suffix, allow_empty=False):
    if suffix.startswith('/') or suffix.startswith('s3://'):
        raise UserError('对象参数应为桶内相对 key，不要填写完整 URI 或前导斜杠。')
    key = '/'.join(x for x in (c['prefix'], suffix) if x)
    if not key and not allow_empty:
        raise UserError('对象 key 不能为空。')
    return key


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def error_code(exc):
    return str(getattr(exc, 'response', {}).get('Error', {}).get('Code', ''))


def head_optional(s3, bucket, key):
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        if error_code(exc) in ('404', 'NoSuchKey', 'NotFound'):
            return None
        raise


def configure(args):
    path, secret_path = profile_paths(args.profile)
    if not args.replace and (path.exists() or secret_path.exists()):
        raise UserError('profile 已存在；换一个名称，或明确指定 --replace。')
    c = validate_config(dict(endpoint=args.endpoint, bucket=args.bucket, region=args.region,
                             prefix=args.prefix, addressing_style=args.addressing_style,
                             credential_mode='environment' if args.env_only else 'local'))
    secret = None
    if not args.env_only:
        if not sys.stdin.isatty():
            raise UserError('请在自己的交互终端 configure；已有环境变量时可用 --env-only。')
        ak = getpass.getpass('Access Key ID（隐藏输入）: ').strip()
        sk = getpass.getpass('Secret Access Key（隐藏输入）: ').strip()
        token = getpass.getpass('Session token（长期 AK/SK 留空）: ').strip()
        if not ak or not sk:
            raise UserError('AK/SK 不能为空，未保存。')
        secret = dict(access_key=ak, secret_key=sk, session_token=token)
    if secret is not None:
        private_write(secret_path, json.dumps(secret, indent=2), replace=args.replace)
    private_write(path, json.dumps(c, ensure_ascii=False, indent=2), replace=args.replace)
    emit(dict(configured=True, profile=args.profile, config_file=str(path),
              credentials='runtime environment' if args.env_only else 'private local file',
              network_accessed=False))


def upload(s3, c, args):
    src = Path(args.source).expanduser()
    if not src.is_file() or src.is_symlink():
        raise UserError('上传来源必须为普通文件；目录传输请阅读 ads-cli 指南。')
    key = object_key(c, args.key)
    if head_optional(s3, c['bucket'], key) is not None and not args.overwrite:
        raise UserError('对象已存在，默认不覆盖；确实需要时明确指定 --overwrite。')
    size = src.stat().st_size
    digest = sha256(src) if args.sha256 else None
    extra = {'Metadata': {'sha256': digest}} if digest else {}
    s3.upload_file(str(src), c['bucket'], key, ExtraArgs=extra)
    h = s3.head_object(Bucket=c['bucket'], Key=key)
    if h['ContentLength'] != size:
        raise UserError('上传后远端大小不一致，请确认对象状态，不要盲目重传。')
    emit(dict(uploaded=True, bucket=c['bucket'], key=key, bytes=size, local_sha256=digest,
              verification='remote size; SHA-256 metadata is not independent remote verification',
              note='existence precheck is not an atomic lock against concurrent writers'))


def download(s3, c, args):
    dest = Path(args.destination).expanduser()
    if dest.is_symlink() or (dest.exists() and not args.overwrite):
        raise UserError('本地目标已存在或是符号链接；请选择新路径，或明确覆盖普通文件。')
    key = object_key(c, args.key)
    h = s3.head_object(Bucket=c['bucket'], Key=key)
    expected = args.sha256 or (h.get('Metadata') or {}).get('sha256')
    if expected and not re.fullmatch('[0-9a-fA-F]{64}', expected):
        raise UserError('期望 SHA-256 格式不正确。')
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.aoss-download-', dir=dest.parent)
    os.close(fd)
    try:
        s3.download_file(c['bucket'], key, tmp)
        size = Path(tmp).stat().st_size
        if size != h['ContentLength']:
            raise UserError('下载字节数不匹配，未发布本地目标。')
        digest = sha256(tmp)
        if expected and digest.lower() != expected.lower():
            raise UserError('SHA-256 不匹配，未发布本地目标。')
        if args.overwrite:
            os.replace(tmp, dest)
        else:
            os.link(tmp, dest)  # atomic no-replace; the temp is on the same filesystem
        emit(dict(downloaded=True, file=str(dest), bytes=size, sha256=digest,
                  expected_sha256_matched=True if expected else None))
    finally:
        Path(tmp).unlink(missing_ok=True)


def run(args):
    if args.command == 'configure':
        return configure(args)
    c = load_config(args.profile)
    if args.command == 'doctor':
        credentials(args.profile, c['credential_mode'] == 'environment')
        info = dict(profile=args.profile, config=c, credential_available=True, network_checked=False)
        if args.online:
            s3 = client(args.profile, c)
            if args.key:
                s3.head_object(Bucket=c['bucket'], Key=object_key(c, args.key))
                info['operation'] = 'HeadObject'
            else:
                prefix = c['prefix'] + '/' if c['prefix'] else ''
                s3.list_objects_v2(Bucket=c['bucket'], Prefix=prefix, MaxKeys=1)
                info['operation'] = 'ListObjectsV2 (MaxKeys=1)'
            info['network_checked'] = True
        emit(info)
        return
    s3 = client(args.profile, c)
    if args.command == 'list':
        prefix = object_key(c, args.prefix, allow_empty=True)
        if c['prefix'] and not args.prefix:
            prefix += '/'
        rows, token = [], None
        while len(rows) < args.limit:
            kw = dict(Bucket=c['bucket'], Prefix=prefix, MaxKeys=min(1000, args.limit - len(rows)))
            if token:
                kw['ContinuationToken'] = token
            r = s3.list_objects_v2(**kw)
            rows.extend(dict(key=x['Key'], bytes=x['Size']) for x in r.get('Contents', []))
            token = r.get('NextContinuationToken') if r.get('IsTruncated') else None
            if not token:
                break
        emit(dict(bucket=c['bucket'], objects=rows[:args.limit], more_available=bool(token)))
    elif args.command == 'head':
        key = object_key(c, args.key)
        h = s3.head_object(Bucket=c['bucket'], Key=key)
        emit(dict(bucket=c['bucket'], key=key, bytes=h['ContentLength'],
                  last_modified=h.get('LastModified'), storage_class=h.get('StorageClass', 'STANDARD'),
                  metadata_sha256=(h.get('Metadata') or {}).get('sha256')))
    elif args.command == 'upload':
        upload(s3, c, args)
    elif args.command == 'download':
        download(s3, c, args)
    elif args.command == 'presign':
        key = object_key(c, args.key)
        s3.head_object(Bucket=c['bucket'], Key=key)
        url = s3.generate_presigned_url('get_object', Params=dict(Bucket=c['bucket'], Key=key),
                                       ExpiresIn=args.expires)
        private_write(Path(args.output), url + '\n')
        emit(dict(saved=str(Path(args.output).expanduser()), expires_seconds=args.expires,
                  note='持有链接者可访问该对象；生成链接不代表客户端已验证下载。'))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', default='default')
    sp = p.add_subparsers(dest='command', required=True)
    q = sp.add_parser('configure', help='仅保存本地配置，不访问桶')
    q.add_argument('--endpoint', required=True)
    q.add_argument('--bucket', required=True)
    q.add_argument('--region', default='us-east-1')
    q.add_argument('--prefix', default='')
    q.add_argument('--addressing-style', choices=['virtual', 'path'], default='virtual')
    q.add_argument('--env-only', action='store_true', help='仅保存非秘密配置，凭据运行时注入')
    q.add_argument('--replace', action='store_true')
    q = sp.add_parser('doctor')
    q.add_argument('--online', action='store_true')
    q.add_argument('--key')
    q = sp.add_parser('list')
    q.add_argument('--prefix', default='')
    q.add_argument('--limit', type=int, default=20)
    q = sp.add_parser('head')
    q.add_argument('key')
    q = sp.add_parser('upload')
    q.add_argument('source')
    q.add_argument('key')
    q.add_argument('--overwrite', action='store_true')
    q.add_argument('--sha256', action='store_true', help='本地哈希写元数据，不等于远端独立校验')
    q = sp.add_parser('download')
    q.add_argument('key')
    q.add_argument('destination')
    q.add_argument('--overwrite', action='store_true')
    q.add_argument('--sha256', help='从独立可信来源获得的期望SHA-256')
    q = sp.add_parser('presign')
    q.add_argument('key')
    q.add_argument('--output', required=True)
    q.add_argument('--expires', type=int, default=3600)
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.command == 'list' and not 1 <= args.limit <= 10000:
        p.error('--limit 必须为1..10000')
    if args.command == 'presign' and not 1 <= args.expires <= 32400:
        p.error('--expires 必须为1..32400秒，凭据可能更早失效')
    try:
        run(args)
        return 0
    except (UserError, FileExistsError, FileNotFoundError, PermissionError) as exc:
        emit(dict(ok=False, error=str(exc)))
    except Exception as exc:
        # SDK strings can contain headers or signed URLs; never emit raw exceptions.
        emit(dict(ok=False, error_type=type(exc).__name__, service_code=error_code(exc),
                  hint='检查 endpoint/权限/签名region/网络；不输出原始异常以免泄露凭据或签名链接。'))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
