#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Parser for tr-069-style data model .xml files."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import hashlib
import os.path
import re
import string
import sys
import xml.etree.ElementTree

import google3
import bup.options


optspec = """
parse-schema.py [-d dir] files...
--
d,output-dir= Directory to write files to
"""

DEFAULT_BASE_CLASS = 'core.FastExporter'

chunks = {}
imports = {}


def Log(s):
  sys.stdout.flush()
  sys.stderr.write('%s\n' % s)


def AddChunk(spec, objtype, name, root):
  key = (spec, objtype, name)
  assert not chunks.has_key(key)
  chunks[key] = root


def FixSpec(spec):
  # When a spec refers to tr-xxx-1-0-0 or tr-xxx-1-0, we might have to
  # substitute in tr-xxx-1-0-1 instead (a bugfix revision).  Let's just
  # drop out the third version digit so it's easier to use as a dictionary
  # key.
  return re.sub(r':(tr|wt)-(\d+-\d+-\d+)-\d+$', r':tr-\2', spec)


def NiceSpec(spec):
  spec = re.sub(r'^urn:broadband-forum-org:', '', spec)
  spec = re.sub(r'^urn:google-com:', '', spec)
  spec = re.sub(r'^urn:catawampus-org:', '', spec)
  return spec


def SpecNameForPython(spec):
  spec = NiceSpec(spec)
  spec = re.sub(r'tr-(\d+)-(\d+)-(\d+)', r'tr\1_v\2_\3', spec)
  spec = spec.translate(string.maketrans('-', '_'))
  return spec


def ObjNameForPython(name):
  name = re.sub(r':(\d+)\.(\d+)', r'_v\1_\2', name)
  name = name.replace('-', '_')  # X_EXAMPLE-COM_foo vendor data models
  return name


IMPORT_BUG_FIXES = {
    # bugs in tr-181-2-0-1.  It tries to import *_Device2, which doesn't
    # seem to exist anywhere.
    ('urn:broadband-forum-org:tr-143-1-0', 'component',
     'DownloadDiagnostics_Device2'):
         ('urn:broadband-forum-org:tr-143-1-0', 'component',
          'DownloadDiagnostics'),
    ('urn:broadband-forum-org:tr-143-1-0', 'component',
     'UploadDiagnostics_Device2'):
         ('urn:broadband-forum-org:tr-143-1-0', 'component',
          'UploadDiagnostics'),
}


def ParseImports(into_spec, root):
  from_spec = FixSpec(root.attrib['spec'])
  for node in root:
    if node.tag in ('component', 'model'):
      from_name = node.attrib.get('ref', node.attrib['name'])
      into_name = node.attrib['name']
      from_key = (from_spec, node.tag, from_name)
      into_key = (into_spec, node.tag, into_name)
      if from_key in IMPORT_BUG_FIXES:
        from_key = IMPORT_BUG_FIXES[from_key]
      assert not chunks.has_key(into_key)
      assert not imports.has_key(into_key)
      imports[into_key] = from_key
    elif node.tag == 'dataType':
      continue
    else:
      raise KeyError(node.tag)


def ParseFile(filename):
  Log(filename)
  root = xml.etree.ElementTree.parse(open(filename)).getroot()
  spec = FixSpec(root.attrib['spec'])
  Log(NiceSpec(spec))
  for node in root:
    if node.tag == 'import':
      ParseImports(spec, node)
    elif node.tag in ('component', 'model'):
      name = node.attrib['name']
      Log('%-12s %-9s %s' % (NiceSpec(spec), node.tag, name))
      AddChunk(spec, node.tag, name, (spec, name, node))
    elif node.tag in ('description', 'dataType', 'bibliography'):
      continue
    else:
      Log('skip %s' % node.tag)


def ResolveImports():
  for k, v in sorted(imports.items()):
    prefix = ' %-12s %-9s %-20s ' % (NiceSpec(k[0]), k[1], k[2])
    Log('%s\n=%-12s %-9s %s' % (prefix, NiceSpec(v[0]), v[1], v[2]))
    while v in imports:
      v = imports[v]
      Log('=%-12s %-9s %s' % (NiceSpec(v[0]), v[1], v[2]))
    (into_spec, objtype, into_name) = k
    (from_spec, objtype, from_name) = v
    if objtype in ('component', 'model'):
      AddChunk(into_spec, objtype, into_name,
               chunks[(from_spec, objtype, from_name)])
    else:
      raise KeyError(objtype)


def _Params(o):
  return o.params


def _SubObjectNames(o):
  return [i.name for i in o.object_sequence if not i.is_sequence]


def _SequenceNames(o):
  return [i.name for i in o.object_sequence if i.is_sequence]


def _SubsAndSequences(o):
  return [i.name for i in o.object_sequence]


def _GlobalName(namecache, seq):
  """Generate and cache a module-global name for the given object path."""
  # Toplevel objects are special: no need for a special global name, because
  # they *are* the global name.
  if len(seq) == 1:
    return seq[0]

  # Otherwise, use a unique "private" name inside the module.
  last = ObjNameForPython(seq[-1])
  for i in xrange(1000):
    if i == 0:
      n = '_%s' % last
    else:
      n = '_%d_%s' % (i, last)
    if n not in namecache:
      namecache.add(n)
      return n
  raise Exception('weird, no available names for %r?' % last)


def _QuotedList(outlist, space, key, values):
  l = ["'%s'," % i for i in values]
  if l:
    inner_space = space + ' ' * (len(key) + 4)
    s = inner_space.join(l)
    outlist.append('%s = (%s)' % (key, s))


class Object(object):
  """Represents an <object> tag."""

  def __init__(self, model, name, prefix):
    self.model = model
    self.name = re.sub(r'-{i}', '', name)
    self.is_sequence = (self.name != name)
    self.prefix = prefix
    self.params = []
    self.object_sequence = []

  def _Augment(self, lookupfunc):
    """Return a list of all sub-object names, including ones in my parent.

    Args:
      lookupfunc: one of _Params, _SubObjectNames, _SequenceNames,
        or _SubsAndSequences.
    Returns:
      A list of names.
    """
    objlist = []
    obj = self
    while obj:
      objlist.insert(0, obj)
      obj = obj.FindParentClass()
    out = []
    for o in objlist:
      for v in lookupfunc(o):
        if v not in out:
          out.append(v)
    return out

  def _FindUpTree(self, objname):
    obj = self
    while obj:
      for i in obj.object_sequence:
        if i.name == objname:
          return i
      obj = obj.FindParentClass()
    raise KeyError('%r in %r' % (objname, self.name))

  def Render(self, nameprefix, namecache, outcache):
    """Render this object and all its children as python code."""
    fullname_with_seq = re.sub(r'-{i}', '.{i}', '.'.join(self.prefix[:-1]))
    classname = self.name.translate(string.maketrans('-', '_'))
    newprefix = nameprefix + (classname,)
    myname = _GlobalName(namecache, newprefix)

    subout = []
    selfheader = []
    selfout = []

    selfheader.append('')
    selfheader.append('')
    selfheader.append('class %s(core.FastExporter):' % myname)
    if fullname_with_seq:
      selfheader.append('  """Represents %s."""' % fullname_with_seq)
    else:
      selfheader.append('  """Top level datamodel object."""')

    selfout.append('  __slots__ = ()')
    _QuotedList(selfout, '\n', '  export_params',
                self._Augment(_Params))
    _QuotedList(selfout, '\n', '  export_objects',
                self._Augment(_SubObjectNames))
    _QuotedList(selfout, '\n', '  export_object_lists',
                self._Augment(_SequenceNames))

    for objname in self._Augment(_SubsAndSequences):
      obj = self._FindUpTree(objname)
      gname, code = obj.Render(newprefix, namecache, outcache)
      subout.append(code)
      selfout.append('  %s = %s' % (ObjNameForPython(objname), gname))
    outhash = hashlib.sha1('\n'.join(selfout)).digest()
    if outhash not in outcache:
      outcache[outhash] = myname
      return myname, '\n'.join(subout + selfheader + selfout)
    else:
      # An identical object was already rendered; make this name just an
      # alias to it.
      return myname, '%s = %s' % (myname, outcache[outhash])

  def FindParentClass(self):
    parent_model = models.get((self.model.spec.name,
                               self.model.parent_model_name), None)
    while parent_model:
      parent_class = parent_model.objects.get(self.prefix, None)
      if parent_class:
        return parent_class
      parent_model = models.get((parent_model.spec.name,
                                 parent_model.parent_model_name), None)
    return None

  def FullName(self):
    return re.sub(r'-{i}', '', '.'.join(self.prefix[:-1]))


models = {}


class Model(object):
  """Represents a <model> tag."""

  def __init__(self, spec, name, parent_model_name):
    self.spec = spec
    self.name = ObjNameForPython(name)
    if parent_model_name:
      self.parent_model_name = ObjNameForPython(parent_model_name)
    else:
      self.parent_model_name = None
    self.items = {}
    self.objects = {}
    self.object_sequence = []
    models[(self.spec.name, self.name)] = self

  def _AddItem(self, parts):
    self.items[parts] = 1
    if not parts[-1]:
      if len(parts) > 2:
        self._AddItem(parts[:-2] + ('',))
    else:
      if len(parts) > 1:
        self._AddItem(parts[:-1] + ('',))

  def AddItem(self, name):
    parts = tuple(re.sub(r'\.{i}', r'-{i}', name).split('.'))
    self._AddItem(parts)

  def ItemsMatchingPrefix(self, prefix):
    assert (not prefix) or (not prefix[-1])
    for i in sorted(self.items):
      if i[:len(prefix) - 1] == prefix[:-1] and i != prefix:
        yield i[len(prefix) - 1:]

  def Objectify(self, name, prefix):
    """Using self.items, fill self.objects and self.object_sequence.

    Args:
      name: the basename of this object in the hierarchy.
      prefix: a list of parent object names.
    Returns:
      The toplevel Object generated, which corresponds to the Model itself.
    """
    assert (not prefix) or (not prefix[-1])
    obj = Object(self, name, prefix)
    self.objects[prefix] = obj
    for i in self.ItemsMatchingPrefix(prefix):
      if len(i) == 1 and i[0]:
        # a parameter of this object
        obj.params.append(i[0].strip())
      elif len(i) == 2 and not i[1]:
        # a sub-object of this object
        subobj = self.Objectify(i[0], prefix[:-1] + i)
        obj.object_sequence.append(subobj)
    return obj

  def MakeObjects(self):
    assert not self.object_sequence
    obj = self.Objectify(self.name, ('',))
    self.object_sequence = [obj]

  def Render(self, namecache, outcache):
    out = []
    for obj in self.object_sequence:
      unused_gname, code = obj.Render((), namecache, outcache)
      out.append(code)
      out.append('')
    return None, '\n'.join(out)


def ProcessParameter(model, prefix, xmlelement):
  name = xmlelement.attrib.get('base', xmlelement.attrib.get('name', '<??>'))
  model.AddItem('%s%s' % (prefix, name))


def ProcessObject(model, prefix, spec, xmlelement):
  name = xmlelement.attrib.get('base', xmlelement.attrib.get('name', '<??>'))
  prefix += name
  model.AddItem(prefix)
  for i in xmlelement:
    if i.tag == 'parameter':
      ProcessParameter(model, prefix, i)
    elif i.tag == 'object':
      ProcessObject(model, prefix, spec, i)
    elif i.tag in ('description', 'uniqueKey'):
      pass
    else:
      raise KeyError(i.tag)


def ProcessComponent(model, prefix, spec, xmlelement):
  for i in xmlelement:
    if i.tag == 'parameter':
      ProcessParameter(model, prefix, i)
    elif i.tag == 'object':
      ProcessObject(model, prefix, spec, i)
    elif i.tag == 'component':
      refspec, unused_refname, ref = chunks[spec, 'component', i.attrib['ref']]
      component_prefix = prefix + i.attrib.get('path', '')
      ProcessComponent(model, component_prefix, refspec, ref)
    elif i.tag in ('profile', 'description'):
      pass
    else:
      raise KeyError(i.tag)


specs = {}


class Spec(object):
  """Represents a <spec> tag."""

  def __init__(self, name):
    self.name = SpecNameForPython(name)
    self.aliases = []
    self.models = []
    self.deps = []
    specs[name] = self

  def Render(self, namecache, outcache):
    """Renders everything in this spec (one xml file) as python code."""
    out = []
    for model in self.models:
      unused_gname, code = model.Render(namecache, outcache)
      out.append(code)
      out.append('')

    if self.models:
      out.append('# Tip: execute this file to get a simple schema listing')
      out.append("if __name__ == '__main__':")
      out.append('  import handle  # pylint:disable=g-import-not-at-top')
      for model in self.models:
        out.append('  print handle.DumpSchema(%s)' % model.name)
    return None, '\n'.join(out) + '\n'

  def MakeObjects(self):
    for (fromspec, fromname), (tospec, toname) in self.aliases:
      fromname = ObjNameForPython(fromname)
      tospec = SpecNameForPython(tospec)
      toname = ObjNameForPython(toname)
      if (fromspec, fromname) not in models:
        models[(fromspec, fromname)] = models[(tospec, toname)]
        Log('aliased %r' % ((fromspec, fromname),))


def main():
  o = bup.options.Options(optspec)
  (opt, unused_flags, extra) = o.parse(sys.argv[1:])

  output_dir = opt.output_dir or '.'
  Log('Output directory for generated files is %s' % output_dir)

  for filename in extra:
    ParseFile(filename)
  ResolveImports()
  Log('Finished parsing and importing.')

  items = sorted(chunks.items())
  for (specname, objtype, name), (refspec, refname, xmlelement) in items:
    spec = specs.get(specname, None) or Spec(specname)
    if objtype == 'model':
      objname = ObjNameForPython(name)
      parent = xmlelement.attrib.get('base', None)
      if SpecNameForPython(refspec) != spec.name:
        spec.deps.append(refspec)
        spec.aliases.append(((spec.name, objname),
                             (refspec, refname)))
      else:
        if parent:
          model = Model(spec, objname, parent_model_name=parent)
        else:
          model = Model(spec, objname, parent_model_name=None)
        ProcessComponent(model, '', refspec, xmlelement)
        model.MakeObjects()
        spec.models.append(model)

  Log('Finished models.')

  for spec in specs.values():
    spec.MakeObjects()
  for specname, spec in sorted(specs.items()):
    pyspec = SpecNameForPython(specname)
    assert pyspec.startswith('tr') or pyspec.startswith('x_')
    outf = open(os.path.join(output_dir, '%s.py' % pyspec), 'w')
    outf.write('#!/usr/bin/python\n'
               '# Copyright 2011 Google Inc. All Rights Reserved.\n'
               '#\n'
               '# AUTO-GENERATED BY parse-schema.py\n'
               '#\n'
               '# DO NOT EDIT!!\n'
               '#\n'
               '# pylint:disable=invalid-name\n'
               '# pylint:disable=line-too-long\n'
               '#\n'
               '"""Auto-generated from spec: %s."""\n'
               '\n'
               'import core  # pylint:disable=unused-import\n'
               % specname)
    unused_gname, code = spec.Render(set(), {})
    outf.write(code)


if __name__ == '__main__':
  main()
