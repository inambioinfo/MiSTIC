<%!
import mistic.app.data as data
import json
%>
<%inherit file="mistic:app/templates/base.mako"/>
<%block name="pagetitle">Correlation waterfall plot</%block>
<%block name="style">
${parent.style()}
</%block>
<%block name="actions">
  <button class="btn" id="download">CSV</button>
  <!--<button class="btn" id="download-all">CSV [all]</button>-->
  ${parent.actions()}

</%block>


<%block name="controls">
<div id="controls" class="span3">
  <div class="accordion" id="accordion">
    <div class="accordion-group">
      <div class="accordion-heading"><h4 class="accordion-title">
          <a class="accordion-toggle" data-toggle="collapse"  href="#dataset_menu">Dataset </a></h4>
      </div>

      <div id="dataset_menu" class="accordion-body collapse in">
        <div class="accordion-inner">
          <ul id="current_dataset">
          </ul>
          <button class='btn' id="add_dataset">Choose dataset</button>
        </div>
      </div>
    </div>

    <div class="accordion-group">
      <div class="accordion-heading"><h4 class="accordion-title">
          <a class="accordion-toggle" data-toggle="collapse"  href="#gene_menu">Gene </a></h4>
      </div>

      <div id="gene_menu" class="accordion-body collapse in">
        <div class="accordion-inner">
          <input type="text" id="gene" autocomplete='off'>
          <button class="btn" id="plot">Plot</button>
        </div>
      </div>
    </div>

    <div class="accordion-group">
      <div class="accordion-heading"><h4 class="accordion-title">
          <a class="accordion-toggle" data-toggle="collapse"  href="#options_menu">More options </a></h4>
      </div>
      <div id="options_menu" class="accordion-body collapse ">
        <div class="accordion-inner">
          <form class="form-inline">
            <fieldset>
              <div class="control-group">
                <label for="nlabel">Display
                  <input type="text" style="width:20px;" id="nlabel" autocomplete="off" value="10">
                  labels
                </label>
              </div>
              <div class="control-group">
                <label for="geneset_selector">Show geneset members
                  <div id="geneset_selector"></div>
                </label>
              </div>
              <div class="control-group">
                <label>Transformation:</label>
                <div class="btn-group btn-group-justified" data-toggle="buttons-radio" id="transform-buttons"></div>
              </div>
            </fieldset>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
</%block>

<%block name="pagetail">
${parent.pagetail()}

<script type="text/javascript">
require([
    "jquery", "underscore",
    "geneset_selector", "gene_dropdown", "dataset_selector", "corrgraph",
    "domReady!"
], function(
    $, _,
    geneset_selector, gene_dropdown, dataset_selector, corrgraph,
    doc) {

    var opts = {};
    var url_button = function(btn, url) {
        if (url === null) {
            btn
                .attr('disabled', true)
                .off('click.url');
        } else {
            btn
                .attr('disabled', false)
                .on('click.url', function() { window.location.href = url; });
        }
    };

    var updateURLTarget = function(params) {
        var url;
        _.extend(opts, params);
        if (opts.dataset !== null && opts.gene !== null) {
            url = "${request.route_url('mistic.csv.corr', dataset = '_dataset_', gene = '_gene_')}"
                .replace('_dataset_', opts.dataset)
                .replace('_gene_', opts.gene);
            url_button($('#download'), url);

            url = "${request.route_url('mistic.csv.corrds',  dataset = '_dataset_', gene = '_gene_')}"
                .replace('_dataset_', opts.dataset)
                .replace('_gene_', opts.gene);
            url_button($('#download-all'), url);
            
            if (opts.go !== undefined) {
                url += '?go=' + opts.go;
            }
        } else {
            url_button($('#download'), null);
            url_button($('#download-all'), null);
        }
    };

    var dataset_annotation = ${json.dumps(dict([ (ds.id, ds.annotation.id) for ds in data.datasets.all() ]))|n};

    var current_dataset = null;
    var dataset_info = {};
    var current_transform = 'none';
    var current_gene = null;
    var current_geneset = null;
    var current_graph = new corrgraph.corrgraph([], $('#graph'));

    resizeGraph = function() {
        current_graph.elem.height($(window).height() -100 );
        current_graph.resize();
    };

    var gene_entry = new gene_dropdown.GeneDropdown({ el: $("#gene") });

    $('#add_dataset').on('click', function(event) {
        var ds_sel = new dataset_selector.DatasetSelector();
        ds_sel.show(event.currentTarget);
        ds_sel.$el.on('select-dataset', function(event, dataset_id) {
            addDataset(dataset_id);
        });
        event.preventDefault();
    });

    gene_entry.on('change', function(item) {
        current_gene = item;
        gene_entry.$el.toggleClass('valid', item !== null);
        $('#plot').toggleClass('btn-primary', item !== null);
        $('#plot').attr('disabled', item === null);
    });

    var geneset_selector = new geneset_selector.GenesetSelector({
        el: $("#geneset_selector"),
    });

    geneset_selector.on('GenesetSelector:change', function(item) {
        current_geneset = item;
        updateURLTarget({ go: item === null ? undefined : item.id });

        if (item === null) {
            current_graph.markGenes(undefined);
        } else {
            $.ajax({
                url: "${request.route_url('mistic.json.annotation.gene_ids', annotation='_annotation_')}".replace('_annotation_', dataset_annotation[current_dataset]),
                data: { filter_gsid: item.id },
                dataType: 'json',
                success: function(data) {
                    current_graph.markGenes(data);
                },
                error: function() {
                    // inform the user something went wrong.
                }
            });
        }
    });

    var addDataset = function(dataset, sync) {
        var disable = function() {
            dataset_info = {};
            geneset_selector.setDataset(undefined, undefined);
            current_dataset = null;
            gene_entry.setSearchURL(undefined);
            gene_entry.$el.val('');
            $('ul#current_dataset').html('');
        };

        var enable = function(data) {
            dataset_info = data;
            geneset_selector.setDataset(dataset_info.id,
                                        "${request.route_url('mistic.json.annotation.gs', annotation='_annotation_')}".replace('_annotation_', dataset_info.anot));
            current_dataset = dataset;
            gene_entry.setSearchURL("${request.route_url('mistic.json.dataset.search', dataset='_dataset_')}".replace('_dataset_', current_dataset));
            gene_entry.$el.val('');
            $('ul#current_dataset').html('').append('<li>' + dataset + '</li>');
        };

        if (dataset == '') {
            disable();
            return;
        }

        $.ajax({
            url: "${request.route_url('mistic.json.dataset', dataset='_dataset_')}".replace('_dataset_', dataset),
            dataType: 'json',
            async: !sync,
            success: function(data) {
                var xf = $('#transform-buttons');
                xf.empty();
                current_transform = data['xfrm'][0];
                _.each(data['xfrm'], function(val) {
                    var btn = $('<button class="btn btn-default">');
                    btn.on('click', function(event) {
                        current_transform = $(this).text();
                        if (current_dataset !== null && current_gene !== null) {
                            var expt = dataset_info['expt']
                            plot(current_dataset, current_gene.id, (expt=='hts' || expt=='ngs,hts'));
                        }
                        event.preventDefault();
                    });
                    btn.toggleClass('active', current_transform == val);
                    btn.text(val);
                    xf.append(btn);
                });
                enable(data);
            },
            error: disable,
        });
    };
%if dataset is not None:
    addDataset("${dataset.id}", true);
%endif
    var plot = function(dataset, gene, name_labels) {
        $('#plot').button('loading');

        var req = $.ajax({
            url: "${request.route_url('mistic.json.gene.corr', dataset='_dataset_', gene_id='_gene_id_')}".replace('_dataset_', dataset).replace('_gene_id_', gene),
            data: {x: current_transform},
            dataType: 'json',
            beforeSend : function() {
                $("#graph").html('<div id="loading"><center><img src="${request.application_url}/static/img/ajax-loader.gif"/></center> </div>');
            },
            success: function(data) {
                var nlabel = $("#nlabel").val();
                current_graph.annotation = current_dataset.genes;
                current_graph.setLabelNb(nlabel);
                current_graph.setNameAsLabel(name_labels);
                current_graph.setData(data.data);
                current_graph.draw();
                updateURLTarget({ dataset: dataset, gene: gene });
            },
            error: function() {
                // inform the user something went wrong.
            },
            complete: function() {
                req.done(function() { $('#plot').button('reset');
                                      $("div#loading").remove(); });
            }
        });
    };

    $('#plot').click(function (event) {
        if (current_dataset !== null && current_gene !== null) {
            var expt = dataset_info['expt']
            plot(current_dataset, current_gene.id, (expt=='hts' || expt=='ngs,hts'));
        }
        event.preventDefault();
    });

    $('#datasets').change();
    gene_entry.trigger('change', null);
    updateURLTarget({ dataset: null });
    $(window).resize(resizeGraph);
    resizeGraph();
});
</script>
</%block>
