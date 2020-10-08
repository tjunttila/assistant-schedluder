`assistant-scheduler` is a small tool for
scheduling teaching assistants in exercise groups.
It was originally developed for teachers of programming courses
at the CS department of Aalto University.
These courses can have roughly twenty teaching assistants and exercise session groups.
As the assistants are students, they have other duties as well and
can thus only teach in some of the exercise groups.
Furthermore, some groups are required to have more assistants than others.
As finding an optimal scheduling under such constraints can be hard to do by hand, an automated tool was required and developed.

# Requirements

* [Python](https://www.python.org/) programming language, version 3.6 or higher.
* [Clingo](https://github.com/potassco/clingo) answer set solver tool.

# Usage

In the simplest case,
```
python3 assistant-scheduler.py config_file
```
All the options can be printed with `python3 assistant-scheduler.py --help`.

The configuration file describes the exercise groups and assistants.
It can be either in the [JSON](https://tools.ietf.org/html/rfc8259) or [YAML](https://yaml.org/) formats.
Please see the file [sample-1.yaml](sample-1.yaml) file for a commented YAML example,
and [sample-1.json](sample-1.json) for its JSON counterpart.
The file [sample-2.json](sample-2.json) contains a more constrained configuration example in which not all the requirements can be fulfilled.

# License

The `assistant-scheduler` tool is released under the [MIT License](LICENSE).
