import os
import sys
import tarfile
from abc import ABC, abstractmethod


class Storage(ABC):
    archived_names = set()

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def write_description(self, description: str, listing_id: str) -> None:
        pass

    @abstractmethod
    def read_description(self, listing_id: str) -> str:
        pass

    @abstractmethod
    def description_download(self, listing_id: str) -> str:
        pass


class FileStorage(Storage):
    def __init__(self):
        if (data_dir := os.getenv("DATA_DIRECTORY")) is None:
            print("DATA_DIRECTORY not set, defaulting to ./data", file=sys.stderr)
            data_dir = "./data"
        self.listing_directory = data_dir + "/listings"
        self.data_archive = data_dir + "/data-archive.tar.gz"

        if os.path.exists(self.data_archive):
            with tarfile.open(self.data_archive, "r") as tar:
                self.archived_names = set(tar.getnames())

    def write_description(self, description: str, listing_id: str) -> None:
        """
        Writes the description of the listing to the file "{LISTING_DIRECTORY}/{listing_id}.txt"

        description -- The description to write
        listing_id -- The id of the listing
        """
        if description == "":
            print(f"Description for {listing_id} was empty")
            return
        try:
            with open(self._description_path(listing_id), "w+") as f:
                f.write(description)
        except OSError as e:
            print(f"Error writing file for listing {listing_id}: {e}")

    def read_description(self, listing_id: str) -> str | None:
        """
        Read the description of the file from "{LISTING_DIRECTORY}/{listing_id}.txt" or the archive.
        """
        path = self._description_path(listing_id)
        if os.path.exists(path):
            with open(self._description_path(listing_id), "r") as f:
                return f.read()
        elif listing_id in self.archived_names:
            with tarfile.open(self.data_archive, "r") as tar:
                return tar.extractfile(listing_id).read().decode("utf-8")
        else:
            return None

    def description_download(self, listing_id: str) -> bool:
        """
        Checks if the description of the listing has been downloaded.
        """
        return os.path.exists(self._description_path(listing_id)) or listing_id in self.archived_names

    def _description_path(self, listing_id: str) -> str:
        """
        Returns the path to the description file for the given listing
        """
        return f"{self.listing_directory}/{listing_id}.txt"


class S3Storage(Storage):
    pass
