"""将页面同一份行程数据转换为 ima 可阅读的 Markdown；不依赖地图或凭据。"""
import math
import re


def text(value):
    value = str(value if value is not None else '').replace('\r', '')
    # 文档阅读器可能允许 HTML；外部店名、备注不能成为 HTML 或 Markdown 链接。
    value = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return re.sub(r'([\\`*_\[\]{}|])', r'\\\1', value).replace('\n', ' / ')


def amount(value):
    if type(value) in (int, float) and math.isfinite(value):
        return '免费' if value == 0 else '¥{:,.0f}'.format(value)
    return '未查到'


def price(value, kind):
    return amount(value) + ('（估算）' if kind == '估' else '')


def assert_no_credentials(data):
    secret_fields = {'key', 'apikey', 'tmapkey', 'token', 'accesstoken', 'secret', 'password', 'sessiontoken'}
    if isinstance(data, dict):
        for key, value in data.items():
            if re.sub(r'[^a-z]', '', key.lower()) in secret_fields:
                raise ValueError('行程数据包含凭据字段，请先移除后再生成')
            assert_no_credentials(value)
    elif isinstance(data, list):
        for value in data:
            assert_no_credentials(value)


def to_markdown(trip):
    m = trip['meta']
    lines = ['# 松鼠旅行官 · ' + text(m.get('title')), '',
             '{} 至 {} · {} 天 · {} 人'.format(text(m.get('dateStart')), text(m.get('dateEnd')),
                                             text(m.get('days')), text(m.get('people'))),
             '出发地：' + text(m.get('origin')), '目的地：' + ' → '.join(map(text, m.get('destinations', []))), '']
    if m.get('isExample'):
        lines += ['> 示例行程，展示历史资料整理效果，不是实时查询或预订依据。', '']
    if m.get('note'):
        lines += [text(m['note']), '']
    lines += ['## 每日行程', '']
    for i, day in enumerate(trip.get('days', []), 1):
        lines += ['### D{} · {} · {}'.format(i, text(day.get('date')), text(day.get('title'))),
                  '地点：' + text(day.get('city'))]
        for key, label in [('am', '上午'), ('pm', '下午'), ('evening', '晚上')]:
            if day.get(key):
                lines.append('- {}：{}'.format(label, text(day[key])))
        for hotel in trip.get('hotels', []):
            if hotel.get('date') == day.get('date'):
                lines.append('- 住宿：{} · {} · {}。{}'.format(text(hotel.get('name')), text(hotel.get('area')),
                             price(hotel.get('price'), hotel.get('priceType')), text(hotel.get('lockAdvice'))))
        for ticket in day.get('tickets', []):
            lines.append('- 门票 / 预约：{} · {}。{}'.format(text(ticket.get('name')),
                         price(ticket.get('price'), ticket.get('priceType')), text(ticket.get('note'))))
        for food in day.get('foods', []):
            lines.append('- 美食：{} · {} · 人均 {}。营业：{}'.format(text(food.get('name')), text(food.get('dish')),
                         price(food.get('avgPrice'), food.get('priceType')), text(food.get('openHours'))))
        for spot in day.get('photoSpots', []):
            lines.append('- 拍照参考：{} · {} · {}。来源：{}'.format(text(spot.get('name')), text(spot.get('bestTime')),
                         text(spot.get('tip')), text(spot.get('source'))))
        lines.extend('- 注意：' + text(w) for w in day.get('warnings', []))
        lines.append('')
    lines += ['## 交通比选', '']
    if not trip.get('flightsOrTrains'):
        lines += ['尚未查询交通班次和票价。', '']
    for f in trip.get('flightsOrTrains', []):
        lines.append('- {} {} {} → {}，{}–{}，单人 {}。{}'.format(text(f.get('date')), text(f.get('no')),
                     text(f.get('from')), text(f.get('to')), text(f.get('depart')), text(f.get('arrive')),
                     price(f.get('price'), f.get('priceType')), text(f.get('note'))))
    lines += ['', '## 预算', '']
    for b in (trip.get('budget') or {}).values():
        lines += ['### ' + text(b.get('title'))]
        lines.extend('- {}：{}'.format(text(k), amount(v)) for k, v in b.get('items', {}).items())
        lines += ['合计：{}；人均：{}。{}'.format(amount(b.get('total')), amount(b.get('perPerson')), text(b.get('note'))), '']
    lines += ['## 行前清单', '']
    lines.extend('- [{}] {}'.format('x' if t.get('done') else ' ', text(t.get('text'))) for t in trip.get('todos', []))
    lines += ['', '## 资料日期与限制', '']
    source = trip.get('source') or {}
    for key, label in [('tripQueryAt', '交通住宿查询'), ('mapQueryAt', '地图查询'), ('photoQueryAt', '攻略检索')]:
        lines.append('- {}：{}'.format(label, text(source.get(key)) or '未记录 / 未查询'))
    lines.extend('- ' + text(n) for n in source.get('notes', []))
    lines += ['', '本文是生成时的资料快照，不会自动更新票价、营业时间或预约库存。', '',
              '## 保存到腾讯 ima', '',
              '在 WorkBuddy 中选中这份文档 → 上传到云端 → ima 知识库；首次使用按官方入口授权。',
              '在 ima 中选择相应知识库并确认文档可检索后，再询问某天行程、住宿或待办。',
              '网页的勾选仅保存在本机浏览器，不会同步修改此文档或 ima。', '']
    return '\n'.join(lines)
