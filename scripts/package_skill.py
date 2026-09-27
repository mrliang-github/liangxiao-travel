"""从明确的公开文件清单打包 Skill；不打包工作目录、凭据或个人行程。"""
import argparse
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description='打包松鼠旅行官')
    parser.add_argument('output', help='最终保留的 ZIP 绝对或相对路径')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = Path(args.output).resolve()
    if target.suffix != '.zip':
        parser.error('输出文件必须是 .zip')
    files = [root / name for name in ('SKILL.md', 'README.md', 'INSTALL.md', 'LICENSE', 'CHANGELOG.md')]
    for folder, pattern in [('scripts', '*.py'), ('references', '*.md'), ('examples', '*.json')]:
        files.extend(sorted((root / folder).glob(pattern)))
    if any(p.is_symlink() or not p.is_file() for p in files):
        parser.error('文件清单缺失或含符号链接，停止打包')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'liangxiao-travel/' + path.relative_to(root).as_posix())
    print('packaged {} files: {}'.format(len(files), target))


if __name__ == '__main__':
    main()
