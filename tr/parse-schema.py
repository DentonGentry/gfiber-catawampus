#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Parser for tr-069-style data model .xml files."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import errno
import os
import re
import sys
import xml.etree.ElementTree

DEFAULT_BASE_CLASS = 'core.Exporter'

chunks = {}
imports = {}


def Log(s):
    sys.stderr.write('%s\n' % s)


def AddChunk(spec, objtype, name, root):
    key = (spec, objtype, name)
    assert(not chunks.has_key(key))
    chunks[key] = root


def FixSpec(spec):
    # When a spec refers to tr-xxx-1-0-0 or tr-xxx-1-0, we might have to
    # substitute in tr-xxx-1-0-1 instead (a bugfix revision).  Let's just
    # drop out the third version digit so it's easier to use as a dictionary
    # key.
    return re.sub(r':(tr|wt)-(\d+-\d+-\d+)-\d+$', r':tr-\2', spec)


def NiceSpec(spec):
    return re.sub(r'^urn:broadband-forum-org:', '', spec)


def SpecNameForPython(spec):
    return re.sub(r'tr-(\d+)-(\d+)-(\d+)', r'tr\1_v\2_\3', NiceSpec(spec))


def ObjNameForPython(name):
    return re.sub(r':(\d+)\.(\d+)', r'_v\1_\2', name)


def Indented(prefix, s):
    return re.sub(re.compile(r'^', re.M), prefix, unicode(s))


_ImportBugFixes = {
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
            if from_key in _ImportBugFixes:
                from_key = _ImportBugFixes[from_key]
            assert(not chunks.has_key(into_key))
            assert(not imports.has_key(into_key))
            imports[into_key] = from_key
        elif node.tag in ('dataType'):
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
    for k,v in sorted(imports.items()):
        prefix = ' %-12s %-9s %-20s ' % (NiceSpec(k[0]), k[1], k[2])
        Log("%s\n=%-12s %-9s %s" % (prefix, NiceSpec(v[0]), v[1], v[2]))
        while imports.has_key(v):
            v = imports[v]
            Log("=%-12s %-9s %s" % (NiceSpec(v[0]), v[1], v[2]))
        (into_spec, objtype, into_name) = k
        (from_spec, objtype, from_name) = v
        if objtype in ('component', 'model'):
            AddChunk(into_spec, objtype, into_name,
                     chunks[(from_spec, objtype, from_name)])
        else:
            raise KeyError(objtype)


class Object(object):
    def __init__(self, model, name, prefix):
        self.model = model
        self.name = re.sub(r'-{i}', '', name)
        self.is_sequence = (self.name != name)
        self.prefix = prefix
        self.params = []
        self.object_sequence = []

    def __str__(self):
        pre = []
        out = []
        parent_class_name = DEFAULT_BASE_CLASS
        if self.model.parent_model_name:
            parent_class = self.FindParentClass()
            if parent_class:
                parent_class_name = '%s.%s' % (self.model.parent_model_name,
                                               parent_class.FullName())
        if parent_class_name.endswith('.'):
            # Only happens for toplevel Model objects
            parent_class_name = parent_class_name[:-1]
        fullname_with_seq = re.sub(r'-{i}', '.{i}', '.'.join(self.prefix[:-1]))
        pre.append('# %s.%s' % (self.model.name, fullname_with_seq))
        pre.append('class %s(%s):' % (self.name, parent_class_name))
        if self.params or self.object_sequence:
            pre.append('  def __init__(self):')
            pre.append('    %s.__init__(self)' % parent_class_name)
            bits = []
            space = ',\n                '
            if self.params:
                quoted_param_list = ["'%s'" % param for param in self.params]
                quoted_params = (space+'        ').join(quoted_param_list)
                bits.append('params=[%s]' % quoted_params)
            obj_list = [obj.name for obj in self.object_sequence
                        if not obj.is_sequence]
            if obj_list:
                quoted_obj_list = ["'%s'" % obj for obj in obj_list]
                quoted_objs = (space+'         ').join(quoted_obj_list)
                bits.append('objects=[%s]' % quoted_objs)
            objlist_list = [obj.name for obj in self.object_sequence
                            if obj.is_sequence]
            if objlist_list:
                quoted_objlist_list = ["'%s'" % obj for obj in objlist_list]
                quoted_objlists = (space+'       ').join(quoted_objlist_list)
                bits.append('lists=[%s]' % quoted_objlists)
            pre.append('    self.Export(%s)' % (space.join(bits)))
            pre.append('')
        for obj in self.object_sequence:
            if out:
                out.append('')
            out.append(Indented('  ', obj))
        if not self.params and not out:
            out.append('  pass')
        return '\n'.join(pre + out)

    def FindParentClass(self):
        parent_model = models[(self.model.spec.name,
                               self.model.parent_model_name)]
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
        models[(self.spec.name,self.name)] = self

    def AddItem(self, name):
        parts = tuple(re.sub(r'\.{i}', r'-{i}', name).split('.'))
        self.items[parts] = 1

    def ItemsMatchingPrefix(self, prefix):
        assert (not prefix) or (prefix[-1] == '')
        for i in sorted(self.items.keys()):
            if (i[:len(prefix)-1] == prefix[:-1] and i != prefix):
                yield i[len(prefix)-1:]

    def Objectify(self, name, prefix):
        assert (not prefix) or (prefix[-1] == '')
        obj = Object(self, name, prefix)
        self.objects[prefix] = obj
        for i in self.ItemsMatchingPrefix(prefix):
            if len(i) == 1 and i[0] != '':
                # a parameter of this object
                obj.params.append(i[0])
            elif len(i) == 2 and i[1] == '':
                # a sub-object of this object
                subobj = self.Objectify(i[0], prefix[:-1] + i)
                obj.object_sequence.append(subobj)
        return obj

    def MakeObjects(self):
        assert not self.object_sequence
        obj = self.Objectify(self.name, ('',))
        self.object_sequence = [obj]

    def __str__(self):
        out = []
        for obj in self.object_sequence:
            out.append(Indented('', obj))
            out.append('')
        return '\n'.join(out)


def RenderParameter(model, prefix, xml):
    name = xml.attrib.get('base', xml.attrib.get('name', '<??>'))
    model.AddItem('%s%s' % (prefix, name))


def RenderObject(model, prefix, spec, xml):
    name = xml.attrib.get('base', xml.attrib.get('name', '<??>'))
    prefix += name
    model.AddItem(prefix)
    for i in xml:
        if i.tag == 'parameter':
            RenderParameter(model, prefix, i)
        elif i.tag == 'object':
            RenderObject(model, prefix, spec, i)
        elif i.tag in ('description', 'uniqueKey'):
          pass
        else:
            raise KeyError(i.tag)


def RenderComponent(model, prefix, spec, xml):
    for i in xml:
        if i.tag == 'parameter':
            RenderParameter(model, prefix, i)
        elif i.tag == 'object':
            RenderObject(model, prefix, spec, i)
        elif i.tag == 'component':
            refspec, refname, ref = chunks[spec, 'component', i.attrib['ref']]
            refpath = ref.attrib.get('path', ref.attrib.get('name', '<?>'))
            RenderComponent(model, prefix, refspec, ref)
        elif i.tag in ('profile', 'description'):
            pass
        else:
            raise KeyError(i.tag)

specs = {}

class Spec(object):
    def __init__(self, name):
        self.name = SpecNameForPython(name)
        self.aliases = []
        self.models = []
        self.deps = []
        specs[name] = self

    def __str__(self):
        out = []
        for (fromspec,fromname),(tospec,toname) in self.aliases:
            fromname = ObjNameForPython(fromname)
            tospec = SpecNameForPython(tospec)
            toname = ObjNameForPython(toname)
            if not models.has_key((fromspec,fromname)):
                models[(fromspec,fromname)] = models[(tospec,toname)]
                Log('aliased %r' % ((fromspec,fromname),))
            if toname != fromname:
                out.append('from %s import %s as %s' 
                           % (tospec, toname, fromname))
            else:
                out.append('from %s import %s' 
                           % (tospec, toname))
        out.append('')
        for model in self.models:
            out.append(str(model))
            out.append('')
        return '\n'.join(out)

    def MakeObjects(self):
        for (fromspec,fromname),(tospec,toname) in self.aliases:
            fromname = ObjNameForPython(fromname)
            tospec = SpecNameForPython(tospec)
            toname = ObjNameForPython(toname)
            if not models.has_key((fromspec,fromname)):
                models[(fromspec,fromname)] = models[(tospec,toname)]
                Log('aliased %r' % ((fromspec,fromname),))
            

def main():
    for filename in sys.argv[1:]:
        ParseFile(filename)
    ResolveImports()
    Log('Finished parsing and importing.')

    items = sorted(chunks.items())
    for (specname, objtype, name),(refspec, refname, xml) in items:
        spec = specs.get(specname, None) or Spec(specname)
        if objtype == 'model':
            objname = ObjNameForPython(name)
            parent = xml.attrib.get('base', None)
            if SpecNameForPython(refspec) != spec.name:
                spec.deps.append(refspec)
                spec.aliases.append(((spec.name,objname),
                                     (refspec,refname)))
            else:
                if parent:
                    model = Model(spec, objname, parent_model_name=parent)
                else:
                    model = Model(spec, objname, parent_model_name=None)
                RenderComponent(model, '', refspec, xml)
                model.MakeObjects()
                spec.models.append(model)

    Log('Finished models.')

    try:
        os.mkdir('std')
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    open('std/__init__.py', 'w')
    for spec in specs.values():
        spec.MakeObjects()
    for specname,spec in sorted(specs.items()):
        outf = open('std/%s.py' % SpecNameForPython(specname), 'w')
        outf.write('#\n'
                   '# AUTO-GENERATED BY parse-schema.py\n'
                   '#\n'
                   '# DO NOT EDIT!!\n'
                   '#\n'
                   'from .. import core\n')
        outf.write(str(spec))


if __name__ == "__main__":
    main()
