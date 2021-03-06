# -*- coding: utf-8 -*-
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.security import authenticated_userid
from mistic.app import data
from mistic.app.tables import *

import json



class Graph(object):
  def __init__(self, request):
    self.request = request
    self.args = dict(user = authenticated_userid(self.request))

  @view_config(route_name="mistic.modal.datasets")
  def dataset_modal(self):
    datasets = data.datasets.all()

    incl = self.request.GET.getall('i')
    if len(incl):
      datasets = [ ds for ds in datasets if ds.id in incl ]

    excl = self.request.GET.getall('x')
    if len(excl):
      datasets = [ ds for ds in datasets if ds.id not in excl ]

    anot = self.request.GET.getall('anot')
    if len(anot):
      datasets = [ ds for ds in datasets if ds.annotation.id in anot ]

    args = dict(datasets = datasets)
    args.update(self.args)
    favorite = FavoriteDatasetStore.getall(DBSession(), args['user'])
    args['favorite'] = favorite
    return render_to_response('mistic:app/templates/fragments/dataset_modal.mako', args, request = self.request)

  @view_config(route_name="mistic.template.root")
  def root(self):
    args = self.args
    favorite = FavoriteDatasetStore.getall(DBSession(), args['user'])
    args['favorite'] = favorite
    return render_to_response('mistic:app/templates/root.mako', args, request = self.request)

  @view_config(route_name="mistic.template.help")
  def help(self):
    args = self.args
    return render_to_response('mistic:app/templates/help.mako', args, request = self.request)


  @view_config(route_name="mistic.template.corrgraph")
  def corrgraph(self):
    dataset = self.request.matchdict.get('dataset', None)
    args = dict(dataset = dataset)
    args.update(self.args)
    return render_to_response('mistic:app/templates/corrgraph.mako', args, request = self.request)

  @view_config(route_name="mistic.template.scatterplot")
  def scatterplot(self):
    args = self.args
    return render_to_response('mistic:app/templates/scatterplot.mako', args, request = self.request)


  @view_config(route_name="mistic.template.pairplot")
  def pairplot(self):

    dataset = self.request.matchdict.get('dataset', None)
    genes = self.request.matchdict.get('genes', [])
    args = dict(
      dataset = dataset,
      genes = genes,
    )
    args.update(self.args)
    return render_to_response('mistic:app/templates/pairplot.mako', args, request = self.request)



  @view_config(route_name="mistic.template.mds")
  def mds(self):

    dataset = self.request.matchdict.get('dataset', None)
    genes = self.request.matchdict.get('genes', [])

    args = dict(
      dataset = dataset,
      genes = genes,
    )

    args.update(self.args)
    return render_to_response('mistic:app/templates/mdsplot.mako', args, request = self.request)



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
# Not need any more      pos = mst[2]
    )
    args.update(self.args)
    return render_to_response('mistic:app/templates/clustering.mako', args, request = self.request)

  @view_config(route_name="mistic.template.mstplot", request_method="POST")
  def mstplot_post(self):
    dataset = self.request.matchdict['dataset']
    xform = self.request.matchdict['xform']
    max_genes = 200
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
     
    
    args.update(self.args)
    if len(mst[0]) < max_genes:

      if _dataset.experiment=="ngs":
        return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
      else:
        if _dataset.experiment=="hts":
          return render_to_response('mistic:app/templates/mstplot_small_chemical.mako', args, request = self.request)
        else:
          return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
    else:
      args.update ({'max_genes':max_genes})
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
      
    if len(mst) < 3 : 
      args = dict( dataset = self.request.matchdict['dataset'], xform = self.request.matchdict['xform'])
      args.update(self.args)
      return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)

    args = dict(
      dataset = self.request.matchdict['dataset'],
      xform = self.request.matchdict['xform'],
      nodes = mst[0],
      edges = mst[1],
      pos = mst[2]
    )
    args.update(self.args)

    if len(mst[0]) < 200:
      return render_to_response('mistic:app/templates/mstplot_small.mako', args, request = self.request)
    else:
      return render_to_response('mistic:app/templates/mstplot.mako', args, request = self.request)

