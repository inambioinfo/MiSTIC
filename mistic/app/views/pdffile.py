from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render_to_response

import tempfile
import subprocess
import re
import exceptions

class PDFData(object):
  rsvg_convert = None
  phantomjs = None

  def __init__(self, request):
    self.request = request

  def _convert_rsvg(self, input_file, output_file):
    subprocess.call([self.rsvg_convert, '-f', 'pdf', '-o', output_file, input_file ])

  def _convert_phantomjs(self, input_file, output_file, wd, ht):
    import os.path
    render_script = os.path.join(os.path.dirname(__file__), 'render.js')
    if ht and wd:
      subprocess.call([ self.phantomjs, render_script, input_file, output_file, wd, ht ])
    else:
      subprocess.call([ self.phantomjs, render_script, input_file, output_file ])

  def _convert_svg(self, input_file, output_file, wd, ht):
    subprocess.call([ '/bin/cp', input_file, '/tmp/to_render.svg' ])
    if self.phantomjs is not None:
      return self._convert_phantomjs(input_file, output_file, wd, ht)

    elif self.rsvg_convert is not None:
      return self._convert_rsvg(input_file, output_file)

    raise exceptions.RuntimeError('no svg converter available')

  @view_config(route_name="mistic.pdf.fromsvg", request_method="POST")
  def convert_svg(self):
    _data = self.request.POST['pdfdata']

    # XXX: do this with lxml instead of regexp hacks.
    # strip out invisible labels
    _data = re.sub('<text [^<>]* class="circlelabel invisible">[^<>]*</text>', '', _data)
    # explicitly set the fill of highlighted objects
    _data = re.sub('class="highlighted"', 'fill="rgb(20, 216, 28)"', _data)

    # extract width and height
    ht = re.search(r'height\s*=\s*"([^"]*)"', _data)
    wd = re.search( r'width\s*=\s*"([^"]*)"', _data)

    if ht is not None and wd is not None:
      ht = ht.group(1)
      wd = wd.group(1)
    else:
      ht = None
      wd = None

    input = tempfile.NamedTemporaryFile(suffix='.svg')
    input.write(_data.encode('utf-8'))
    input.flush()

    output = tempfile.NamedTemporaryFile('rb', suffix='.pdf')

    try:
      self._convert_svg(input.name, output.name, wd, ht)
    except:
      raise
      raise HTTPNotFound()

    resp = Response(content_type = 'application/pdf',
                    content_disposition = 'inline;filename=plot.pdf')
    # content_disposition = 'attachment;filename=plot.svg')

    resp.body_file.write(output.read())

    return resp
