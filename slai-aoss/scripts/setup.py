#!/usr/bin/env python3
"""Install in a user-owned venv; no credentials or bucket access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import venv


def ensure_pip(python):
    probe = subprocess.run([str(python), '-I', '-c',
                            'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("pip") else 1)'])
    if probe.returncode == 0:
        return
    # Debian/Ubuntu minimal Python can create a venv but lack ensurepip. Bootstrap
    # only this venv, using a pinned wheel verified against PyPI's HTTPS metadata.
    version = '25.3'
    print('该 Python 缺少 ensurepip/pip；从 PyPI 获取固定 pip wheel，仅安装到工具虚拟环境。', flush=True)
    with urllib.request.urlopen(f'https://pypi.org/pypi/pip/{version}/json', timeout=30) as response:
        metadata = json.load(response)
    wheel = next(x for x in metadata['urls'] if x['filename'].endswith('py3-none-any.whl'))
    with tempfile.TemporaryDirectory(prefix='aoss-pip-bootstrap-') as tmp:
        path = Path(tmp) / wheel['filename']
        with urllib.request.urlopen(wheel['url'], timeout=60) as response:
            body = response.read()
        if hashlib.sha256(body).hexdigest() != wheel['digests']['sha256']:
            raise SystemExit('pip wheel 哈希与 PyPI 元数据不一致，停止安装。')
        path.write_bytes(body)
        code = ('import sys,runpy; p=sys.argv[1]; sys.path.insert(0,p); '
                'sys.argv=["pip","install","--no-index",p]; runpy.run_module("pip",run_name="__main__")')
        subprocess.run([str(python), '-I', '-c', code, str(path)], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--venv', type=Path)
    args = p.parse_args()
    if sys.version_info < (3, 10):
        raise SystemExit('需要 Python 3.10+。')
    root = Path(os.environ.get('AOSS_CONFIG_HOME', str(Path.home() / '.config/slai-aoss')))
    target = (args.venv or root / 'tool-venv').expanduser().resolve()
    if not (target / 'pyvenv.cfg').exists():
        if target.exists() and any(target.iterdir()):
            raise SystemExit('目标不是虚拟环境且非空，请选择新的 --venv。')
        venv.EnvBuilder(with_pip=importlib.util.find_spec('ensurepip') is not None).create(target)
    python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    ensure_pip(python)
    requirements = Path(__file__).resolve().parents[1] / 'requirements.txt'
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
    subprocess.run([str(python), '-c', 'import boto3; print("boto3=" + boto3.__version__)'], check=True)
    print('安装完成；工具解释器：')
    print(python)
    print('尚未配置账户，尚未访问 AOSS。')


if __name__ == '__main__':
    main()
