class Version:
    ALLOWED_FILES = ["VERSION", "BUILD"]

    def __init__(self):
        self.version = self.__read_from_file("VERSION")
        self.build = self.__read_from_file("BUILD")

    def __read_from_file(self, filename) -> str:
        if filename not in self.ALLOWED_FILES:
            raise ValueError(f"File {filename} not allowed")

        with open(f"/readonly_fs/{filename}") as f:
            return f.read().strip()
