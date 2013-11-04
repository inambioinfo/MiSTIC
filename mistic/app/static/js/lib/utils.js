(function() {
    info = {};

    info.template = _.template('<span> <%- info %> </span>');

    info.clear = function () {
        var info_div = $('div#more-information');
        info_div.html("");
    };

    info.find = function(information) {
        var info_spans = $('div#more-information span');
        return _.find(info_spans, function(span) { return $(span).data('information') == information; });
    };

    info.toggle = function(information) {
        var info_div = $('div#more-information');
        var info_span = info.find(information);
        if (info_span !== undefined) {
            info_span.remove();
        } else {
            info_span = $(info.template({ info: information }));
            info_span.data('information', information);
            info_div.append(info_span);
        }
    };
    
     info.add = function(information) {
    
        var info_div = $('div#more-information');
        var info_span = info.find(information);
       
        info_span = $(info.template({ info: information }));
        info_span.data('information', information);
        info_div.append(info_span);
        
    
    };

})();



(function() {
  tableToJSON = function (table) {
  
  var rows = table.rows;
  var propCells = rows[0].cells;
  var propNames = [];
  
  var json = "{\"table\": {"
  var obj, row, cells;

  // Use the first row for the property names
  // Could use a header section but result is the same if
  // there is only one header row
  for (var i=0, iLen=propCells.length; i<iLen; i++) {
    var tx = propCells[i].textContent || propCells[i].innerText;
    if (tx!='') { propNames.push(tx);}
  }
 
  // Use the rows for data
  // Could use tbody rows here to exclude header & footer
  // but starting from 1 gives required result
  
  for (var j=1, jLen=rows.length; j<jLen; j++) {
    cells = rows[j].cells;
    
    if (cells.length>1) {
      json += "\""+j+"\":{ ";
      obj = {};

      for (var k=0; k<propNames.length; k++) {
        obj[propNames[k]] = cells[k].textContent || cells[k].innerText;
        json += "\""+propNames[k]+"\":\""+obj[propNames[k]]+"\"";
        if (k<(propNames.length-1)){ json+= ",";}
      }
     ;
      
      json += "}";
      if (j<(rows.length-1)) {    json += "," ; }
      }
      
  }
  json += "}}";
 
  return json;
};
})();


// Functions for dataTable
(function() {
   removeGrouping = function (oTable){


   for (f = 0; f < oTable.fnSettings().aoDrawCallback.length; f++) {
       if (oTable.fnSettings().aoDrawCallback[f].sName == 'fnRowGrouping') {
         oTable.fnSettings().aoDrawCallback.splice(f, 1);
      break;
      }
    }
    // reallowing the sorting on the grouping column
    oTable.fnSettings().aaSortingFixed = null;
    return oTable;

  };
})();

(function() {
   setColReorder = function (oTable){
     oTable.fnSettings().sDom = "Rlfrtip";
     oTable.fnSettings().oInstance._oPluginColReorder.s['allowReorder']= true;
     return oTable;
   };
})();


(function() {
   removeColReorder = function (oTable){
     oTable.fnSettings().sDom = "";
     oTable.fnSettings().oInstance._oPluginColReorder.s['allowReorder']= false;
     return oTable;
   };
})();