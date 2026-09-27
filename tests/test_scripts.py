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
import trip_document

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


def render(data, output_dir, key=FAKE_KEY, local=False):
    source = Path(output_dir) / 'travel-data.json'
    target = Path(output_dir) / 'index.html'
    source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    args = ['build_html.py', str(source), str(target)] + (['--local-map'] if local else [])
    with patch.object(sys, 'argv', args):
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
                self.assertEqual(check_deps.main([]), 0)
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

    def test_missing_key_does_not_block_public_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = render(self.data, tmp, key=None)
            self.assertTrue((Path(tmp) / 'index.md').exists())
        self.assertIn('var MAP_KEY = "";', html)
        self.assertIn('松鼠旅行官', html)

    def test_public_html_never_reads_author_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'travel-data.json'
            source.write_text(json.dumps(self.data), encoding='utf-8')
            target = Path(tmp) / 'index.html'
            with patch.object(sys, 'argv', ['build_html.py', str(source), str(target)]):
                with patch.object(check_deps, 'load_tmap_key', side_effect=AssertionError('must not read credentials')):
                    with contextlib.redirect_stdout(io.StringIO()):
                        runpy.run_path(str(ROOT / 'scripts/build_html.py'), run_name='__main__')
            self.assertNotIn(FAKE_KEY, target.read_text(encoding='utf-8'))

    def test_missing_key_exits_only_for_explicit_local_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                render(self.data, tmp, key=None, local=True)
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((Path(tmp) / 'index.html').exists())

    def test_local_key_cannot_break_out_of_script(self):
        key = "OFFLINE-'&</script>"
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                html = render(self.data, tmp, key=key, local=True)
        self.assertNotIn(key, html)
        self.assertIn('encodeURIComponent(MAP_KEY)', html)
        self.assertIn('OFFLINE-', html)
        tags = ScriptTags()
        tags.feed(html)
        self.assertEqual(len(tags.scripts), 3)

    def test_different_trips_have_isolated_checklists(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = render(self.data, tmp)
            self.data['meta']['title'] = '另一个行程'
            second = render(self.data, tmp)
        pattern = r'var STORAGE_PREFIX = (.+);'
        self.assertNotEqual(re.search(pattern, first)[1], re.search(pattern, second)[1])

    def test_credentials_in_trip_data_rejected(self):
        self.data['source']['access_token'] = FAKE_KEY
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                render(self.data, tmp)
            self.assertFalse((Path(tmp) / 'index.html').exists())

    def test_query_dates_do_not_inherit_another_service_or_document_date(self):
        self.data['source'] = {'mapQueryAt': '2026-09-20'}
        self.data['meta']['updatedAt'] = '2026-09-27'
        with tempfile.TemporaryDirectory() as tmp:
            html = render(self.data, tmp)
        self.assertIn('交通住宿资料日期：未标注 · 地图资料日期：2026-09-20', html)
        self.data['source'] = {'tripQueryAt': '2026-09-19'}
        with tempfile.TemporaryDirectory() as tmp:
            html = render(self.data, tmp)
        self.assertIn('交通住宿资料日期：2026-09-19 · 地图资料日期：未标注', html)

    def test_markdown_matches_trip_and_escapes_external_content(self):
        attack = '<script>alert(1)</script>[click](javascript:alert(1))'
        self.data['days'][0]['title'] = attack
        doc = trip_document.to_markdown(self.data)
        self.assertNotIn('<script>', doc)
        self.assertNotIn('[click]', doc)
        self.assertIn('示例行程', doc)
        self.assertIn('未查到', doc)
        self.assertIn('不会自动更新', doc)
        with tempfile.TemporaryDirectory() as tmp:
            render(self.data, tmp)
            self.assertEqual((Path(tmp) / 'index.md').read_text(encoding='utf-8'), doc)


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'onboarding-state.json'

    def invoke(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_deps.main(['--state', str(self.state), '--json'] + list(args))
        return code, json.loads(out.getvalue())

    def guided(self, has_skill, has_key, connected):
        with patch.object(check_deps, '_tmap_skill_dirs', return_value=['official'] if has_skill else []):
            with patch.object(check_deps, 'load_tmap_key', return_value=(FAKE_KEY if has_key else None, 'test')):
                with patch.object(check_deps, 'check_tongcheng', return_value={'ok': connected, 'how': '去连应用授权'}):
                    return self.invoke('--mode', 'guided')

    def test_one_current_step_then_ready(self):
        cases = [(False, False, False, 'map_skill'), (True, False, False, 'map_key'),
                 (True, True, False, 'tongcheng'), (True, True, True, 'plan')]
        for skill, key, connected, stage in cases:
            code, state = self.guided(skill, key, connected)
            self.assertEqual(state['stage'], stage)
            self.assertEqual(code, 0 if stage == 'plan' else 1)
            self.assertNotIn(FAKE_KEY, self.state.read_text(encoding='utf-8'))

    def test_basic_mode_never_reads_credentials_and_survives_resume(self):
        with patch.object(check_deps, 'load_tmap_key', side_effect=AssertionError('secret read')):
            with patch.object(check_deps, 'check_tongcheng', side_effect=AssertionError('connector call')):
                code, state = self.invoke('--mode', 'basic')
                resumed_code, resumed = self.invoke()
        self.assertEqual((code, resumed_code), (0, 0))
        self.assertEqual(resumed['mode'], 'basic')
        self.assertFalse(any(resumed['capabilities'].values()))

    def test_resume_rechecks_previously_ready_configuration(self):
        self.guided(True, True, True)
        code, state = self.guided(True, False, True)
        self.assertEqual((code, state['stage']), (1, 'map_key'))

    def test_brief_is_preserved_but_secret_fields_are_not(self):
        brief = Path(self.tmp.name) / 'brief.json'
        brief.write_text(json.dumps({'origin': '武汉', 'people': 3, 'token': FAKE_KEY}), encoding='utf-8')
        self.invoke('--mode', 'basic', '--brief', str(brief))
        _, state = self.invoke()
        self.assertEqual(state['brief'], {'origin': '武汉', 'people': 3})
        self.assertNotIn(FAKE_KEY, self.state.read_text(encoding='utf-8'))

    def test_invalid_state_is_preserved_and_not_echoed(self):
        self.state.write_text('broken secret ' + FAKE_KEY, encoding='utf-8')
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = check_deps.main(['--state', str(self.state), '--mode', 'basic'])
        self.assertEqual(code, 2)
        self.assertEqual(self.state.read_text(encoding='utf-8'), 'broken secret ' + FAKE_KEY)
        self.assertNotIn(FAKE_KEY, error.getvalue())

    def test_symlink_state_cannot_overwrite_another_file(self):
        target = Path(self.tmp.name) / 'unrelated.json'
        target.write_text('leave untouched', encoding='utf-8')
        self.state.symlink_to(target)
        with contextlib.redirect_stderr(io.StringIO()):
            code = check_deps.main(['--state', str(self.state), '--mode', 'basic'])
        self.assertEqual(code, 2)
        self.assertEqual(target.read_text(encoding='utf-8'), 'leave untouched')


if __name__ == '__main__':
    unittest.main()
