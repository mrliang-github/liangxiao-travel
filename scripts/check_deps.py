# -*- coding: utf-8 -*-
"""松鼠旅行官首次启用。只输出当前一步，不回显凭据。

0 = 可开始规划（查看 mode / capabilities）；1 = 等待配置；2 = 状态文件错误。
--state 显式保存到任务目录；恢复时永远重新检测，不能信任上次的 ready 状态。
"""
from __future__ import annotations

import json
import argparse
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
import tempfile

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


BRIEF_FIELDS = ('origin', 'destinations', 'dateStart', 'dateEnd', 'people', 'budget', 'preferences')


def clean_brief(value):
    if not isinstance(value, dict):
        raise ValueError('需求必须是 JSON 对象')
    # 白名单只保留旅行需求，不把凭据、授权结果或任意状态字段写回磁盘。
    result = {}
    for key in BRIEF_FIELDS:
        item = value.get(key)
        if item is None:
            continue
        if key == 'destinations':
            if not isinstance(item, list) or any(not isinstance(x, str) for x in item):
                raise ValueError('destinations 必须是文字列表')
            item = [x[:200] for x in item[:20]]
        elif key == 'people':
            if type(item) is not int or not 1 <= item <= 100:
                raise ValueError('people 必须是 1 到 100 的整数')
        elif not isinstance(item, (str, int, float)) or isinstance(item, bool):
            raise ValueError('需求字段格式不正确')
        elif isinstance(item, str):
            item = item[:2000]
        result[key] = item
    return result


def read_state(path):
    if not path:
        return {}
    target = Path(path)
    if target.name != 'onboarding-state.json' or target.is_symlink():
        raise ValueError('状态文件必须命名为 onboarding-state.json，且不能是符号链接')
    if not target.exists():
        return {}
    data = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schemaVersion') != 1:
        raise ValueError('状态文件版本不支持，原文件已保留')
    return data


def save_state(path, state):
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.onboarding-', delete=False) as stream:
            name = stream.name
            json.dump(state, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def onboarding_status(mode, brief):
    # 基础模式不触碰凭据或连接器。用户可以随时切回 guided 重新检查增强能力。
    if mode == 'basic':
        return {'schemaVersion': 1, 'mode': mode, 'stage': 'plan', 'brief': brief,
                'capabilities': {'map': False, 'tongcheng': False},
                'message': '基础攻略已就绪。继续使用已保存的旅行需求；缺必填项时一次补齐。'
                           '仅整理公开资料，不标实查票价、不编坐标；以后可再开通增强查询。'}
    map_skill = bool(_tmap_skill_dirs())
    map_key = bool(load_tmap_key()[0])
    tongcheng = check_tongcheng()
    capabilities = {'map': map_skill and map_key, 'tongcheng': bool(tongcheng['ok'])}
    if not map_skill:
        stage = 'map_skill'
        message = ('第 1 步：安装腾讯地图助手。\n'
                   '在 WorkBuddy 技能市场搜索「腾讯地图助手」并安装官方版本。\n'
                   '完成后回复「继续」，接着进行地图开通。无需寻找或填写 Key。')
    elif not map_key:
        stage = 'map_key'
        message = ('第 2 步：开通地图查询。\n'
                   '接下来由已安装的官方腾讯地图助手引导：阅读并同意服务协议 → 手机验证 → 自动保存 Key。\n'
                   '无需去控制台找 Key，也不要把 Key 复制到网页。由本人完成协议确认和手机验证。')
    elif not tongcheng['ok']:
        stage = 'tongcheng'
        message = '第 3 步：连接同程旅行。地图配置已检测到。\n' + tongcheng['how']
    else:
        stage = 'plan'
        message = ('配置检查通过，开始规划。沿用已有需求，不重复提问。\n'
                   '这是本地授权与有效期检查；实际查询失败时只处理对应服务，不能把失败当查询结果。')
    if stage != 'plan':
        message += '\n也可以回复「先做基础攻略」，暂时跳过增强查询；不会生成未经查询的票价或坐标。'
    return {'schemaVersion': 1, 'mode': mode, 'stage': stage, 'brief': brief,
            'capabilities': capabilities, 'message': message}


def main(argv=None):
    parser = argparse.ArgumentParser(description='松鼠旅行官 · 首次启用与恢复')
    parser.add_argument('--state', help='当前任务的 outputs/my-trip/onboarding-state.json')
    parser.add_argument('--brief', help='旅行需求 JSON 文件，只接收白名单字段')
    parser.add_argument('--mode', choices=('guided', 'basic'), help='用户选择后切换；默认恢复已有选择')
    parser.add_argument('--json', action='store_true', help='给 Agent 的结构化状态，不含 Key 或 token')
    args = parser.parse_args(argv)
    try:
        previous = read_state(args.state)
        brief = clean_brief(previous.get('brief', {}))
        if args.brief:
            brief.update(clean_brief(json.loads(Path(args.brief).read_text(encoding='utf-8'))))
        mode = args.mode or previous.get('mode', 'guided')
        if mode not in ('guided', 'basic'):
            raise ValueError('状态中的模式不支持')
        state = onboarding_status(mode, brief)
        save_state(args.state, state)
    except (OSError, ValueError, TypeError):
        # 不回显原始 JSON、路径内容或第三方错误，避免把混入的秘密写进日志。
        print('无法读取或保存启用状态。请检查任务文件格式与权限，原文件未被主动清理。', file=sys.stderr)
        return 2
    print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else state['message'])
    return 0 if state['stage'] == 'plan' else 1


if __name__ == '__main__':
    sys.exit(main())
