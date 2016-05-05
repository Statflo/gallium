""" Prototype for Tori 4.0+ and Imagination 1.10+

    :Author: Juti Noppornpitak
"""

import argparse
import json
import sys

from imagination.loader import Loader

from .core       import Core
from .ext.helper import activate
from .helper     import Reflector
from .interface  import ICommand, IExtension, alias_property_name

class Console(object):
    """ Console

        This is designed to handle subcommands and extensions.
    """
    CONST_CONF_KEY_CMD_SETTINGS = 'settings'

    def __init__(self, name, core = None, config={}, config_path=None, loaders=[]):
        self.name   = name
        self.core   = core or Core()
        self.config = config

        if config_path:
            with open(config_path) as f:
                self.config.update(json.load(f))

        activate(self.core, self.config)

        self.loaders  = loaders
        self.commands = {}
        self.settings = {}

    def activate(self):
        main_parser = argparse.ArgumentParser(self.name)
        subparsers  = main_parser.add_subparsers(help='sub-commands')

        self._define_primary(main_parser)

        try:
            self.settings.update(self.config[type(self).CONST_CONF_KEY_CMD_SETTINGS])
        except KeyError as e:
            pass # not settings overridden

        for loader in self.loaders:
            key = loader.configuration_section_name()

            try:
                loader_config = self.config[key]
            except KeyError as e:
                continue # nothing to load with this loader

            for identifier, kind, command in loader.all(self.config[key]):
                self._register_command(subparsers, identifier, kind, command)

        if not self.commands:
            print('No commands available')

            sys.exit(15)

        args = main_parser.parse_args()

        if not hasattr(args, 'func'):
            main_parser.print_help()

            sys.exit(15)

        try:
            args.func(args)
        except KeyboardInterrupt as e:
            sys.exit(15)

    def _define_primary(self, main_parser):
        main_parser.add_argument(
            '--process-debug',
            help   = 'Process-wide debug flag (this may or may not run Gallium in the debug mode.)',
            action = 'store_true'
        )

    def _register_command(self, subparsers, identifier, cls, command_instance):
        # Handle the command interface.
        self._add_parser(
            subparsers,
            identifier,
            (
                Reflector.short_description(cls.__doc__) \
                or '(See {}.{})'.format(cls.__module__, cls.__name__)
            ),
            command_instance
        )

        # Handle aliasing.
        if hasattr(command_instance, alias_property_name):
            for alias in getattr(command_instance, alias_property_name):
                self._add_parser(
                    subparsers,
                    alias,
                    'Alias to "{}"'.format(identifier),
                    command_instance
                )

    def _add_parser(self, subparsers, identifier, documentation, command_instance):
        parser = subparsers.add_parser(identifier, help=documentation)
        parser.set_defaults(func=command_instance.execute)

        command_instance.define(parser)
        command_instance.set_core(self.core)
        command_instance.set_settings(self.settings)

        self.commands[identifier] = command_instance
