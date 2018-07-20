#!/usr/bin/python3

import argparse
import logging
import netrc
import pprint
import requests
import sys
import yaml

from urllib.parse import urlsplit, urlunsplit


FORMAT = "%(funcName)20s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)


class SquadConnectionException(Exception):
    pass


class SquadConnection(object):
    def __init__(self, url, passwords_file):
        self.url = url
        self.passwords_file = passwords_file
        urlparts = urlsplit(self.url)
        self.base_url = urlparts.netloc
        self.url_scheme = urlparts.scheme

        connection_token = "Token %s" % self.__get_connection_token__(self.url)
        self.headers = {
            "Authorization": connection_token
        }

    def get_prepared_request(self, endpoint, method):
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s" % endpoint,
             None,
             None))
        req = requests.Request(method, URL, headers=self.headers)
        return req.prepare()

    def __get_connection_token__(self, url):
        netrcauth = netrc.netrc(self.passwords_file)
        try:
            self.username, _, self.token = netrcauth.authenticators(self.base_url)
            logger.info("Using username: %s" % self.username)
            return self.token
        except TypeError:
            logger.error("No credentials found for %s" % self.base_url)
            sys.exit(1)

    def download_list(self, endpoint, params=None):
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s" % endpoint,
             None,
             None))
        logger.debug(URL)
        response = requests.get(URL, params=params, headers=self.headers)
        result_list = []
        if response.status_code == 200:
            response_json = response.json()
            result_list = response_json['results']
            while response_json['next'] is not None:
                response = requests.get(response_json['next'], headers=self.headers)
                if response.status_code == 200:
                    response_json = response.json()
                    result_list = result_list + response_json['results']
                else:
                    break
        else:
            logger.error(URL)
            logger.error(response.status_code)
            logger.error(response.text)
        return result_list

    def download_object(self, url):
        if url is None:
            return None
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def filter_object(self, endpoint, params):
        old_configs = self.download_list(endpoint, params)
        if len(old_configs) == 0:
            # the config is new
            return None
        if len(old_configs) != 1:
            logger.error("Found too many objects of type: %s" % endpoint)
            logger.error("Params: %s" % params)
            raise SquadConnectionException("Too many objects found")
        return old_configs[0]

    def put_object(self, endpoint, config):
        object_id = config.get('id')
        URL = urlunsplit(
            (self.url_scheme,
             self.base_url,
             "api/%s/%s/" % (endpoint, object_id),
             None,
             None))
        logger.debug(URL)
        logger.debug(config)
        response = requests.put(URL, data=config, headers=self.headers)
        if response.status_code != 200:
            logger.error(response.text)

    def post_object(self, endpoint, config):
        URL = urlunsplit((self.url_scheme, self.base_url, "api/%s/" % endpoint, None, None))
        logger.debug(URL)
        logger.debug(config)
        response = requests.post(URL, data=config, headers=self.headers)
        if response.status_code != 201:
            logger.error(response.text)


class SquadKnownIssueException(Exception):
    pass


class SquadKnownIssue(object):
    def __init__(self, config, squad_project, strict=False):
        self.test_name = config.get('test_name')
        if self.test_name is None:
            raise SquadKnownIssueException("TestName not defined")
        self.title = squad_project.name + "/" + self.test_name
        self.url = config.get('url')
        self.notes = config.get('notes')
        self.active = config.get('active')
        self.intermittent = config.get('intermittent')
        self.projects = config.get('projects')
        for project in self.projects:
            if project not in squad_project.projects:
                # ignore projects that are not defined
                # in the SquadProject.projects
                self.projects.remove(project)
                if strict:
                    raise SquadKnownIssueException("Project not defined: %s" % project)
        self.environments = set()
        for item in config.get('environments'):
            if 'slug' in item.keys():
                if item['slug'] in squad_project.environment_slugs:
                    self.environments.add(item['slug'])
                else:
                    if strict:
                        raise SquadKnownIssueException(
                            "Incorrect environment: %s" % item['slug'])
            if 'architecture' in item.keys():
                if item['architecture'] in squad_project.environment_architectures.keys():
                    for env in squad_project.environment_architectures[item['architecture']]:
                        self.environments.add(env)
                else:
                    if strict:
                        raise SquadKnownIssueException(
                            "Unknown architecture: %s" % item['architecture'])


class SquadProjectException(Exception):
    pass


class SquadProject(object):
    def __init__(self, config, passwords_file, sanity_check=False):
        self.name = config.get('name')
        self.url = config.get('url')
        if self.url is None:
            raise SquadProjectException("Project URL is empty")
        self.connection = SquadConnection(self.url, passwords_file)
        self.projects = config.get('projects')
        self.environments = config.get('environments')
        self.environment_slugs = set([item.get('slug') for item in self.environments])
        self.environment_architectures = {}
        for item in self.environments:
            arch_name = item.get('architecture')
            if arch_name is None:
                continue
            if arch_name in self.environment_architectures.keys():
                self.environment_architectures[arch_name].add(item.get('slug'))
            else:
                self.environment_architectures.update({arch_name: set([item.get('slug')])})
        self.known_issues = [SquadKnownIssue(conf, self, sanity_check) for conf in config.get('known_issues')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--config-files",
                        nargs="+",
                        required=True,
                        help="Instance config files",
                        dest="config_files")
    parser.add_argument("-p",
                        "--passwords-file",
                        required=True,
                        help="Passwords file in the .netrc form",
                        dest="passwords_file")
    parser.add_argument("-d",
                        "--dry-run",
                        action="store_true",
                        default=False,
                        help="Dry run",
                        dest="dry_run")
    parser.add_argument("-s",
                        "--sanity-check",
                        action="store_true",
                        default=False,
                        help="Sanity check. Implies dry run.",
                        dest="sanity_check")
    parser.add_argument("-v",
                        "--debug",
                        action="store_true",
                        default=False,
                        help="Enable debug",
                        dest="debug")

    args = parser.parse_args()

    config_data = {}
    for f in args.config_files:
        with open(f, 'r') as stream:
            try:
                loaded_config = yaml.load(stream)
                for project in loaded_config.get('projects'):
                    config_data.update({project['name']: project})
            except yaml.YAMLError as exc:
                logger.error(exc)
                sys.exit(1)

    for project_name, project in config_data.items():
        s = SquadProject(project, args.passwords_file, args.sanity_check)
        if args.sanity_check:
            # validate if projects defined in the instance exist
            for squad_project in s.projects:
                squad_project_group, squad_project_name = squad_project.split("/", 1)
                api_project = s.connection.filter_object(
                    'projects',
                    {'group__slug': squad_project_group, 'slug': squad_project_name})
                if api_project is None:
                    raise SquadProjectException(
                        "Project %s doesn't exist in the instance %s" % (squad_project, s.url))

        for known_issue in s.known_issues:
            # create/uptade the issues in remote instance
            # for each project defined in the known_issue
            # get the environment IDs based on the environment name
            api_known_issue = s.connection.filter_object(
                'knownissues',
                {'title': known_issue.title, 'test_name': known_issue.test_name})
            affected_environments = []
            for known_issue_project in known_issue.projects:
                group_name, project_name = known_issue_project.split('/', 1)
                api_project = s.connection.filter_object(
                    'projects',
                    {'group__slug': group_name, 'slug': project_name})
                if api_project is None:
                    continue
                api_environments = s.connection.download_list(
                    'environments',
                    {'project': api_project['id']})
                for api_env in api_environments:
                    if api_env['slug'] in known_issue.environments:
                        logger.debug(
                            "Adding env: %s to known issue: %s" % (
                                api_env['slug'],
                                known_issue.title))
                        affected_environments.append(api_env)

            if not args.dry_run:
                known_issue_api_object = {
                    'title': known_issue.title,
                    'test_name': known_issue.test_name,
                    'url': known_issue.url,
                    'notes': known_issue.notes,
                    'active': known_issue.active,
                    'intermittent': known_issue.intermittent,
                    'environment': [item['url'] for item in affected_environments]
                }

                if api_known_issue is None:
                    # create new KnownIssue
                    s.connection.post_object(
                        'knownissues',
                        known_issue_api_object
                    )
                else:
                    # update existing KnownIssue
                    api_known_issue.update(known_issue_api_object)
                    s.connection.put_object(
                        'knownissues',
                        api_known_issue
                    )
            else:
                pprint.pprint(known_issue.title)
                pprint.pprint(known_issue.projects)
                pprint.pprint(known_issue.environments)


if __name__ == '__main__':
    main()
