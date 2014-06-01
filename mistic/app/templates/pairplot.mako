<%!
import mistic.app.data as data
import mistic.app.tables as tables
import json
%>

<%inherit file="mistic:app/templates/base.mako"/>
<%block name="pagetitle">Multi-way scatterplot</%block>

<%block name="actions">
  ${parent.actions()}
   <a id="share_url" href="#link_to_share" role="button" class="btn" >Link to share</a>
</%block>

<%block name="controls">
<div id="controls" class="span3">
  <div id="menu">
    <div class="accordion" id="accordion">
      <div class="accordion-group">
        <div class="accordion-heading">
          <h4 class="accordion-title">
            <a class="accordion-toggle" data-toggle="collapse"  href="#dataset_menu">Datasets <div id="nb_datasets" class='text-info' style='display:inline;'>(0)</div></a>
          </h4>
        </div>

        <div id="dataset_menu" class="accordion-body collapse in">
          <div class="accordion-inner">
            <ul id="current_datasets">
            </ul>
            <button class='btn' id="add_dataset">Choose dataset</button>
          </div>
        </div>
      </div>

      <div class="accordion-group">
        <div class="accordion-heading">
          <h4 class="accordion-title">
            <a class="accordion-toggle" data-toggle="collapse"  href="#gene_menu">Genes <div id="nb_genes" class='text-info' style='display:inline;'>(0)</div></a>
          </h4>
        </div>

        <div id="gene_menu" class="accordion-body collapse ">
          <div class="accordion-inner">
            <input type="text" id="gene" autocomplete="off" placeholder='Select a gene'/> <br>	
            <span id="genelist"></span>
          </div>
        </div>
      </div>

      <div class="accordion-group">
        <div class="accordion-heading">
          <h4 class="accordion-title">
            <a class="accordion-toggle" data-toggle="collapse"  href="#sample_menu">Samples
              <div id="nb_samples" class='text-info' style='display:inline;'>(0)</div></a>
          </h4>
        </div>

        <div id="sample_menu" class="accordion-body collapse in ">
          <div class="accordion-inner">
            <h5><a class="accordion-toggle" data-toggle="collapse"  href="#current_selection">Highlight groups</a></h5>
            <div id="current_selection" class="accordion-body collapse in ">
            </div>
            <br>
            <button type="button" class='btn' id="new_group">New group</button>
            <hr>
            <div id="sample_characteristic">
              <div class="input-append">
                <input id="sample_annotation" type="text" style="text-overflow : ellipsis;" autocomplete="off" placeholder="Select a characteristic">
                <div class="btn-group">
                  <button id="sample_annotation_drop" class="btn dropdown-toggle" data-toggle="dropdown">
                    <span class="caret"></span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="accordion-group">
        <div class="accordion-heading">
          <h4 class="accordion-title">
            <a class="accordion-toggle" data-toggle="collapse"  href="#options_menu">More options</a>
          </h4>
        </div>

        <div id="options_menu" class="accordion-body collapse ">
          <div class="accordion-inner">
            <ul id="options" class="nav nav-list">
              <li><a id='show_labels'  href="#">Show labels</a></li>
              <li><a id='clear_labels' href="#">Clear labels</a></li>
              <li class="divider"></li>
              <li><a id="change_axes"  href="#">Change axes</a></li>
              <li>
                Transformation:
                <div class="btn-group btn-group-justified" data-toggle="buttons-radio" id="transform-buttons">
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="accordion-group">
        <div class="accordion-heading">
          <h4 class="accordion-title">
            <a class="accordion-toggle" data-toggle="collapse" href="#sample_enrichment_panel">Sample term enrichment</a>
          </h4>
        </div>

        <div id="sample_enrichment_panel" class="accordion-body collapse">
          <div class="accordion-inner">
            <div id="sample_enrichment"></div>
          </div>
        </div>
      </div>

    </div>
  </div>	
</div>
</%block>

<%block name="graph">
${parent.graph()}

<div class="modal hide" id="link_to_share">
  <div class="modal-dialog" >
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
        <h4 class="modal-title">Permanent link for this plot</h4>
      </div>
      <div class="modal-body">
        <span id="share"></span>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn" data-clipboard-target="share" id="copy-to-clipboard">Copy to clipboard</button>
      <button type="button" class="btn btn-primary" data-dismiss="modal">Done</button>
    </div>
  </div>
</div>
</%block>
<%block name="info"></%block>
<%block name="style">
${parent.style()}
</%block>

<%block name="pagetail">
<%include file="mistic:app/templates/fragments/tmpl_point_group.mako"/>

${parent.pagetail()}

<script type="text/javascript">
require([
    "jquery", "underscore", "backbone", "d3", "zeroclipboard",
    "gene_dropdown", "sample_annotation_dropdown",
    "point_group", "point_group_view",
    "dataset_selector",
    "math",
    "pairplot", "domReady!",
], function(
    $, _, Backbone, d3, ZeroClipboard,
    gene_dropdown, sample_annotation_dropdown,
    point_group, point_group_view,
    dataset_selector,
    math,
    pairplot, doc) {

    var clip = new ZeroClipboard($("#copy-to-clipboard"));

    var gene_entry = new gene_dropdown.GeneDropdown({ el: $("#gene") });
    var sample_annotation_entry = new sample_annotation_dropdown.SampleAnnotationDropdown({el:$('#sample_annotation')});

    current_datasets = [];
    dataset_info = [];
    current_transform = "none";
    current_graph = new pairplot.pairplot(undefined, undefined, $('#graph'));
    current_graph.setScaleType(false, false);

    $("#options").css('display', 'none');

    var group_colours = [ "rgba(252,132,3,.65)", "rgba(11,190,222,.65)", "rgba(36,153,36,.65)", 
                          "rgba(155,42,141,.65)", "rgba(255,3,79,.65)","rgba(11,162,162,.65)"  ,
                          "rgba(204,0,0,.65)", "rgba(0,76,153,.65)", "rgba(0,204,0,.65)" ];
    var next_group = 0;

    var pgs = new point_group.PointGroupCollection();
    current_graph.setPointGroups(pgs);

    var pgs_view = new point_group_view.PointGroupListView({ groups: pgs, graph: current_graph, el: $("#current_selection") })

    var newGroup = function() {
        next_group = $('.point-group').length;
        var pg = new point_group.PointGroup({
            style: { fill: group_colours[next_group % 9] }
        });
        pgs.add(pg);
        ++next_group;
    };

<%
    hl = request.GET.get('hl')
    if hl is not None:
        hl = tables.JSONStore.fetch(tables.DBSession(), hl)
%>
%if hl is not None:
    pgs.reset(${hl|n});
%else:
    newGroup();
%endif

    $('#new_group').on('click', function(event) { 
        newGroup(); 
        $('.sg-ops').bind('click', function(event) { 
            _.defer(updateInfo);
        });
        event.preventDefault(); 
    });
    
    $('.sg-ops').on('click', function(event) { 
        _.defer(updateInfo);
    });

    var updateInfo = function() {	
        
        // Update counts label (dataset, genes, samples)
        var nplots = math.stats.sum(_.range(1,current_graph.data.length));
        var nsamples = 0;

        if (!(_.isUndefined(nplots)) & current_graph.point_groups != null) {     
            var s = _.flatten(_.map(current_graph.point_groups.models, function(d) {return d.get('point_ids');}));
            s = _.without(s, "");
            s = _.uniq(s);
            var nsamples = s.length;
        }
        if (_.isNaN(nsamples)) {
            nsamples=0;
        }
        $("#nb_datasets").text('('+current_datasets.length+')');
        $("#nb_samples").text('('+nsamples+')');
        $("#nb_genes").text('('+current_graph.data.length+')');
        $("#options").css('display', 'none');
        if(current_graph.data.length>=2) {
            $("#options").css('display', 'inline');
        }
    };

<%
    xf = {'log':'log', 'rank':'rank', 'none':''}
    ds = data.datasets.all()[0]
    xf['log'] = 'log%(base)s(%(scale)s * RPKM + %(biais)s)' % dict(zip(['scale','biais','base'],ds._makeTransform('log').params))
%>

    var setCurrentTransform = function(xfrm) {
        
        if (current_transform !== xfrm) {
            var avail_xfrms = dataset_info[0]['xfrm']
            if (_.contains(avail_xfrms, xfrm)) {
                $('#transform-buttons button').toggleClass('active', current_transform == xfrm);
                current_transform = xfrm;
                reloadAll();
                // choose log scales if 'log' is a valid transformation, and the selected transformation is 'none'
                var lg = current_transform === 'none' && _.contains(avail_xfrms, 'log');
                current_graph.setScaleType(lg, lg);
            }
        }
        else {
            $('#transform-buttons button:contains("'+xfrm+'")').toggleClass('active', current_transform == xfrm);
        }
        var xform_text = current_transform;
        if (current_transform==='log') { xform_text = "${xf['log']}"; }
        if (current_transform==='none') { xform_text = "${xf['none']}"; }
        current_graph.updateXform(xform_text);
        
    };

    var setAvailableTransforms = function(xfrm_list) {
        var xf = $('#transform-buttons');
        xf.empty();
        
        current_transform = xfrm_list[0];
        _.each(xfrm_list, function(val) {
            var btn = $('<button class="btn btn-default">');
            btn.on('click', function(event) {
                setCurrentTransform($(this).text());
                event.preventDefault();
            });
            btn.text(val);
            xf.append(btn);
        });
    };

    var addDataset = function(dataset, sync) {
        current_graph.removeData(function() { return true; });
        
        $.ajax({
            url: "${request.route_url('mistic.json.dataset', dataset='_dataset_')}".replace('_dataset_', dataset),
            dataype: 'json',
            async: !sync,
            success: function(data) {
                $('ul#current_datasets').html('').append('<li>' + dataset + '</li>');
                
                setAvailableTransforms(data['xfrm']);
                setCurrentTransform(data['xfrm'][0]);
                current_datasets = [dataset];
                dataset_info = [data];
                
                
                gene_entry.setSearchURL("${request.route_url('mistic.json.dataset.search', dataset='_dataset_')}".replace('_dataset_', current_datasets[0]));
                sample_annotation_entry.setSearchURL("${request.route_url('mistic.json.dataset.sampleinfo.search', dataset='_dataset_')}".replace('_dataset_', dataset));
                $("#sample_annotation").val('');
                $("#sample_annotation_drop").attr('disabled', false);
                $("#gene").attr('disabled', false);
                $("input").attr('disabled', false);
                
            },
            error: function() {
                current_dataset = [];
                dataset_info = [];
                gene_entry.setSearchURL(undefined);
                sample_annotation_entry.setSearchURL(undefined);
                $("#sample_annotation_drop").attr('disabled', true);
                $("#gene").attr('disabled', true);
                $('input').attr('disabled', true);
            },
            complete: function() {
                gene_entry.$el.val('');
                $('#genelist').empty();
                updateEnrichmentTable([]);
                updateInfo();
                

            }
        });
    };

    var reloadAll = function(sync) {
        _.each(current_graph.data, function(data) {
            reloadGene(data.gene, sync);
        });
    };

    var reloadGene = function(gene_id, sync) {
        $.ajax({
            url: "${request.route_url('mistic.json.gene.expr', dataset='_dataset_', gene_id='_gene_id_')}".replace('_dataset_', current_datasets[0]).replace('_gene_id_', gene_id),
            dataype: 'json',
            data: { x: current_transform },
            async: !sync,
            success: function(data) {
                current_graph.updateData(data);
                updateInfo();
            },
            error: function() {
                // inform the user something went wrong.
            }
        });
    };

    var addGene = function(gene_id, gene_symbol, sync) {
        
        $.ajax({
            url: "${request.route_url('mistic.json.gene.expr', dataset='_dataset_', gene_id='_gene_id_')}".replace('_dataset_', current_datasets[0]).replace('_gene_id_', gene_id),
            dataype: 'json',
            data: { x: current_transform },
            async: !sync,
            success: function(data) {
                current_graph.addData(data);
                var label = $('<span>')
                    .addClass('badge')
                    .css({ 'margin': '0px 5px' })
                    .attr({ 'data-idx': current_graph.data.length - 1 })
                    .html(gene_symbol ? gene_symbol : gene_id);
                label.append($('<i>')
                             .addClass('icon-white icon-remove-sign')
                             .css({ 'cursor': 'pointer', 'margin-right': -8, 'margin-left': 4 }));
                $('#genelist').append(label);

                updateInfo();
            },
            error: function() {
                // inform the user something went wrong.
            }
        });
    };

    var updateEnrichmentTable = function(data) {
        $('#sample_enrichment').html('');
        if (!data.length) return;
        var s = ['Number of selected points with annotations : '+eval(data[0].tab[0].join('+'))+'/'+($('.selected').length/$('.scatterplot').length)].join(' ');
        $('#sample_enrichment').html(s);
        
        var table = d3
            .select('#sample_enrichment')
            .insert('table', ':first-child');

        var thead = table.append('thead');
        var tbody = table.append('tbody');

        var thr = thead.selectAll("tr")
            .data([ 1 ])
            .enter()
            .append("tr")

        var th = thr.selectAll('th')
            .data([ 'P-val', 'Odds', 'Selected', 'Key : Value' ])
            .enter()
            .append('th')
            .text(function(d) { return d; });

        var tr = tbody.selectAll('tr')
            .data(data)

        tr.enter()
            .append('tr');

        var td = tr.selectAll('td')
            .data(function(d) { 
                var title = '\t\tIn Selection |  Not in Selection\nIn Category\t\t'+ d.tab[0][0]+' | '+d.tab[1][0]+'\nNot in Category\t'+d.tab[0][1]+' | '+d.tab[1][1];
                return [
                    { value: d.p_val.toExponential(1), title:title },
                    { value: typeof(d.odds) === "string" ? d.odds : d.odds.toFixed(1) , title:title },
                    { value: d.tab[0][0]+'/'+ (parseInt(d.tab[1][0])+ parseInt(d.tab[0][0])), title:title},
                    { value: d.key +' : '+d.val, title:title },
                    
                ];
            });

        td.enter()
            .append('td')
            .text(           function(d) { return d.value; })
            .attr('title',   function(d) { return d.title; })
            .attr('classed', function(d) { return d.class; });

        $('#sample_enrichment table')
            .dataTable({
                "aoColumnDefs": [
                    { "sType": "scientific", "aTargets": [ 0 ], 'aaSorting':["asc"] },
                    { "sType": "numeric", "aTargets": [ 1 ]}
                ],
                "bPaginate" : false,
                "iDisplayLength": 10,
                "sPaginationType": "full_numbers",
                "bLengthChange": false,
                "bFilter": false,
                "bSort": true,
                "bInfo": false
            });
    }

    var _selection = { active: false, pending: undefined };

    var selectionSearch = function(selection) {
        
        if (_selection.active) {
            _selection.pending = selection;
        } else {
            if (_.isUndefined(selection) || !selection.length) {
                updateEnrichmentTable([])
                return;
            }
            _selection.active = true;
            _selection.pending = undefined;
            $.ajax({
                url: "${request.route_url('mistic.json.dataset.samples.enrich', dataset='_dataset_')}".replace('_dataset_', current_datasets[0]),
                dataType: 'json',
                type: 'POST',
                data: { samples: JSON.stringify(selection) },
                error: function(req, status, error) {
                    console.log('got an error', status, error);
                },
                success: function(data) {
                    updateEnrichmentTable(data);
                },
                complete: function() {
                    _selection.active = false;
                    window.setTimeout(function() {
                        if (!_selection.active && _selection.pending !== undefined) selectionSearch(_selection.pending);
                    }, 0);
                }
            });
        }
    }

<%
    ds = data.datasets.get(dataset)
    gene_data = [ ds.expndata(gene) for gene in genes ]
%>

%if ds is not None:
    addDataset("${dataset}", true);
    // Gene symbols were passed in the URL
%for g in genes:
    addGene(${json.dumps(g)|n}, undefined, true);
%endfor
%else:
    gene_entry.setSearchURL(undefined);
    sample_annotation_entry.setSearchURL(undefined);
    $("#sample_annotation_drop").attr('disabled', true);
    $('input').attr('disabled', true);
    $("#gene").attr('disabled', true);
    updateEnrichmentTable([]);
%endif

    $("#share_url").on('click', function(event){
        var url = "${request.route_url('mistic.template.pairplot', dataset='_dataset_', genes=[])}"
            .replace('_dataset_', current_datasets[0]);

        if (current_graph.data.length>0){
            _.each(current_graph.data, function(x) { url += '/' + x.gene; });
        }

        $.ajax({
            url: "${request.route_url('mistic.json.attr.set')}",
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(pgs.toJSON()),
            error: function(req, status, error) {
                console.log('failed to construct a URL');
            },
            success: function(data) {
                $("span#share").html(url + '?hl=' + data);
                $("#link_to_share").modal({keyboard : true, 
                                           backdrop: true });

            },
        });
        event.preventDefault();
    });

    $('body').on('click.remove', 'i.icon-remove-sign', function(event) {
        var badge = $(event.target).closest('span.badge');
        var badge_idx = parseInt(badge.attr('data-idx'));

        current_graph.removeData(function(d, i) { return i === badge_idx; });
        badge.remove();

        var badges = d3.selectAll('.badge');
        badges.each (function(d,i) {d3.select(this).attr('data-idx',i);});
        if (current_graph.data.length<2) {
            $("#options").css('display', 'none');
        }
        updateInfo();
    });

    gene_entry.on('change', function(item) {
        if (item === null) return;
        addGene(item.id, item.get('symbol'));
        gene_entry.$el.val('');
    });

    $(current_graph.svg).on('updateselection', function(event, selection) {
        selectionSearch(selection);
        $('#sample_enrichment_panel').collapse('show');
    });

    resizeGraph = function() {
        $('div#graph').height($(window).height() - 124);

        current_graph.resize(
            $('div#graph').width(),
            $('div#graph').height());
    };

    $('div#graph').append(current_graph.svg);

    resizeGraph();
    $(window).resize(resizeGraph);

    $('#show_labels').on("click", function(event){
        var selected;
        selected = d3.select(current_graph.svg).selectAll("g.node.selected .circlelabel");
        if (selected[0].length == 0 ) {
            selected = d3.select(current_graph.svg).selectAll("g.node .circlelabel");
        }
        selected.classed('invisible', false);
        event.preventDefault();
    });

    $('#clear_labels').on("click", function(event){
        var selected;
        selected = d3.select(current_graph.svg).selectAll("g.node.selected .circlelabel");
        if (selected[0].length == 0 ) {
            selected = d3.select(current_graph.svg).selectAll("g.node .circlelabel");
        }
        selected.classed('invisible', true);
        event.preventDefault();
    });
    
    var minimal_axes = false;
    $('#change_axes').on('click', function(event){
        minimal_axes = !minimal_axes;
        current_graph.setMinimalAxes(minimal_axes);
        current_graph.draw()
    });

    $('#sample_annotation_drop').on('click', function() {
        sample_annotation_entry.$el.val('');
        sample_annotation_entry.update();
        sample_annotation_entry.$el.focus();
        return false;
    });
    
    sample_annotation_entry.on("change", function(item){
        if (item === null) return;
        var val = item.id.split('.');
        
        var l1 = _.initial(val).join('.');
        var l2 = val[val.length-1];
        var kv = {};
        kv[l1] = l2
        $.ajax({
            url:  "${request.route_url('mistic.json.dataset.samples', dataset='_dataset_')}".replace('_dataset_', current_datasets[0]),
            data: kv,
            datatype: 'json',
            success: function(data) {
                current_graph.setSelection(data);
            }
        });
    });

    $('#add_dataset').on('click', function(event) {
        var ds_sel = new dataset_selector.DatasetSelector();
        ds_sel.disable_rows(current_datasets);
        ds_sel.show(event.currentTarget);
        
        ds_sel.$el.on('select-dataset', function(event, dataset_id) {
            pgs.reset();
            newGroup();
            addDataset(dataset_id);
            $('input').val('');
            updateInfo();
        });
        
        
        event.preventDefault();
    });

    $("#transform-buttons").button();
});
</script>
</%block>
