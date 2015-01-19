from glob import glob
import logging
import os
import subprocess

from localconfig import LocalConfig

from workspace.config import product_groups

log = logging.getLogger(__name__)


class ToxIni(LocalConfig):
  """ Represents tox.ini """

  def __init__(self, repo=None):
    """
    :param str repo: The repo to load tox*.ini from.
    """
    self.repo = repo
    self.path = self.path_for(repo)
    super(ToxIni, self).__init__(self.path)

  @classmethod
  def path_for(cls, repo):
    """
    :param str repo: Repo to get tox*.ini for
    :return: Path to tox*.ini file in :attr:`self.repo`
    :raise FileNotFoundError: if there is no tox*.ini found
    """

    tox_inis = glob(os.path.join(repo, 'tox*.ini'))

    if not tox_inis:
      raise FileNotFoundError('No tox.ini found in %s. Please run "wst setup --product" first to setup tox.' % self.repo)

    elif len(tox_inis) > 1:
      log.warn('More than one ini files found - will use first one: %s', ', '.join(tox_inis))

    return tox_inis[0]

  @property
  def envlist(self):
    return filter(None, self.tox.envlist.split(','))

  def envsection(self, env):
    return 'testenv:%s' % env

  @property
  def workdir(self):
    return os.path.join(self.repo, self.get('tox', 'toxworkdir', '.tox'))

  def envdir(self, env):
    envsection = self.envsection(env)
    if envsection not in self:
      log.debug('Using default envdir and commands as %s section is not defined in %s', envsection, self.path)

    return self.get(envsection, 'envdir', os.path.join(self.repo, '.tox', env)).replace('{toxworkdir}', self.workdir)

  def bindir(self, env, script=None):
    dir = os.path.join(self.envdir(env), 'bin')
    if script:
      dir = os.path.join(dir, script)
    return dir

  def commands(self, env):
    envsection = self.envsection(env)
    commands = self.get(envsection, 'commands', self.get('testenv', 'commands', 'py.test {env:PYTESTARGS:}'))
    return filter(None, commands.split('\n'))



class ProductPager(object):
  """ Pager to show contents from multiple products (repos) """
  MAX_TERMINAL_ROWS = 25

  def __init__(self, optional=False):
      """ If optional is True, then pager is only used if the # of lines of the first write exceeds `self.MAX_TERMINAL_ROWS` lines. """
      self.pager = None
      self.optional = optional

  def write(self, product, output, branch=None):
    if not self.pager:
      if not self.optional or len(output.split('\n')) > self.MAX_TERMINAL_ROWS:
        self.pager = create_pager('^\[.*]')

    if self.pager:
      self.pager.stdin.write('[ ' + product + ' ]\n')
      if branch and branch != 'master':
        self.pager.stdin.write('# On branch %s\n' % branch)
      self.pager.stdin.write(output.strip() + '\n\n')
    else:
      if branch and branch != 'master':
        print '# On branch %s' % branch
      print output

  def close_and_wait(self):
    if self.pager:
      self.pager.stdin.close()
      self.pager.wait()


def create_pager(highlight_text=None):
  """ Returns a pipe to PAGER or "less" """
  pager_cmd = os.environ.get('PAGER')

  if not pager_cmd:
    pager_cmd = ['less']
    if highlight_text:
      pager_cmd.extend(['-p', highlight_text])

  pager = subprocess.Popen(pager_cmd, stdin=subprocess.PIPE)

  return pager


def expand_product_groups(names):
  """ Expand product groups found in the given list of names to produce a sorted list of unique names. """
  unique_names = set(names)

  for group, names in product_groups().items():
    if group in unique_names:
      unique_names.remove(group)
      unique_names.update(expand_product_groups(names))

  return sorted(list(unique_names))
