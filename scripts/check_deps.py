# -*- coding: utf-8 -*-
"""运行时依赖检查。缺什么只提示什么，不打印任何 Key 原文。

退出码：
  0  同程已授权 + 腾讯地图 Key 可用，可以开始规划
  1  缺依赖，stdout 是给用户看的引导文案（Agent 必须原样展示，然后停）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date

SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _home():
    return os.path.expanduser('~')


def _chengxin_bin():
    cands = [shutil.which('tc-chengxin')]
    cands.append(os.path.join(
        _home(), '.workbuddy', 'binaries', 'node',
        'cli-connector-packages', 'bin', 'tc-chengxin'))
    for p in cands:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def check_tongcheng():
    """同程是连接器授权，不是 API Key。探测 `tc-chengxin token`。"""
    how = (
        '1. 打开 WorkBuddy → 插件 → 连应用\n'
        '2. 连接「同程旅行」或「同程程心」并完成授权\n'
        '3. 连上后再说「继续」\n'
        '不要向我粘贴 token / API Key。同程不走手填 Key。'
    )
    exe = _chengxin_bin()
    if not exe:
        return {
            'ok': False,
            'id': 'tongcheng',
            'title': '同程旅行连接器未安装',
            'how': how,
        }
    try:
        r = subprocess.run(
            [exe, 'token'],
            capture_output=True, text=True, timeout=12,
        )
    except Exception as e:
        return {
            'ok': False,
            'id': 'tongcheng',
            'title': '同程旅行连接器探测失败',
            'how': how + '\n（探测异常：%s）' % type(e).__name__,
        }
    out = ((r.stdout or '') + '\n' + (r.stderr or '')).strip()
    fail_marks = ('未登录', '凭证已失效', '重新连接', '未授权', 'not login', 'unauthorized')
    if r.returncode != 0 or any(m in out.lower() for m in fail_marks):
        return {
            'ok': False,
            'id': 'tongcheng',
            'title': '同程旅行连接器未授权',
            'how': how,
        }
    token = (r.stdout or '').strip().splitlines()
    token = token[-1].strip() if token else ''
    # 真 token 通常是一长串，不含空格和中文。过短或含中文都当失败，且绝不回显。
    if (len(token) < 16 or any(ch.isspace() for ch in token)
            or any('\u4e00' <= ch <= '\u9fff' for ch in token)):
        return {
            'ok': False,
            'id': 'tongcheng',
            'title': '同程旅行连接器未授权',
            'how': how,
        }
    return {'ok': True, 'id': 'tongcheng'}


def _tmap_skill_dirs():
    names = (
        '腾讯地图助手',
        'tencentmap-map-assistant',
        'tencentmap-map-assistant__skillhub',
    )
    roots = [os.path.join(_home(), '.workbuddy', 'skills')]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for name in entries:
            if name not in names:
                continue
            skill_md = os.path.join(root, name, 'SKILL.md')
            if os.path.isfile(skill_md):
                found.append(os.path.join(root, name))
    return found


def load_tmap_key():
    """供依赖检查和页面生成共用；返回值只在进程内使用，禁止写入日志。"""
    path = os.path.join(_home(), '.tencentmap', 'tempkey.json')
    if not os.path.isfile(path):
        return None, 'missing_file'
    try:
        with open(path, encoding='utf-8') as stream:
            data = json.load(stream)
    except Exception:
        return None, 'bad_file'
    today = date.today()
    cands = []
    if isinstance(data, dict):
        for v in data.values():
            if not isinstance(v, dict):
                continue
            key = v.get('key') or ''
            if not isinstance(key, str) or not key.strip():
                continue
            status = str(v.get('status') or 'active').lower()
            if status not in ('active', 'ok', ''):
                continue
            exp = str(v.get('expire_time') or '')[:10]
            if exp:
                try:
                    if date.fromisoformat(exp) < today:
                        continue
                except ValueError:
                    continue
            cands.append((exp, key.strip()))
    if not cands:
        return None, 'empty'
    cands.sort(key=lambda item: item[0], reverse=True)
    return cands[0][1], 'ok'


def check_tmap():
    skill_ok = bool(_tmap_skill_dirs())
    key_ok, key_reason = load_tmap_key()

    if skill_ok and key_ok:
        return {'ok': True, 'id': 'tmap'}

    bits = []
    if not skill_ok:
        bits.append(
            '【缺：腾讯地图助手 Skill】\n'
            '请先安装官方「腾讯地图助手」（tencentmap-map-assistant）。\n'
            'WorkBuddy 市场搜「腾讯地图助手」安装，或从 GitHub '
            'TencentLBS/tencentmap-map-assistant 拷到 ~/.workbuddy/skills/ 。'
        )
    if not key_ok:
        why = {
            'missing_file': '本机还没有 ~/.tencentmap/tempkey.json',
            'bad_file': '~/.tencentmap/tempkey.json 读失败或格式不对',
            'empty': 'Key 文件在，但没有仍有效的 active Key（可能过期）',
        }.get(key_reason, '未检测到可用 Key')
        bits.append(
            '【缺：腾讯地图 Key】\n'
            '%s\n'
            '不要把 Key 发给我、也不要写进这个 skill 包。\n'
            '装好「腾讯地图助手」后，在对话里说「申请腾讯地图体验 Key」，\n'
            '按它的引导用手机号收验证码。申请成功会自动写入：\n'
            '  macOS/Linux  ~/.tencentmap/tempkey.json\n'
            '  Windows      %%USERPROFILE%%\\.tencentmap\\tempkey.json' % why
        )
    return {
        'ok': False,
        'id': 'tmap',
        'title': '腾讯地图未就绪',
        'how': '\n\n'.join(bits),
    }


def main():
    items = [check_tongcheng(), check_tmap()]
    missing = [x for x in items if not x.get('ok')]
    if not missing:
        print('OK\ntongcheng=authorized\ntmap=key-ready')
        return 0

    lines = [
        'liangxiao-travel 还不能开始规划。下面缺的依赖需要你自己完成，我无法替你点授权或申请 Key。',
        '',
        '缺了：',
    ]
    for i, m in enumerate(missing, 1):
        lines.append('%d. %s' % (i, m.get('title') or m['id']))
    lines.append('')
    for m in missing:
        lines.append('—— %s ——' % (m.get('title') or m['id']))
        lines.append(m.get('how') or '')
        lines.append('')
    lines.append('做完后直接回「继续」，我会再检查一次。两样都过才会开始查票、出行程页。')
    lines.append('宿主必须是 WorkBuddy。Cursor / 纯 Claude 里同程连接器不可用。')
    print('\n'.join(lines).rstrip())
    return 1


if __name__ == '__main__':
    sys.exit(main())
