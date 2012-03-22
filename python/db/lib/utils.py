#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Thu 12 May 08:33:24 2011 

"""Some utilities to talk to bob SQLite databases.
"""

import os
import sys
import errno
import stat
import logging

class null(object):
  """A look-alike stream that discards the input"""

  def write(self, s):
    pass
  
  def flush(self):
    pass

def location(dbname):
  """Returns the location of the database. The location of the database, by
  default, is the directory containing the database library. If the environment
  variable $BOB_DB_DIR is defined, it is used as the base-location of the
  file."""
  
  envvar = 'BOB_DB_DIR'

  if os.environ.has_key(envvar) and os.environ[envvar].strip():
    dirname = os.path.realpath(os.environ[envvar])
    fname = os.path.join(dirname, dbname + '.sql3')

  else:
    dirname = os.path.dirname(os.path.realpath(__file__))
    fname = os.path.join(dirname, dbname, 'db.sql3')

  return 'sqlite:///%s' % fname

def session(dbname, echo=False):
  """Creates a session to an SQLite database"""

  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker

  engine = create_engine(location(dbname), echo=echo)
  Session = sessionmaker(bind=engine)
  return Session()

def dbshell(options):
  """Drops you into a database shell"""

  import subprocess

  arguments = ['sqlite3', options.location.replace('sqlite:///','')]

  try:
    p = subprocess.Popen(arguments)
  except OSError as e:
    # occurs when the file is not executable or not found
    print("Error executing '%s': %s (%d)" % (' '.join(arguments), e.strerror,
        e.errno))
    sys.exit(e.errno)
  
  try:
    p.communicate()
  except KeyboardInterrupt: # the user CTRL-C'ed
    import signal
    os.kill(p.pid, signal.SIGTERM)
    return signal.SIGTERM

  return p.returncode

def dbshell_command(subparsers):
  """Adds a new dbshell subcommand to your subparser"""
  
  parser = subparsers.add_parser('dbshell', help=dbshell.__doc__)
  parser.set_defaults(func=dbshell)

def print_location(options):
  """Prints the current location of the database SQL file."""
  
  if options.with_protocol:
    print(options.location)
  else:
    print(options.location.replace('sqlite:///',''))

def location_command(subparsers):
  """Adds a new location subcommand to your parser"""

  parser = subparsers.add_parser('location', help=print_location.__doc__)
  parser.add_argument('--with-protocol', dest="with_protocol", 
      default=False, action='store_true', 
      help="prints the filepath or directory leading to the database with the specific database protocol prepended")
  parser.set_defaults(func=print_location)

  return parser

def copyfrom(options):
  """Copies the database from a given directory."""

  import shutil
  src = os.path.join(options.directory[0], options.dbname + '.sql3')
  dest = options.location.replace('sqlite:///','')
  if not os.path.exists(os.path.dirname(dest)):
    if options.verbose: 
      print "Creating directory '%s'..." % os.path.dirname(dest)
    makedirs_safe(os.path.dirname(dest))
  if os.path.exists(dest):
    if options.verbose: print "Removing existing copy '%s'..." % dest
    os.unlink(dest)
  if options.verbose: print "Copying %s -> %s" % (src, dest)
  shutil.copy2(src, dest)

def copyfrom_command(subparsers):
  
  parser = subparsers.add_parser('copyfrom', help=copyfrom.__doc__)
  parser.add_argument('--verbose', dest="verbose", default=False,
      action='store_true', help="produces more output while copying")
  parser.add_argument('directory', help="sets the directory to which the database will be copied from", nargs=1)
  parser.set_defaults(func=copyfrom)

  return parser

def copy(options):
  """Copies the database to a given directory."""

  import shutil
  d = options.directory[0]
  makedirs_safe(d)
  dest = os.path.join(d, options.dbname + '.sql3')
  if os.path.exists(dest): 
    if options.verbose: print "Removing existing file '%s'..." % dest
    os.unlink(dest)
  src = options.location.replace('sqlite:///','')
  if options.verbose: print "Copying %s -> %s" % (src, dest)
  shutil.copy2(src, dest)

def copy_command(subparsers):
  
  parser = subparsers.add_parser('copy', help=copy.__doc__)
  parser.add_argument('--verbose', dest="verbose", default=False,
      action='store_true', help="produces more output while copying")
  parser.add_argument('directory', help="sets the directory to which the database will be copied to", nargs=1)
  parser.set_defaults(func=copy)

  return parser

def standard_commands(subparsers):
  """Adds all standard commands to databases that can respond to them."""

  dbshell_command(subparsers)
  location_command(subparsers)
  copy_command(subparsers)
  copyfrom_command(subparsers)

def makedirs_safe(fulldir):
  """Creates a directory if it does not exists, with concurrent access support"""
  try:
    if not os.path.exists(fulldir): os.makedirs(fulldir)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST: pass
    else: raise