#!/usr/bin/python3

"""
A small script for scheduling assistant to tutorial groups.
Author: Tommi Junttila
License: The MIT License
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import yaml

# Character constants used to present the preferability of groups
prefBad = ' '
prefOk = '1'
prefGood = '2'
prefChars = [prefBad, prefOk, prefGood]

def myExec(commands, compOut=sys.stdout, expectedRetvals=[]):
    compErr = tempfile.TemporaryFile()
    print("Executing: "+" ".join(commands))
    retval = subprocess.call(commands, stdout=compOut, stderr=compErr)
    if retval not in expectedRetvals:
        print(f'Failed with return value {retval}, error output follows:')
        compErr.seek(0)
        for line in compErr: sys.stdout.write(line.decode('utf-8'))
        sys.exit(1)
    compErr.close()

fileExtensions = {
    'JSON': ['json', 'js', 'jso'],
    'YAML': ['yaml', 'yml']
}

class Config:
    def __init__(self):
        self.penalty_bad_time = 1000
        self.penalty_ok_time = 100
        self.penalty_good_time = 0
        self.penalty_consecutive = 10
        self.groups = []
        self.assistants = []
    def json(self):
        s = f"""{{
  "penalty_bad_time": {self.penalty_bad_time},
  "penalty_ok_time":  {self.penalty_ok_time},
  "penalty_good_time":  {self.penalty_good_time},
  "penalty_consecutive":  {self.penalty_consecutive},
  "groups": [
"""
        s += ",\n".join("    "+g.json() for g in self.groups)+"\n"
        s += "  ],\n"
        s += '  "assistants": {\n'
        s += ",\n".join("    "+a.json() for a in self.assistants)+"\n"
        s += "  }\n"
        s += "}"
        return s
    def __repr__(self):
        return self.json()
    def __str__(self):
        return self.json()

class Group:
    def __init__(self, name, index):
        assert name
        self.name = name
        self.index = index
        self.min = 1
        self.max = 1
        self.pred = None
    def json(self):
        pred = f', "pred": "{self.pred.name}"' if self.pred else ""
        return f'{{"name": {self.name}, "min": {self.min}, "max": {self.max}{pred}}}'
    def __repr__(self):
        return self.json()
    def __str__(self):
        return self.json()

class Assistant:
    def __init__(self, name, index, prefs):
        self.name = name
        self.index = index
        self.prefs = prefs
        self.min = 1
        self.max = 1
    def json(self):
        return f'"{self.name}": {{"prefs": "{self.prefs}", "min": {self.min}, "max": {self.max}}}'
    def __repr__(self):
        return self.json()
    def __str__(self):
        return self.json()
    
def loadConfiguration(p, args):
    inputFormat = None
    inputNameAsLower = args.input_file.lower()
    for fileFormat in fileExtensions:
        if inputFormat: break
        for extension in fileExtensions[fileFormat]:
            if inputNameAsLower.endswith('.'+extension):
                inputFormat = fileFormat
                break
    if inputFormat == None:
        s = "\n".join([f"- {fileFormat}: "+", ".join(fileExtensions[fileFormat]) for fileFormat in fileExtensions])
        p.error("""Cannot detect the format of the configuration file.
The supported file formats and extensions are:
"""+s)

    conf = Config()
    penalties = ['penalty_bad_time', 'penalty_ok_time', 'penalty_good_time', 'penalty_consecutive']
    other_keys = ['groups', 'assistants']
    if inputFormat == 'JSON':
        inp = json.load(open(args.input_file, 'r', encoding = 'utf-8'))
        for attr in penalties:
            if attr in inp: conf.__setattr__(attr, inp[attr])
        for k in inp:
            if k not in penalties and k not in other_keys:
                p.error(f'Invalid key "{k}" in the configuration file')
        gnameToIndex = {}
        for (index, g) in enumerate(inp['groups']):
            name = g['name']
            if name in gnameToIndex:
                p.error(f"Group '{name}' defined twice")
            o = Group(name, index)
            conf.groups.append(o)
            gnameToIndex[name] = index
            for attr in ['min','max']:
                if attr in g: o.__setattr__(attr, g[attr])
        for g in inp['groups']:
            name = g['name']
            if 'pred' in g:
                pred = g['pred']
                if pred not in gnameToIndex:
                    p.error(f'The predecessor group "{pred}" is not defined')
                conf.groups[gnameToIndex[name]].pred = conf.groups[gnameToIndex[pred]]
        anameToIndex = {}
        for (index,aname) in enumerate(inp['assistants']):
            if aname in anameToIndex:
                p.error(f'Assistant "{aname}" defined twice')
            a = inp['assistants'][aname]
            if 'prefs' not in a:
                p.error(f'Assistant "{aname}" must have a "prefs" field')
            o = Assistant(aname, index, a['prefs'])
            anameToIndex[aname] = index
            conf.assistants.append(o)
            for attr in ['min','max']:
                if attr in a: o.__setattr__(attr, a[attr])
    elif inputFormat == 'YAML':
        inp = yaml.safe_load(open(args.input_file, 'r', encoding = 'utf-8'))
        for attr in penalties:
            if attr in inp: conf.__setattr__(attr, inp[attr])
        for k in inp:
            if k not in penalties and k not in other_keys:
                p.error(f'Invalid key "{k}" in the configuration file')
        gnameToIndex = {}
        for (index, g) in enumerate(inp['groups']):
            assert len(g) == 1
            (name,g) = list(g.items())[0]
            if name in gnameToIndex:
                p.error(f"Group '{name}' defined twice")
            o = Group(name, index)
            conf.groups.append(o)
            gnameToIndex[name] = index
            for attr in ['min','max']:
                if attr in g: o.__setattr__(attr, g[attr])
        for g in inp['groups']:
            (name,g) = list(g.items())[0]
            if 'pred' in g:
                pred = g['pred']
                if pred not in gnameToIndex:
                    p.error(f'The predecessor group "{pred}" is not defined')
                conf.groups[gnameToIndex[name]].pred = conf.groups[gnameToIndex[pred]]
        anameToIndex = {}
        for (index,a) in enumerate(inp['assistants']):
            assert len(a) == 1
            (aname,a) = list(a.items())[0]
            if aname in anameToIndex:
                p.error(f'Assistant "{aname}" defined twice')
            if 'prefs' not in a:
                p.error(f'Assistant "{aname}" must have a "prefs" field')
            o = Assistant(aname, index, a['prefs'])
            anameToIndex[aname] = index
            conf.assistants.append(o)
            for attr in ['min','max']:
                if attr in a: o.__setattr__(attr, a[attr])
    else:
        p.error("Should not happen")

    #
    # Some semantic validation
    #
    for penalty in penalties:
        if conf.__getattribute__(penalty) < 0:
            p.error(f'The penalty "{penalty}" must be non-negative')

    minPersonnel = 0
    maxPersonnel = 0
    for group in conf.groups:
        name = group.name
        if group.min < 0:
            p.error(f'The "min" field of the group "{name}" must be non-negative')
        minPersonnel += group.min
        if group.max < 0:
            p.error(f'The "max" field of the group "{name}" must be non-negative')
        maxPersonnel += group.max
        if group.min > group.max:
            p.error(f'The "min" field must be at most the "max" field in the group "{name}"')
    nofGroups = len(conf.groups)
    nofAssistants = len(conf.assistants)
    minAvailablePersonnel = 0
    maxAvailablePersonnel = 0
    for a in conf.assistants:
        if a.min < 0:
            p.error(f'Assistant "{a.name}" must have a non-negative field "min".')
        minAvailablePersonnel += a.min
        if a.max < 0:
            p.error(f'Assistant "{a.name}" must have a non-negative field "max".')
        maxAvailablePersonnel += a.max
        if a.min > a.max:
            p.error(f'The "min" field must be at most the "max" field in the assistant "{a.name}".')
        prefs = a.prefs
        if len(prefs) != nofGroups:
            p.error(f'Assistant "{a.name}" has a wrong number ({len(prefs)} instead of {nofGroups}) group preferences.')
        for c in prefs:
            if c not in prefChars:
                p.error(f'An illegal character "{c}" in the preferences of the assistant "{a.name}".')

    if maxAvailablePersonnel < minPersonnel:
        p.error(f'Not enough assistant shifts available (only {maxAvailablePersonnel} but at least {minPersonnel} required).')
    if minAvailablePersonnel > maxPersonnel:
        p.error(f'Not enough group shifts so that minimum amount of shifts of all assistants can be filled (only {maxPersonnel} shifts but assistants want to have at least {minAvailablePersonnel}).')
    return conf


if __name__ == "__main__":
    description = "Schedule assistants to exercise groups."
    p = argparse.ArgumentParser(formatter_class = argparse.ArgumentDefaultsHelpFormatter, description = description)
    p.add_argument('--time_limit', metavar='T', type=int, default=60,
                   help='the time limit for the constraint solver')
    p.add_argument('--clingo', metavar='S', type=str, default="clingo",
                   help='the Clingo executable name')
    p.add_argument('input_file', help="the configuration file")
    args = p.parse_args()
    print(args)
    conf = loadConfiguration(p, args)

    aspFile = open("schedule.asp", "w", encoding = 'utf-8')
    print(f'Generating the constraint problem in the file "{aspFile.name}"')
    def f(s): aspFile.write(s+"\n")

    #
    # Output clingo ASP program
    #
    def aInGroup(assistant, group):
        return f"in({assistant.index},{group.index})"
    # Assistants as facts
    for assistant in conf.assistants:
        f(f'a({assistant.index}).')
    # Groups as facts
    for group in conf.groups:
        f(f'group({group.index}).')
    for assistant in conf.assistants:
        # Each assistant must take a specified number of groups
        f(f"{assistant.min} <= {{in({assistant.index},G):group(G)}} <= {assistant.max}.")
        # Assistant preferences with "weak constraints"
        prefs = assistant.prefs
        for (index, group) in enumerate(conf.groups):
            term = aInGroup(assistant,group)
            pref = prefs[index]
            if pref == prefBad:
                f(f":~ {term}. [ {conf.penalty_bad_time},{term} ]")
            elif pref == prefOk:
                f(f":~ {term}. [ {conf.penalty_ok_time},{term} ]")
            elif pref == prefGood:
                f(f":~ {term}. [ {conf.penalty_good_time},{term} ]")
            else:
                assert False
        # Penalty for scheduling the assistant in consecutive groups
        for group in conf.groups:
            if group.pred:
                t1 = aInGroup(assistant,group.pred)
                t2 = aInGroup(assistant,group)
                f(f":~ {t1}, {t2}. [ {conf.penalty_consecutive},{t1},{t2} ]")
    # Each group must have a specified number of assistants
    for group in conf.groups:
        f(f"{group.min} <= {{in(A,{group.index}):a(A)}} <= {group.max}.")
    aspFile.close()

    #
    # Run clingo
    #
    print(f"""Calling the constraint solver.
This may take some time: the time limit is set to {args.time_limit} seconds.""")
    clingoOutput = tempfile.TemporaryFile()
    myExec([args.clingo,f'--time-limit={args.time_limit}',aspFile.name], clingoOutput, [11,30]) #[30,1])
    # Parse the result
    clingoOutput.seek(0)
    nofModels = 0
    bestModel = set()
    optValue = 0
    while True:
        line = clingoOutput.readline()
        line = line.decode('utf-8')
        if line == '': break
        if line.startswith("Answer:"):
            line = clingoOutput.readline().decode('utf-8')
            bestModel = line.split()
            continue
        m = re.match(r"^Models\s+:\s+(\d+)\+?\s+.*", line)
        if m != None: nofModels = int(m.group(1))
        m = re.match(r"^Optimization\s+:\s+(\d+)\s+.*", line)
        if m != None: optValue = int(m.group(1))
    clingoOutput.close()
    #print(optValue)
    
    if nofModels == 0:
        print("No scheduling found within time limits. Perhaps not enough assistants available?")
        exit(0)

    # Interpret the best model
    schedule = {}
    for g in conf.groups: schedule[g.index] = set()
    #print(bestModel)
    penalties = []
    for atom in bestModel:
        m = re.match(r"^in\((.*),(.*)\)", atom)
        if m == None: continue
        aIndex = int(m.group(1))
        gIndex = int(m.group(2))
        a = conf.assistants[aIndex]
        g = conf.groups[gIndex]
        schedule[gIndex].add(a)
        pref = a.prefs[gIndex]
        if pref == prefBad:
            penalties.append(f'"{a.name}" on "{g.name}": bad time')
        elif pref == prefOk:
            penalties.append(f'"{a.name}" on "{g.name}": ok time')
        #elif pref == prefGood:
        #    penalties.append(f"{a} on {g}: good time")
    for group in conf.groups:
        if group.pred:
            for a in schedule[group.pred.index]:
                if a in schedule[group.index]:
                    penalties.append(f'"{a.name}" on {group.pred.name} and {group.name}: consecutive groups')
    print('Schedule:')
    for group in conf.groups:
        l = [a.name for a in schedule[group.index]]
        print(" "+group.name+": "+(", ".join(sorted(l))))
    print("")
    print(f'Solution cost: {optValue}')
    print('Non-optimalities:')
    for p in penalties: print(' '+p)
    exit(0)
