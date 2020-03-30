from functools import reduce

import click
from ruamel.yaml import YAML

from . import cache
from . import compliance
from . import schema
from . import auth
from . import config


@click.group()
@click.option('-c', '--config', 'config_filename', default=config.default_dir() / 'scality.yml')
@click.option('--user-map', 'usermap_filename', default=config.default_dir() / 'user map.yml')
@click.option('--policy', 'policy_filename', default=config.default_dir() / 'policy.yml')
@click.pass_context
def cli(ctx, config_filename, usermap_filename, policy_filename):
    ctx.ensure_object(dict)
    with open(config_filename) as conf_file:
        conf = YAML(typ='safe').load(conf_file)
    with open(usermap_filename) as usermap_file:
        usermap = YAML(typ='safe').load(usermap_file)
    with open(policy_filename) as policy_file:
        policy = YAML(typ='safe').load(policy_file)
    ctx.obj['config'] = conf
    ctx.obj['usermap'] = usermap
    ctx.obj['policies'] = policy['policies']


@cli.group('compliance')
def compliance_group():
    pass


@compliance_group.command('check-all')
@click.pass_context
def compliance_check_all(ctx):
    compliance.check_all(
        ctx.obj['config'],
        ctx.obj['usermap'],
        ctx.obj['policies'])


@cli.group('cache')
def cache_group():
    pass


@cache_group.command('path')
def cache_path():
    print(cache.file_path())


@cache_group.command('refresh')
@click.option('--token-pass-name', default='scality/ghaudit-token')
@click.pass_context
def cache_refresh(ctx, token_pass_name):
    auth_driver = auth.github_auth_token_passpy(token_pass_name)
    cache.refresh(ctx.obj['config'], auth_driver)


def print_list(elems, elem_fmt):
    def fmt(elem):
        return ' * {}\n'.format(elem_fmt(elem))
    print(reduce(lambda x, y: x + fmt(y), elems, ''))


def user_short_str(user):
    if schema.user_name(user):
        return '{} ({})'.format(
            schema.user_login(user),
            schema.user_name(user)
        )
    return '{}'.format(schema.user_login(user))


def repo_short_str(repo):
    return schema.repo_name(repo)


@cli.command()
def list_org_members():
    rstate = cache.load()
    members = schema.org_members(rstate)
    print_list(members, user_short_str)


@cli.command()
def list_org_repositories():
    rstate = cache.load()
    repos = schema.org_repositories(rstate)
    print_list(repos, repo_short_str)
