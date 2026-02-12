import os
import sys
import tarfile
from abc import ABC, abstractmethod

import boto3
import botocore


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
    def description_download(self, listing_id: str) -> bool:
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
            with open(path, "r") as f:
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
    def __init__(self):
        s3_endpoint_url = os.getenv("S3_ENDPOINT_URL")
        s3_key_id = os.getenv("S3_KEY_ID")
        s3_access_key = os.getenv("S3_ACCESS_KEY")
        if not (s3_endpoint_url and s3_key_id and s3_access_key):
            print("Please provide S3_ENDPOINT_URL, S3_KEY_ID and S3_ACCESS_KEY to use S3")
            raise Exception("S3_ENDPOINT_URL, S3_KEY_ID and S3_ACCESS_KEY to use S3")

        s3 = boto3.resource(
            "s3",
            endpoint_url=s3_endpoint_url,
            aws_access_key_id=s3_key_id,
            aws_secret_access_key=s3_access_key,
            aws_session_token=None,
            config=boto3.session.Config(signature_version="s3v4"),
            verify=False,
        )
        self.bucket = s3.Bucket("job-search")

    def write_description(self, description: str, listing_id: str) -> None:
        if description == "":
            print(f"Description for {listing_id} was empty")
            return
        self.bucket.put_object(Key=listing_id + ".txt", Body=description)

    def read_description(self, listing_id: str) -> str:
        obj = self.bucket.Object(listing_id + ".txt").get()
        return obj["Body"].read().decode("utf-8")

    def description_download(self, listing_id: str) -> bool:
        try:
            self.bucket.Object(listing_id + ".txt").load()
            return True
        except botocore.exceptions.ClientError:
            return False
