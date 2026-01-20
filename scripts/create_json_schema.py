import argparse
import importlib.util
import pathlib
import pydantic
import sys
import json

def load_schema(schema_python_path: pathlib.Path, root: str | None) \
-> pydantic.RootModel | None:
    """ Dynamically load a python file containing the Schema
    as a pydantic BaseModel class. If the root name is not given
    then the root should be exported as a gloabal variable
    named ROOT_SCHEMA_CLASS. """
    try:
        python_module = schema_python_path.stem
        spec = importlib.util.spec_from_file_location(python_module, schema_python_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[python_module] = module
        spec.loader.exec_module(module)

        root = root if root else "ROOT_SCHEMA_CLASS"
        return getattr(module, root)

    except Exception as e:
        print(e)
        return None
    
def prepare_schema_path(path: str | None, name: str) -> pathlib.Path:
    if path is not None:
        file_path = pathlib.Path(path)
    else:
        home = pathlib.Path.home()
        file_path = home / "schemas" / f"{name}.schema.json"

    if not file_path.parent.exists(): 
        file_path.parent.mkdir(parents=True, exist_ok=True)

    if not file_path.exists(): file_path.touch()
    abs_path = file_path.resolve()
    return abs_path
    
def create_json_schema( model: pydantic.RootModel, output: str | None ) -> None:
    """ Create the JSON file with the schema """
    output_path = prepare_schema_path( output, model.__name__ )
    print(f"[*] Saving the schema at {output_path.stem}")
    with open( output_path, mode='w', encoding='utf-8' ) as io:
        json.dump( model.model_json_schema(), io, indent=2 )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("schema_file", help="Abs path of the python file with the schema")
    parser.add_argument("-r", "--root", help="Root object name of the schema", required=False, type=str)
    parser.add_argument("-o", "--output", help="Abs output path", required=False, type=str)
    args = parser.parse_args()

    schema_path = pathlib.Path(args.schema_file)
    assert schema_path.absolute().is_file(), f"{schema_path.str()} does not exists"

    print(f"[*] Loading schema from {args.schema_file}", end="")
    if args.root: print(f" at root {args.root}", end="")
    print()
    schema: pydantic.RootModel = load_schema( schema_path, args.root )
    
    create_json_schema( schema, args.output )

if __name__ == "__main__":
    main()