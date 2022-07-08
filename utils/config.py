import tomli

DEFAULT_FILE_LOCATION = "./config.toml"


class ConfigLoader:
    """ConfigLoader provides methods for loading and reading values from a .toml file."""

    def __init__(self, file_path: str = DEFAULT_FILE_LOCATION) -> None:
        self._file_path = file_path
        self.values = {}
        self.reload()

    def reload(self):
        """Loads the config using the path this loader was initialized with, overriding any previously stored values."""
        with open(self._file_path, "rb") as f:
            self.values = tomli.load(f)
        self.set_attributes()

    def set_attributes(self):
        self.bot = self.values["bot"]
