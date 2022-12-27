import os
import csv
import argparse
import getpass
import sys

import urllib3
import requests
from requests.exceptions import MissingSchema

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CSV_FILENAME = "registries.csv"


def get_user_settings():
    parser = argparse.ArgumentParser(description="Prisma CLoud ECR Adder")
    parser.add_argument(
        "-u",
        "--prisma-cloud-url",
        help='Prisma Cloud API URL. It can be found in "Compute" -> '
        '"System" -> "Utilities"',
        required=True,
    )
    parser.add_argument(
        "-d",
        "--duplicate-entries",
        help="Allow duplicate entries: Y or N",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--regions",
        help="Comma separated list of regions to scan, e.g: "
        "ap-southeast-1,ap-southeast-2",
        required=True,
    )
    args = vars(parser.parse_args())

    args["duplicate_entries"] = _check_duplicate_entries_setting(
        args["duplicate_entries"]
    )

    print(
        'Please retrieve your API token from "Compute" -> "System" -> "Utilities" and enter it below.'
    )
    prisma_cloud_token = getpass.getpass(prompt="API token: ")

    args["prisma_cloud_token"] = prisma_cloud_token

    return args


def _check_duplicate_entries_setting(duplicate_entries_setting):
    if duplicate_entries_setting.upper() == "Y":
        return True
    elif duplicate_entries_setting.upper() == "N":
        return False
    else:
        sys.exit(
            '\nError: The "duplicate-entries" parameter must be set to "Y" or "N".'
        )


class EcrAdder:
    def __init__(self, user_settings):
        prisma_cloud_token = user_settings["prisma_cloud_token"]
        self.prisma_cloud_url = user_settings["prisma_cloud_url"]
        self.allow_duplicate_entries = user_settings["duplicate_entries"]
        self.regions = set(user_settings["regions"].split(","))

        self.auth_headers = self._get_auth_headers(prisma_cloud_token)
        self.existing_registry_names = self.get_existing_registry_names()

        self.new_registry_hostnames = set()
        self.duplicate_registry_hostnames = set()
        self.errored_registries = dict()
        self.account_counter = 0

    @staticmethod
    def _get_auth_headers(prisma_cloud_token):
        auth_headers = {
            "Authorization": f"Bearer {prisma_cloud_token}",
            "content-type": "application/json",
        }

        return auth_headers

    def get_existing_registry_names(self):
        existing_registry_names = set()

        url = f"{self.prisma_cloud_url}/api/v1/settings/registry"
        try:
            response = requests.get(url, headers=self.auth_headers, verify=False).json()

        except MissingSchema:
            sys.exit(
                "\nError: Your Prisma Cloud URL appears to be incorrect. Please retrieve it from "
                '"Compute" -> "System" -> "Utilities".'
            )

        try:
            specifications = response["specifications"]

        except KeyError:
            sys.exit(
                "\nError: Could not log into Prisma Cloud. Please check your URL and API token. Both can be "
                'retrieved from "Compute" -> "System" -> "Utilities".'
            )

        for entry in specifications:
            registry_name = entry["registry"]
            existing_registry_names.add(registry_name)

        return existing_registry_names

    def add_registries(self):
        script_dir_abs_path = os.path.dirname(os.path.realpath(__file__))
        csv_abs_path = os.sep.join([script_dir_abs_path, CSV_FILENAME])

        api_url = f"{self.prisma_cloud_url}/api/v1/settings/registry"

        with open(csv_abs_path, "r") as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                account_id = row[0]
                if account_id == "accountId":
                    continue

                print(
                    f'\nFound Account ID "{account_id}". Adding registries in the specified regions:'
                )
                self.account_counter += 1
                self._add_registries(api_url, account_id, row)

        self._generate_registry_report()

    @staticmethod
    def _print_standard_report(title, registry_hostnames, registry_count):
        print(f"\n{registry_count} {title}:")
        if registry_hostnames:
            for count, registry_hostname in enumerate(registry_hostnames, start=1):
                print(f"{count}. {registry_hostname}")
        else:
            print("N/A")

    def _print_errored_report(self, errored_registry_count):
        print(f"\n{errored_registry_count} REGISTRIES THAT EXPERIENCED ERRORS:")
        if not self.errored_registries:
            print("N/A")

            return

        count = 1
        for registry_name, error_msg in self.errored_registries.items():
            print(f"{count}. {registry_name} - {error_msg}")
            count += 1

    def _generate_registry_report(self):
        divider = "*" * 100

        print(f"\n{divider}")

        new_registry_count = len(self.new_registry_hostnames)
        duplicate_registry_count = len(self.duplicate_registry_hostnames)
        region_count = len(self.regions)
        errored_registry_count = len(self.errored_registries)

        duplicates_added = "ADDED" if self.allow_duplicate_entries else "(SKIPPED)"

        self._print_standard_report(
            "NEW REGISTRIES ADDED", self.new_registry_hostnames, new_registry_count
        )
        self._print_standard_report(
            f"DUPLICATE REGISTRIES {duplicates_added}",
            self.duplicate_registry_hostnames,
            duplicate_registry_count,
        )
        self._print_errored_report(errored_registry_count)

        print(f"\n{divider}")

        if self.allow_duplicate_entries:
            total_registry_count = duplicate_registry_count + new_registry_count

            print(
                f"Successfully added {total_registry_count} registries across "
                f"{self.account_counter} accounts and {region_count} regions.\n"
                f"Out of the {total_registry_count} registries added, {new_registry_count} were new "
                f"registries and {duplicate_registry_count} were duplicates."
            )

        else:
            print(
                f"Successfully added {new_registry_count} registries across {self.account_counter} "
                f"accounts and {region_count} regions.\n"
                f"{duplicate_registry_count} duplicate registries were found and skipped."
            )

        if errored_registry_count:
            print(
                f"{errored_registry_count} registries encountered errors. Please see above for more "
                f"information."
            )

        print(f"{divider}")

    def _get_registry_payload(self, registry_hostname, row):
        scanner_str = row[4]

        try:
            num_scanners = int(scanner_str)

        except ValueError:
            error_msg = (
                f'The number of scanners for {registry_hostname} is "{scanner_str}". '
                f"Please update your CSV file"
            )

            print(f"Error: {error_msg}")
            self.errored_registries[registry_hostname] = error_msg

            return

        registry_payload = {
            "version": "aws",
            "registry": registry_hostname,
            "credentialID": row[1],
            "collections": [row[2]],
            "os": row[3],
            "scanners": num_scanners,
        }

        return registry_payload

    def _add_registries(self, api_url, account_id, row):
        for region in self.regions:
            registry_hostname = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
            print(f'Checking "{registry_hostname}"...')

            if (
                registry_hostname in self.existing_registry_names
                and not self.allow_duplicate_entries
            ):
                print(
                    "It is a duplicate. Skipping it because allowing duplicate entries is disabled."
                )

                self.duplicate_registry_hostnames.add(registry_hostname)
                continue

            registry_payload = self._get_registry_payload(registry_hostname, row)

            # skip adding payload if CSV file has an incorrect value
            if not registry_payload:
                continue

            response = requests.post(
                api_url, headers=self.auth_headers, json=registry_payload, verify=False
            )

            if response.status_code == 200:
                if registry_hostname not in self.existing_registry_names:
                    print("Successfully added new registry.")
                    self.new_registry_hostnames.add(registry_hostname)

                else:
                    print(
                        "It is a duplicate but it was added anyway because allowing duplicate entries was enabled."
                    )

                    self.duplicate_registry_hostnames.add(registry_hostname)

            else:
                get_error_msg = response.json()["err"].capitalize()
                error_msg = (
                    f"{get_error_msg}. Please ensure the settings in your CSV file match your Prisma Cloud "
                    f"configuration"
                )
                print(f"Error: {error_msg}")
                self.errored_registries[registry_hostname] = error_msg


def main():
    user_settings = get_user_settings()
    ecr_adder = EcrAdder(user_settings)
    ecr_adder.add_registries()


if __name__ == "__main__":
    main()
