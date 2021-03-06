# -*- coding: utf-8 -*-
import sys
import io
import os
import re
import uuid
import collections
import mistic.data.dataset
import json
import logging
import exceptions
import pandas
import yaml
import copy

from beaker.cache import *
from cache_helpers import *
from mistic.util.extractPeaks import *



class OrderedDictYAMLLoader(yaml.Loader):
  def __init__(self, *args, **kwargs):
    yaml.Loader.__init__(self, *args, **kwargs)

    self.add_constructor(u'tag:yaml.org,2002:map', self.__class__.construct_yaml_map)
    self.add_constructor(u'tag:yaml.org,2002:omap', self.__class__.construct_yaml_map)

  def construct_yaml_map(self, node):
    data = collections.OrderedDict()
    yield data
    value = self.construct_mapping(node)
    data.update(value)

  def construct_mapping(self, node, deep=False):
    if isinstance(node, yaml.MappingNode):
      self.flatten_mapping(node)
    else:
      raise yaml.constructor.ConstructorError(
        None, None, 'expected a mapping node, but found %s' % node.id, node.start_mark)

    mapping = collections.OrderedDict()
    for key_node, value_node in node.value:
      key = self.construct_object(key_node, deep=deep)
      try:
        hash(key)
      except TypeError, exc:
        raise yaml.constructor.ConstructorError('while constructing a mapping',
          node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
      value = self.construct_object(value_node, deep=deep)
      mapping[key] = value
    return mapping



def read_json_table(path, converters = {}):
  rows = []
  index = []
  col_order = collections.OrderedDict()
  for rownum, row in enumerate(io.open(path, 'rbU')):
    #ident, row = row.split(None, 1)
    i = row.index('{')
    ident = row[0:i].strip()
    row = row[i:]
    
    try:
      row = json.loads(row, object_pairs_hook=collections.OrderedDict)
      for k in row.keys():
        col_order[k] = 1
        if k in converters:
          row[k] = converters[k](row[k])
    except ValueError:
      #logging.warn('failed to parse JSON data for identifier {0} on row {1} of {2}'.format(ident, rownum, path))
      continue
    index.append(ident)
    rows.append(row)
  columns = col_order.keys()
  table = pandas.DataFrame(rows, index = pandas.Series(index, dtype=str), columns = columns, dtype = object)
  return table

def write_json_table(path, table, converters = {}):
  out = io.open(path, 'wb')

  for ident in table.index:
    row = collections.OrderedDict()
    for col in table.columns:
      try:
        v = table.ix[ident, col]
        if col in converters:
          v = converters[col](v)
        row[col] = v
      except ValueError:
        pass
        #logging.warn('failed to convert value {0} on row {1} while writing to {2}'.format(repr(v), ident, path))
    try:
      row = json.dumps(row)
      out.write(ident)
      out.write(' ')
      out.write(row)
      out.write('\n')
    except:
      pass
      #logging.warn('failed to serialize {0} on row {1} while writing to {2}'.format(repr(row), ident, path))

  out.close()



__obo_unescape = {
  't': '\t',
  'n': '\n',
  'W': ' '
}

def obo_unescape(x):
  return re.sub(r'\\(.)', lambda m: __obo_unescape.get(m.group(1), m.group(1)), x)

def obo_def(x):
  return x

def parse_obo(file):
  rectype = 'Header'
  kv = []

  comment_re = re.compile(r'(?<!\\)!.*')
  cont_re = re.compile(r'(?<!\\)\\$')
  tag_re = re.compile(r'^(.*?)(?<!\\):\s*(.*)')

  while True:
    line = file.readline()
    if line == '':
      break
    line = comment_re.sub('', line.rstrip('\n'))

    if line.startswith('['):
      if rectype is not None:
        yield rectype, kv
      rectype = line[1:-1]
      kv = []
      continue

    while cont_re.search(line) is not None:
      line = file.readline()
      if line == '':
        logging.warn('incomplete last line')
        break
      cont = comment_re.sub('', line.rstrip('\n'))
      line = line[:-1] + cont

    if not len(line):
      continue

    m = tag_re.match(line)
    if m is None:
      logging.warn('unknown OBO line: [%r]' % (line,))
      continue

    tag, val = m.groups()
    tag = obo_unescape(tag)

    kv.append((tag, val))

  if rectype is not None:
    yield rectype, kv



class OntologyNode(object):
  __namespace_short = dict(
    biological_process = 'BP',
    cellular_component = 'CC',
    molecular_function = 'MF'
  )

  @staticmethod
  def transform_id(ident):
    assert ident.startswith('GO:')
    return ident[3:]

  def __init__(self, kv):
    self.parents = set()
    self.alt_ids = set()
    self.subsets = set()
    for tag, val in kv:
      if tag == 'id':
        self.id = self.transform_id(val.strip())
      elif tag == 'alt_id':
        self.alt_ids.add(self.transform_id(val.strip()))
      elif tag == 'namespace':
        self.namespace = intern(val)
      elif tag == 'name':
        self.name = obo_unescape(val)
      elif tag == 'def':
        self.definition = obo_def(val)
      elif tag == 'is_a':
        self.parents.add(intern(val.strip()))
      elif tag == 'subset':
        self.subsets.add(intern(val.strip()))
      # else:
      #   logging.warn('skipped: %r' % ((tag, val),))

    self.parents = tuple(sorted(self.parents))
    self.alt_ids = tuple(sorted(self.alt_ids))
    self.subsets = tuple(sorted(self.subsets))

  @property
  def namespace_short(self):
    return self.__namespace_short[self.namespace]


class Ontology(object):
  def __init__(self, path, global_config):
    self.nodes = {}

    self.path = path

    obo = os.path.join(path, 'gene_ontology_ext.obo')

    for rectype, kv in parse_obo(open(global_config.file_path(obo), 'rbU')):
      if rectype == 'Term':
        n = OntologyNode(kv)
        self.nodes[n.id] = n

    for v in self.nodes.values():
      for alt_id in v.alt_ids:
        assert alt_id not in self.nodes
        self.nodes[alt_id] = v

  def parents(self, terms):
    o = set(terms)
    visited = set()
    while len(o):
      n = o.pop()
      if n in visited:
        continue

      visited.add(n)

      node = self.nodes.get(n)
      if node is None:
        logging.warn('no node for GO ID %s' % (n,))
        continue

      o.update(set(node.parents) - visited)

    return visited - set(terms)



class Orthology(object):
  def __init__(self, path, global_config):
    self.annot_id_to_og = {}
    self.og_to_annot_ids = collections.defaultdict(lambda: collections.defaultdict(set))

    self.path = path

    for row in open(global_config.file_path(self.path), 'rbU'):
      row = row.split()
      og = row[0]
      items = [ tuple(x.split(':', 1)) for x in row[1:] ]
      for i in items:
        self.og_to_annot_ids[og][i[0]].add(i[1])
        self.annot_id_to_og[i] = og

    self.og_to_annot_ids = dict([
        (k1, dict([ (k2, frozenset(v2)) for k2, v2 in v1.iteritems() ]))
        for k1, v1 in self.og_to_annot_ids.iteritems()
    ])

  def map_ids(self, ids, src_annot, tgt_annot):
    if src_annot == tgt_annot:
      return [ frozenset((i,)) for i in ids ]
    result = []
    for i in ids:
      og = self.annot_id_to_og.get((src_annot, i))
      result.append(self.og_to_annot_ids.get(og, {}).get(tgt_annot, frozenset()))
    return result



class Annotation(object):
  def __init__(self, config, global_config):
    self.config      = config

    self.id          = self.config.get('id', uuid.uuid4())
    self.name        = self.config.get('name', self.id)
    self.description = self.config.get('desc', '')
    self.path        = self.config['path']

    self.data = read_json_table(global_config.file_path(self.path))

  def get(self, id, default = None):
    try:
      return dict(self.data.ix[id])
    except KeyError:
      return default



class DatasetAnnotation(Annotation):
  def __init__(self, config, global_config):
    super(DatasetAnnotation, self).__init__(config, global_config)

  @property
  def info(self):
    return dict(id = self.id,
                name = self.name,
                desc = self.description)



class GeneAnnotation(Annotation):
  def __init__(self, config, global_config):
    super(GeneAnnotation, self).__init__(config, global_config)

    self.genesets = {}
    self.genes = frozenset(self.data.index)

  def geneset_info(self, gsid):
    gsid, ident = gsid.rsplit(':', 1)
    gsid, gscat = gsid.split('.', 1)

    gs = self.genesets.get(gsid)
    if gs is None:
      return None
    try:
      return gs.genesets.ix[ident]
    except KeyError:
      return None

  def all_genesets(self):
    for gsid, gs in self.genesets.iteritems():
      for gid, row in gs.annotations[self.id].geneset_to_gene.iterrows():
        yield gs.full_geneset_id(gid), frozenset(row['ids'])

  def add_geneset(self, geneset):
    self.genesets[geneset.id] = geneset

  def _get_gene_ids(self, gsid = None):
    '''
    return a set of gene ids for this annotation, optionally filtered
    by the intersection of one or more genesets, that are provided in
    the form: geneset_id:identifier (e.g. go:0000007 - low-affinity
    zinc ion transmembrane transporter activity)

    other possibilities to consider allowing (not currently implemented):
      *:*     (all genes that are part of a geneset)
      go:*    (all genes with an assigned go term)
      go.BP:* (all genes with an assigned go term in the biological_process namespace)
    '''
    if gsid is None or not len(gsid):
      return self.genes

    elif isinstance(gsid, basestring):
      geneset_id, ident = gsid.rsplit(':', 1)
      geneset_id = geneset_id.split('.')
      geneset_id, geneset_cat = geneset_id[0], geneset_id[1:]

      geneset_list = []

      if geneset_id == '*':
        geneset_list = self.genesets.values()
      else:
        geneset = self.genesets.get(geneset_id)
        if geneset is not None:
          geneset_list.append(geneset)

      s = set()

      for geneset in geneset_list:
        gsa = geneset.annotations[self.id]

        if ident != '*':
          s.update(gsa.geneset_to_gene.ix[ident, 'ids'])
        else:
          for gsid, gsrow in geneset.genesets.iterrows():
            gscat = gsrow.get('cat', '').split('.')
            for q, r in zip(geneset_cat, gscat):
              if q != '*' and q != r:
                break
            else:
              s.update(gsa.geneset_to_gene.ix[ident, 'ids'])

      return frozenset(s)

    elif isinstance(gsid, collections.Iterable):
      s = set(self.data.index)
      for g in gsid:
        s.intersection_update(self._get_gene_ids(g))
      return frozenset(s)

  def get_gene_ids(self, gsid = None, filt = None):
    r = self._get_gene_ids(gsid)

    if filt is not None:
      r = frozenset([ x for x in r if filt(self.genes.ix[x]) ])

    return r

  def get_geneset_ids(self, gene = None, genesets = None):
    def all(g):
      return True

    def make_pattern_match(genesets):
      genesets = [ x.split('.') for x in genesets ]

      def pattern_match(g):
        gsid = g.rsplit(':', 1)[0]
        gsid_path = gsid.split('.')

        for p in genesets:
          for q, r in zip(p, gsid_path):
            if q != '*' and q != r:
              break
          else:
            return True
        return False

      return pattern_match

    if genesets is None or not len(genesets):
      filt = all
    else:
      filt = make_pattern_match(genesets)

    r = set()
    for g in self.genesets.itervalues():
      r.update([ x for x in g.get_genesets(self.id, gene) if filt(x) ])
    return r

  def get_symbol(self, gene, default = None):
    try:
      return self.data.ix[gene]['symbol']
    except KeyError:
      return default

  def get_name(self, gene, default = None):
    try:
      return self.data.ix[gene]['name']
    except KeyError:
      return default

  @property
  def info(self):
    return dict(id = self.id,
                name = self.name,
                desc = self.description,
                gset = sorted(self.genesets.keys()))



class GeneSetAnnotation(object):
  def __init__(self, path, global_config):
    self.geneset_to_gene = read_json_table(global_config.file_path(path))

    self.gene_to_geneset = {}

    for geneset_id, row in self.geneset_to_gene.iterrows():
      for gene_id in row['ids']:
        self.gene_to_geneset.setdefault(gene_id, set()).add(geneset_id)


class GeneSet(object):
  def __init__(self, config, global_config):
    self.config      = config

    self.id          = self.config.get('id', uuid.uuid4())
    self.name        = self.config.get('name', self.id)
    self.description = self.config.get('desc', '')

    if self.id == 'go':
      go_nodes = ontology.nodes.items()
      self.path     = None
      self.genesets = pandas.DataFrame(
        [ dict(
            cat = go.namespace_short,
            name = go.name,
            desc = go.definition
          )
          for go_id, go in go_nodes ],
        index = [ go_id for go_id, go in go_nodes ]
      )
    else:
      self.path     = self.config['path']
      self.genesets = read_json_table(global_config.file_path(self.path))

    self.annotations = dict([
        (annotation, GeneSetAnnotation(path, global_config))
        for annotation, path in self.config.get('anot', {}).iteritems() ])

    for k in self.annotations.keys():
      a = annotations.get(k)
      a.add_geneset(self)

  def full_geneset_id(self, gsid):
    if 'cat' in self.genesets:
      cat = self.genesets.ix[gsid, 'cat']
      if cat:
        return self.id + '.' + cat + ':' + gsid

    return self.id + ':' + gsid

  def get_genesets(self, annotation, gene):
    ga = self.annotations.get(annotation)
    if ga is None:
      return set()

    if gene is None:
      return set(ga.geneset_to_gene.index.map(self.full_geneset_id))
    else:
      r = set()
      for gsid in ga.gene_to_geneset.get(gene, set()):
        r.add(self.full_geneset_id(gsid))
      return r

  @property
  def info(self):
    return dict(id = self.id,
                name = self.name,
                desc = self.description,
                anot = sorted(self.annotations.keys()))



def make_id_map(x, y, matcher):
  r = {}
  d = []
  for i in x:
    l = [ j for j in y if matcher(i, j) ]
    if len(l) > 1:
      logging.warn('mapping must not be ambiguous %s %s', i,  str(l))
      # mapping must not be ambiguous
      l.sort()
      r[i]=l[0]
      d.append(l[1:])
      continue
    elif len(l) == 0:
      # mapping may skip source ids
      continue
    r[i] = l[0]
  if not len(r):
    # mapping must not be empty
    return None, None
  if len(set(r.values())) != len(r):
    # mapping must be 1:1
    return None, None
  #if set(r.values()) != set(y):
  #  # mapping must cover all target ids
  #  return None
  d = sum(d, [])
  return r,d

def prefix_map(x, y):
  return make_id_map(x, y, lambda i, j: j.startswith(i))

def prefix_map_identity(x, y):
  return make_id_map(x, y, lambda i, j: j==i)


def rev_prefix_map(x, y):
  return make_id_map(x, y, lambda i, j: i.startswith(j))

class DataSet(object):
  VALID_TRANSFORMATIONS = set(('log', 'rank', 'anscombe', 'none'))

  def __init__(self, config, global_config):
    self.config      = config

    self.id          = self.config.get('id', uuid.uuid4())
    self.name        = self.config.get('name', self.id)
    self.description = self.config.get('desc', '')
    self.source      = global_config.file_path(self.config['path'])
    self.data        = mistic.data.dataset.DataSet.readTSV(self.source)
    self.type        = self.config.get('type', '')
    self.tags        = self.config.get('tags', '')
    self.experiment  = self.config.get('expt', '')
    self.annotation  = annotations.get(self.config['annr']) # row/gene/compounds
    self.cannotation = dataset_annotations.get(self.config['annc'])  # sample annotation

    self.annotation_in_ds = self.annotation.data.index.map(lambda x: x in self.data.df.index)
    annotated_genes = sum(self.annotation_in_ds)
    logging.info('dataset {0} has {1} genes, {2} without annotations, {3} annotated genes do not appear in dataset'.format(
      self.id,
      len(self.data.df.index),
      len(self.data.df.index) - annotated_genes,
      len(self.annotation.data.index) - annotated_genes))

    if self.cannotation is None:
      logging.warn('dataset {0} does not have a sample annotation record'.format(self.id))
    else:
      self.catchMappedSampleIDs()
      self.checkAllSamplesHaveAnnotations()

    self.transforms  = []

    for x in self.config.get('xfrm', ['none']):
      if x in self.VALID_TRANSFORMATIONS:
        self.transforms.append(x)

  def checkAllSamplesHaveAnnotations(self):
    sample_set = set(self.samples)
    cann_set = set(self.cannotation.data.index)
    samples_without_annotation = sorted(sample_set - cann_set)

    if len(samples_without_annotation):
      logging.warn('no sample annotation for samples [{0}] in dataset {1} (sample annotation {2})'.format(
        ', '.join(samples_without_annotation),
        self.id,
        self.config['annc']))

  def catchMappedSampleIDs(self):
    sample_set = set(self.samples)
    cann_set = set(self.cannotation.data.index)

    if len(sample_set & cann_set):
      return

    logging.warn('sample annotation IDs do not match dataset IDs for dataset {0} (sample annotation {1}). Trying to recover.'.format(
      self.id,
      self.config['annc']))
    for mapper in (prefix_map, rev_prefix_map):
      tmp = mapper(cann_set, sample_set)
      cann_map,ambiguous = tmp

      if cann_map is not None:
        #logging.warn('mapping found: {0}'.format(mapper.__name__))
        self.cannotation = copy.copy(self.cannotation)
        self.cannotation.data = self.cannotation.data.copy()
        self.cannotation.data.index = self.cannotation.data.index.map(cann_map.get)
        self.cannotation.data = self.cannotation.data.drop([None], axis=0)

        if len(ambiguous):
          n = len(self.data.df.columns)
          self.data.df = self.data.df.drop(ambiguous, axis=1)
          logging.warn('%s samples in dataset.  Removed duplicates: %s.  Now %s samples in dataset', n,  str(ambiguous), len(self.data.df.columns))

        break
    else:
      logging.warn('no mapping found, no annotation information will be available.')

  @property
  def info(self):
    return dict(
      id = self.id,
      name = self.name,
      desc = self.description,
      anot = self.annotation.id,
      type = self.type,
      tags = self.tags,
      expt = self.experiment,
      xfrm = self.transforms
    )

  @property
  def genes(self):
    return self.data.rownames

  @property
  def symbols(self):
    return [self.annotation.symbol.get(r) for r in self.data.rownames]

  @property
  def samples(self):
    return self.data.colnames



  @property
  def numberSamples(self):
    return len(self.data.colnames)

  def _makeTransform(self, xform):
    return dict(
      log =      mistic.data.dataset.LogTransform,
      anscombe = mistic.data.dataset.AnscombeTransform,
      rank =     mistic.data.dataset.RankTransform
      ).get(xform, lambda: None)()

  @key_cache_region('mistic', 'genecorr', lambda args: (args[0].id,) + args[1:])
  def _genecorr(self, gene, xform, absthresh, thresh):
    row = self.data.r(gene)

    if not isinstance(row, list) :
      row = [row]

    result = [self.data.rowcorr(row[i], transform = self._makeTransform(xform)) for i in range(len(row))]

    if absthresh is not None:
      absthresh = float(absthresh)
      result = [[r for r in res if abs(r[2]) >= absthresh] for res in result]

    if thresh is not None:
      thresh = float(thresh)
      result = [[r for r in res if abs(r[2]) >= thresh] for res in result]

    return dict(
      gene = gene,
      symbol = self.annotation.get_symbol(gene, ''),
      name = self.annotation.get_name(gene, ''),
      dataset = self.id,
      row = str(self.data.r(gene)),
      xform = xform,
      data = tuple([[
          dict(
            idx=a,
            gene=b,
            symbol = self.annotation.get_symbol(b, ''),
            name = self.annotation.get_name(b, ''),
            corr=c,
            row=str(row[i])
            ) for a,b,c in result[i]] for i in range(len(result)) ]))

  def genecorr(self, gene, xform = None, absthresh = None, thresh = None):
    return self._genecorr(gene, xform, absthresh, thresh)

  def calcMDS(self, genes, xform):
    return self.data.calcMDS(genes, self._makeTransform(xform))

  def readPositionData(self, pos):
    node_re = re.compile(r'^\s*(\S*)\s+\[(.*?)\];$', re.S|re.M)
    attr_re = re.compile(r'(\S+=(?:[^"\s]+|"[^"]*"))\s*,\s*', re.S|re.M)

    if isinstance(pos, basestring):
      try:
        pos = open(pos, 'rbU')
      except IOError:
        return None
    pos_data = {}

    for m in node_re.finditer(pos.read()):
      node, args = m.groups()
      if node in ('node', 'edge', 'graph'):
        continue

      node = int(node) - 1

      for x in attr_re.split(args):
        if len(x):
          k, v = x.split('=', 1)
          if k == 'pos':
            pos_data[node] = map(float, v[1:-1].split(','))

    n_components = min([ len(v) for v in pos_data.itervalues() ])
    ranges = [ (min([ v[c] for v in pos_data.itervalues()]),
                max([ v[c] for v in pos_data.itervalues()])) for c in range(n_components) ]
    extents = [ x[1] - x[0] for x in ranges ]
    centres = [ (x[1] + x[0]) / 2.0 for x in ranges ]
    scale = max(extents)

    def transform(pos):
      if pos is None:
        return tuple([ 0.0 ] * n_components)
      return tuple([ (pos[c] - centres[c]) / scale + 0.5 for c in range(n_components) ])

    return [ transform(pos_data.get(n)) for n in range(max(pos_data.iterkeys())+1) ]

  @key_cache_region('mistic', 'mst', lambda args: (args[0].id,) + args[1:])
  def mst(self, xform):
    d, f = os.path.split(self.source)

    g = os.path.join(d, 'transformed', xform, os.path.splitext(f)[0] + '.g')
# not need any more    pos = os.path.join(d, 'transformed', xform, os.path.splitext(f)[0] + '.output.dot')

    try:
      g = open(g, 'rbU')
    except IOError:
      return None

    h = g.readline()
    m = re.match(r'p\s+edge\s+([0-9]+)\s+([0-9]+)\s*$', h)
    if m is None:
      return None

    n_nodes, n_edges = map(int, m.groups())
    nodes = [ None ] * n_nodes

    lines = list(g)

    for l in lines:
      if l[0] == 'n':
        l = l.split()
        nodes[int(l[1])-1] = l[2].replace('id=', '').split(':')[0]

    def E(l):
      l = l.split()
      e1 = int(l[1]) - 1
      e2 = int(l[2]) - 1
      w = float(l[3].replace('weight=', ''))
      return (e1, e2), w

    edges = [ E(l) for l in lines if l[0] == 'e' ]

# not need any more    return nodes, edges, self.readPositionData(pos)
    return nodes, edges

  def mst_subset(self, xform, geneset):

    mst = self.mst(xform)
    if mst is None:
      return None

# not need any more    nodes, edges, pos = mst
    nodes, edges = mst

    geneset = sorted(set(geneset) & set(nodes))

    dataset_idx = dict([ (j, i) for i, j in enumerate(geneset) ])

    new_nodes = geneset
    new_edges = [
      ((dataset_idx[nodes[a]], dataset_idx[nodes[b]]), w)
      for (a, b), w in edges
      if nodes[a] in dataset_idx and nodes[b] in dataset_idx
      ]
    new_pos = [ (0.0, 0.0) ] * len(new_nodes)
    ind = 0.01
    for i, n in enumerate(nodes):
      if n in dataset_idx:
        # New version: We started with random position (not need of output.dot file (sfdp) any more)
        new_pos[dataset_idx[n]] = "(" + str(ind) + "," + str(ind) + ")"
        ind = ind + 0.02
#        new_pos[dataset_idx[n]] = pos[i]

    return new_nodes, new_edges, new_pos

  def extract_peaks(self, xform, min_w, max_w, min_h, max_h, file_out=None):
    d, f = os.path.split(self.source)
    file_g = os.path.join(d, 'transformed', xform, os.path.splitext(f)[0] + '.g')

    return exec_extract_peaks(file_g, min_w, max_w, min_h, max_h, file_out) #see mistic/util/extractPeaks.py


  def expndata(self, gene, xform = None):
    expn = self.data.row(self.data.r(gene), transform = self._makeTransform(xform))

    if len(expn.shape) == 1 :
      expn.shape = (1,expn.shape[0])


    row = self.data.r(gene)
    if isinstance(row, int) : row = [row]

    return dict(
      gene = gene,
      symbol = self.annotation.get_symbol(gene, ''),
      name = self.annotation.get_name(gene, ''),
      dataset = self.id,
      row = str(row)  ,
      xform = xform,
      data = tuple([[dict(sample=a, expr=float(b), row=int(row[i])) for a, b in zip(self.samples, expn[i,])] for i in range(expn.shape[0]) ])
    )

  def getSamplesByCharacteristic (self, ki, vi):
    return [k for k,v in d.items() if v[ki]==vi]




class Collection(object):
  def __init__(self, obj_cls):
    self.obj_cls = obj_cls
    self.objects = []
    self.id_to_index = {}

  def load(self, obj, *extra_args, **extra_kw):
    if obj is not None:
      for o in obj:
        if self.get(o.get('id')) is None:
          self.add(self.obj_cls(o, *extra_args, **extra_kw))

  def add(self, obj):
    self.id_to_index[obj.id] = len(self.objects)
    self.objects.append(obj)

  def get(self, id):
    if id not in self.id_to_index: return None
    return self.objects[self.id_to_index[id]]

  def all(self):
    return tuple(self.objects)



ontology = None
orthology = None
dataset_annotations = Collection(DatasetAnnotation)
annotations = Collection(GeneAnnotation)
genesets = Collection(GeneSet)
datasets = Collection(DataSet)



class GlobalConfig(object):
  def __init__(self, config_path):

    self.config_path = config_path
    if os.path.splitext(self.config_path)[1].lower() == '.yaml':
      self.config = yaml.load(
        open(self.config_path, 'rbU'),
        Loader=OrderedDictYAMLLoader)
    else:
      self.config = json.loads(
        re.sub(r'(?m)//.*$', '', open(self.config_path, 'rbU').read()),
        object_pairs_hook=collections.OrderedDict)

  @property
  def config_dir(self):
    return os.path.split(os.path.abspath(self.config_path))[0]

  def file_path(self, path):
    if os.path.isabs(path):
      return path
    else:
      return os.path.join(self.config_dir, path)

  def load_metadata(self):
    global ontology
    global col_annotations
    global annotations
    global genesets
    global orthology

    logging.info('loading ontology')
    ontology = Ontology(self.config.get('ontology'), self)
    logging.info('loading orthologs')
    orthology = Orthology(self.config.get('orthology'), self)
    logging.info('loading annotations')
    annotations.load(self.config.get('annotations'), self)
    logging.info('loading dataset annotations')
    dataset_annotations.load(self.config.get('dataset_annotations'), self)
    logging.info('loading genesets')
    genesets.load(self.config.get('genesets'), self)
    logging.info('metadata loading done')

  def load(self, dataset = None):
    global datasets

    logging.info('loading data')
    if dataset is None:
      datasets.load(self.config.get('datasets'), self)
    else:
      datasets.load([ x for x in self.config.get('datasets') if x.get('id') == dataset ], self)

    logging.info('data loading done')

def load(settings_json):
  gc = GlobalConfig(settings_json)
  gc.load_metadata()
  gc.load()
  return gc
