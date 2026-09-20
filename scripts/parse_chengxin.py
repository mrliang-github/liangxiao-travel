# -*- coding: utf-8 -*-
"""解析同程 CLI 的 Markdown 输出，转结构化 JSON，并校验返回日期。

为什么需要它：
  同程接口只返回一整篇 markdown，没有结构化价格数组。比价、校验日期
  都必须先把表格抠出来。抠表的逻辑放在包里，才能保证每次运行结果一致。

用法：
  python3 parse_chengxin.py <同程输出文件>
  python3 parse_chengxin.py <同程输出文件> --expect-date 2026-09-26
  python3 parse_chengxin.py --guard-date 2026-09-01

选项：
  --expect-date YYYY-MM-DD  校验表格里的月日是否等于该日期（同程只给月日，不给年）
  --guard-date  YYYY-MM-DD  只做日期体检：早于今天直接报错，不解析文件
  --pretty                  缩进输出

退出码：
  0  正常
  1  日期有问题（已过去 / 月日不符）—— 调用方必须停下来，不能拿这份数据继续
  2  解析失败（没有 JSON 块 / 没有表格）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date

# 列名 → 语义。按关键词匹配，不依赖列的位置，兼容 5 套表头。
COL_RULES = (
    ('name', ('航班', '车次', '班次', '酒店', '景点', '名称')),
    ('date', ('日期',)),
    ('time', ('时间',)),
    ('duration', ('时长', '历时', '车程', '开放/游玩', '开放', '游玩')),
    ('price', ('价格', '票价')),
    ('rating', ('评分', '星级')),
    ('area', ('位置', '区域', '亮点', '特色')),
    ('booking', ('预订',)),
)

KIND_RULES = (
    ('flight', ('航班',)),
    ('train', ('车次',)),
    ('bus', ('班次',)),
    ('hotel', ('酒店',)),
    ('scenery', ('景点',)),
)


def load_payload(path):
    """取出 WORKBUDDY_VISUAL_JSON_START … END 之间的 JSON。"""
    try:
        if path == '-':
            text = sys.stdin.read()
        else:
            with open(path, encoding='utf-8') as stream:
                text = stream.read()
    except (OSError, UnicodeError):
        return None
    m = re.search(
        r'WORKBUDDY_VISUAL_JSON_START\s*(.*?)\s*WORKBUDDY_VISUAL_JSON_END',
        text, re.S,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def is_sep(cells):
    return all(set(c) <= set('-: ') for c in cells if c != '') and any(cells)


def parse_groups(md):
    """把 markdown 切成若干表格分组。同一篇里表头会重复出现（最便宜/最快/综合）。"""
    groups = []
    cur = None
    last_title = ''
    for line in md.splitlines():
        s = line.strip()
        if s.startswith('#'):
            last_title = s.lstrip('#').strip()
            continue
        if not s.startswith('|'):
            continue
        cells = split_row(s)
        if not cells or is_sep(cells):
            continue
        if cells[0] == '序号':
            cur = {'title': last_title, 'header': cells, 'rows': []}
            groups.append(cur)
            continue
        if cur is not None and cells[0].isdigit():
            cur['rows'].append(cells)
    return groups


def col_map(header):
    out = {}
    for i, h in enumerate(header):
        for key, words in COL_RULES:
            if key in out:
                continue
            if any(w in h for w in words):
                out[key] = i
                break
    return out


def kind_of(header):
    joined = ' '.join(header)
    for kind, words in KIND_RULES:
        if any(w in joined for w in words):
            return kind
    return 'unknown'


def parse_money(raw):
    """从 '¥447' / '二等座¥105.0，一等座¥168.0' 里取出所有金额。"""
    if not raw:
        return None, []
    nums = []
    number = r'(\d[\d,]*(?:\.\d+)?)'
    tokens = re.findall(r'[¥￥]\s*' + number, raw)
    if not tokens:
        tokens = re.findall(number + r'\s*元', raw)
    if not tokens and re.fullmatch(number + r'\s*起?', raw.strip()):
        tokens = re.findall(number, raw)
    for token in tokens:
        try:
            nums.append(float(token.replace(',', '')))
        except ValueError:
            pass
    nums = [n for n in nums if n > 0]
    return (min(nums) if nums else None), nums


def parse_md_date(raw):
    """'9月25日 周五' → ('09-25', 9, 25)。同程不给年份。"""
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', raw or '')
    if not m:
        return None, None, None
    mo, dy = int(m.group(1)), int(m.group(2))
    return '%02d-%02d' % (mo, dy), mo, dy


def booking_url(raw):
    m = re.search(r'\((https?://[^)]+)\)', raw or '')
    return m.group(1) if m else ''


def collect(groups):
    items, seen, kinds = [], set(), []
    for g in groups:
        cm = col_map(g['header'])
        k = kind_of(g['header'])
        if k not in kinds:
            kinds.append(k)
        for row in g['rows']:
            def cell(key):
                i = cm.get(key)
                return row[i] if i is not None and i < len(row) else ''
            md_date, mo, dy = parse_md_date(cell('date'))
            price, variants = parse_money(cell('price'))
            name = cell('name')
            rec = {
                'name': name,
                'route': cell('route') if 'route' in cm else '',
                'date': cell('date'),
                'dateMD': md_date,
                'time': cell('time'),
                'duration': cell('duration'),
                'price': price,
                'priceVariants': variants,
                'priceRaw': cell('price'),
                'rating': cell('rating'),
                'area': cell('area'),
                'booking': booking_url(cell('booking')),
                'group': g['title'],
                'kind': k,
            }
            # 交通类没有 route 列名，第 3 列就是走向；酒店/景区没有
            if not rec['route'] and k in ('flight', 'train', 'bus') and len(row) > 2:
                rec['route'] = row[2]
            key = (k, name, rec['route'], rec['date'], rec['time'], rec['priceRaw'])
            if not name or key in seen:
                continue
            seen.add(key)
            items.append(rec)
    return items, kinds


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('source', nargs='?', default=None)
    ap.add_argument('--expect-date', dest='expect', default=None)
    ap.add_argument('--guard-date', dest='guard', default=None)
    ap.add_argument('--pretty', action='store_true')
    args = ap.parse_args()

    # ---- 模式一：只做日期体检 ----
    if args.guard:
        try:
            want = date.fromisoformat(args.guard)
        except ValueError:
            print(json.dumps({'ok': False, 'error': 'bad_date',
                              'message': '日期格式应为 YYYY-MM-DD：%s' % args.guard},
                             ensure_ascii=False))
            return 1
        today = date.today()
        past = want < today
        out = {
            'ok': not past,
            'guardDate': args.guard,
            'today': today.isoformat(),
            'daysFromToday': (want - today).days,
            'message': (
                '日期 %s 已过去（今天 %s）。同程对过去的日期不会报错，会静默顺延一个月返回，'
                '必须让用户重新给日期。' % (args.guard, today.isoformat())
                if past else
                '日期可用（距今天 %d 天）。' % (want - today).days
            ),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if out['ok'] else 1

    # ---- 模式二：解析文件 ----
    if not args.source:
        print(json.dumps({'ok': False, 'error': 'no_source',
                          'message': '需要给同程输出文件路径，或用 --guard-date 只做日期体检。'},
                         ensure_ascii=False))
        return 2

    payload = load_payload(args.source)
    if not isinstance(payload, dict) or not isinstance(payload.get('markdown'), str):
        print(json.dumps({'ok': False, 'error': 'no_json_block',
                          'message': '文件里没找到 WORKBUDDY_VISUAL_JSON 块：%s' % args.source},
                         ensure_ascii=False))
        return 2

    groups = parse_groups(payload.get('markdown') or '')
    items, kinds = collect(groups)
    if not items:
        print(json.dumps({'ok': False, 'error': 'no_table_rows',
                          'message': '未解析出可用表格数据，不能当作查询成功。'},
                         ensure_ascii=False))
        return 2
    kind = kinds[0] if len(kinds) == 1 else ('mixed' if kinds else 'unknown')

    returned = sorted({i['dateMD'] for i in items if i['dateMD']})

    date_check = {'expected': args.expect, 'returned': returned, 'status': 'no_expectation',
                  'message': ''}
    if args.expect:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.expect):
                raise ValueError
            want = date.fromisoformat(args.expect)
        except ValueError:
            date_check.update(status='bad_expect',
                              message='--expect-date 必须是有效的 YYYY-MM-DD 日期')
        else:
            mo = want.strftime('%m-%d')
            missing = any(not i['dateMD'] and i['kind'] not in ('hotel', 'scenery')
                          for i in items)
            if want < date.today():
                date_check.update(status='past', message='请求日期已过去，必须重新确认日期。')
            elif missing:
                date_check.update(status='missing_date',
                                  message='交通结果含缺失或无法识别的日期，不能验证为可用。')
            elif not returned:
                date_check.update(status='no_date_column',
                                  message='这份结果没有日期列（酒店/景区通常没有），无法比对月日。')
            elif returned == [mo]:
                date_check.update(status='ok', message='返回日期的月日与请求一致。')
            else:
                date_check.update(
                    status='mismatch',
                    message='请求 %s，返回的月日却是 %s。同程对越界日期会静默换日期，'
                            '这份数据不可用，必须重查。' % (args.expect, '、'.join(returned)),
                )

    warnings = []
    if not items:
        warnings.append('没解析出任何数据行，检查源文件是否为空结果。')
    if kind == 'mixed':
        warnings.append('这篇结果混了多种类型（%s），按需分别处理。' % '、'.join(kinds))
    if len(returned) > 1:
        warnings.append('返回结果包含多个日期（%s），比价时注意区分。' % '、'.join(returned))
    if date_check['status'] == 'mismatch':
        warnings.append('日期校验未通过，禁止继续使用这份数据。')

    out = {
        'ok': date_check['status'] in ('ok', 'no_expectation', 'no_date_column'),
        'source': args.source,
        'kind': kind,
        'total': (payload.get('stats') or {}).get('total') if isinstance(payload.get('stats'), dict) else None,
        'parsed': len(items),
        'returnedDates': returned,
        'dateCheck': date_check,
        'warnings': warnings,
        'items': items,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
