import click
from ruamel.yaml import YAML

from ghaudit import cache
from ghaudit import compliance
from ghaudit import schema
from ghaudit import auth
from ghaudit import config
from ghaudit import ui


@click.group()
@click.option('-c', '--config', 'config_filename',
              default=config.default_dir() / 'scality.yml')
@click.option('--user-map', 'usermap_filename',
              default=config.default_dir() / 'user map.yml')
@click.option('--policy', 'policy_filename',
              default=config.default_dir() / 'policy.yml')
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


def user_short_str(user):
    if schema.user_name(user):
        return '{} ({})'.format(
            schema.user_login(user),
            schema.user_name(user)
        )
    return '{}'.format(schema.user_login(user))


def repo_short_str(repo):
    return schema.repo_name(repo)


def team_short_str(team):
    return schema.team_name(team)


@cli.command()
def stats():
    rstate = cache.load()
    print('teams: {}'.format(len(schema.org_teams(rstate))))
    print('repositories: {}'.format(len(schema.org_repositories(rstate))))
    print('members: {}'.format(len(schema.org_members(rstate))))
    print('users: {}'.format(len(schema.users(rstate))))


def _user_table_info(user=None):
    if user:
        return (
            (schema.user_login(user), 30),
            (schema.user_name(user), 30),
            (schema.user_company(user), 30),
            (schema.user_email(user), 30),
        )
    return (
        ('login', 30),
        ('name', 30),
        ('company', 30),
        ('email', 30),
    )


def _common_list(list_func, mode, fmt, rstate=None):
    if not rstate:
        rstate = cache.load()
    _list = list_func(rstate)
    ui.print_items(mode, _list, fmt)


@cli.group('org')
def org_group():
    pass


@org_group.group('repositories')
def org_repositories_group():
    pass


@org_repositories_group.command('list')
@click.option('--format', 'mode',
              type=click.Choice(['basic', 'json', 'table']),
              default='basic')
def org_repositories_list(mode):
    _common_list(schema.org_repositories, mode, ui.Formatter(
        (('name', 40), ('archived', 8), ('fork', 5)),
        lambda x: (
            (schema.repo_name(x), 40),
            (schema.repo_archived(x), 8),
            (schema.repo_forked(x), 5),
        ),
        repo_short_str
    ))


@org_repositories_group.command('count')
def org_repositories_count():
    rstate = cache.load()
    repos = schema.org_repositories(rstate)
    print(len(repos))


@org_group.group('members')
def org_members_group():
    pass


@org_members_group.command('list')
@click.option('--format', 'mode',
              type=click.Choice(['basic', 'json', 'table']),
              default='basic')
def org_members_list(mode):
    _common_list(schema.org_members, mode, ui.Formatter(
        (('login', 30), ('name', 30), ('company', 30), ('email', 30)),
        lambda x: (
            (schema.user_login(x), 30),
            (schema.user_name(x), 30),
            (schema.user_company(x), 30),
            (schema.user_email(x), 30),
        ),
        user_short_str
    ))


@org_members_group.command('count')
def org_members_count():
    rstate = cache.load()
    members = schema.org_members(rstate)
    print(len(members))


@org_group.group('teams')
def org_teams_group():
    pass


@org_teams_group.command('list')
@click.option('--format', 'mode',
              type=click.Choice(['basic', 'json', 'table']),
              default='basic')
def org_teams_list(mode):
    rstate = cache.load()
    _common_list(schema.org_teams, mode, ui.Formatter(
        (('name', 30), ('repositories', 12), ('members', 7)),
        lambda x: (
            (schema.team_name(x), 30),
            (len(schema.team_repos(rstate, x)), 12),
            (len(schema.team_members(rstate, x)), 7),
        ),
        team_short_str
    ), rstate)


@org_teams_group.command('count')
def org_teams_count():
    rstate = cache.load()
    teams = schema.org_teams(rstate)
    print(len(teams))


@org_group.group('repository')
def org_repository_group():
    pass


@org_repository_group.command('show')
@click.argument('name')
def org_repository_show(name):
    def collaborators(repository):
        result = '\n'
        for collaborator in schema.repo_collaborators(rstate, repository):
            permission = collaborator['role']
            result += ('   * {} ({}): {}\n'.format(
                schema.user_name(collaborator),
                schema.user_login(collaborator),
                permission,
            ))
        return result

    rstate = cache.load()
    repository = schema.org_repo_by_name(rstate, name)
    print((
        ' * name: {}\n'
        + ' * description: {}\n'
        + ' * archived: {}\n'
        + ' * is fork: {}\n'
        + ' * collaborators: {}')
          .format(
              schema.repo_name(repository),
              schema.repo_description(repository),
              schema.repo_archived(repository),
              schema.repo_forked(repository),
              collaborators(repository)
          ))


@org_group.group('team')
def org_team_group():
    pass


@org_team_group.command('tree')
def org_team_tree():
    def print_items(items, indent):
        for item in items:
            print('{}* {}'.format(''.rjust(indent * 2), schema.team_name(item)))
            not_self = lambda x: schema.team_name(x) != schema.team_name(item)
            children = [x for x in schema.team_children(rstate, item) if not_self(x)]
            print_items(children, indent + 1)

    rstate = cache.load()
    teams = schema.org_teams(rstate)
    roots = [x for x in teams if not schema.team_parent(rstate, x)]
    print_items(roots, 1)


@org_team_group.command('show')
@click.argument('name')
def org_team_show(name):
    def members(team):
        result = '\n'
        for member in schema.team_members(rstate, team):
            permission = member['role']
            result += ('   * {} ({}): {}\n'.format(
                schema.user_name(member),
                schema.user_login(member),
                permission,
            ))
        return result

    def repositories(team):
        result = '\n'
        for repo in schema.team_repos(rstate, team):
            permission = repo['permission']
            result += ('   * {}: {}\n'.format(
                schema.repo_name(repo),
                permission,
            ))
        return result

    def children(team):
        result = '\n'
        for child in schema.team_children(rstate, team):
            result += ('   * {}\n'.format(
                schema.team_name(child),
            ))
        return result

    rstate = cache.load()
    team = schema.org_team_by_name(rstate, name)
    print(
        (
            ' * name: {}\n'
            + ' * description: {}\n'
            + ' * members: {}'
            + ' * repositories: {}'
            + ' * sub teams: {}')
        .format(
            schema.team_name(team),
            schema.team_description(team),
            members(team),
            repositories(team),
            children(team),
        ))


@cli.group('user')
def user_group():
    pass


@user_group.command('show')
@click.argument('login')
def user_show(login):
    def teams():
        result = '\n'
        for team in schema.org_teams(rstate):
            for member in schema.team_members(rstate, team):
                if schema.user_login(member) == login:
                    result += '   * {}\n'.format(schema.team_name(team))
        return result

    rstate = cache.load()
    user = schema.user_by_login(rstate, login)
    print((
        ' * name: {}\n'
        + ' * login: {}\n'
        + ' * email: {}\n'
        + ' * company: {}\n'
        + ' * teams: {}')
          .format(
              schema.user_name(user),
              schema.user_login(user),
              schema.user_email(user),
              schema.user_company(user),
              teams()
          ))
