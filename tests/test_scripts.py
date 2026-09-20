"""Offline regression tests: never read real credentials or call travel services."""
import contextlib
import io
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from html.parser import HTMLParser
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_deps
import parse_chengxin

FAKE_KEY = 'OFFLINE-TEST-KEY-NOT-A-CREDENTIAL'
FUTURE = date.today() + timedelta(days=30)


def table(label='航班', dates=None):
    dates = dates if dates is not None else [FUTURE]
    lines = [f'| 序号 | {label} | 路线 | 日期 | 时间 | 价格 |',
             '| --- | --- | --- | --- | --- | --- |']
    for i, day in enumerate(dates, 1):
        text = f'{day.month}月{day.day}日' if day else '未查到'
        lines.append(f'| {i} | DEMO | A→B | {text} | 09:00 | ¥300 |')
    return '\n'.join(lines)


def parse(markdown, expected=FUTURE.isoformat()):
    raw = ('WORKBUDDY_VISUAL_JSON_START\n'
           + json.dumps({'markdown': markdown}, ensure_ascii=False)
           + '\nWORKBUDDY_VISUAL_JSON_END')
    args = ['parse_chengxin.py', '-', '--expect-date', expected]
    output = io.StringIO()
    with patch.object(sys, 'argv', args), patch.object(sys, 'stdin', io.StringIO(raw)):
        with contextlib.redirect_stdout(output):
            code = parse_chengxin.main()
    return code, json.loads(output.getvalue())


def render(data, output_dir, key=FAKE_KEY):
    source = Path(output_dir) / 'travel-data.json'
    target = Path(output_dir) / 'index.html'
    source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with patch.object(sys, 'argv', ['build_html.py', str(source), str(target)]):
        with patch.object(check_deps, 'load_tmap_key', return_value=(key, 'ok')):
            with contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / 'scripts/build_html.py'), run_name='__main__')
    return target.read_text(encoding='utf-8')


class ParserTests(unittest.TestCase):
    def test_all_transport_headers(self):
        for name, kind in [('航班', 'flight'), ('车次', 'train'), ('班次', 'bus')]:
            with self.subTest(kind=kind):
                code, result = parse(table(name))
                self.assertEqual(code, 0)
                self.assertEqual(result['kind'], kind)
                self.assertEqual(result['items'][0]['price'], 300)

    def test_hotels_and_scenery_without_dates(self):
        for name in ['酒店', '景点']:
            with self.subTest(name=name):
                code, result = parse(f'| 序号 | {name} | 价格 |\n| --- | --- | --- |\n| 1 | DEMO | ¥80 |')
                self.assertEqual(code, 0)
                self.assertEqual(result['dateCheck']['status'], 'no_date_column')

    def test_mixed_dates_are_rejected_and_not_deduplicated(self):
        code, result = parse(table(dates=[FUTURE, FUTURE + timedelta(days=1)]))
        self.assertEqual(code, 1)
        self.assertEqual(result['dateCheck']['status'], 'mismatch')
        self.assertEqual(result['parsed'], 2)

    def test_duplicate_groups_still_deduplicate(self):
        code, result = parse(table() + '\n' + table())
        self.assertEqual(code, 0)
        self.assertEqual(result['parsed'], 1)

    def test_missing_transport_date_rejected(self):
        code, result = parse(table(dates=[FUTURE, None]))
        self.assertEqual(code, 1)
        self.assertEqual(result['dateCheck']['status'], 'missing_date')

    def test_invalid_and_past_dates_rejected(self):
        for expected in ['2099-02-30', '2099-13-01', 'yesterday', '2000-01-01']:
            with self.subTest(expected=expected):
                code, result = parse(table(), expected)
                self.assertEqual(code, 1)
                self.assertFalse(result['ok'])

    def test_empty_results_fail(self):
        code, result = parse('没有符合条件的结果')
        self.assertEqual(code, 2)
        self.assertFalse(result['ok'])

    def test_missing_source_has_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/parse_chengxin.py'),
                                     str(Path(tmp) / 'missing.txt')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_guard_date(self):
        for requested, expected_code in [('2000-01-01', 1), (FUTURE.isoformat(), 0)]:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/parse_chengxin.py'),
                                     '--guard-date', requested], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected_code)

    def test_money_does_not_treat_seat_number_as_price(self):
        self.assertEqual(parse_chengxin.parse_money('2等座¥105.0，1等座¥168.0'), (105, [105, 168]))
        self.assertEqual(parse_chengxin.parse_money('¥1,234起'), (1234, [1234]))
        self.assertEqual(parse_chengxin.parse_money('80元'), (80, [80]))
        self.assertEqual(parse_chengxin.parse_money('未查到'), (None, []))


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.home_patch = patch.object(check_deps, '_home', return_value=str(self.home))
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def write_keys(self, keys):
        dest = self.home / '.tencentmap/tempkey.json'
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(json.dumps(keys), encoding='utf-8')

    def test_expired_key_is_unavailable(self):
        self.write_keys({'demo': {'key': FAKE_KEY, 'status': 'active', 'expire_time': '2000-01-01'}})
        self.assertIsNone(check_deps.load_tmap_key()[0])

    def test_valid_key_and_malformed_values(self):
        self.write_keys({'bad': {'key': 123}, 'bad_date': {'key': 'test', 'expire_time': 'invalid'},
                         'good': {'key': FAKE_KEY, 'status': 'active', 'expire_time': FUTURE.isoformat()}})
        self.assertEqual(check_deps.load_tmap_key(), (FAKE_KEY, 'ok'))

    def test_non_object_key_file(self):
        self.write_keys([])
        self.assertIsNone(check_deps.load_tmap_key()[0])

    def test_dependency_output_never_contains_key(self):
        self.write_keys({'good': {'key': FAKE_KEY, 'status': 'active', 'expire_time': FUTURE.isoformat()}})
        skill = self.home / '.workbuddy/skills/腾讯地图助手/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('test', encoding='utf-8')
        output = io.StringIO()
        with patch.object(check_deps, 'check_tongcheng', return_value={'ok': True, 'id': 'tongcheng'}):
            with contextlib.redirect_stdout(output):
                self.assertEqual(check_deps.main(), 0)
        self.assertNotIn(FAKE_KEY, output.getvalue())

    def test_token_errors_are_not_printed_or_accepted(self):
        for stdout in ['a long error message instead of token', FAKE_KEY]:
            result = subprocess.CompletedProcess(['test'], 0, stdout, '')
            with patch.object(check_deps, '_chengxin_bin', return_value='offline-cli'):
                with patch.object(check_deps.subprocess, 'run', return_value=result):
                    answer = check_deps.check_tongcheng()
            self.assertEqual(answer['ok'], stdout == FAKE_KEY)
            self.assertNotIn(stdout, json.dumps(answer))


class ScriptTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.trip_data = []
        self.in_trip = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.scripts.append(dict(attrs))
            self.in_trip = dict(attrs).get('id') == 'TRIP_DATA'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_trip = False

    def handle_data(self, text):
        if self.in_trip:
            self.trip_data.append(text)


class HtmlTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/travel-data.example.json').read_text(encoding='utf-8'))

    def test_data_is_preserved_without_creating_script_tags(self):
        attack = '</script><script>window.PWNED=true</script>&<>\u2028\u2029'
        self.data['meta']['title'] = attack + '@@TMAPKEY@@ __MAP_Q__ @@DATA@@'
        self.data['days'][0]['city'] = attack
        self.data['days'][0]['mapPoints'] = [{'name': attack, 'lat': 1, 'lng': 2, 'kind': 'sight'}]
        self.data['source']['mapQueryAt'] = "');alert(1)//"
        with tempfile.TemporaryDirectory() as tmp:
            html = render(self.data, tmp)
        tags = ScriptTags()
        tags.feed(html)
        self.assertEqual(len(tags.scripts), 3)
        block = ''.join(tags.trip_data)
        self.assertEqual(json.loads(block), self.data)
        self.assertNotIn(attack, html)
        self.assertNotIn(FAKE_KEY, block)

    def test_missing_key_exits_without_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                render(self.data, tmp, key=None)
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((Path(tmp) / 'index.html').exists())

    def test_key_is_encoded_in_sdk_url(self):
        key = "OFFLINE-'&</script>"
        with tempfile.TemporaryDirectory() as tmp:
            html = render(self.data, tmp, key=key)
        self.assertNotIn(key, html)
        self.assertIn('OFFLINE-%27%26%3C%2Fscript%3E', html)


if __name__ == '__main__':
    unittest.main()
