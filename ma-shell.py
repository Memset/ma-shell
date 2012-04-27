#!/usr/bin/python
"""
Memset API interactive shell

Copyright (C) 2012 Memset Ltd; http://www.memset.com/

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

API_URL = r"https://%s:@api.memset.com/v1/xmlrpc"
VERSION = '0.2'

# pylint: disable-msg=E0202

from optparse import OptionParser
from xmlrpclib import ServerProxy, Fault, DateTime, ProtocolError
import socket
try:
    import json
except:
    try:
        import simplejson as json
    except:
        print "(notice: json not found, please install simplejson)"
try:
    import readline
except:
    print "(notice: readline support not found)"

class JSONDateEncoder(json.JSONEncoder):
    """JSON Encoder to support DateTime objects"""
    def default(self, obj):
        if isinstance(obj, DateTime):
            return str(obj)
        return super(JSONDateEncoder, self).default(obj)

def serialize_xml(data, lvl=0):
    """Simple dict to XML serializer"""
    xml = ''
    for key in data.keys():
        if isinstance(data[key], dict):
            xml = '%s%s<%s>\n%s</%s>\n' % (xml, ' '*lvl, key, serialize_xml(data[key], lvl+2), key)
        elif isinstance(data[key], list):
            xml = '%s%s<%s>\n' % (xml, ' '*lvl, key)
            lvl += 2
            for item in data[key]:
                xml = '%s%s<item>\n%s%s</item>\n' % (xml, ' '*lvl, serialize_xml(item, lvl+2), ' '*lvl)
            lvl -= 2
            xml = '%s%s</%s>\n' % (xml, ' '*lvl, key)
        else:
            xml = '%s%s<%s>%s</%s>\n' % (xml, ' '*lvl, key, data[key], key)
    return xml

class Main(object):
    def __init__(self):
        parser = OptionParser(usage="%prog [options] [command [param_name [type] param_value ...]]",
                              version="%prog v" + VERSION,
                              description="Memset API interactive shell",
                              epilog="For further information, please visit: http://www.memset.com/apidocs/")
        parser.add_option("-u", "--url",
                          type="str",
                          dest="url",
                          default=API_URL,
                          help="API URL (default: %s)" % API_URL,
                          )
        parser.add_option("-k", "--api-key",
                          type="str",
                          dest="key",
                          default=None,
                          help="API KEY (required)",
                          )
        parser.add_option("-x", "--xml",
                          action="store_true",
                          dest="xml",
                          default=False,
                          help="Use XML as output format (default: JSON)",
                          )

        self.options, self.args = parser.parse_args()

        if self.options.key is None:
            parser.error("No API KEY provided")
        if r"%s:" not in self.options.url:
            parser.error(r"No %s substitution found in API URL")

        if self.options.xml:
            self.serializer = lambda result: serialize_xml(dict(result=result)).strip()
        else:
            self.serializer = lambda result: json.dumps(result, cls=JSONDateEncoder, indent=2)

        try:
            self.proxy = ServerProxy(self.options.url % self.options.key)
            self.methods = self.proxy.system.listMethods()
        except ProtocolError, e:
            parser.error("Failed to connect to the server: %s" % e)


    def execute(self, cmd, quiet=False):
        """Execute a shell command"""
        # internal (local) commands first
        if cmd[0].lower() == 'quit':
            print "(quit)\n"
            return False
        elif cmd[0].lower() in ['help', '?']:
            if len(cmd) == 1:
                print "Local commands:\nhelp\nquit"
                print "\nCommand invocation:\ncommand [param_name [type] param_value ... | filename]\n"
                print "Value types can be indicated with (type) before the param_value."
                print "Valid types are: string, int, float, boolean and list (comma separated values).\n"
                print "Use 'help remote' for remote commands.\n"
            else:
                if cmd[1] == 'remote':
                    print "Remote command list:\n%s" % '\n'.join(self.methods)
                elif cmd[1] == 'quit':
                    print "quit\n"
                    print "Exit the API shell."
                elif cmd[1] == 'help':
                        print "help [command]\n"
                        print "Describe commands."
                else:
                    result = self.proxy.system.methodHelp(cmd[1])
                    print result
        else:
            # remote commands
            if cmd[0] not in self.methods:
                print "%s: command not found" % cmd[0]
            else:
                method = self.proxy.__getattr__(cmd[0])
                args = dict()
                pipe = None
                if len(cmd) > 1:

                    # process pipe arguments
                    if cmd[-1] == '|':
                        print "%s: param | without output filename" % cmd[0]
                        return True
                    elif cmd[-2] == '|':
                        pipe = cmd[-1]
                        cmd = cmd [:-2]

                    # process types
                    for key in xrange(1, len(cmd)):
                        if key+1 < len(cmd):
                            cast = None
                            if cmd[key].lower() == '(string)':
                                cast = str
                            elif cmd[key].lower() == '(int)':
                                cast = int
                            elif cmd[key].lower() == '(float)':
                                cast = float
                            elif cmd[key].lower() == '(boolean)':
                                cast = bool
                            elif cmd[key].lower() == '(list)':
                                cmd[key+1] = [x.strip() for x in cmd[key+1].split(',')]
                                del cmd[key]
                                continue
                            if cast:
                                try:
                                    cmd[key+1] = cast(cmd[key+1])
                                except ValueError:
                                    print "%s: invalid value type %s for %s" % (cmd[0], cmd[key], cmd[key+1])
                                finally:
                                    # string will be used
                                    del cmd[key]

                    for key in xrange(1, len(cmd), 2):
                        try:
                            args[cmd[key]] = cmd[key+1]
                        except IndexError:
                            print "%s: param %s without value" % (cmd[0], cmd[key])

                try:
                    result = method(args)
                except Fault, e:
                    print "%s: %s" % (cmd[0], e)
                except socket.error, e:
                    print "%s: %s" % (cmd[0], e)
                else:
                    if not quiet:
                        print "(%s result)" % cmd[0]
                    print self.serializer(result)

                    if pipe:
                        with open(pipe, "w") as fd:
                            fd.write(self.serializer(result))
                        if not quiet:
                            print "(result piped to %s)" % pipe
        return True

    def run(self):

        if self.args:
            self.execute(self.args, quiet=True)
            return

        print "(Memset API shell v%s)" % VERSION
        prompt = "[...%s]> " % self.options.key[-8:]
        while True:
            try:
                cmd = raw_input(prompt)
            except EOFError:
                print "\nEOF (quit)\n"
                break
            except KeyboardInterrupt:
                print "\n(quit)\n"
                break

            if not cmd:
                continue
            else:
                cmd = cmd.strip().split(' ')

            if not self.execute(cmd):
                break


if __name__ == "__main__":
    main = Main()
    main.run()

