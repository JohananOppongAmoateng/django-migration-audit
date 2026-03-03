# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/JohananOppongAmoateng/django-migration-audit/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/django\_migration\_audit/\_\_init\_\_.py                          |        1 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/apps.py                                  |        4 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/core/\_\_init\_\_.py                     |        0 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/core/extractor.py                        |       56 |       11 |       38 |        2 |     76% |112, 137-166 |
| src/django\_migration\_audit/core/introspection.py                    |       34 |        0 |        6 |        0 |    100% |           |
| src/django\_migration\_audit/core/loader.py                           |       43 |        0 |       10 |        0 |    100% |           |
| src/django\_migration\_audit/core/state.py                            |      111 |        6 |       32 |        8 |     90% |132->exit, 141, 143->exit, 155->exit, 160->exit, 166->exit, 178->exit, 186, 190, 194, 198, 235 |
| src/django\_migration\_audit/invariants/\_\_init\_\_.py               |        5 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/invariants/base.py                       |      101 |        8 |       26 |        0 |     94% |65, 71, 81, 118, 146, 180, 208, 236 |
| src/django\_migration\_audit/invariants/columns.py                    |       64 |        5 |       22 |        2 |     92% |24, 77, 92, 133, 144 |
| src/django\_migration\_audit/invariants/constraints.py                |       74 |        9 |       36 |        6 |     86% |28, 35, 73, 97-98, 100->79, 131, 139, 144->136, 174, 192 |
| src/django\_migration\_audit/invariants/tables.py                     |       63 |        6 |       20 |        2 |     90% |22, 54, 62, 104, 147, 171 |
| src/django\_migration\_audit/management/\_\_init\_\_.py               |        0 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/management/commands/\_\_init\_\_.py      |        0 |        0 |        0 |        0 |    100% |           |
| src/django\_migration\_audit/management/commands/audit\_migrations.py |       89 |       14 |       20 |        3 |     81% |79-82, 85->92, 116-135, 144->149 |
| src/django\_migration\_audit/models.py                                |        0 |        0 |        0 |        0 |    100% |           |
| **TOTAL**                                                             |  **645** |   **59** |  **210** |   **23** | **89%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/JohananOppongAmoateng/django-migration-audit/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/JohananOppongAmoateng/django-migration-audit/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/JohananOppongAmoateng/django-migration-audit/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/JohananOppongAmoateng/django-migration-audit/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FJohananOppongAmoateng%2Fdjango-migration-audit%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/JohananOppongAmoateng/django-migration-audit/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.