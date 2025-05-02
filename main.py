#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
import yaml
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ConfigRedundancyChecker:
    """
    Detects redundant or conflicting configuration settings in YAML or JSON files.
    """

    def __init__(self, file_path: str):
        """
        Initializes the ConfigRedundancyChecker.

        Args:
            file_path (str): The path to the configuration file.
        """
        self.file_path = file_path
        self.config_data: Optional[Dict[str, Any]] = None
        self.file_type: Optional[str] = None  # added file_type attribute

    def load_config(self) -> None:
        """
        Loads the configuration file and determines its type (YAML or JSON).
        """
        try:
            with open(self.file_path, "r") as f:
                try:
                    self.config_data = yaml.safe_load(f)
                    self.file_type = "yaml"
                    logging.info(f"Successfully loaded YAML configuration from {self.file_path}")
                except yaml.YAMLError:
                    f.seek(0) # Reset file pointer to beginning
                    try:
                        self.config_data = json.load(f)
                        self.file_type = "json"
                        logging.info(f"Successfully loaded JSON configuration from {self.file_path}")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to load {self.file_path} as either YAML or JSON: {e}")
                        raise ValueError("Invalid configuration file format. Must be YAML or JSON.")
        except FileNotFoundError:
            logging.error(f"File not found: {self.file_path}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading the file: {e}")
            raise

    def check_redundancy(self) -> List[str]:
        """
        Checks for redundant or conflicting configuration settings.

        Returns:
            List[str]: A list of strings describing any detected redundancies or conflicts.
        """

        if not self.config_data:
            logging.warning("No configuration data loaded. Call load_config() first.")
            return []

        redundancies: List[str] = []

        # Placeholder for more advanced checks.  This is where the core logic would reside.
        # Example:
        # if "option_a" in self.config_data and "option_b" in self.config_data:
        #     if self.config_data["option_a"] == True and self.config_data["option_b"] == False:
        #         redundancies.append("option_b is redundant as option_a overrides it.")

        # Example checking for duplicate keys (not a reliable way in general JSON/YAML but illustrative)
        seen_keys = set()
        def check_duplicate_keys(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    full_path = f"{path}.{key}" if path else key
                    if key in seen_keys:
                        redundancies.append(f"Duplicate key found: {full_path}")
                    else:
                        seen_keys.add(key)
                    check_duplicate_keys(value, full_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    check_duplicate_keys(item, f"{path}[{i}]")

        #reset seen keys so that each check only sees keys related to the section being inspected
        seen_keys = set()
        check_duplicate_keys(self.config_data)

        if not redundancies:
            logging.info("No redundancies or conflicts found.")
        else:
            for redundancy in redundancies:
                logging.warning(redundancy)

        return redundancies


def setup_argparse() -> argparse.ArgumentParser:
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Detects redundant or conflicting configuration settings in YAML or JSON files."
    )
    parser.add_argument(
        "file_path",
        type=str,
        help="The path to the configuration file.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )

    return parser


def main() -> int:
    """
    Main function to execute the configuration redundancy checker.

    Returns:
        int: 0 on success, 1 on failure.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled.")


    file_path = args.file_path
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return 1

    try:
        checker = ConfigRedundancyChecker(file_path)
        checker.load_config()
        redundancies = checker.check_redundancy()

        if redundancies:
            print("Redundancies/Conflicts found:")
            for redundancy in redundancies:
                print(f"- {redundancy}")
            return 1  # Indicate failure due to detected redundancies
        else:
            print("No redundancies or conflicts found.")
            return 0  # Indicate success

    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())