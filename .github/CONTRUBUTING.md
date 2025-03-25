# Contributing

## Updating environment packages

1. Edit packages in `Pipfile`: `pipenv install <package>`
1. Lock environment/generate the updated `Pipfile.lock`: `pipenv lock`
1. Install latest environment from `Pipfile.lock`: `pipenv install --ignore-pipfile`
1. Commit updated `Pipfile` and `Pipfile.lock`.

## Submitting a pull request

1. Create a new branch: `git checkout -b my-branch-name`
1. Make your change, add tests, and ensure tests pass: `python3 -m unittest -v`
1. Submit a pull request: `gh pr create --web`
