"""
A small script for scheduling assistants in exercise groups.
Author: Tommi Junttila
License: The MIT License
"""

import json
from typing import Callable
import yaml

# Character constants used to present the preferability of groups
PREF_BAD = ' '
PREF_OK = '1'
PREF_GOOD = '2'
PREF_CHARS = [PREF_BAD, PREF_OK, PREF_GOOD]


class Instance:
    """An exercise session scheduling instance describing
    the assistants, groups, and penalties."""
    def __init__(self):
        self.penalty_bad_time = 1000
        self.penalty_ok_time = 100
        self.penalty_good_time = 0
        self.penalty_consecutive = 10
        self.groups = []
        self.assistants = []

    def json(self):
        """Give a JSON representation of the instance."""
        result = f"""{{
  "penalty_bad_time": {self.penalty_bad_time},
  "penalty_ok_time":  {self.penalty_ok_time},
  "penalty_good_time":  {self.penalty_good_time},
  "penalty_consecutive":  {self.penalty_consecutive},
  "groups": [
"""
        result += ',\n'.join([f'    {group.json()}'
                              for group in self.groups])+'\n'
        result += '  ],\n'
        result += '  "assistants": {\n'
        result += ',\n'.join([f'    {assistant.json()}'
                              for assistant in self.assistants])+'\n'
        result += '  }\n'
        result += '}'
        return result

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()

    @staticmethod
    def load_json(filename: str, error: Callable[[str], None]):
        """Load an instance from a JSON file."""
        penalties = ['penalty_bad_time', 'penalty_ok_time',
                     'penalty_good_time', 'penalty_consecutive']
        other_keys = ['groups', 'assistants']
        group_name_to_index = {}
        instance = Instance()
        inp = json.load(open(filename, 'r', encoding='utf-8'))
        for attr in penalties:
            if attr in inp:
                instance.__setattr__(attr, inp[attr])
        for key in inp:
            if key not in penalties and key not in other_keys:
                error(f'Invalid key "{key}" in the instance file')
        for (index, group_data) in enumerate(inp['groups']):
            name = group_data['name']
            if name in group_name_to_index:
                error(f"Group '{name}' defined twice")
            group = Group(name, index)
            instance.groups.append(group)
            group_name_to_index[name] = index
            for attr in ['min', 'max', 'pred']:
                if attr in group_data:
                    group.__setattr__(attr, group_data[attr])
        assistant_name_to_index = {}
        for (index, name) in enumerate(inp['assistants']):
            if name in assistant_name_to_index:
                error(f'Assistant "{name}" defined twice')
            data = inp['assistants'][name]
            if 'prefs' not in data:
                error(f'Assistant "{name}" must have a "prefs" field')
            assistant = Assistant(name, index, data['prefs'])
            assistant_name_to_index[name] = index
            instance.assistants.append(assistant)
            for attr in ['min', 'max']:
                if attr in data:
                    assistant.__setattr__(attr, data[attr])

        # Link the predecessor groups
        for group in instance.groups:
            if group.pred is not None:
                if group.pred not in group_name_to_index:
                    error(f'The predecessor group "{group.pred}" '
                          f'of {group.name} is not defined')
                group.pred = instance.groups[group_name_to_index[group.pred]]

        return instance

    @staticmethod
    def load_yaml(filename: str, error: Callable[[str], None]):
        """Load an instance from a YAML file."""
        instance = Instance()
        penalties = ['penalty_bad_time', 'penalty_ok_time',
                     'penalty_good_time', 'penalty_consecutive']
        other_keys = ['groups', 'assistants']
        group_name_to_index = {}
        inp = yaml.safe_load(open(filename, 'r', encoding='utf-8'))
        for attr in penalties:
            if attr in inp:
                instance.__setattr__(attr, inp[attr])
        for key in inp:
            if key not in penalties and key not in other_keys:
                error(f'Invalid key "{key}" in the instance file')
        # Read group information
        for (index, ginfo) in enumerate(inp['groups']):
            # ginfo is of form {name: fields}
            assert len(ginfo) == 1
            (name, fields) = list(ginfo.items())[0]
            if name in group_name_to_index:
                error(f"Group '{name}' defined twice")
            group = Group(name, index)
            instance.groups.append(group)
            group_name_to_index[name] = index
            for attr in ['min', 'max', 'pred']:
                if attr in fields:
                    group.__setattr__(attr, fields[attr])
        # Read assistant information
        assistant_name_to_index = {}
        for (index, ainfo) in enumerate(inp['assistants']):
            # ainfo is of form {name: fields}
            assert len(ainfo) == 1
            (name, fields) = list(ainfo.items())[0]
            if name in assistant_name_to_index:
                error(f'Assistant "{name}" defined twice')
            if 'prefs' not in fields:
                error(f'Assistant "{name}" must have a "prefs" field')
            assistant = Assistant(name, index, fields['prefs'])
            assistant_name_to_index[name] = index
            instance.assistants.append(assistant)
            for attr in ['min', 'max']:
                if attr in fields:
                    assistant.__setattr__(attr, fields[attr])

        # Link the predecessor groups
        for group in instance.groups:
            if group.pred is not None:
                if group.pred not in group_name_to_index:
                    error(f'The predecessor group "{group.pred}" '
                          f'of {group.name} is not defined')
                group.pred = instance.groups[group_name_to_index[group.pred]]

        return instance

    @staticmethod
    def load(filename: str, error: Callable[[str], None]):
        """Load an instance from a JSON or YAML file."""
        file_extensions = {
            'JSON': ['json', 'js', 'jso'],
            'YAML': ['yaml', 'yml']
        }
        input_format = None
        filename_as_lower = filename.lower()
        for (file_format, extensions) in file_extensions.items():
            if input_format:
                break
            for extension in extensions:
                if filename_as_lower.endswith(f'.{extension}'):
                    input_format = file_format
                    break
        if input_format is None:
            exts = '\n'.join([f'- {fmt}: ' + ', '.join(exts)
                              for (fmt, exts) in file_extensions.items()])
            error(f"""Cannot detect the file format of "{filename}".
The supported file formats and extensions are:
"""+exts)

        instance = None
        if input_format == 'JSON':
            instance = Instance.load_json(filename, error)
        elif input_format == 'YAML':
            instance = Instance.load_yaml(filename, error)
        else:
            error('Should not happen')
        assert instance is not None

        penalties = ['penalty_bad_time', 'penalty_ok_time',
                     'penalty_good_time', 'penalty_consecutive']

        #
        # Some semantic validation
        #
        for penalty in penalties:
            if instance.__getattribute__(penalty) < 0:
                error(f'The penalty "{penalty}" must be non-negative')

        min_personnel = 0
        max_personnel = 0
        for group in instance.groups:
            if not 0 <= group.min <= group.max:
                error(f'Group "{group.name}": '
                      f'0 <= "min" <= "max" does not hold')
            min_personnel += group.min
            max_personnel += group.max
        nof_groups = len(instance.groups)
        min_available_personnel = 0
        max_available_personnel = 0
        for assistant in instance.assistants:
            context = f'Assistant "{assistant.name}"'
            if not 0 <= assistant.min <= assistant.max:
                error(f'{context}: 0 <= "min" <= "max" does not hold')
            min_available_personnel += assistant.min
            max_available_personnel += assistant.max
            prefs = assistant.prefs
            if len(prefs) != nof_groups:
                error(f'{context}: wrong numberof group preferences '
                      f'({len(prefs)} instead of {nof_groups})')
            for char in prefs:
                if char not in PREF_CHARS:
                    error(f'{context}: illegal character "{char}" '
                          f'in the preferences')

        if max_available_personnel < min_personnel:
            error(f'Not enough assistant shifts available '
                  f'(only {max_available_personnel} but at least '
                  f'{min_personnel} required).')
        if min_available_personnel > max_personnel:
            error(f'Not enough group shifts so that minimum amount of '
                  f'shifts of all assistants can be filled '
                  f'(only {max_personnel} shifts but assistants want to '
                  f'have at least {min_available_personnel}).')
        return instance


class Group:
    """Representation of an exercise session group."""
    def __init__(self, name: str, index):
        assert name, "Each group should have a name"
        self.name = name
        self.index = index
        self.min = 1
        self.max = 1
        self.pred = None

    def json(self):
        """Give a JSON representation of the group."""
        pred = f', "pred": "{self.pred.name}"' if self.pred else ""
        return (f'{{"name": {self.name}, "min": {self.min}, '
                f'"max": {self.max}{pred}}}')

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()


class Assistant:
    """Representation of an assistant."""
    def __init__(self, name: str, index, prefs):
        assert name, 'Each assistant should have a name'
        self.name = name
        self.index = index
        self.prefs = prefs
        self.min = 1
        self.max = 1

    def json(self):
        """Give a JSON representation of the assistant."""
        return (f'"{self.name}": {{"prefs": "{self.prefs}", '
                f'"min": {self.min}, "max": {self.max}}}')

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()
