#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Parser for tr-069-style data model .xml files."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import xml.etree.ElementTree
import re
import sys


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
            AddChunk(spec, node.tag, name, (spec, node))
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

models = {}

class Model(object):
    def __init__(self, spec, name, parent):
        self.spec = SpecNameForPython(spec)
        self.name = ObjNameForPython(name)
        if parent:
            self.parent = ObjNameForPython(parent)
        else:
            self.parent = None
        self.items = {}
        self.depends = {}
        models[(self.spec,self.name)] = self

    def AddItem(self, name):
        parts = tuple(re.sub(r'\.{i}', r'-{i}', name).split('.'))
        self.items[parts] = 1

    def ItemsMatchingPrefix(self, prefix):
        for i in sorted(self.items.keys()):
            if (i[:len(prefix)-1] == prefix[:-1] and i != prefix):
                yield i

    def Objectify(self, name, parent, prefix):
        assert (not prefix) or (prefix[-1] == '')
        params = []
        objs = []
        out = []
        for i in self.ItemsMatchingPrefix(prefix):
            if len(i) == len(prefix) and i[-1] != '':
                # a parameter of this object
                params.append(i[-1])
            elif len(i) == len(prefix) + 1 and i[-1] == '':
                # a sub-object of this object
                objs.append((i[len(prefix)-1],
                             self.Objectify(i[-2], 'Oogle', i)))
        name = re.sub(r'-{i}', '', name)  # FIXME
        out.append('class %s(%s):' % (name, parent))
        for param in params:
            out.append('  %s = 1' % (param,))
        for objname,obj in objs:
            if len(out) > 1:
                out.append('')
            out.append(Indented('  ', unicode(obj)))
        if len(out) == 1:
            out.append('  pass')
        return '\n'.join(out)

    def __str__(self):
        return self.Objectify(self.name,
                              self.parent or 'BaseClass', ('',))


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
            refspec, ref = chunks[spec, 'component', i.attrib['ref']]
            refpath = ref.attrib.get('path', ref.attrib.get('name', '<?>'))
            RenderComponent(model, prefix, refspec, ref)
        elif i.tag in ('profile', 'description'):
            pass
        else:
            raise KeyError(i.tag)


def main():
    print 'class BaseClass: pass'
    print 'class Oogle: pass'
    print
    
    for filename in sys.argv[1:]:
        ParseFile(filename)
    ResolveImports()

    items = sorted(chunks.items())
    lastspec = None
    for (spec, objtype, name),(refspec, xml) in items:
        if spec != lastspec:
            print 'class %s:' % SpecNameForPython(spec)
            lastspec = spec
        if objtype == 'model':
            objname = ObjNameForPython(name)
            parent = xml.attrib.get('base', None)
            if refspec != spec:
                print '  %s = %s.%s' % (objname, SpecNameForPython(refspec),
                                        ObjNameForPython(name))
                print
                continue
            if parent:
                model = Model(spec, objname, parent=parent)
            else:
                model = Model(spec, objname, parent=None)
            RenderComponent(model, '', refspec, xml)
            print Indented('  ', model)
            print


if __name__ == "__main__":
    main()
