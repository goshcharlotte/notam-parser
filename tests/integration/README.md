# Setup

1. Create a virtual environment if you haven't already. In the root of 'tests':
```bash
python -m venv .parser_env
```

2. Activate your environment and install the python libraries:
```bash
source .parser_env/bin/activate
python -m pip install -r ./requirements.txt
```

## Tests
The db integration tests are run against docker instance of mongodb. It uses python_on_whales to execute docker compose and dispose of the container and image at the end of the test.

At the root of the project:
```bash
python tests/integration/utils/db_setup.py stop_docker_db && python tests/integration/utils/db_setup.py start_docker_db && python -m pytest tests/integration/parser_test.py && python tests/integration/utils/db_setup.py stop_docker_db
```

### Debugging Integration tests


