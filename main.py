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

    def find_raw_duplicate_keys(self) -> List[str]:
        """Detect true duplicate keys from the raw document tree.

        yaml.safe_load collapses a repeated key before any check can see it,
        so this walks the composed node tree instead, where both pairs of a
        repeated key in one mapping are still present.
        """
        findings: List[str] = []
        try:
            with open(self.file_path, "r") as f:
                node = yaml.compose(f)
        except Exception:
            return findings
        def walk(node, path=""):
            if isinstance(node, yaml.MappingNode):
                seen = {}
                for key_node, value_node in node.value:
                    key = getattr(key_node, "value", str(key_node))
                    full_path = f"{path}.{key}" if path else str(key)
                    if key in seen:
                        note = f"Duplicate key found: {full_path}"
                        if getattr(value_node, "value", None) != getattr(seen[key], "value", None):
                            note += " (set multiple times with different values)"
                        findings.append(note)
                    else:
                        seen[key] = value_node
                    walk(value_node, full_path)
            elif isinstance(node, yaml.SequenceNode):
                for i, item in enumerate(node.value):
                    walk(item, f"{path}[{i}]")
        if node is not None:
            walk(node)
        return findings

    def check_redundancy(self) -> List[str]:
        """
        Checks for redundant or conflicting configuration settings.

        Returns:
            List[str]: A list of strings describing any detected redundancies or conflicts.
        """

        if not isinstance(self.config_data, dict) or not self.config_data:
            raise ValueError("No configuration data to check: the file is empty or does not contain a mapping of settings.")

        redundancies: List[str] = []
        redundancies.extend(self.find_raw_duplicate_keys())

        # Seen keys are scoped to the single mapping that holds them, so the
        # same key name in two different sections is not a duplicate.
        def check_duplicate_keys(data, path=""):
            if isinstance(data, dict):
                seen_keys = set()
                for key, value in data.items():
                    full_path = f"{path}.{key}" if path else key
                    if key in seen_keys:
                        msg = f"Duplicate key found: {full_path}"
                        if msg not in redundancies:
                            redundancies.append(msg)
                    else:
                        seen_keys.add(key)
                    check_duplicate_keys(value, full_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    check_duplicate_keys(item, f"{path}[{i}]")

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
        print(f"Error: {e}")
        return 1
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())