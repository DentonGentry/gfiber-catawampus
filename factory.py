"""Simple web server for the factory.
"""

import subprocess
import traceback
import tornado.web


FACTORY_SH = ['factory_status.sh']


class FactoryHandler(tornado.web.RequestHandler):
  """Display information about the device, useful in manufacturing."""

  def get(self):    # pylint: disable=g-bad-name
    try:
      script = subprocess.Popen(FACTORY_SH, stdout=subprocess.PIPE)
      factory_output, _ = script.communicate(None)
      self.write(factory_output)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to invoke %s' % FACTORY_SH
      print traceback.print_exc()
      self.write('script invocation failed')
    self.set_header('Content-Type', 'text/plain')


def FactoryFactory():
  """I'm sorry. I couldn't resist. I'm sorry. Sorry, sorry, sorry."""
  return tornado.web.Application([(r'/factory', FactoryHandler)])
