#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scriptter

Scriptter is a brain for your cron job.

Usage:
    scriptter [--reset] [--verbose] [--state <state-path>] [trial | run] <schedule>
    scriptter [--verbose] check <schedule>

Options:
    -h --help              Show this screen.
    --version              Show version.
    --verbose              Show verbose output.
    --state <state-path>   Path for storing state [default: "./state.yml"]
    --reset                Reset stored state
"""  # noqa
from collections import deque, Iterable, Mapping, OrderedDict
from codecs import open
import datetime as dt
import hashlib
import itertools as it
import logging
import pprint
import shlex
import subprocess

from docopt import docopt
from path import path
import parsedatetime
import pytz
import six
import yaml

__version__ = "0.3"


logger = logging.getLogger('scriptter')

# __all__ = ['Schedule']


# Ordered loading/dumping of YAML: http://stackoverflow.com/a/21912744/18950
class OrderedLoader(yaml.Loader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))
OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping)


class OrderedDumper(yaml.Dumper):
    pass


def _dict_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        data.items())
OrderedDumper.add_representer(OrderedDict, _dict_representer)


def _load_yaml(method, data):
    result = getattr(yaml, method)(data, Loader=OrderedLoader)
    if method == 'load_all':
        result = deque(result)
    return result


def _load_file_path_or_yaml(method, data):
    if isinstance(data, six.string_types):
        if len(data.strip().splitlines()) > 1:
            return _load_yaml(method, data)
        else:
            file_path = path(data)
            if file_path.exists():
                with open(data, encoding='utf-8') as fi:
                    return _load_yaml(method, fi)

    else:
        return _load_yaml(method, data)


def yaml_load(data):
    result = _load_file_path_or_yaml('load', data)
    return result if result is not None else {}


def yaml_load_all(data):
    result = _load_file_path_or_yaml('load_all', data)
    return result if result is not None else deque()


def yaml_dump(data):
    return yaml.dump(data, Dumper=OrderedDumper, default_flow_style=False)


def yaml_dump_all(data):
    return yaml.dump_all(data, Dumper=OrderedDumper, default_flow_style=False)


if six.PY2:  # pragma: nocover
    def _ensure_unicode_strings(value):
        if isinstance(value, six.text_type):
            return value
        elif isinstance(value, six.string_types):
            return value.decode('utf-8')
        elif isinstance(value, Mapping):
            return {k: _ensure_unicode_strings(v) for k, v in value.items()}
        elif isinstance(value, Iterable):
            return [_ensure_unicode_strings(i) for i in value]
        else:
            return value
else:
    def _ensure_unicode_strings(value):  # pragma: no cover
        return value

DEFAULTS = {
    'delay': '1 minute',
    'timezone': 'US/Pacific',
    'cmd': 'echo Hello {timezone}!',
    'repeat': True,
}


class ScheduleLoader(object):
    def __init__(self, schedule_path):
        self.file_path = schedule_path
        options, items = self.extract_options_and_schedule_items(schedule_path)

        self.loaded_options = options
        self.options = OrderedDict()
        self.options.update(DEFAULTS)
        self.options.update(options)

        self.items = items

    @classmethod
    def extract_options_and_schedule_items(klass, data):
        schedule = yaml_load_all(data)
        options = {}
        items = []

        # Get first item, see if it contains defaults:
        item = schedule.popleft()
        if 'defaults' in item:
            options = item['defaults']
        else:
            items.append(item)

        # Everything else is a schedule item.
        items.extend(schedule)

        return options, items


class Schedule(object):
    def __init__(self, options, items):
        self.options = options
        self.items = items
        self.by_id = {}
        self.next_after_id = {}

        self.index()

    def get_timezone(self):
        return pytz.timezone(self.options['timezone'])

    def localize_naive_utc_datetime(self, time):
        return pytz.UTC.localize(time).astimezone(self.get_timezone())

    def get_now(self):
        return self.localize_naive_utc_datetime(dt.datetime.utcnow())

    def index(self):
        self.by_id.clear()
        self.next_after_id.clear()
        last_item = None
        for item in self.items:
            if 'id' not in item:
                item['id'] = self.hash_item(item)
            item_id = item['id']
            self.by_id[item_id] = item
            if last_item is not None:
                self.next_after_id[last_item['id']] = item
            last_item = item
        if self.options.get('repeat'):
            self.next_after_id[last_item['id']] = self.items[0]

    def hash_item(self, item):
        if not isinstance(item, six.string_types):
            if isinstance(item, Mapping):
                item = tuple(sorted(
                    (k, self.hash_item(v))
                    for k, v in item.items()
                    if k != 'id'
                ))
            elif isinstance(item, Iterable):
                item = tuple(sorted(item))

        return hashlib.md5(repr(item).encode('utf-8')).hexdigest()


class StateLoader(object):
    def __init__(self, state_path):
        self.state_path = state_path
        self.state = yaml_load(state_path)

    def write_state(self, fp=None):
        if fp is None:
            assert isinstance(self.state_path, six.string_types)
            fp = self.state_path

        with open(fp, 'w') as fo:
            state = yaml_dump(self.state)
            fo.write(state)

    def reset(self):
        self.state.clear()


class SENTINEL(object):
    pass


class Scriptter(object):
    def __init__(self, schedule, state):
        self.state = state
        self.schedule = schedule
        self.calendar = parsedatetime.Calendar()

    def get_scheduled_item(self):
        scheduled_item = None
        scheduled_id = self.state.get('scheduled', SENTINEL)
        if scheduled_id is SENTINEL:
            scheduled_item = self.schedule.items[0]
        elif scheduled_id:
            try:
                scheduled_item = self.schedule.by_id[scheduled_id]
            except KeyError:
                logger.error("Could not find scheduled item %s", scheduled_id)

        return scheduled_item

    def get_scheduled_run_time(self, item, now=None):
        when = self.state.get('when')
        if not when:
            when = self.get_next_run_time(item, now=now)
        else:
            when = pytz.UTC.localize(when)

        return when.astimezone(self.schedule.get_timezone())

    def get_next_item_after(self, item):
        try:
            return self.schedule.next_after_id[item['id']]
        except KeyError:
            return None

    def get_next_run_time(self, item, now=None):
        ctx = self.get_context(item)
        delay = ctx['delay']
        tz = pytz.timezone(ctx['timezone'])
        if now is None:
            now = pytz.UTC.localize(dt.datetime.utcnow())
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)
        now = now.astimezone(tz)
        logger.debug('Using base `now`: %s', now)
        when = self.calendar.parseDT(
            delay,
            sourceTime=now,
            tzinfo=tz,
        )[0]
        logger.debug('Parsed `%s` as %s', delay, when)
        return when

    def set_next(self, item, now=None):
        next_item = self.get_next_item_after(item)
        if next_item is None:
            next_id = None
        else:
            next_id = next_item['id']

        self.state['scheduled'] = next_id
        self.state['when'] = (
            None if next_id is None
            else self.get_next_run_time(next_item, now=now))

    def get_context(self, item):
        ctx = {}
        for data in (self.schedule.options, item):
            for key, value in data.items():
                # Ensure that all values are unicode strings
                ctx[key] = _ensure_unicode_strings(value)

        return ctx

    def get_commands(self, item):
        ctx = self.get_context(item)
        cmd = ctx['cmd']
        if isinstance(cmd, six.string_types):
            commands = [cmd]
        elif isinstance(cmd, Iterable):
            commands = list(cmd)

        return [command.format(**ctx) for command in commands]

    def run(self, dry_run=False):
        item = self.get_scheduled_item()

        if item is None:
            logger.warning("Nothing to do!")
            return

        when = self.get_scheduled_run_time(item)
        now = self.schedule.get_now()

        if when > now:
            for command in self.get_commands(item):
                logger.warning("Will run `%s` at %s", command, when.isoformat())
            return

        self.set_next(item)
        logger.debug('Running with item:\n%s', pprint.pformat(dict(item)))

        for command in self.get_commands(item):
            command = shlex.split(command)
            logger.info("Running command: %r", command)
            if not dry_run:
                result = subprocess.check_output(command)
                logger.info("Result was: %s", result)

    def check(self):
        formatter = '%b %d, %Y at %X'
        now = self.schedule.get_now()
        print((
            six.u("%s %s -- (start)") % (now.strftime(formatter), now.tzinfo)
        ).encode('utf-8'))
        for item in self.schedule.items:
            print('-----')
            delay = self.get_context(item)['delay']
            when = self.get_next_run_time(item, now=now)
            print((
                six.u("%s -- (%s)") % (when.strftime(formatter), delay)
            ).encode('utf-8'))
            for command in self.get_commands(item):
                print(command.encode('utf-8'))
            now = when
        print('-----')


def main():   # pragma: no cover
    logging.basicConfig()
    arguments = docopt(__doc__, version='Scriptter {}'.format(__version__))
    if arguments.get('--verbose'):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.debug("Received arguments: %s", pprint.pformat(arguments))
    loaded_schedule = ScheduleLoader(arguments['<schedule>'])

    schedule = Schedule(loaded_schedule.options, loaded_schedule.items)

    state_path = arguments.get('--state', './state.yml')
    state = StateLoader(state_path)

    if arguments['--reset']:
        state.reset()
        state.write_state()

    scriptter = Scriptter(schedule, state.state)

    if arguments['run'] or arguments['trial']:
        scriptter.run(dry_run=arguments['trial'])
        if arguments['run']:
            state.write_state()
    elif arguments['check']:
        scriptter.check()


if __name__ == '__main__':   # pragma: no cover
    main()
