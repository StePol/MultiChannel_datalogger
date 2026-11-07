"""Console framing and real START/STOP/STATUS handlers without Pico startup."""
import ast
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serial_commands import SerialCommands, HELP_LINES, configuration_lines


class Input:
    def __init__(self, text=''):
        self.text = text
        self.calls = 0
    def read(self, count):
        self.calls += 1
        char, self.text = self.text[:count], self.text[count:]
        return char
    def poll(self, timeout):
        assert timeout == 0
        return [(self, 1)] if self.text else []


class ConsoleTests(unittest.TestCase):
    def test_partial_commands_crlf_case_and_backspace(self):
        source = Input('sta')
        reader = SerialCommands(source, source)
        self.assertIsNone(reader.read_command())
        source.text += 'rt\r\n status \nHELP\nSTOX\bP\n'
        self.assertEqual([reader.read_command() for _ in range(4)],
                         ['START', 'STATUS', 'HELP', 'STOP'])
        self.assertIsNone(reader.read_command())

    def test_bounded_work_and_overlong_suffix_not_executed(self):
        source = Input('x'*100 + 'START\nSTOP\n')
        reader = SerialCommands(source, source)
        self.assertIsNone(reader.read_command())
        self.assertEqual(source.calls, 64)
        self.assertEqual(reader.read_command(), '!LINE_TOO_LONG')
        self.assertEqual(reader.read_command(), 'STOP')
        source.text = 'STA\x00RT\nHELP\n'
        self.assertEqual(reader.read_command(), '!INVALID_CHARACTER')
        self.assertEqual(reader.read_command(), 'HELP')

    def test_poll_error_does_not_try_blocking_read(self):
        source = Input('START\n')
        reader = SerialCommands(source, types.SimpleNamespace(poll=lambda timeout: [(source, 16)]))
        self.assertIsNone(reader.read_command())
        self.assertEqual(source.calls, 0)

    def test_disconnect_clears_incomplete_command(self):
        source = Input('STA')
        reader = SerialCommands(source, source)
        reader.read_command()
        def fail(count):
            raise OSError('USB unavailable')
        source.text = 'R'
        source.read = fail
        self.assertIsNone(reader.read_command())
        self.assertEqual(reader.buffer, '')


class HandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        names = ('start_recording', 'stop_recording', 'serial_status', 'handle_serial_command')
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        cls.code = compile(ast.Module(body=nodes, type_ignores=[]), 'serial handlers', 'exec')
        loop = next(node for node in tree.body if isinstance(node, ast.While))
        button = next(node for node in loop.body if isinstance(node, ast.If)
                      and 'last_btn' in ast.unparse(node.test))
        cls.button = compile(ast.Module(body=[button], type_ignores=[]), 'button handler', 'exec')

    def setUp(self):
        self.messages = []
        self.files = []
        self.scans = []
        def filename(timestamp):
            self.files.append(timestamp)
            return '/sd/test_{}.csv'.format(len(self.files))
        def scan():
            self.scans.append(1)
            return ['rom']
        self.state = dict(
            mode='PAUZA', interval=60, filename='', roms=[], ds_v=[], posledny_zapis_ms=0,
            time=types.SimpleNamespace(ticks_ms=lambda: 12345, localtime=lambda: (2026,11,7,12,0,0,0,0),
                                       sleep_ms=lambda ms: None),
            ds_sensor=types.SimpleNamespace(scan=scan), new_recording_filename=filename,
            print=lambda *args: self.messages.append(' '.join(str(arg) for arg in args)),
            HELP_LINES=HELP_LINES, configuration_lines=configuration_lines,
            BUILD_VERSION='1.0.7-dev', BUILD_GIT_SHA='abc12345', BUILD_NUMBER='71', BUILD_DIRTY=True,
            sd_ready=True, ADS1256_ENABLED=True, ads_raw=False, ads_samples=8,
            ads_buffer=False, ads_divider=(True,10000,90000), ADS1256_VREF=2.503,
            ADS1256_AVDD=5, ads_values=[1]*8, ads_error='', settings_error=False,
            LED_EXT=types.SimpleNamespace(value=lambda value:None),
            last_btn=1, curr_btn=0)
        exec(self.code, self.state)

    def command(self, command):
        self.state['handle_serial_command'](command)

    def test_start_stop_are_idempotent_and_next_start_has_new_file(self):
        self.command('START')
        self.assertEqual(self.state['mode'], 'REC')
        self.assertEqual(self.state['posledny_zapis_ms'], 12345)
        self.assertEqual(self.state['ds_v'], [0])
        self.command('START')
        self.assertEqual(len(self.files), 1)
        self.command('STOP')
        self.assertEqual(self.state['mode'], 'PAUZA')
        self.command('STOP')
        self.command('START')
        self.assertEqual(self.state['filename'], '/sd/test_2.csv')
        self.assertEqual(len(self.scans), 2)
        self.assertEqual(self.state['ads_samples'], 8)
        self.assertEqual(self.state['ads_divider'], (True,10000,90000))

    def test_start_does_not_leave_menu_or_change_interval(self):
        for mode in ('ADC_MENU','ADC_SAMPLES','ADC_DIVIDER','TEST','SYNC','ADC_SWITCH'):
            self.state.update(mode=mode, interval=60)
            self.command('START')
            self.command('STOP')
            self.assertEqual(self.state['mode'], mode)
            self.assertEqual(self.state['interval'], 60)
        for interval in (-3,-2,-1,0,3,301):
            self.state.update(mode='PAUZA', interval=interval)
            self.command('START')
            self.assertEqual(self.state['mode'], 'PAUZA')
            self.assertEqual(self.state['interval'], interval)
        self.assertEqual(self.files, [])

    def test_no_sd_or_adc_keeps_existing_start_policy(self):
        self.state.update(sd_ready=False, ads_error='DRDY timeout', ads_values=None)
        self.command('START')
        self.assertEqual(self.state['mode'], 'REC')
        self.command('STATUS')
        text='\n'.join(self.messages)
        self.assertIn('sd=NOT_READY', text)
        self.assertIn('error=DRDY timeout', text)

    def test_failed_filename_lookup_leaves_pause(self):
        def fail(timestamp):
            raise OSError('filesystem error')
        self.state['new_recording_filename']=fail
        self.command('START')
        self.assertEqual(self.state['mode'], 'PAUZA')
        self.assertEqual(self.state['filename'], '')
        self.assertIn('[ERR] START', self.messages[-1])

    def test_status_help_unknown_command_are_read_only(self):
        before=dict(self.state)
        for command in ('STATUS','HELP','START 5','SET RAW ON','!LINE_TOO_LONG'):
            self.command(command)
        for key,value in before.items():
            self.assertEqual(self.state[key],value,key)
        text='\n'.join(self.messages)
        for item in ('1.0.7-dev', 'Rgnd=10000Ohm', 'Rin=90000Ohm', 'K=10.6',
                     'range_nom=0-53V', 'samples_effective=8', '[STATUS] END', '[HELP]', '[ERR]'):
            self.assertIn(item,text)
        self.state.update(ads_raw=True, ads_buffer=True)
        self.messages.clear()
        self.command('STATUS')
        self.assertIn('samples_effective=1','\n'.join(self.messages))
        self.assertIn('Zadc=40000000.0Ohm','\n'.join(self.messages))

    def test_reset_only_in_pause_and_sync_before_restart(self):
        events = []
        self.state.update(uos=types.SimpleNamespace(sync=lambda: events.append('sync')),
                          machine=types.SimpleNamespace(reset=lambda: events.append('reset')))
        for mode in ('REC','ADC_MENU','ADC_SAMPLES','ADC_DIVIDER','TEST','SYNC','ADC_SWITCH'):
            self.state['mode'] = mode
            self.command('RESET')
            self.assertEqual(events, [])
            self.assertEqual(self.state['mode'], mode)
            self.assertIn('[ERR] RESET', self.messages[-1])
        self.state['mode'] = 'PAUZA'
        self.command('RESET')
        self.assertEqual(events, ['sync', 'reset'])
        self.assertEqual(self.messages[-1], '[OK] RESET restarting firmware')
        self.assertTrue(any('RESET' in line for line in HELP_LINES))

    def test_failed_sync_refuses_reset(self):
        events = []
        def fail():
            raise OSError('storage failure')
        self.state.update(uos=types.SimpleNamespace(sync=fail),
                          machine=types.SimpleNamespace(reset=lambda: events.append('reset')))
        self.command('RESET')
        self.assertEqual(events, [])
        self.assertEqual(self.state['mode'], 'PAUZA')
        self.assertIn('[ERR] RESET sync failed', self.messages[-1])

    def test_button_and_serial_use_same_transition_functions(self):
        exec(self.button,self.state)
        self.assertEqual(self.state['mode'],'REC')
        self.assertIn('source=BUTTON',self.messages[-1])
        self.command('STOP')
        self.command('START')
        exec(self.button,self.state)
        self.assertEqual(self.state['mode'],'PAUZA')
        self.assertIn('source=BUTTON',self.messages[-1])
