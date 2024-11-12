import logging
import click
from deepfigures import settings
from scripts import execute

logger = logging.getLogger(__name__)

@click.command(
    context_settings={
        'help_option_names': ['-h', '--help']
    })
def build():
    """Build docker images for deepfigures."""
    
    # 只构建 CPU 镜像
    docker_img = settings.DEEPFIGURES_IMAGES['cpu']
    tag = docker_img['tag']
    dockerfile_path = docker_img['dockerfile_path']

    execute(
        'docker build'
        ' --tag {tag}:{version}'
        ' --file {dockerfile_path} .'.format(
            tag=tag,
            version=settings.VERSION,
            dockerfile_path=dockerfile_path),
        logger)

if __name__ == '__main__':
    build()