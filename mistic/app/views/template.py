from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render_to_response

from mistic.app import data

import json
import base64



class Graph(object):
  def __init__(self, request):
    self.request = request

  @view_config(route_name="mistic.template.root")
  def root(self):
    args = dict()
    return render_to_response('mistic:app/templates/root.mako', args, request = self.request)

  @view_config(route_name="mistic.template.corrgraph")
  def corrgraph(self):
    args = dict()
    return render_to_response('mistic:app/templates/corrgraph.mako', args, request = self.request)

  @view_config(route_name="mistic.template.corrgraph_static")
  def corrgraph_static(self):
    dataset = self.request.matchdict['dataset']
    gene = self.request.matchdict['gene']
    go_term = self.request.GET.getall('go')

    _dataset = data.datasets.get(dataset)
    if _dataset is None:
      raise HTTPNotFound()

    _row = _dataset.data.r(gene)
    if _row == -1:
      raise HTTPNotFound()

    args = dict(
      dataset = dataset,
      gene = gene,
      go = None if len(go_term) == 0 else go_term[0]
    )
    return render_to_response('mistic:app/templates/corrgraph_static.mako', args, request = self.request)

  @view_config(route_name="mistic.template.scatterplot")
  def scatterplot(self):
    args = dict()
    return render_to_response('mistic:app/templates/scatterplot.mako', args, request = self.request)

  @view_config(route_name="mistic.template.scatterplot_static")
  def scatterplot_static(self):
    dataset = self.request.matchdict['dataset']
    gene1 = self.request.matchdict['gene1']
    gene2 = self.request.matchdict['gene2']

    _dataset = data.datasets.get(dataset)
    if _dataset is None:
      raise HTTPNotFound()

    _row1 = _dataset.data.r(gene1)
    if _row1 == -1:
      raise HTTPNotFound()
    _row2 = _dataset.data.r(gene2)
    if _row2 == -1:
      raise HTTPNotFound()

    args = dict(
      dataset = dataset,
      gene1 = gene1,
      gene2 = gene2,
    )
    return render_to_response('mistic:app/templates/scatterplot_static.mako', args, request = self.request)


  @view_config(route_name="mistic.template.pairplot")
  def pairplot(self):
    
    dataset = self.request.matchdict.get('dataset', None)
    genes = self.request.matchdict.get('genes', [])
    others =  dict(self.request.GET)
    
    try: 
      others = base64.b64decode(others['o'])
      others = dict([o.split('=') for o in  others.split(';')[:-1]])
    except Exception, e :
      pass
      
    args = dict(
      dataset = dataset,
      genes = genes,
      others = others,
    )
    
    return render_to_response('mistic:app/templates/pairplot.mako', args, request = self.request)


  @view_config(route_name="mistic.template.clustering")
  def clustering(self):
    dataset = self.request.matchdict['dataset']
    xform = self.request.matchdict['xform']

    
    _dataset = data.datasets.get(dataset)
    
    if _dataset is None:
      print 'Not found'
      
      raise HTTPNotFound()

    mst = _dataset.mst(xform)
   
    if mst is None:
      raise HTTPNotFound()

    args = dict(
      dataset = self.request.matchdict['dataset'],
      xform = self.request.matchdict['xform'],
      nodes = mst[0],
      edges = mst[1],
      pos = mst[2]
    )

    return render_to_response('mistic:app/templates/clustering.mako', args, request = self.request)

  @view_config(route_name="mistic.template.mstplot", request_method="POST")
  def mstplot_post(self):
  
    
    dataset = self.request.matchdict['dataset']
    xform = self.request.matchdict['xform']

    geneset = set(json.loads(self.request.POST['geneset']))

    _dataset = data.datasets.get(dataset)
    if _dataset is None:
      raise HTTPNotFound()

    mst = _dataset.mst_subset(xform, geneset)

    if mst is None:
      raise HTTPNotFound()

    args = dict(
      dataset = self.request.matchdict['dataset'],
      xform = self.request.matchdict['xform'],
      nodes = mst[0],
      edges = mst[1],
      pos = mst[2]
    )
   
    if len(mst[0]) < 200:
     
      if _dataset.experiment=="ngs":
        return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
      else : 
        if _dataset.experiment=="hts":
          return render_to_response('mistic:app/templates/mstplot_small_chemical.mako', args, request = self.request)
        else : 
          return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
    else:
      return render_to_response('mistic:app/templates/mstplot.mako', args, request = self.request)



  @view_config(route_name="mistic.template.mstplot", request_method="GET")
  def mstplot_get(self):
    dataset = self.request.matchdict['dataset']
    xform = self.request.matchdict['xform']

    _dataset = data.datasets.get(dataset)
    if _dataset is None:
      raise HTTPNotFound()

    mst = _dataset.mst(xform)
    if mst is None:
      raise HTTPNotFound()

    args = dict(
      dataset = self.request.matchdict['dataset'],
      xform = self.request.matchdict['xform'],
      nodes = mst[0],
      edges = mst[1],
      pos = mst[2]
    )

    if len(mst[0]) < 200:
      return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
    else:
      return render_to_response('mistic:app/templates/mstplot.mako', args, request = self.request)

