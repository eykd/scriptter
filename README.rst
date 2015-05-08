##########
Scriptter!
##########

.. image:: https://travis-ci.org/eykd/scriptter.svg?branch=master
    :target: https://travis-ci.org/eykd/scriptter


.. image:: https://coveralls.io/repos/eykd/scriptter/badge.svg
  :target: https://coveralls.io/r/eykd/scriptter


Scriptter is a brain for your cron job. You write a script (using a special
YAML_ format), specifying a sequence of commands to run and a human-readable
delay between each group of commands. Then, run Scriptter against your script
every minute (or as often as you can). Scriptter will make sure that your
commands are run in the sequence and timing you specified.

.. _YAML: http://www.yaml.org/


Uses:
=====

I conceived of Scriptter as a way to author Twitter bots, especially Twitter
bots that converse with each other. But there's no limitation to Twitter:
anything you can do in the shell, you can do in Scriptter.


Example:
========

Here's a simple script to run a daily conversation between two Twitter
accounts, using the `t Twitter CLI`_::

    defaults:
      delay: 1min
      activate: t set active
      update: t update
      cmd:
      - '{activate} {as}'
      - '{update} "{say}"'
      timezone: US/Eastern
    ---
    as: Costello
    say: "@Abbott I'm not... stay out of the infield! I want to know what's the guy's name in left field?"
    ---
    as: Abbott
    say: "@Costello No, What is on second."
    ---
    as: Costello
    say: "@Abbott I'm not asking you who's on second."
    ---
    as: Abbott
    say: "@Costello Who's on first!"
    ---
    as: Costello
    say: "@Abbott I don't know."
    ---
    cmd:
    - '{activate} Abbott'
    - '{update} "@Costello Third base!"'
    - '{activate} Costello'
    - '{update} "@Abbott Third base!"'
    ---
    delay: 10min
    as: Costello
    say: '@Abbott Look, you gotta outfield?'

.. _t Twitter CLI: https://github.com/sferik/t

Classic, I know. Here's what's going on: every time Scriptter runs, it
remembers where it left off at, and at what time the next item should run. When
that time comes, it looks at the ``cmd`` member. If a member isn't present on
the item, it looks in the defaults. ``cmd`` can be a single string, or a list
of strings. Command strings can be templates containing `formatting instructions`_.

.. _formatting instructions: https://docs.python.org/2/library/string.html#formatstrings


Templating
==========

The context for a command template comes from the item itself, filled in with
any global defaults from the document. That's how we can just define
``activate`` and ``update`` at the top and use them willy-nilly in command
strings later. The Twitter account to use (``as``) and the content of the tweet
(``say``) are defined in each item.


Time Delay
==========

They say that comedy is all about... TIMING! So how do we control the timing of
our comedic commands? The ``delay`` attribute is a human-readable time span or
delay, like "5 minutes" or "5mins" or "tomorrow at 8am", relative to the
previous item. We set a default ``delay`` at the top (or if we don't set a
default, the default is, by default, ``5mins``).

The ``delay`` of the first item is special: that determines how long after the
first invocation the script will begin. This might be useful for a script that
is keyed to time of day--you could say ``tomorrow at 8am`` and the script would
begin in the morning, next day after you start your cron job.


Repeating a Script
==================

Some scripts should only run once, some should repeat forever. By default, your
script will repeat (go back to the beginning) after it completes. To change
this behavior, include this at the top of your script::

    defaults:
        repeat: false


Command Line
============

You'll usually be interacting with Scriptter via the command line::

    $ scriptter --help


Normal Run
==========

To actually run the schedule, perform commands, and change state::

    $ scriptter run schedule.yaml


Trial Run
=========

To do a trial run and find out what Scriptter will do in a given state::

    $ scriptter trial schedule.yaml

This will do a dry run of the schedule, with the current state, but stop short
of actually performing any actions or changing the state.


Checking Delays
===============

If you need to get a feel for how an item list will play out in time, use the
``check`` command::

    $ scriptter check schedule.yaml

This will first verify that the complete schedule is valid, well-formed, and
renderable. It will go through and simulate each item in sequence, reporting
when that item would run and what commands would be performed.
