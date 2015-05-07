# -*- coding: utf-8 -*-
from collections import deque, OrderedDict
import datetime as dt
import mock
import unittest
import pep8
import tempfile

from ensure import ensure
from path import path
import pytz
import six

import scriptter


PATH = path(__file__).abspath().dirname()
DATA = PATH / 'test-data'


class TestCodeFormat(unittest.TestCase):

    def test_pep8_conformance(self):
        """Test that we conform to PEP8."""
        pep8style = pep8.StyleGuide(config_file=PATH / '.pep8')
        result = pep8style.check_files(['scriptter.py', 'tests.py'])
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")


class YamlTests(unittest.TestCase):
    def setUp(self):
        self.docs = DATA / 'simple_document_stream.yaml'
        self.doc = DATA / 'simple_document.yaml'

    def test_it_should_load_all_documents_from_a_string(self):
        result = scriptter.yaml_load_all(self.docs.text())
        ensure(result).is_a(deque).of(list)
        ensure(result).has_length(2)

    def test_it_should_load_all_documents_from_a_filepath(self):
        result = scriptter.yaml_load_all(self.docs)
        ensure(result).is_a(deque).of(list)
        ensure(result).has_length(2)

    def test_it_should_load_all_documents_from_a_file(self):
        with open(self.docs) as fi:
            result = scriptter.yaml_load_all(fi)
        ensure(result).is_a(deque).of(list)
        ensure(result).has_length(2)

    def test_it_should_load_a_document_from_a_string(self):
        result = scriptter.yaml_load(self.doc.text())
        ensure(result).is_a(dict)
        ensure(result).has_key('foo').whose_value.equals('bar')  # noqa
        ensure(result).has_key('baz').whose_value.equals('blah')  # noqa

    def test_it_should_load_a_document_from_a_filepath(self):
        result = scriptter.yaml_load(self.doc)
        ensure(result).is_a(dict)
        ensure(result).has_key('foo').whose_value.equals('bar')  # noqa
        ensure(result).has_key('baz').whose_value.equals('blah')  # noqa

    def test_it_should_load_a_document_from_a_file(self):
        with open(self.doc) as fi:
            result = scriptter.yaml_load(fi)
        ensure(result).is_a(dict)
        ensure(result).has_key('foo').whose_value.equals('bar')  # noqa
        ensure(result).has_key('baz').whose_value.equals('blah')  # noqa

    def test_it_should_dump_a_document_to_a_string(self):
        result = scriptter.yaml_dump(
            OrderedDict([('foo', 'bar'), ('baz', 'blah')])
        )
        ensure(result).equals(self.doc.text())

    def test_it_should_dump_a_stream_of_documents_to_a_string(self):
        result = scriptter.yaml_dump_all(
            [
                ['foo'],
                ['bar'],
            ]
        )
        ensure(result).equals(self.docs.text())


if six.PY2:
    class UnicodeEnforcementTests(unittest.TestCase):
        def setUp(self):
            self.str = 'foo'
            self.u_str = u'foo'
            self.high_chars = '\xe3\x81\xab'
            self.u_chars = self.high_chars.decode('utf-8')

        def test_it_doesnt_touch_unicode_strings(self):
            result = scriptter._ensure_unicode_strings(self.u_chars)
            ensure(result).is_a(six.text_type)

        def test_it_casts_non_unicode_strings(self):
            result = scriptter._ensure_unicode_strings(self.high_chars)
            ensure(result).equals(self.u_chars)

        def test_it_casts_strings_in_dicts(self):
            data = {'foo': self.high_chars}
            expected = {'foo': self.u_chars}
            result = scriptter._ensure_unicode_strings(data)
            ensure(result).equals(expected)

        def test_it_casts_strings_in_lists(self):
            data = [self.high_chars, self.str]
            expected = [self.u_chars, self.u_str]
            result = scriptter._ensure_unicode_strings(data)
            ensure(result).equals(expected)

        def test_it_casts_nested_strings_in_lists(self):
            data = [[self.high_chars, self.str]]
            expected = [[self.u_chars, self.u_str]]
            result = scriptter._ensure_unicode_strings(data)
            ensure(result).equals(expected)

        def test_it_casts_nested_strings_in_dicts(self):
            data = {'foo': {'bar': self.high_chars}}
            expected = {'foo': {'bar': self.u_chars}}
            result = scriptter._ensure_unicode_strings(data)
            ensure(result).equals(expected)


class ScheduleExtractionWithDefaultsTests(unittest.TestCase):
    def setUp(self):
        result = scriptter.ScheduleLoader.extract_options_and_schedule_items(
            DATA / 'schedule_with_defaults.yaml'
        )
        self.result = result

    def test_it_extracts_options_and_a_schedule_from_a_stream(self):
        ensure(self.result).is_a(tuple)
        ensure(self.result).has_length(2)
        ensure(self.result[0]).is_a(dict)
        ensure(self.result[1]).is_a(list)

    def test_it_extracts_options_from_a_stream(self):
        ensure(self.result[0]).has_length(2)
        ensure(
            self.result[0]
        ).has_key('delay').whose_value.equals('30min')  # noqa
        ensure(
            self.result[0]
        ).has_key('timezone').whose_value.equals('US/Eastern')  # noqa

    def test_it_extracts_a_schedule_from_a_stream(self):
        ensure(self.result[1]).is_a(list).of(dict)
        ensure(self.result[1]).has_length(3)


class ScheduleExtractionWithoutDefaultsTests(unittest.TestCase):
    def setUp(self):
        result = scriptter.ScheduleLoader.extract_options_and_schedule_items(
            DATA / 'schedule_without_defaults.yaml'
        )
        self.result = result

    def test_it_extracts_options_and_a_schedule_from_a_stream(self):
        ensure(self.result).is_a(tuple)
        ensure(self.result).has_length(2)
        ensure(self.result[0]).is_a(dict)
        ensure(self.result[1]).is_a(list)

    def test_it_extracts_options_from_a_stream(self):
        ensure(self.result[0]).is_empty()

    def test_it_extracts_a_schedule_from_a_stream(self):
        ensure(self.result[1]).is_a(list).of(dict)
        ensure(self.result[1]).has_length(3)


class ScheduleLoaderOptionsTests(unittest.TestCase):
    def test_it_should_load_default_options(self):
        loader = scriptter.ScheduleLoader(
            DATA / 'schedule_without_defaults.yaml'
        )
        options = loader.options
        ensure(options).is_a(dict)
        ensure(options).equals(scriptter.DEFAULTS)

    def test_it_should_mask_default_options_with_loaded_options(self):
        loader = scriptter.ScheduleLoader(
            DATA / 'schedule_with_defaults.yaml'
        )
        options = loader.options
        ensure(options).is_a(dict)
        ensure(
            options
        ).has_key('delay').whose_value.equals('30min')  # noqa
        ensure(
            options
        ).has_key('timezone').whose_value.equals('US/Eastern')  # noqa


class ScheduleConstructorTests(unittest.TestCase):
    def setUp(self):
        self.options, self.items = options, items = {}, []
        self.schedule = scriptter.Schedule(options, items)

    def test_it_should_instantiate_with_options(self):
        ensure(self.schedule.options).is_(self.options)

    def test_it_should_instantiate_with_items(self):
        ensure(self.schedule.items).is_(self.items)


class ScheduleIndexTests(unittest.TestCase):
    def setUp(self):
        self.loader = scriptter.ScheduleLoader(
            DATA / 'schedule_without_defaults.yaml'
        )

        self.schedule = scriptter.Schedule(
            self.loader.options,
            self.loader.items
        )

    def test_it_should_index_items(self):
        ensure(self.schedule.by_id).is_a(dict)
        ensure(self.schedule.by_id).is_nonempty()

    def test_it_should_assign_ids(self):
        ensure.each_of(self.schedule.by_id.values()).contains('id')

    def test_it_should_index_neighbors(self):
        ensure(self.schedule.next_after_id).is_a(dict)
        ensure(
            self.schedule.next_after_id
        ).is_a(dict).of(six.string_types[0]).to(dict)


class ScheduleOperationsTests(unittest.TestCase):
    def setUp(self):
        loaded = scriptter.ScheduleLoader(
            DATA / 'schedule_with_defaults_and_ids.yaml'
        )

        self.schedule = scriptter.Schedule(loaded.options, loaded.items)

    def test_it_should_get_items_by_id(self):
        item = self.schedule.by_id['36292ccff3f811e4889bc82a1417f375']
        ensure(item).is_a(dict)
        ensure(item).has_key('say').whose_value.equals('Hello, world!')  # noqa

    def test_getting_a_nonexistent_items_by_id_raises_an_IndexError(self):
        ensure(
            self.schedule.by_id.__getitem__
        ).called_with('foo').raises(KeyError)

    def test_it_should_get_the_next_item_after_an_id(self):
        item = self.schedule.next_after_id['36292ccff3f811e4889bc82a1417f375']
        ensure(item).is_a(dict)
        ensure(item).has_key('say').whose_value.equals('Hey, @eykd!')  # noqa

    def test_it_should_wrap_around_when_getting_the_next_item_after_an_id(self):
        item = self.schedule.next_after_id['4156347af3f811e4a134c82a1417f375']
        ensure(item).is_a(dict)
        ensure(item).has_key('say').whose_value.equals('Hello, world!')  # noqa

    def test_it_should_not_wrap_around_when_repeat_is_False(self):
        self.schedule.options['repeat'] = False
        self.schedule.index()  # This will honor the new option
        ensure(
            self.schedule.next_after_id.__getitem__
        ).called_with(
            '4156347af3f811e4a134c82a1417f375'
        ).raises(KeyError)

    def test_it_should_obtain_the_timezone(self):
        ensure(
            self.schedule.get_timezone
        ).called_with().equals(pytz.timezone('US/Eastern'))


class StateLoaderOperationsTests(unittest.TestCase):
    def setUp(self):
        tmpdir = self.tmpdir = path(tempfile.mkdtemp())
        state = DATA / 'test_state.yaml'
        dest = self.state_path = tmpdir / state.name
        state.copy(dest)
        self.loader = scriptter.StateLoader(self.state_path)

    def tearDown(self):
        self.tmpdir.rmtree_p()

    def test_it_should_load_the_state(self):
        state = self.loader.state
        ensure(state).has_key(  # noqa
            'scheduled'
        ).whose_value.equals('ac8cd482f36b11e49c68c82a1417f375')

        expected = dt.datetime(2015, 5, 5, 20, 7, 31)
        ensure(state).has_key(  # noqa
            'when'
        ).whose_value.equals(expected)

    def test_it_should_write_changes_to_state(self):
        self.loader.state['next'] = 'foo'
        self.loader.write_state()

        new_loader = scriptter.StateLoader(self.state_path)
        ensure(new_loader.state).has_key('next'  # noqa
        ).whose_value.equals('foo')

    def test_it_should_reset_state(self):
        self.loader.reset()
        ensure(self.loader.state).is_empty()


class ScriptterConstructorTests(unittest.TestCase):
    def setUp(self):
        self.options, self.items = options, items = {}, []
        self.schedule = scriptter.Schedule(options, items)
        self.state = {}
        self.scriptter = scriptter.Scriptter(self.schedule, self.state)

    def test_it_should_instantiate_with_options(self):
        ensure(self.schedule.options).is_(self.options)

    def test_it_should_instantiate_with_items(self):
        ensure(self.schedule.items).is_(self.items)


class ScriptterOperationsTests(unittest.TestCase):
    def setUp(self):
        loaded = scriptter.ScheduleLoader(
            DATA / 'schedule_with_defaults_and_ids.yaml'
        )

        self.schedule = scriptter.Schedule(loaded.options, loaded.items)
        self.state = {}
        self.scriptter = scriptter.Scriptter(self.schedule, self.state)

    def test_it_should_get_the_first_scheduled_item(self):
        ensure(
            self.scriptter.get_scheduled_item
        ).called_with().is_(self.schedule.items[0])

    def test_it_should_get_the_saved_scheduled_item(self):
        self.scriptter.state['scheduled'] = '3d13091cf3f811e4a8edc82a1417f375'
        ensure(
            self.scriptter.get_scheduled_item
        ).called_with().is_(
            self.schedule.by_id['3d13091cf3f811e4a8edc82a1417f375']
        )

    def test_it_should_log_an_error_if_it_cant_get_a_scheduled_item(self):
        self.scriptter.state['scheduled'] = 'foo'
        with mock.patch('scriptter.logger.error') as patched:
            ensure(
                self.scriptter.get_scheduled_item
            ).called_with().is_none()
            ensure(patched.call_count).equals(1)

    def test_it_should_get_utcnow_for_the_scheduled_run_time(self):
        utcnaw = dt.datetime(2015, 12, 25, 13, 57)
        utc_localized = pytz.UTC.localize(utcnaw)
        localized = utc_localized.astimezone(self.schedule.get_timezone())
        fake_datetime = mock.Mock(utcnow=mock.Mock(return_value=utcnaw))
        with mock.patch('datetime.datetime', fake_datetime):
            ensure(
                self.scriptter.get_scheduled_run_time
            ).called_with().equals(
                localized
            )

    def test_it_should_get_the_next_item_after(self):
        item = self.schedule.by_id['36292ccff3f811e4889bc82a1417f375']
        expected = self.schedule.by_id['3d13091cf3f811e4a8edc82a1417f375']
        ensure(
            self.scriptter.get_next_item_after
        ).called_with(
            item
        ).is_(expected)

    def test_it_should_return_None_when_theres_no_item_after(self):
        self.schedule.options['repeat'] = False
        self.schedule.index()  # This will honor the new option
        item = self.schedule.by_id['4156347af3f811e4a134c82a1417f375']
        ensure(
            self.scriptter.get_next_item_after
        ).called_with(
            item
        ).is_none()

    def test_it_should_get_a_datetime_as_next_runtime(self):
        result = self.scriptter.get_next_run_time({})

        ensure(result).is_a(dt.datetime)

    def test_it_should_get_the_default_delay_as_next_runtime(self):
        utcnaw = dt.datetime(2015, 12, 25, 13, 53)
        # US/Eastern time and 30 minutes later:
        expected = pytz.timezone('US/Eastern').localize(
            dt.datetime(2015, 12, 25, 9, 23)
        )
        result = self.scriptter.get_next_run_time({}, now=utcnaw)

        ensure(result).equals(expected)

    def test_it_should_save_the_next_scheduled_item(self):
        item = self.schedule.by_id['3d13091cf3f811e4a8edc82a1417f375']
        self.scriptter.set_next(item)
        ensure(
            self.scriptter.state
        ).has_key('scheduled').whose_value.equals(  # noqa
            '4156347af3f811e4a134c82a1417f375'
        )

    def test_it_should_save_the_next_scheduled_time(self):
        utcnaw = dt.datetime(2015, 12, 25, 13, 53)
        # US/Eastern time and 30 seconds later:
        expected = pytz.timezone('US/Eastern').localize(
            dt.datetime(2015, 12, 25, 8, 53, 30)
        )
        item = self.schedule.by_id['36292ccff3f811e4889bc82a1417f375']
        self.scriptter.set_next(item, now=utcnaw)
        ensure(
            self.scriptter.state
        ).has_key('when').whose_value.equals(  # noqa
            expected
        )

    def test_it_should_save_None_if_no_more_scheduled_items(self):
        self.schedule.options['repeat'] = False
        self.schedule.index()  # This will honor the new option
        item = self.schedule.by_id['4156347af3f811e4a134c82a1417f375']
        self.scriptter.set_next(item)
        ensure(
            self.scriptter.state
        ).has_key('scheduled').whose_value.is_none()  # noqa

    def test_it_should_create_item_context(self):
        item = self.schedule.by_id['4156347af3f811e4a134c82a1417f375']
        expected = dict()
        expected.update(scriptter.DEFAULTS)
        expected.update(self.schedule.options)
        expected.update(item)

        ctx = self.scriptter.get_context(item)

        ensure(ctx).equals(expected)

    def test_it_should_render_a_command_to_run(self):
        item = self.schedule.by_id['4156347af3f811e4a134c82a1417f375']
        result = self.scriptter.get_commands(item)
        ensure(result).is_a(list).of(six.text_type)
        ensure(result).equals(
            [('echo @somebodyelse says: '
              'Yo @worldsenoughstudios you know I can\'t be beat; '
              'I heard you like twitter so I put some wit in your tweet!')]
        )

    def test_it_should_render_commands_to_run(self):
        self.schedule.options['cmd'] = [
            'echo @{as} says: {say}',
            'echo with a delay of {delay}'
        ]
        item = self.schedule.by_id['4156347af3f811e4a134c82a1417f375']
        result = self.scriptter.get_commands(item)
        ensure(result).is_a(list).of(six.text_type)
        ensure(result).equals(
            [
                ('echo @somebodyelse says: '
                 'Yo @worldsenoughstudios you know I can\'t be beat; '
                 'I heard you like twitter so I put some wit in your tweet!'),
                'echo with a delay of tomorrow at 8am',
            ]
        )

    def test_it_should_run(self):
        self.scriptter.state['next'] = '36292ccff3f811e4889bc82a1417f375'
        self.scriptter.state['when'] = dt.datetime.now() - dt.timedelta(60)
        with mock.patch('subprocess.check_output') as patched:
            self.scriptter.run()
            ensure(patched.call_count).equals(1)
            ensure(patched.call_args[0][0]).equals(
                ['echo', '@eykd', 'says:', 'Hello,', 'world!']
            )

    def test_it_should_not_run_if_not_time_to_run_yet(self):
        self.scriptter.state['next'] = '36292ccff3f811e4889bc82a1417f375'
        self.scriptter.state['when'] = dt.datetime.now() + dt.timedelta(60)
        with mock.patch('subprocess.check_output') as patched:
            self.scriptter.run()
            ensure(patched.call_count).equals(0)

    def test_it_should_not_run_if_nothing_to_run(self):
        self.schedule.options['repeat'] = False
        self.scriptter.state['scheduled'] = None
        with mock.patch('subprocess.check_output') as patched:
            self.scriptter.run()
            ensure(patched.call_count).equals(0)

    def test_it_should_check_a_schedule(self):
        with mock.patch('sys.stdout') as patched:
            # A bit of a cheat: just ensure that it runs w/o issue.
            self.scriptter.check()
            ensure(patched.write.call_count).does_not_equal(0)
