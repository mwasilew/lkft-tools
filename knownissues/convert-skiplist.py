#!/usr/bin/python3

import argparse
import logging
import pprint
import yaml


FORMAT = "%(funcName)20s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--config-files",
                        nargs="+",
                        required=True,
                        help="Instance config files",
                        dest="config_files")
    parser.add_argument("-v",
                        "--debug",
                        action="store_true",
                        default=False,
                        help="Enable debug",
                        dest="debug")
    parser.add_argument("-s",
                        "--suite_name",
                        help="Test Suite name to be prepanded to test name",
                        required=True,
                        dest="suite_name")

    args = parser.parse_args()

    skiplist = []
    for f in args.config_files:
        with open(f, 'r') as stream:
            try:
                loaded_config = yaml.load(stream)
                skiplist = skiplist + loaded_config.get('skiplist', [])
            except yaml.YAMLError as exc:
                logger.error(exc)
                sys.exit(1)


    production_project = {
        'name': 'LKFT',
        'url': 'https://qa-reports.linaro.org',
        'projects': [
            'lkft/linux-mainline-oe',
            'lkft/linux-next-oe',
            'lkft/linux-stable-rc-4.4-oe',
            'lkft/linux-stable-rc-4.9-oe',
            'lkft/linux-stable-rc-4.14-oe',
            'lkft/linux-stable-rc-4.16-oe',
            'lkft/linux-stable-rc-4.17-oe'
            ],
        'environments': [
            {'slug': 'hi6220-hikey',
             'architecture': 'arm64'},
            {'slug': 'juno-r2',
             'architecture': 'arm64'},
            {'slug': 'dragonboard-410c',
             'architecture': 'arm64'},
            {'slug': 'x15',
             'architecture': 'arm32'},
            {'slug': 'x86',
             'architecture': 'x86_64'},
            {'slug': 'qemu_x86_64',
             'architecture': 'x86_64'},
            {'slug': 'qemu_x86_32',
             'architecture': 'x86'},
            {'slug': 'qemu_arm',
             'architecture': 'arm32'},
            {'slug': 'qemu_arm64',
             'architecture': 'arm64'}
            ],
        'known_issues': []
    }
    staging_project = {
        'name': 'LKFT-staging',
        'url': 'https://staging-qa-reports.linaro.org',
        'projects': [
            'lkft/linux-mainline-oe',
            'lkft/linux-next-oe',
            'lkft/linux-stable-rc-4.4-oe',
            'lkft/linux-stable-rc-4.9-oe',
            'lkft/linux-stable-rc-4.14-oe',
            'lkft/linux-stable-rc-4.16-oe',
            'lkft/linux-stable-rc-4.17-oe'
            ],
        'environments': [
            {'slug': 'hi6220-hikey',
             'architecture': 'arm64'},
            {'slug': 'juno-r2',
             'architecture': 'arm64'},
            {'slug': 'dragonboard-410c',
             'architecture': 'arm64'},
            {'slug': 'x15',
             'architecture': 'arm32'},
            {'slug': 'x86',
             'architecture': 'x86_64'},
            {'slug': 'qemu_x86_64',
             'architecture': 'x86_64'},
            {'slug': 'qemu_x86_32',
             'architecture': 'x86'},
            {'slug': 'qemu_arm',
             'architecture': 'arm32'},
            {'slug': 'qemu_arm64',
             'architecture': 'arm64'}
            ],
        'known_issues': []
    }

    conversion_dict = {
        '4.4': 'lkft/linux-stable-rc-4.4-oe',
        '4.9': 'lkft/linux-stable-rc-4.9-oe',
        '4.14': 'lkft/linux-stable-rc-4.14-oe',
        '4.15': 'lkft/linux-stable-rc-4.15-oe',
        '4.16': 'lkft/linux-stable-rc-4.16-oe',
        '4.17': 'lkft/linux-stable-rc-4.17-oe',
        'mainline': 'lkft/linux-mainline-oe',
        'next': 'lkft/linux-next-oe',
    }
    all_boards = [
        {'slug': 'hi6220-hikey'},
        {'slug': 'juno-r2'},
        {'slug': 'dragonboard-410c'},
        {'slug': 'x15'},
        {'slug': 'x86'},
        {'slug': 'qemu_x86_64'},
        {'slug': 'qemu_x86_32'},
        {'slug': 'qemu_arm'},
        {'slug': 'qemu_arm64'}
    ]
    for item in skiplist:
        test_list = item['tests']
        if not isinstance(test_list, list):
            test_list = [test_list]

        for test in test_list:
            known_issue_object = {
                'test_name': args.suite_name + "/" + test,
                'url': item.get('url'),
                'notes': item.get('reason'),
            }
            boards = item.get('boards')
            if boards == 'all':
                known_issue_object.update({'boards': all_boards})
            else:
                board_list = [{'slug': board_name} for board_name in boards]
                known_issue_object.update({'boards': board_list})
            branches = item.get('branches')
            if branches == 'all':
                project_list = [value for name, value in conversion_dict.items()]
                known_issue_object.update({'projects': project_list})
            else:
                known_issue_object.update({'projects': [conversion_dict[str(name)] for name in item.get('branches')]})
            env = item.get('environments')
            if env == 'all':
                production_project['known_issues'].append(known_issue_object)
                staging_project['known_issues'].append(known_issue_object)
            if env == 'production':
                production_project['known_issues'].append(known_issue_object)
            if env == 'staging':
                staging_project['known_issues'].append(known_issue_object)

    pprint.pprint(production_project)
    with open(args.suite_name + '-production.yaml', 'w') as yaml_file:
        yaml.dump(production_project, yaml_file, default_flow_style=False)
    pprint.pprint(staging_project)
    with open(args.suite_name + '-staging.yaml', 'w') as yaml_file:
        yaml.dump(production_project, yaml_file, default_flow_style=False)

if __name__ == '__main__':
    main()
