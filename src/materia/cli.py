import click
import json
from pathlib import Path
from materia.epd.pipeline import run_materia

# We print the results in an output_path for the moment


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("epd_folder_path", type=click.Path(exists=True))
@click.option("--output_path", "-o", type=click.Path(), help="Optional output path. ")
def main(input_path, epd_folder_path, output_path):  # ADD EPD_PATH ARGUMENT
    """Process the given file or folder path."""
    path_gen = Path(input_path)
    # path_epds = Path(epd_path)
    click.echo(f"Received path: {path_gen}")

    average, uuid = run_materia(input_path, epd_folder_path)

    if output_path:
        output_path = Path(output_path)
        click.echo(f"Output will be written to: {Path(output_path)}")
        # Ensure parent folders exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(average, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        click.echo(f"Output has been written in {output_path}")
    else:
        if path_gen.is_file():  # path_gen is a file
            output_folder_temp = Path(path_gen).parent.parent
        elif path_gen.is_dir():  # path_gen is a folder
            output_folder_temp = Path(path_gen).parent

        output_folder = output_folder_temp / "output_generic"
        output_folder.mkdir(parents=True, exist_ok=True)

        output_file = output_folder / f"{uuid}_output.json"
        output_file.write_text(
            json.dumps(average, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        click.echo(f"No output path provided. File created at {output_file}")
