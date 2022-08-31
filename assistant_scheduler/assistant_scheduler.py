#!/usr/bin/python3

"""
A small script for scheduling assistants in exercise groups.
Author: Tommi Junttila
License: The MIT License
"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from clingo.control import Control
from .instance import Instance, PREF_BAD, PREF_OK, PREF_GOOD


def make_program(instance: Instance):
    """Make a logic program corresponding to a scheduling problem instance."""
    program = []

    def prog(line: str):
        """Append a line to the logic program."""
        nonlocal program
        program.append(line)

    def in_atom(assistant, group):
        return f'in({assistant.index},{group.index})'

    # Assistants as facts
    for assistant in instance.assistants:
        prog(f'a({assistant.index}).')
    # Groups as facts
    for group in instance.groups:
        prog(f'group({group.index}).')
    for assistant in instance.assistants:
        # Each assistant must take a specified number of groups
        prog(f'{assistant.min} '
             f'<= {{in({assistant.index},G):group(G)}} '
             f'<= {assistant.max}.')
        # Assistant preferences with "weak constraints"
        prefs = assistant.prefs
        for (index, group) in enumerate(instance.groups):
            term = in_atom(assistant, group)
            pref = prefs[index]
            if pref == PREF_BAD:
                prog(f":~ {term}. [ {instance.penalty_bad_time},{term} ]")
            elif pref == PREF_OK:
                prog(f":~ {term}. [ {instance.penalty_ok_time},{term} ]")
            elif pref == PREF_GOOD:
                prog(f":~ {term}. [ {instance.penalty_good_time},{term} ]")
            else:
                assert False
        # Penalty for scheduling the assistant in consecutive groups
        for group in instance.groups:
            if group.pred:
                atom1 = in_atom(assistant, group.pred)
                atom2 = in_atom(assistant, group)
                prog(f':~ {atom1}, {atom2}. '
                     f'[ {instance.penalty_consecutive},{atom1},{atom2} ]')
    # Each group must have a specified number of assistants
    for group in instance.groups:
        prog(f"{group.min} <= {{in(A,{group.index}):a(A)}} <= {group.max}.")
    return program


def main():
    """The main method for command line use."""
    description = "Schedule assistants to exercise groups."
    argp = ArgumentParser(description=description,
                          formatter_class=ArgumentDefaultsHelpFormatter)
    argp.add_argument('--time_limit', metavar='T', type=int, default=2,
                      help='the time limit for the constraint solver')
    argp.add_argument('input', type=str, help='the instance file name')
    args = argp.parse_args()
    if args.time_limit <= 0:
        argp.error('the time limit must be positive')

    print('Loading the problem instance...')
    instance = Instance.load(args.input, argp.error)
    # print(instance)

    # Create Clingo "control" (grounder and solver)
    clingo = Control()

    print('Generating the logic program...')
    program = make_program(instance)
    # print('\n'.join(program))

    #
    # Run clingo
    #
    clingo.add('base', [], '\n'.join(program))
    print('Grounding the logic program...')
    clingo.ground([('base', [])])
    print('Calling the logic solver...')
    # Go through the models and keep a best
    best_model = None
    hnd = clingo.solve(yield_=True, async_=True)
    while True:
        if not hnd.wait(args.time_limit):
            break
        result = hnd.get()
        if result.satisfiable:
            model = hnd.model()
            if model is None:
                break
            print(f'Found of a model of cost {model.cost}')
            if best_model is None or model.cost < best_model.cost:
                best_model = model
        else:
            break
        hnd.resume()
    # print(best_model)

    # Interpret the best model
    # "schedule" is a mapping from the group indices to a set of assistants
    schedule = {}
    for group in instance.groups:
        schedule[group.index] = set()
    penalties = []
    for atom in best_model.symbols(atoms=True):
        if atom.name != 'in':
            continue
        # Atom in(a, g)
        assistant = instance.assistants[atom.arguments[0].number]
        group = instance.groups[atom.arguments[1].number]
        schedule[group.index].add(assistant)
        pref = assistant.prefs[group.index]
        if pref == PREF_BAD:
            penalties.append(f'"{assistant.name}" on "{group.name}": bad time')
        elif pref == PREF_OK:
            penalties.append(f'"{assistant.name}" on "{group.name}": ok time')

    for group in instance.groups:
        if group.pred:
            for assistant in schedule[group.pred.index]:
                if assistant in schedule[group.index]:
                    penalties.append(f'"{assistant.name}" on "{group.pred.name}" and "{group.name}": consecutive groups')
    print('Schedule:')
    for group in instance.groups:
        personnel = [assistant.name for assistant in schedule[group.index]]
        print(f' {group.name}: '+(', '.join(sorted(personnel))))
    print('')
    print(f'Solution cost: {best_model.cost}')
    print('Inoptimalities:')
    for penalty in penalties:
        print(' '+penalty)


if __name__ == '__main__':
    main()
