#!/usr/bin/env python3

# Copyright 2021 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import json
import requests

from argparse import ArgumentParser
from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path
from sys import exit


URL_API = "https://opendev.org/api/v1/repos/openstack"
DIR_CONTENT_ENDPOINT = URL_API + "/{project}/contents/{folder}?ref={branch}"


def process_arguments() -> tuple:
    """
    Return the branch,
    destination folder
    and project name of the processed arguments
    """
    parser = ArgumentParser()
    parser.add_argument(
        '-p', '--project',
        dest='project',
        help="Insert the project name",
        metavar="PROJECT",
        required=True
    )
    parser.add_argument(
        '-b', '--branch',
        dest='branch',
        help="Select branch to work",
        metavar="BRANCH",
        required=True
    )
    parser.add_argument(
        '-d', '--destination',
        dest='destination',
        help="Insert the destination folder",
        metavar="DESTINATION",
        required=True
    )
    arguments = parser.parse_args()
    return arguments


def download_file(url: str, destination_folder: str) -> None:
    Path(destination_folder).mkdir(parents=True, exist_ok=True)
    file_name = url.split('/')[-1]
    try:
        data = requests.get(url)
        with open(f"{destination_folder}/{file_name}", 'wb') as file:
            print(f"Downloading file {file_name}")
            file.write(data.content)
    except Exception as e:
        print(f"Error downloading file {file_name}. Details: {repr(e)}")
        exit(1)


def get_raw_url_files_in_repository(
    project_name: str,
    data_required: dict,
    branch: str = 'master'
) -> list:
    response = requests.get(
        url=DIR_CONTENT_ENDPOINT.format(
            project=project_name,
            folder='.',
            branch=branch
        )
    )
    if response.status_code != 200:
        print("Error getting URLs files from folder in remote repository."
              f"Details: {repr(json.loads(response.text)['errors'])}")
        exit(1)
    url_files = []
    for folder_file_information in json.loads(response.text):
        file_name = folder_file_information['name']
        if file_name in data_required['files']:
            url_files.append(folder_file_information['download_url'])
        if file_name in data_required['folder']:
            response = requests.get(
                url=DIR_CONTENT_ENDPOINT.format(
                    project=project_name,
                    folder=file_name,
                    branch=branch
                )
            )
            for folder_file_information in json.loads(response.text):
                url_files.append(folder_file_information['download_url'])
    return url_files


def download_files_parallel(urls: list, destination_folder: str) -> None:
    pool = Pool(cpu_count())
    download_function = partial(
        download_file,
        destination_folder=destination_folder
    )
    pool.map(download_function, urls)
    pool.close()
    pool.join()


def main() -> None:
    arguments = process_arguments()
    data_required = {
        'folder': ['zuul.d', '.zuul.d'],
        'files': ['zuul.yaml', '.zuul.yaml']
    }
    urls = get_raw_url_files_in_repository(
        arguments.project,
        data_required,
        arguments.branch
    )
    download_files_parallel(urls, arguments.destination)


if __name__ == "__main__":
    main()