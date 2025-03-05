"""DB setup.

This class file serves as a util for providing and destroying the docker db for testing
"""

import sys

from python_on_whales import DockerClient

docker_image = DockerClient(compose_files=["tests/integration/utils/docker-compose.yml"])


def start_docker_db() -> None:
    """
    Start mongo docker container
    """
    print("calling docker...")

    try:
        print("running compose")
        docker_image.compose.up(
            pull="always",
            color=True,
            detach=True,
        )

        print("mongo db container up and running")
    except Exception as error:
        print(f"ERROR :  {error}")


def stop_docker_db() -> None:
    """
    Stop mongo docker container
    """
    print("stopping docker db")
    docker_image.compose.down(remove_orphans=True, volumes=True, remove_images="all")
    docker_image.compose.kill(services=["mongodb"])
    print("mongo db container stopped and volumes removed")

if __name__ == "__main__":
    globals()[sys.argv[1]]()