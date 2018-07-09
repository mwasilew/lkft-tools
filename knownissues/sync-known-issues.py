#!/usr/bin/python3

import argparse
import yaml

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Known Issue yaml file")
    args = parser.parse_args()

    config = args.config
    with open(config, 'r') as f:
        config_data = yaml.load(f)

    print(config_data)


if __name__ == '__main__':
    main()
