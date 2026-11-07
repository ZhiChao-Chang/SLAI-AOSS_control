#!/usr/bin/env python3
"""Install the bundled skill only. No dependency install, credentials or network access."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-dir', type=Path, help='override target skills directory')
    parser.add_argument('--replace', action='store_true', help='back up an existing skill before replacing')
    args = parser.parse_args()
    src = Path(__file__).resolve().parent / 'slai-aoss'
    if not (src / 'SKILL.md').is_file():
        parser.error('请先完整解压分享包；安装脚本旁必须有 slai-aoss/SKILL.md。')
    if any(p.is_symlink() for p in src.rglob('*')):
        parser.error('技能包含符号链接，拒绝安装。')
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser()
    root = (args.skills_dir or home / 'skills').expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / 'slai-aoss'
    if dest.is_symlink():
        parser.error('目标是符号链接，拒绝覆盖。')
    if dest.exists() and not args.replace:
        parser.error('技能已存在；需更新时明确指定 --replace，旧版会备份。')
    backup = None
    with tempfile.TemporaryDirectory(prefix='.slai-aoss-install-', dir=root) as tmp:
        staged = Path(tmp) / 'slai-aoss'
        shutil.copytree(src, staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if dest.exists():
            # Keep backup outside discovery, and do not leave stale old files in the new skill.
            backup = root.parent / 'skill-backups' / ('slai-aoss-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            backup.parent.mkdir(parents=True, exist_ok=True)
            dest.rename(backup)
        try:
            staged.rename(dest)
        except Exception:
            if backup is not None and not dest.exists():
                backup.rename(dest)
            raise
    if backup is not None:
        print('旧版备份：', backup)
    print('已安装：', dest)
    print('请重新打开 Codex 会话，然后输入：使用 $slai-aoss 帮我配置自己的 AOSS，并先做只读验证。')
    print('只安装技能，尚未安装工具依赖、配置凭据或访问存储桶。')


if __name__ == '__main__':
    main()
