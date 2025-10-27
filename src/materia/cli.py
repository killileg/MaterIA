# materia/cli.py
import click
from pathlib import Path
from materia.epd.pipeline import run_materia


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.argument("epd_folder_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output_path", "-o", type=click.Path(path_type=Path), required=False)
def main(input_path: Path, epd_folder_path: Path, output_path: Path | None):
    """Process the given file or folder path."""
    run_materia(input_path, epd_folder_path, output_path)
