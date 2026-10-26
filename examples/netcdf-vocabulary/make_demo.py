"""Create two synthetic metadata examples, refusing to overwrite either file."""
import argparse
import os
from pathlib import Path

from netCDF4 import Dataset


def make_demo(folder):
    folder = Path(folder)
    paths = [folder / "og.nc", folder / "partner.nc"]
    if any(os.path.lexists(path) for path in paths):
        raise FileExistsError("Choose a directory without og.nc or partner.nc")
    folder.mkdir(parents=True, exist_ok=True)
    examples = [
        [("TCPUCHLA", "OG1", "TCPUCHLA", "1", [100, 101, 102]),
         ("CNDC", "OG1", "CNDC", "S m-1", [3.8, 3.9, 4.0])],
        [("cpu_temperature", "P01", "TCNTICPU", "1", [201, 202, 203]),
         ("conductivity", "P01", "CNDCZZ01", "S m-1", [4.1, 4.2, 4.3])],
    ]
    for path, variables in zip(paths, examples):
        with Dataset(path, "w", clobber=False, format="NETCDF4") as dataset:
            dataset.title = "Synthetic vocabulary lookup example"
            dataset.comment = "Focused metadata example; not a complete CF or OceanGliders dataset."
            dataset.createDimension("sample", 3)
            sample = dataset.createVariable("sample", "i4", ("sample",))
            sample[:] = [0, 1, 2]
            sample.long_name = "Synthetic sample index"
            for name, collection, concept, units, values in variables:
                variable = dataset.createVariable(name, "f8", ("sample",))
                variable[:] = values
                variable.units = units
                variable.vocabulary = f"http://vocab.nerc.ac.uk/collection/{collection}/current/{concept}/"
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    for path in make_demo(args.directory):
        print(path)
