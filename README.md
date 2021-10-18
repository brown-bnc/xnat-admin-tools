# xnat-admin-tools
Scripts used for xnat administration tasks

## Code Style

#### Pre-Commit hooks

This repository has pre-commit hooks configured to enforce typing and formatting.

To set up the hooks, run 

```
poetry run pre-commit install
```

Now, you hooks will run on `git commit`

If you would like to run on all files (not just staged ones), you can run

```
poetry run pre-commit run --all-files
```

The following hooks are set up 
- [isort](https://github.com/timothycrosley/isort) - Sorting imports
- [black](https://github.com/ambv/black) - Formatting
- [flake8](https://gitlab.com/pycqa/flake8) - Linting
- [mypy](https://github.com/pre-commit/mirrors-mypy) - Typing

More details below on these tools

### Typing

Please use [type hints](https://mypy.readthedocs.io/en/stable/) on all signatures where reasonable.  This will make sure the code is more readable, can be statically tested for type soundness, and helps fill in the documentation.

### Formatting

### black

The code must conform to `black`'s standards and this is automatically checked via github actions.  While it is highly recommended to run the pre-commit hooks, you can also run black directly  to automatically fix files with `poetry run black .` from the root of the `xnat_tools` directory.

### flake8
The code must not have any egregious linting errors. And others should be minimized as reasonable.
