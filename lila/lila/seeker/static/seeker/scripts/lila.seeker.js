var django = {
  "jQuery": jQuery.noConflict(true)
};
var jQuery = django.jQuery;
var $ = jQuery;

String.prototype.format = function () {
  var formatted = this;
  for (var arg in arguments) {
    formatted = formatted.replace("{" + arg + "}", arguments[arg]);
  }
  return formatted;
};

(function ($) {
  $(function () {
    $(document).ready(function () {
      // Initialize event listeners
      ru.lila.seeker.init_charts();
    });
  });
})(django.jQuery);

var ru = (function ($, ru) {
  "use strict";

  ru.lila.seeker = (function ($, config) {
    // Define variables for ru.lila.seeker here
    var loc_example = "",
        loc_bManuSaved = false,
        loc_vscrolling = 0,
        loc_simulation = null,
        loc_network_options = {},
        loc_network_linktypes = null,
        loc_newSermonNumber = 0,
        loc_clicked_nodeid = "",
        loc_manual_colors = [],
        loc_progr = [],         // Progress tracking
        loc_urlStore = "",      // Keep track of URL to be shown
        loc_goldlink_td = null, // Where the goldlink selection should go
        loc_goldlink = {},      // Store one or more goldlinks
        loc_divErr = "lila_err",
        loc_sWaiting = " <span class=\"glyphicon glyphicon-refresh glyphicon-refresh-animate\"></span>",
        lAddTableRow = [
          { "table": "manu_search", "prefix": "manu", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "gftxt_formset", "prefix": "gftxt", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "gedi_formset", "prefix": "gedi", "counter": false, "events": ru.lila.init_typeahead,
            "select2_options": { "templateSelection": ru.lila.litref_template }
          },
          // super
          { "table": "scol_formset", "prefix": "scol", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "ssgeq_formset", "prefix": "ssgeq", "counter": false, "events": ru.lila.init_typeahead,
            "select2_options": { "templateSelection": ru.lila.sg_template }
          },
          { "table": "ssglink_formset", "prefix": "ssglink", "counter": false, "events": ru.lila.init_typeahead,
            "select2_options": { "templateSelection": ru.lila.ssg_template }
          },

          // gold
          { "table": "gkw_formset", "prefix": "gkw", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "geq_formset", "prefix": "geq", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "glink_formset", "prefix": "glink", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "sglit_formset", "prefix": "sglit", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "glit_formset", "prefix": "glit", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "eqgcol_formset", "prefix": "eqgcol", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "gsign_formset", "prefix": "gsign", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "gcol_formset", "prefix": "gcol", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "gftxt_formset", "prefix": "gftxt", "counter": false, "events": ru.lila.init_typeahead },

          // manu
          { "table": "mprov_formset", "prefix": "mprov", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "mlit_formset", "prefix": "mlit", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "mcol_formset", "prefix": "mcol", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "mext_formset", "prefix": "mext", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "mkw_formset", "prefix": "mkw", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "mdr_formset", "prefix": "mdr", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "lrel_formset", "prefix": "lrel", "counter": false, "events": ru.lila.init_typeahead },
                    
          // sermon
          { "table": "sdcol_formset", "prefix": "sdcol", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "sdsign_formset", "prefix": "sdsign", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "stog_formset", "prefix": "stog", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "sdkw_formset", "prefix": "sdkw", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "sedi_formset", "prefix": "sedi", "counter": false, "events": ru.lila.init_typeahead },
          { "table": "srmsign_formset", "prefix": "srmsign", "counter": false, "events": ru.lila.init_typeahead }
        ];

    const rgb2hex = (rgb) => `#${rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/).slice(1).map(n => parseInt(n, 10).toString(16).padStart(2, '0')).join('')}`;


    // Private methods specification
    var private_methods = {
      /**
       *
       */
      addLegend: function (options) {
        var sMethod = "", // Sampling method
            iSize = 0,    // Sample size
            sExcl = "";   // Exclusion string

        try {
          // Check to see if the correct options are there
          if (!('divsvg' in options && 'x' in options &&
                 'y' in options && 'legend' in options)) {
            private_methods.errMsg("Error in addLegend: missing option");
            return false;
          }
          d3.select(options['divsvg']).append("svg:g")
              .append("svg:text")
              .attr("x", options['x'])
              .attr("y", options['y'])
              .attr("class", "ca-legendtext")
              .text(options['legend']);
          d3.select(options['divsvg']).append("svg:g")
              .append("svg:text")
              .attr("x", options['x'])
              .attr("y", options['y'] + 15)
              .attr("class", "ca-legendtext");

          return true;
        } catch (err) {
          private_methods.errMsg("addLegend", err);
          return false;
        }
      },

      /**
       * codico_hlisttree
       *    Make an object list of the current codico hierarchy
       * 
       * @param {el} elRoot
       * @returns {list} list of integers
       */
      codico_hlisttree: function (elRoot) {
        var hList = [],
            srm_codi = {};

        try {
          // Creae a lis of thecurrent hierarchy
          $(elRoot).find(".codico-unit > table").each(function (idx, el) {
            var codico_id = "";

            codico_id = parseInt($(el).attr("id"), 10);
            hList.push(codico_id);
          });
          return hList;
        } catch (ex) {
          private_methods.errMsg("codico_hlisttree", ex);
          return [];
        }
      },

      /**
       * codico_renumber
       *    Re-number the codicological unites of this reconstruction manuscript
       * 
       * @param {el} elRoot
       * @returns {bool}
       */
      codico_renumber: function (elRoot) {
        var counter = 1,
            sRuler = "<div class=\"codico-ruler\"><hr /></div>",
            number = 0;

        try {
          // Get the number of elements
          number = $(elRoot).find(".codico-target").length;
          // Get list of current hierarchy
          $(elRoot).find("table").each(function (idx, el) {
            var argnode = null;

            argnode = $(el).find(".codico-target");
            if (argnode.length > 0) {
              argnode.first().text(counter++);
              // Double check the presence of a <hr>, unless it is the last one
              if (idx < (number - 1)) {
                // There must be a <hr>
                if ($(el).closest(".codico-unit").find(".codico-ruler").length === 0) {
                  // A ruler must be inserted
                  $(sRuler).insertAfter(el);
                }
              } else {
                // There may not be a <hr>
                $(el).closest(".codico-unit").find(".codico-ruler").remove();
              }
            }
          });
          return true;
        } catch (ex) {
          private_methods.errMsg("codico_renumber", ex);
          return false;
        }
      },

      /**
       * fitFeatureBox
       *    Initialize the <svg> in the @sDiv
       * 
       * @param {object} oBound
       * @param {el} elTarget
       * @returns {object}
       */
      fitFeatureBox: function (oBound, elTarget) {
        var rect = null;

        try {
          // Take into account scrolling
          oBound['x'] -= document.documentElement.scrollLeft || document.body.scrollLeft;
          oBound['y'] -= document.documentElement.scrollTop || document.body.scrollTop;
          // Make sure it all fits
          if (oBound['x'] + $(elTarget).width() + oBound['width'] + 10 > $(window).width()) {
            oBound['x'] -= $(elTarget).width() + oBound['width'];
          } else if (oBound['x'] < 0) {
            oBound['x'] = 10;
          }
          if (oBound['y'] + $(elTarget).height() + oBound['height'] + 10 > $(window).height()) {
            oBound['y'] -= $(elTarget).height() + oBound['height'];
          } else if (oBound['y'] < 0) {
            oBound['y'] = 10;
          } else {
            oBound['y'] += oBound['height'] + 10;
          }
          // Take into account scrolling
          oBound['x'] += document.documentElement.scrollLeft || document.body.scrollLeft;
          oBound['y'] += document.documentElement.scrollTop || document.body.scrollTop;
          return oBound;
        } catch (ex) {
          private_methods.errMsg("fitFeatureBox", ex);
          return oBound;
        }
      },

      /**
       * getIntParam - get a numerical parameter from the qdict
       *  
       * @param {object} qdict
       * @param {string} sParamName
       * @param {int}    iDefault
       * @returns {Number}
       */
      getIntParam: function (qdict, sParamName, iDefault) {
        var iBack = 0,  // Integer value
          sBack = "";   // Value as string

        try {
          // Validate
          if (qdict === undefined || qdict === null) return -1;
          if (sParamName === undefined || sParamName === "") return -1;
          if (qdict.hasOwnProperty(sParamName)) {
            sBack = qdict[sParamName];
            if (/^\+?(0|[1-9]\d*)$/.test(sBack)) {
              iBack = Number(sBack);
            }
          } else if (iDefault !== undefined) {
            iBack = iDefault;
          }
          // Return what we have found
          return iBack;
        } catch (err) {
          private_methods.errMsg("getIntParam", err);
          return -1;
        }
      },

      /**
       * getStringParam - get a string parameter from the qdict
       *  
       * @param {type} qdict
       * @param {type} sParamName
       * @returns {String}
       */
      getStringParam: function (qdict, sParamName) {
        var sBack = "";
        try {
          // Validate
          if (qdict === undefined || qdict === null) return "";
          if (sParamName === undefined || sParamName === "") return "";
          if (qdict.hasOwnProperty(sParamName)) {
            sBack = qdict[sParamName].toString().trim();
          }
          return sBack;
        } catch (err) {
          private_methods.errMsg("getStringParam", err);
          return "";
        }
      },

      /**
       * methodNotVisibleFromOutside - example of a private method
       * @returns {String}
       */
      methodNotVisibleFromOutside: function () {
        return "something";
      },

      /**
       *  is_in_list
       *      whether item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @returns {boolean}
       */
      is_in_list: function (lstThis, sName) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              return true;
            }
          }
          // Failure
          return false;
        } catch (ex) {
          private_methods.errMsg("is_in_list", ex);
          return false;
        }
      },

      /**
       *  get_list_value
       *      get the value of the item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @returns {string}
       */
      get_list_value: function (lstThis, sName) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              return lstThis[i]['value'];
            }
          }
          // Failure
          return "";
        } catch (ex) {
          private_methods.errMsg("get_list_value", ex);
          return "";
        }
      },

      /**
       *  set_list_value
       *      Set the value of the item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @param {string} sValue
       * @returns {boolean}
       */
      set_list_value: function (lstThis, sName, sValue) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              lstThis[i]['value'] = sValue;
              return true;
            }
          }
          // Failure
          return false;
        } catch (ex) {
          private_methods.errMsg("set_list_value", ex);
          return false;
        }
      },

      /**
       * prepend_styles
       *    Get the html in sDiv, but prepend styles that are used in it
       * 
       * @param {el} HTML dom element
       * @returns {string}
       */
      prepend_styles: function (sDiv, sType) {
        var lData = [],
            el = null,
            i, j,
            sheets = document.styleSheets,
            used = "",
            elems = null,
            tData = [],
            rules = null,
            rule = null,
            s = null,
            sSvg = "",
            defs = null;

        try {
          // Get the correct element
          if (sType === "svg") { sSvg = " svg";}
          el = $(sDiv + sSvg).first().get(0);
          // Get all the styles used 
          for (i = 0; i < sheets.length; i++) {
            rules = sheets[i].cssRules;
            for (j = 0; j < rules.length; j++) {
              rule = rules[j];
              if (typeof (rule.style) !== "undefined") {
                elems = el.querySelectorAll(rule.selectorText);
                if (elems.length > 0) {
                  used += rule.selectorText + " { " + rule.style.cssText + " }\n";
                }
              }
            }
          }

          // Get the styles
          s = document.createElement('style');
          s.setAttribute('type', 'text/css');
          switch (sType) {
            case "html":
              s.innerHTML = used;

              // Get the table
              tData.push("<table class=\"func-view\">");
              tData.push($(el).find("thead").first().get(0).outerHTML);
              tData.push("<tbody>");
              $(el).find("tr").each(function (idx) {
                if (idx > 0 && !$(this).hasClass("hidden")) {
                  tData.push(this.outerHTML);
                }
              });
              tData.push("</tbody></table>");

              // Turn into a good HTML
              lData.push("<html><head>");
              lData.push(s.outerHTML);
              lData.push("</head><body>");
              // lData.push(el.outerHTML);
              lData.push(tData.join("\n"));
              
              lData.push("</body></html>");
              break;
            case "svg":
              s.innerHTML = "<![CDATA[\n" + used + "\n]]>";

              defs = document.createElement('defs');
              defs.appendChild(s);
              el.insertBefore(defs, el.firstChild);

              el.setAttribute("version", "1.1");
              el.setAttribute("xmlns", "http://www.w3.org/2000/svg");
              el.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
              lData.push("<?xml version=\"1.0\" standalone=\"no\"?>");
              lData.push("<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\" >");
              lData.push(el.outerHTML);
              break;
          }

          return lData.join("\n");
        } catch (ex) {
          private_methods.errMsg("prepend_styles", ex);
          return "";
        }
      },

      /**
       * sermon_treetotable
       *    Convert the <div> oriented tree structure in [elRoot] into a list
       *      of appropriate <tr> items under <elTable>
       * 
       * @param {el}  elRoot
       * @param {el}  elTable
       * @param {el}  selectedid (optional)
       * @returns {bool}
       */
      sermon_treetotable: function (elRoot, elTable, selectedid) {
        var elTbody = null,
            elSel = null,
            elAnc = null,
            sermonid = "",
            rows = [];

        try {
          // Get a list of the <div> elements
          rows = private_methods.sermon_treelist(elRoot, selectedid);

          // Replace the rows that are there now with the new ones
          $(elTable).html("");
          $(elTable).html(rows.join("\n"));

          // Possibly find the <div.tree> that is selected
          if (selectedid !== undefined && selectedid !== "") {
            elSel = $(elRoot).find("div.tree[sermonid={0}]".format(selectedid));
            // From here find the ancestor
            elAnc = $(elSel).parentsUntil("#sermon_tree");
            // Now find all the <div.tree> that are my descendants
            $(elAnc).find("div.tree").each(function (idx, el) {
              // Get this one's sermonid
              sermonid = $(el).attr("sermonid");
              // Make sure the corresponding row is visible
              $(elTable).find("tr[sermonid={0}]".format(sermonid)).first().removeClass("hidden");
            });
          }

          return true;
        } catch (ex) {
          private_methods.errMsg("sermon_treetotable", ex);
          return false;
        }
      },

      /**
       * sermon_treelist
       *    Convert the <div> oriented tree structure in [elDiv] into a list
       *      of appropriate <tr> items under <elTable>
       * 
       * @param {el}  elDiv
       * @param {el}  selectedid (optional)
       * @returns {list}
       */
      sermon_treelist: function (elDiv, selectedid) {
        var elTbody = null,
            elTd = null,
            elSermon = null,
            elParent = null,
            sermons = [],
            sermonid = "",
            targeturl = "",
            hidden = "",
            selected = "",
            nodeid = -1,
            childof = -1,
            maxdepth = -1,
            hasChildren = false,
            colspan = 0,
            td = "",
            tr = "",
            lTr = [],
            level = -1,
            idx = -1,
            lBack = [];

        try {
          // Get all the sermons
          sermons = $(elDiv).find("div.tree");

          // Find the maximum depth
          for (idx = 0; idx < sermons.length; idx++) {
            elSermon = sermons[idx];
            level = parseInt($(elSermon).attr("level"), 10);
            if (level > maxdepth) { maxdepth = level;}
          }

          // Start creating the head
          lBack.push("<thead><tr><th colspan='{0}'>Details of this manuscript's {1} items</th><th>id</th></tr></thead>".format(maxdepth+1, sermons.length));
          lBack.push("<tbody>");

          // Walk all the sermons
          for (idx = 0; idx < sermons.length; idx++) {
            elSermon = sermons[idx];
            // The nodeid starts at 2, because '1' is reserved for the root element as parent
            nodeid = idx + 2;
            $(elSermon).attr("nodeid", nodeid);
            // Get the parent
            elParent = $(elSermon).parent(".tree");
            if (elParent === null || elParent.length === 0) {
              childof = "1";
            } else {
              childof = $(elParent).attr("nodeid");
            }

            // Get the parameters from the current sermon
            sermonid = $(elSermon).attr("sermonid");
            level = parseInt($(elSermon).attr("level"), 10);
            elTd = $(elSermon).find("span.td").first();
            td = $(elTd).html();
            targeturl = $(elTd).attr("targeturl");
            hidden = (level === 1) ? "" : " hidden";
            hasChildren = ($(elSermon).children("div.tree").length > 0);
            selected = "";
            if (selectedid !== undefined && selectedid !== "" && sermonid === selectedid) {
              selected = " selected";
            }

            // Create the <tr> myself
            lTr = [];
            lTr.push("<tr class='form-row{0}{1}' nodeid='{2}' childof='{3}' sermonid='{4}'>".format(hidden, selected, nodeid, childof, sermonid));

            if (hasChildren) {
              if (level > 1) {
                // Indicate level depth
                lTr.push("  <td class='arg-pre' colspan='{0}' style='min-width: {1}px;'></td>".format(level-1, (level-1) * 20));
              }
              // This starts a new level
              lTr.push("  <td class='arg-plus' style='min-width: 20px;' onclick='crpstudio.htable.plus_click(this, \"func-inline\");'>+</td>");
            } else {
              // Indicate level depth
              lTr.push("  <td class='arg-pre' colspan='{0}' style='min-width: {1}px;'></td>".format(level, level * 20));
            }

            // The actual content
            colspan = maxdepth - level + 1;
            // if (hasChildren) { colspan += 1;}
            lTr.push("  <td id='sermon-number-{0}' colspan='{1}' class='clickable' style='width: 100%;' targeturl='{2}' number='{0}'>".format(idx + 1, colspan, targeturl));
            lTr.push("     <span class='arg-nodeid'>{0}</span>".format(idx + 1));
            lTr.push(td);
            lTr.push("  </td>");

            // The ID of the sermon: this is used for selecting and de-selecting a row
            lTr.push("  <td class='tdnowrap clickable selectable' title='Select or de-select this row'");
            lTr.push("      onclick='ru.lila.seeker.form_row_select(this);'>{0}</td>".format(sermonid));

            // Finish the <tr>
            lTr.push("</tr>");
            tr = lTr.join("\n");

            // Add to the list
            lBack.push(tr);
          }

          lBack.push("</tbody>");

          return lBack;
        } catch (ex) {
          private_methods.errMsg("sermon_treelist", ex);
          return [];
        }
      },
      
      /**
       * sermon_tree
       *    Convert [elTable] into a correct TREE structure
       * 
       * @param {el}     elTable
       * @param {parent} the [nodeid] of the parent - if defined
       * @returns {object}
       */
      sermon_tree: function (elTable, row) {
        var oTree = {},
            previous = null,
            parent = null,
            children = [],
            select = [],
            rowidx = -1,
            nodeid = "",
            sermonid = "",
            search = "";

        try {
          // What is the node we have?
          if (row === undefined) {
            // We need to get the first node in the table
            select = $(elTable).find("tr.form-row");
            if (select.length > 0) {
              row = select.first();
              nodeid = $(row).attr("childof");
              sermonid = "";
              row = null;
            }
          } else {
            // Get details 
            sermonid = $(row).attr("sermonid");
            nodeid = $(row).attr("nodeid");
            rowidx = $(elTable).find("tr").index(row);
          }

          // Can we continue?
          if (nodeid !== "") {

            // Fill in the details of this node
            oTree['sermonid'] = sermonid;
            oTree['rowidx'] = rowidx;
            oTree['row'] = row;
            oTree['parent'] = null;
            oTree['next'] = null;
            oTree['prev'] = null;
            oTree['firstchild'] = null;

            // Look for children
            children = $(elTable).find("tr.form-row[childof='" + nodeid + "']");

            // Are there children?
            if (children.length > 0) {
              oTree['child'] = []
              // Walk all the children of this parent
              previous = null;
              children.each(function (idx, el) {
                var oChild;

                // Fill in the details of this child
                oChild = private_methods.sermon_tree(elTable, el);
                if (oChild !== null) {
                  // Is this the first child?
                  if (idx === 0) { oTree['firstchild'] = oChild; }
                  // Normal processing
                  oChild['parent'] = oTree;
                  oChild['prev'] = previous;
                  // Add this child to my children
                  oTree['child'].push(oChild);
                  if (previous !== null) {
                    previous['next'] = oChild;
                  }
                  // Keep track of the previous
                  previous = oChild;
                }
              });
            }
          }


          // Return the result
          return oTree;
        } catch (ex) {
          private_methods.errMsg("sermon_tree", ex);
          return null;
        }
      },

      /**
       * sermon_down
       *    Move nodeid one place down
       * 
       * @param {obj} oTree
       * @param {tr}  row
       * @returns {list}
       */
      sermon_down: function (oTree, row) {
        var sermonid = "",
            i = 0,
            child = [],
            parent = null,
            next = null,
            prev = null,
            node = null;

        try {
          // Get the sermonid in the row
          sermonid = $(row).attr("sermonid");

          // Find the sermon in the tree
          node = private_methods.sermon_node(oTree, sermonid);
          if (node !== null) {
            // We found the node with this sermon
            // Find the next sibling of this node
            next = node['next'];
            prev = node['prev'];
            if (prev !== null) {
              prev['next'] = next;
            }
            if (next !== null) {
              // There is a 'next' sibling, so we can go past it
              node['next'] = next['next'];
              next['next'] = node;
              next['prev'] = node['prev'];
              node['prev'] = next;
              // Keep track of firstchild
              if (node['prev'] === null) {
                node['parent']['firstchild'] = node;
              } else if (next['prev'] === null) {
                next['parent']['firstchild'] = next;
              }
            }
            // Re-arrange the list of children in the parent
            parent = node['parent'];
            next = parent['firstchild'];
            child = [];
            while (next !== null) {
              child.push(next);
              next = next['next'];
            }
            parent['child'] = child;
          }

          // Return the result
          return oTree;
        } catch (ex) {
          private_methods.errMsg("sermon_down", ex);
          return null;
        }
      },

      /**
       * sermon_reorder
       *    Order the surface form of the table in accordance with the tree
       * 
       * @param {obj} oTree
       * @returns {bool}
       */
      sermon_reorder: function (elTable, oTree) {
        var lst_this = [],
            prevtr = null,
            oNode = null,
            row = null,
            i = 0;

        try {
          // Get a list of nodes
          private_methods.canwit_list(oTree, lst_this);

          // Walk the list
          for (i = 0; i < lst_this.length; i++) {
            oNode = lst_this[i];
            if (prevtr === null) {
              // Is this a good one?
              if (oNode['row'] !== null) {
                // This must be the first visible child 
                // See: https://stackoverflow.com/questions/2007357/how-to-set-dom-element-as-the-first-child
                // if (elTable.firstChild !== )
              }
            }
          }

          return true;
        } catch (ex) {
          private_methods.errMsg("sermon_reorder", ex);
          return false;
        }
      },

      /**
       * canwit_list
       *    Create a list of sub nodes
       * 
       * @param {obj}  oNode
       * @parem {list} lst_this
       * @returns {bool}
       */
      canwit_list: function (oNode, lst_this) {
        var next = null,
            i = 0,
            child = [];

        try {
          // Add myself to the list
          lst_this.push(oNode)
          // Get my children
          next = oNode['firstchild'];
          while (next !== null) {
            private_methods.canwit_list(next, lst_this);
            //for (i = 0; i < child.length; i++) {
            //  lst_this.push(child[i]);
            //}
            next = next['next'];
          }
          return true;
        } catch (ex) {
          private_methods.errMsg("canwit_list", ex);
          return false;
        }
      },

      /**
       * sermon_simple
       *    Simple text representation of this node
       * 
       * @param {obj} oNode
       * @parem {int} level
       * @returns {text}
       */
      sermon_simple: function(oNode, level) {
        var lHtml = [],
            next = null,
            spaces = "";

        try {
          if (level === undefined) { level = 0; }
          // Print this node
          spaces = Array( level * 2 +1).join(" ");
          lHtml.push(spaces + oNode['sermonid'] + "\t"+ oNode['rowidx']);
          // Treat children
          next = oNode['firstchild'];
          while (next !== null) {
            lHtml.push(private_methods.sermon_simple(next, level + 1));
            next = next['next'];
          }
          return lHtml.join("\n");
        } catch (ex) {
          private_methods.errMsg("sermon_simple", ex);
        }
      },

      /**
       * sermon_node
       *    Find the node with the identified sermonid
       * 
       * @param {obj} node
       * @param {id}  sermonid
       * @returns {node}
       */
      sermon_node: function (node, sermonid) {
        var child = null,
            children = [],
            i = 0,
            response = null;

        try {
          // Validate
          if (node === null) return null;

          // Is this the one?
          if (node['sermonid'] === sermonid) {
            return node;
          }

          // Check the children
          if ('child' in node) {
            children = node['child'];
            for (i = 0; i < children.length; i++) {
              child = children[i];
              response = private_methods.sermon_node(child, sermonid);
              if (response !== null) {
                return response;
              }
            }
          }
          // Getting here means no result
          return null;
        } catch (ex) {
          private_methods.errMsg("sermon_node", ex);
          return null;
        }
      },

      /**
       * sermon_sibling
       *    Within [elTable] look for rows that are under [childof] and before [nodeid]
       * 
       * @param {el}  elTable
       * @param {int} nodeid
       * @param {int} childof
       * @returns {list}
       */
      sermon_sibling: function (elTable, nodeid, childof, order) {
        var sibling = [];

        try {
          $(elTable).find("tr.form-row[childof='" + childof + "']").each(function (idx, el) {
            var thisid = $(el).attr("nodeid");

            if (thisid !== undefined && thisid !== "") {
              switch (order) {
                case "preceding":
                  if (parseInt(thisid, 10) < nodeid) { sibling.push(el); }
                  break;
                case 'following':
                  if (parseInt(thisid, 10) > nodeid) { sibling.push(el); }
                  break;
              }
            }
          });
          return sibling;
        } catch (ex) {
          private_methods.errMsg("sermon_sibling", ex);
          return [];
        }
      },

      /**
       * sermon_exchange
       *    Make two sermons exchange place (siblings)
       * 
       * @param {el} elSrc
       * @param {el} elDst
       * @returns {bool}
       */
      sermon_exchange: function (elSrc, elDst) {
        var nodesrcid = -1,
            nodedstid = -1,
            highid = -1,
            lowid = -1,
            children = [],
            counter = 1,
            mapping = {},
            oTree = {},
            method = "new",
            elTable = null;

        try {
          // Get the table
          elTable = $(elSrc).closest("table");

          // Get the current values
          nodesrcid = parseInt($(elSrc).attr("nodeid"), 10);
          nodedstid = parseInt($(elDst).attr("nodeid"), 10);

          switch (method) {
            case "old":
              // Exchange source and destination 
              $(elSrc).attr("nodeid", nodedstid);
              $(elDst).attr("nodeid", nodesrcid);

              // Change all the children of the original source
              $(elTable).find("tr.form-row").each(function (idx, el) {
                var sNodeSrc = nodesrcid.toString(),
                    sNodeDst = nodedstid.toString();

                // Is this row a child of source?
                if ($(el).attr("childof") === sNodeSrc) {
                  $(el).attr("childof", sNodeDst);
                  children.push(el);
                } else if ($(el).attr("childof") === sNodeDst) {
                  $(el).attr("childof", sNodeSrc);
                  children.push(el);
                }
              });

              // Determine where to move
              if (nodesrcid < nodedstid) {
                // We are moving a node 'down'
                if (children.length === 0) {
                  // No children: simple moving
                  elSrc.insertAfter(elDst);
                } else {
                  // Move after the last child
                  elSrc.insertAfter(children[children.length - 1]);
                }
              } else {
                // We are moving a node 'up'
                if (children.length === 0) {
                  // No children: simple moving
                  elSrc.insertBefore(elDst);
                } else {
                  // Move before the first
                  elSrc.insertBefore(elDst);
                  // elSrc.insertBefore(children[0]);
                }
              }

              break;
            case "attempt":
              // Determine the correct interval
              if (nodesrcid < nodedstid) {
                highid = nodesrcid; lowid = nodedstid;
              } else {
                highid = nodedstid; lowid = nodesrcid;
              }

              // Determine where to move
              if (nodesrcid < nodedstid) {
                // We are moving a node 'down'
                if (children.length === 0) {
                  // No children: simple moving
                  elSrc.insertAfter(elDst);
                } else {
                  // Move after the last child
                  elSrc.insertAfter(children[children.length - 1]);
                }
              } else {
                // We are moving a node 'up'
                if (children.length === 0) {
                  // No children: simple moving
                  elSrc.insertBefore(elDst);
                } else {
                  // Move before the first
                  elSrc.insertBefore(elDst);
                  // elSrc.insertBefore(children[0]);
                }
              }

              // Treat all the rows that need it
              $(elTable).find("tr.form-row").each(function (idx, el) {
                var nodeid = parseInt($(el).attr("nodeid"), 10);

                // Find out where we should be
                counter += 1;
                // Make a mapping if needed
                if (nodeid !== counter) {
                  mapping[nodeid.toString()] = counter;
                }
              });

              // Now apply the mapping
              $(elTable).find("tr.form-row").each(function (idx, el) {
                var nodeid = $(el).attr("nodeid"),
                    childof = $(el).attr("childof");

                // Check if a mapping is needed
                if (nodeid in mapping) {
                  $(el).attr("nodeid", mapping[nodeid]);
                }
                if (childof in mapping) {
                  $(el).attr("childof", mapping[childof])
                }
                
              });

              break;
            case "new":
              // ================ TESTING ==================

              // Create a Tree from the sermons
              oTree = private_methods.sermon_tree(elTable);
              // move 
              break;
          }
          
          // Re-number the sermon list
          private_methods.sermon_renumber(elTable);

          // Return positively 
          return true
        } catch (ex) {
          private_methods.errMsg("sermon_exchange", ex);
          return false;
        }
      },

      /**
       * sermon_renumber
       *    Re-number the sermons in the list of current table rows
       * 
       * @param {el} elTable
       * @returns {bool}
       */
      sermon_renumber: function (elTable) {
        var counter = 1;

        try {
          // Get list of current hierarchy
          $(elTable).find("tr.form-row").each(function (idx, el) {
            var argnode = null;

            argnode = $(el).find(".arg-nodeid");
            if (argnode.length > 0) {
              argnode.first().text(counter++);
            }
          });
          return true;
        } catch (ex) {
          private_methods.errMsg("sermon_renumber", ex);
          return false;
        }
      },

      /**
       * sermon_hlisttree
       *    Make an object list of the current sermon hierarchy
       * 
       * @param {el} elRoot
       * @returns {bool}
       */
      sermon_hlisttree: function (elRoot) {
        var hList = [],
            srm_codi = {};

        try {
          $(elRoot).find("div.tree").each(function (idx, el) {
            var sermonid = "",
                previd = "",
                nextid = "",
                firstchild = "",
                parent = "",
                srm_match = null,
                elTreeNext = null,
                elTreePrev = null,
                elTreeChild = null,
                elTreeParent = null,
                elHr = null,
                oNew = {};

            // Get my own sermonid
            sermonid = $(el).attr("sermonid");
            if (sermonid === "") {
              // See if there is a following sibling under which this falls
              srm_match = $(el).nextAll(".tree[sermontype='head'],.tree[sermontype='sermon']").first();
              if (srm_match !== undefined && srm_match !== null) {
                // Make a link
                srm_codi[$(srm_match).attr("sermonid")] = $(el).attr("targetid");
              }
              // Cannot process this one
              return;
            }

            // Get the sermonid of any preceding <div.tree>
            elTreePrev = $(el).prev(".tree").first();
            if (elTreePrev !== null && $(elTreePrev).length > 0) {
              previd = $(elTreePrev).attr("sermonid");
            }

            // Get the sermonid of a following <div.tree>
            elTreeNext = $(el).next(".tree").first();
            if (elTreeNext !== null && $(elTreeNext).length > 0) {
              nextid = $(elTreeNext).attr("sermonid");
            }

            // Get the parent if exists
            elTreeParent = $(el).parent(".tree").first();
            if (elTreeParent !== null && $(elTreeParent).length > 0) {
              parent = $(elTreeParent).attr("sermonid");
            }

            // Get the sermonid of a first-child <div.tree>
            elTreeChild = $(el).children(".tree").first();
            if (elTreeChild !== null && $(elTreeChild).length > 0) {
              firstchild = $(elTreeChild).attr("sermonid");
            }

            // Look for a possible ruler start
            elHr = $(el).children(".codi-start").first();

            oNew = { id: sermonid, previd: previd, nextid: nextid, parent: parent, firstchild: firstchild };

            if (elHr !== null && $(elHr).length > 0) {
              oNew['codi'] = $(elHr).attr("targetid");
            }

            // Check if this is a structural element
            if (sermonid.indexOf("new") >= 0) {
              // If it is a structural element, then also pass on the user-defined title text
              oNew['title'] = $(el).find(".sermon-new-head > div").text();
            } else if ($(el).find("table .shead").length > 0) {
              // THis is a [shead] element
              oNew['title'] = $(el).find(".shead").first().text();
              oNew['locus'] = $(el).find("code.draggable").first().text();
              // See if this needs deletion
              if ($(el).hasClass("hidden")) {
                oNew['action'] = "delete";
              }
            }

            hList.push(oNew);
          });

          return hList;
        } catch (ex) {
          private_methods.errMsg("sermon_hlisttree", ex);
          return [];
        }
      },

      /**
       * sermon_hlist
       *    Make an object list of the current table rows contents
       * 
       * @param {el} elTable
       * @returns {bool}
       */
      sermon_hlist: function (elTable) {
        var hList = [];

        try {
          // Get list of current hierarchy
          $(elTable).find("tr.form-row").each(function (idx, el) {
            var sermonid, nodeid, childof, oNew = {};

            sermonid = $(el).attr("sermonid");
            nodeid = $(el).attr("nodeid");
            childof = $(el).attr("childof");
            oNew = { id: sermonid, nodeid: nodeid, childof: childof };
            hList.push(oNew);
          });
          return hList;
        } catch (ex) {
          private_methods.errMsg("sermon_hlist", ex);
          return [];
        }
      },

      /**
       * screenCoordsForRect
       *    Get the correct screen coordinates for the indicated <svg> <rect> element
       * 
       * @param {el} svgRect
       * @returns {object}
       */
      screenCoordsForRect: function (svgRect) {
        var pt = null,
            elSvg = null,
            rect = null,
            oBound = {},
            matrix;

        try {
          // Get the root <svg>
          elSvg = $(svgRect).closest("svg").get(0);

          rect = svgRect.get(0);
          oBound = rect.getBoundingClientRect();

          // Take into account scrolling
          oBound['x'] += document.documentElement.scrollLeft || document.body.scrollLeft;
          oBound['y'] += document.documentElement.scrollTop || document.body.scrollTop;
          return oBound;
        } catch (ex) {
          private_methods.errMsg("screenCoordsForRect", ex);
          return oBound;
        }

      },

      /**
       *  var_move
       *      Move variable row one step down or up
       *      This means the 'order' attribute changes
       */
      var_move: function (elStart, sDirection, sType) {
        var elRow = null,
            el = null,
            tdCounter = null,
            rowSet = null,
            iLen = 0;

        try {
          // Find out what type we have
          if (sType === undefined) { sType = ""; }
          switch (sType) {
            case "selected":
              // Find the selected row
              elRow = $(elStart).closest("form").find("tr.selected").first();
              // The element is below
              el = $(elRow).find(".var-order input").parent();
              break;
            default:
              // THe [el] is where we start
              el = elStart;
              // The row is above me
              elRow = $(el).closest("tr");
              break;
          }
          // Perform the action immediately
          switch (sDirection) {
            case "down":
              // Put the 'other' (=next) row before me
              $(elRow).next().after($(elRow));
              break;
            case "up":
              // Put the 'other' (=next) row before me
              $(elRow).prev().before($(elRow));
              break;
            default:
              return;
          }
          // Now iterate over all rows in this table
          rowSet = $(elRow).parent().children(".form-row").not(".empty-form");
          iLen = $(rowSet).length;
          $(rowSet).each(function (index, el) {
            var elInput = $(el).find(".var-order input");
            var sOrder = $(elInput).val();
            // Set the order of this element
            if (parseInt(sOrder, 10) !== index + 1) {
              $(elInput).attr("value", index + 1);
              $(elInput).val(index + 1);
              // Look for a <td> element with class "counter"
              tdCounter = $(el).find("td.counter");
              if (tdCounter.length > 0) {
                $(tdCounter).html(index+1);
              }
            }
            if (sType === "") {
              // Check visibility of up and down
              $(el).find(".var-down").removeClass("hidden");
              $(el).find(".var-up").removeClass("hidden");
              if (index === 0) {
                $(el).find(".var-up").addClass("hidden");
              }
              if (index === iLen - 1) {
                $(el).find(".var-down").addClass("hidden");
              }
            }
          });
        } catch (ex) {
          private_methods.errMsg("var_move", ex);
        }
      },

      /**
       * draw_hpie_chart
       *    Show a pie-chart using Highcharts
       *
       */
      draw_hpie_chart: function (divid, data) {
        var chartformat = null,
            i = 0,
            title = {
              'hpie_sermo': 'Sermons',
              'hpie_manu': 'Manuscripts',
              'hpie_super': 'SSGs'};

        try {
          chartformat = {
            chart: { plotBackgroundColor: null, plotBorderWidth: null, plotShadow: false, type: 'pie' },
            title: { text: title[divid] },
            tooltip: { pointFormat: '{series.name}: <b>{point.y}</b>' },
            plotOptions: { pie: { allowPointSelect: true, cursor: 'pointer', dataLabels: { enabled: false } } },
            series: [{
              name: title[divid], colorByPoint: true, data: []
            }]
          };
          for (i = 0; i < data.length; i++) {
            chartformat.series[0].data.push({name: data[i].name, y: data[i].value});
          }

          Highcharts.chart(divid, chartformat);
        } catch (ex) {
          private_methods.errMsg("draw_hpie_chart", ex);
        }
      },

        /**
       * draw_pie_chart
       *    Show a pie-chart using D3
       *
       *  The data is expected to be: 'count', 'freq'
       *  See: https://observablehq.com/@d3/pie-chart
       *
       */
      draw_pie_chart: function (divid, data) {
        var margin = null,
            width_g = 200,
            height_g = 200,
            translate_h = 0,
            width = 0,
            height = 0,
            viewbox = "",
            svg = null,
            pie = null,
            path = null,
            label = null,
            arcLabel = null,
            arc = null,
            arcs = null,
            radius = null,
            arcRadius = null,
            title = {
              'pie_manu': 'Manuscripts',
              'pie_canwit': 'Canon witnesses',
              'pie_austat': 'Authority statements'},
            g = null,
            color = null,
            colidx = -1,    // COlor index into array [color]
            i = 0,
            showGuide = null,
            tooltip = null, showTooltip = null, moveTooltip = null, hideTooltip = null;

        try {
          // Set the margin, width and height
          margin = { top: 20, right: 20, bottom: 20, left: 20 }
          width = width_g - margin.left - margin.right;
          height = height_g - margin.top - margin.bottom;

          // Do *NOT* use a viewbox, otherwise downloading as PNG doesn't work
          // viewbox = "0 0 970 510";

          // Create an SVG top node
          svg = d3.select("#" + divid).append("svg")
            //.attr("width", "100%").attr("height", "100%")
            //.attr("viewBox", viewbox)
            .attr("width", width_g)
            .attr("height", height_g)
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("xmlns:xlink", "http://www.w3.org/1999/xlink");

          // Create an over-arching <g> element
          translate_h = width_g / 2 - 20;
          g = svg
            .append("g")
            .attr("transform", "translate(" + translate_h + "," + height_g / 2 + ")");

          // Define the colors that we want to use
          color = d3.scaleOrdinal(['red', 'orange', 'green']);

          // Calculate the radius
          radius = Math.min(width, height) / 2;
          arcRadius = Math.min(width, height) / 2 * 0.7;

          // Generate the pie
          pie = d3.pie().value(function (d) {
            return d.value;
          });

          // Tooltip data respond function
          showTooltip = function (event, d) {
            var ptc = Math.round( parseInt(d.data.value, 10) * 100 / parseInt(d.data.total, 10));
            tooltip.transition().duration(100).style("opacity", 1.0);
            // tooltip.html(d.length + " SSGs have a set of " + d.x0 + " sermon(s)")
            tooltip.html(d.data.name +
              ":</br> <b>" + d.data.value.toLocaleString() + "</b> (" + ptc + "%)")
              .style("left", (event.x + 10) + "px")
              .style("top", (event.y - 35) + "px");
            // All arcs become transparent
            $(event.target).closest("svg").find(".arc > path").attr("opacity", "0.2");
            // I myself become my *FULL* color
            $(event.target).attr("opacity", "1.0");
          };
          // Make sure the tooltip shows about where the user hovers
          moveTooltip = function (event, d) {
            tooltip.style("left", (event.x + 10) + "px")
                   .style("top", (event.y - 35) + "px");
          };
          // Change the opacity again
          hideTooltip = function (event, d) {
            tooltip.transition().duration(300).style("opacity", 0);
            // Restore all colors to their original
            $(event.target).closest("svg").find(".arc > path").each(function () {
              $(this).attr("opacity", "0.8");
            });
          };
          // Act on the CLICK function
          showGuide = function (event, d) {
            var elDiv = null;
            elDiv = $(event.target).closest("div[targeturl]");
            window.location.href = $(elDiv).attr("targeturl");
          };

          path = d3.arc().outerRadius(radius - 10).innerRadius(0);
          label = d3.arc().outerRadius(radius).innerRadius(radius - 80);
          arcLabel = d3.arc().innerRadius(arcRadius).outerRadius(arcRadius);
          arcs = pie(data);

          // Generate the arcs
          arc = g.selectAll("arc")
                 .data(arcs)
                 .enter()
                 .append("g")
                 .attr("class", "arc lila-pie-arc")
                 .on("click", showGuide)
                 .on("mouseover", showTooltip)
                 .on("mousemove", moveTooltip)
                 .on("mouseleave", hideTooltip);

          // Draw the arc paths
          arc.append("path")
              .attr("d", path)
              .attr("fill", function (d, i) {
                return color(i);
              })
              .attr("opacity", "0.8");

          console.log(arc);

          // Add a label to each of the arcs

          svg.append("g")
             .attr("transform", "translate(" + translate_h + "," + height_g / 2 + ")")
             .attr("font-family", "sans-serif").attr("font-size", 10).attr("text-anchor", "middle")
             .selectAll("text")
             .data(arcs)
             .join("text")
             .attr("transform", function (d) {
               return "translate(" + arcLabel.centroid(d) + ")";
             });
            /* This would have been to add a <tspan> with the number to the pie
            .call(text => text.append("tspan")
               //.attr("x", 0)
               .attr("y", "0.1em")
               .attr("font-weight", "bold")
               .text(function (d) {
                 return d.data.value.toLocaleString();
               })
               ); */

          svg.append("g")
              .attr("transform", "translate(" + translate_h + "," + 10 + ")")
              .attr("text-anchor", "middle")
              .append("text")
              .text(title[divid])
              .attr("class", "title");

          // Add a tooltip <div>
          tooltip = d3.select("#" + divid)
            .append("div").attr("class", "tooltip").style("opacity", 0);


          // THis should have drawn the pie-chart correctly
        } catch (ex) {
          private_methods.errMsg("draw_pie_chart", ex);
        }
      },

      /**
       * draw_network
       *    draw a force-directed network (e.g. for Cluster Analysis)
       *
       * See: https://observablehq.com/@d3/force-directed-graph
       *
       * node: {id: "Champtercier", group: 1}
       * link: {source: "CountessdeLo", target: "Myriel", value: 1}
       * 
       * @param {type} options
       * @returns {Boolean}
       */
      draw_network: function (options) {
        var svg,      // the SVG element within the DOM that is being used
            divSvg,   // The target svg div
            color,    // D3 color scheme
            factor,
            width,
            height,
            watermark,
            gravityvalue = 10,
            gravityid = "#gravityvalue",
            p = {},
            g = null,
            gwm = null,
            link,
            node;
        const scale = d3.scaleOrdinal(d3.schemeCategory10);

        try {
          // Validate the options
          if (!('nodes' in options && 'links' in options &&
                options['nodes'] !== undefined && options['links'] !== undefined &&
                'target' in options && 'width' in options &&
                'height' in options)) { return false; }

          // Initialize
          loc_simulation = null;
          if ($(gravityid).length > 0) {
            gravityvalue = parseInt($(gravityid).text(), 10);
          }

          // Get parameters
          width = options['width'];
          height = options['height'];
          factor = options['factor'];
          watermark = options['watermark'];

          // Define the SVG element and the color scheme
          divSvg = "#" + options['target'] + " svg";
          $(divSvg).empty();

          // Get the width and height
          width = $(divSvg).width();
          height = $(divSvg).height();

          svg = d3.select(divSvg);
          svg.attr("width", width)
            .attr("height", height)
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("xmlns:xlink", "http://www.w3.org/1999/xlink")
          g = svg.append("g");
          color = network_color;

          // Append a legend
          private_methods.addLegend({
            'x': 50,  // width / 2,
            'y': 50,  // height - 50,
            'divsvg': divSvg,
            'legend': options['legend']
          });

          // This is based on D3 version *6* !!! (not version 3)
          loc_simulation =  d3.forceSimulation(options['nodes'])
              .force("link", d3.forceLink(options['links']).id(function (d) {
                var result;
                // This determines the size of each link
                // Should be: result = d.value * factor;
                result = d.id;
                return result;
              }).distance(function (d) { return 40; })
              )
              // .force("charge", d3.forceManyBody().strength(-100)) // Was: .charge(-100)
              .force("charge", d3.forceManyBody().strength(-1 * gravityvalue))
              .force("center", d3.forceCenter(width / 2, height / 2))
              .on("tick", ticked);

          // Define the zooming
          svg.call(d3.zoom()
            .extent([[0, 0], [width, height]])
            .scaleExtent([0.2, 100])
            .on("zoom", zoomed));

          // Define a d3 function based on the information in 'nodes' and 'links'
          link = g.append("g")
                    .attr("class", "links")
                    .selectAll("line")
                    .data(options['links'])
                    .join("line")
                    .attr("stroke-width", function (d) {
                      return Math.sqrt(2 * d.value);
                    });
          node = g.append("g")
                    .attr("class", "nodes")
                    .selectAll("circle")
                    .data(options['nodes'])
                    .join("circle")
                    .attr("r", function (d) {
                      var scount = d.scount;
                      var iSize = Math.max(10, scount / 2);
                      return iSize;
                    })
                    .attr("fill", color)
                    .attr("stroke", "white")
                    .attr("stroke-width", "1")
                    .call(network_drag(loc_simulation));



          // Add popup title to nodes;
          node.append("title")
            .text(function (d) { return d.id; });
          // Add popup title to links: this provides the actual weight
          link.append("title")
                  .text(function (d) { return d.value; });

          // Now add the watermark
          gwm = svg.append("g");
          gwm.attr("class", "watermark-main")
             .attr("transform", "translate(" + options['width'] / 2 + "," + (options['height'] - 33) + ") scale(2.0)");
          $(".watermark-main").html(watermark);

          // Defind the 'zoomed' function
          function zoomed(event) {
            // Get the transform
            var transform = event.transform;
            var scale = event.transform.k;

            // THis is geometric re-scale:
            // (but note: CSS prevents lines from scaling)
            g.attr("transform", event.transform);

            link.style("stroke-width", function (d) {
              return Math.sqrt(2 * d.value);
            });

            node.style("stroke-width", function (d) {
              return 1 / scale;
            });
            node.attr("r", function (d) {
              var scount = d.scount;
              var iSize = Math.max(10, scount / 2);
              return iSize /scale;
            });

            // Semantic rescale: just the size of the circles
            //g.selectAll("circle")
            //  .attr('transform', event.transform);
          }

          // Define the 'ticked' function
          function ticked() {
            node.attr("cx", function (d) {
              var radius = 10;
              if (d.scount !== undefined) { radius = Math.max(10, d.scount / 2);}
              return d.x = Math.max(radius, Math.min(width - radius, d.x));
            })
                .attr("cy", function (d) {
                  var radius = 10;
                  if (d.scount !== undefined) { radius = Math.max(10, d.scount / 2); }
                  return d.y = Math.max(radius, Math.min(height - radius, d.y));
                });
            link.attr("x1", function (d) { return d.source.x; })
                .attr("y1", function (d) { return d.source.y; })
                .attr("x2", function (d) { return d.target.x; })
                .attr("y2", function (d) { return d.target.y; });
          }

          function network_color(d) {
            var col_result = "";
            if (d.group > 1) {
              col_result = "aap";
            }
            col_result = scale(d.group);
            return col_result;
          }

          function network_drag(simulation) {
            function dragstarted(event) {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              event.subject.fx = event.subject.x;
              event.subject.fy = event.subject.y;
            }

            function dragged(event) {
              event.subject.fx = event.x;
              event.subject.fy = event.y;
            }

            function dragended(event) {
              if (!event.active) simulation.alphaTarget(0);
              event.subject.fx = null;
              event.subject.fy = null;
            }

            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
          }


          // Return positively
          return true;
        } catch (ex) {
          private_methods.errMsg("draw_network", ex);
          return false;
        }
      },

      /**
       * draw_network_overlap
       *    draw a force-directed network similar to the one by Boodts & Denis "A sermon by any other name?"
       *
       * See: https://observablehq.com/@d3/force-directed-graph
       *
       * node: {id: "Champtercier", group: 1}
       * link: {source: "CountessdeLo", target: "Myriel", value: 1}
       * 
       * @param {type} options
       * @returns {Boolean}
       */
      draw_network_overlap: function (options) {
        var svg,          // the SVG element within the DOM that is being used
            divSvg,       // The target svg div
            color,        // D3 color scheme
            // grayrange,    // D3 gray color
            opacityrange, // D3 opacity range
            widthrange,   // D3 width range
            colrange,     // D3 color range (attempt) for node coloring
            factor,
            width,
            height,
            watermark,
            calcW,
            calcH,
            i,
            count,
            max_width = 2,
            fixed_width = 1,
            max_value = 1,
            max_group = 1,
            bDoTransform = true,
            linktypes = ["prt", "neq", "ech", "uns"],
            sLinktype = "",
            maxcount = 0,
            gravityvalue = 100,
            gravityid = "#gravity_overlap_value",
            degree = 1,
            p = {},
            g = null,
            gwm = null,
            link,
            node;
        const scale = d3.scaleOrdinal(d3.schemeCategory10);

        try {
          // Validate the options
          if (!('nodes' in options && 'links' in options &&
                options['nodes'] !== undefined && options['links'] !== undefined &&
                'target' in options && 'width' in options &&
                'height' in options)) { return false; }

          // Initialize
          loc_simulation = null;
          if ($(gravityid).length > 0) {
            gravityvalue = parseInt($(gravityid).text(), 10);
          }

          // Get parameters
          width = options['width'];
          height = options['height'];
          factor = options['factor'];
          degree = options['degree'];
          max_value = options['max_value'];
          max_group = options['max_group'];
          watermark = options['watermark'];

          // Create a grayscale color range
          //grayrange = d3.scaleLinear()
          //  .domain([1, max_value])
          //  .range(["#DDD", "#000"]);

          opacityrange = d3.scaleLinear()
            .domain([1, max_value])
            .range([0.1, 0.9]);

          widthrange = d3.scaleLinear()
            .domain([1, max_value])
            .range([1, max_width]);

          //colrange = d3.scaleQuantile()
          //  .range(["#fe433c", "#f31d64", "#a224ad", "#6a38b3", "#3c50b1", "#0095ef"])
          //  .domain([1, max_group]);

          colrange = d3.scaleLinear()
            .range(["red", "darkblue"])
            .domain([1, max_group]);

          // Calculate the maxcount within the nodes 'scount' feature
          for (i = 0; i < options['nodes'].length; i++) {
            count = options['nodes'][i]['scount'];
            if (count > maxcount) {
              maxcount = count;
            }
          }

          // Define the SVG element and the color scheme
          divSvg = "#" + options['target'] + " svg";
          $(divSvg).empty();
          svg = d3.select(divSvg);
          calcW = $(svg).parent().width();
          calcH = $(svg).parent().height();
          // Add a viewbox
          svg.attr("viewBox", [0, 0, width, height])
          svg.attr("width", width )
            .attr("height", height )
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("xmlns:xlink", "http://www.w3.org/1999/xlink")
          color = network_color;
          // Needed for e.g. zooming
          g = svg.append("g");

          // Append a legend (with the title): top center
          private_methods.addLegend({
            'x': 50,          // width / 2,
            'y': 50,          // height - 50,
            'divsvg': divSvg,
            'legend': options['legend']
          });

          // This is based on D3 version *6* !!! (not version 3)
          loc_simulation = d3.forceSimulation(options['nodes'])
              .force("link", d3.forceLink(options['links']).id(function (d) {
                var result = d.id;
                return result;
              }).distance(function (d) { return 10 * maxcount / degree; })
              )
              .force("charge", d3.forceManyBody().strength(-1 * gravityvalue))
              .force("center", d3.forceCenter(width / 2, height / 2))
              .force("collide", d3.forceCollide(d => 65).radius(function (d) {
                return get_height(d) + 1;
              }).iterations(3))
              .on("tick", ticked);
          
          if (bDoTransform) {
            // Define the zooming
            svg.call(d3.zoom()
              .extent([[0, 0], [width, height]])
              .scaleExtent([0.2, 100])
              .on("zoom", zoomed));
          }

          // Define arrow heads
          g.append("defs").selectAll("marker")
            .data(["arrow_uses"])
            .enter().append("marker")
            .attr("id", function (d) {
              return d;
            })
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 18)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("fill", "black")
            .attr("d", 'M0,-5L10,0L0,5');

          // Define a d3 function based on the information in 'nodes' and 'links'
          link = g.append("g")
                  .attr("class", "links")
                  .selectAll("line")
                  .data(options['links'])
                  .join("line")
                  // .join("polyline")  // See issue #511
                  .attr("class", function (d) {
                    var m = "linktype_" + d.linktype;
                    return m;
                  })
                  .attr("stroke", function (d) {
                    var m = ru.lila.seeker.overlap_stroke(d);
                    return m;
                  })
                  .attr("stroke-opacity", function (d, or) {
                    var m = "";
                    if ("overlap_linktypes" in loc_network_options &&
                      loc_network_options["overlap_linktypes"] === true &&
                      loc_network_linktypes !== null &&
                      loc_network_linktypes.indexOf(d.linktype) < 0) {
                      // Hide it by using a low opacity
                      m = "0.02";
                    } else {
                      // Calculate the opacity
                      m = ru.lila.seeker.overlap_stroke_opacity(d, opacityrange);
                    }
                    return m;
                  })
                  .attr("stroke-opacity-copy", function (d, or) {
                    var m = ru.lila.seeker.overlap_stroke_opacity(d, opacityrange);
                    return m;
                  })
                  .attr("stroke-width", function (d) {
                    var width;
                    // Issue #510: used to be:
                    //width = widthrange(d.value);
                    width = fixed_width;
                    return width;
                  })
                  //.attr("marker-mid", function (d) {
                  //  var m = ru.lila.seeker.overlap_marker_end(d);
                  //  return m;
                  //})
                  //.attr("marker-mid-copy", function (d) {
                  //  var m = ru.lila.seeker.overlap_marker_end(d);
                  //  return m;
                  //})
                  .attr("marker-end", function (d) {
                    var m = ru.lila.seeker.overlap_marker_end(d);
                    return m;
                  })
                  .attr("marker-end-copy", function (d) {
                    var m = ru.lila.seeker.overlap_marker_end(d);
                    return m;
                  })
          ;
          node = g.append("g")
                  .attr("class", "nodes")
                  .selectAll("g")
                  .data(options['nodes'])
                  .join("g")
                  .attr("hcs", function (d) {
                    return d.hcs;
                  })
                  .attr("nodeid", function (d) { return d.id;})
                  .attr("data-toggle", "modal")
                  .attr("data-target", "#modal-nodecolor")
                  .attr("class", "overlap-node")
                  .call(network_drag(loc_simulation));

          // Add the circle below the <g>
          node.append("circle")
              .attr("r", get_radius)
              .attr('fill', color);

          // Add signature to node below the <g>
          node.append("text")
              .attr("x", function (d) {
                var x = -1 * get_width(d) / 2;
                return x.toString();
              })
              .attr("y", function (d) {
                var x = 3 * get_radius(d);
                return x.toString();
              })
              .text(function (d) {
                return d.label;
              })
              .clone(true).lower()
              .attr("fill", "none")
              .attr("stroke", "white")
              .attr("stroke-width", 3);

          // Add popup title to nodes;
          node.append("title")
            .text(function (d) {
              return "Authority File(s): " + d.lila + "\n Linked manifestations: " + d.scount + " (id=" + d.id + ")";
            });
          // Add popup title to links: this provides the actual weight
          link.append("title")
            .text(function (d) {
              var sTitle = "";
              // Construct what is shown: link type, spec type, notes
              if (d.link !== undefined && d.link !== null && d.link !== "") {
                sTitle = "Link type: " + d.link;
              }
              if (d.spec !== undefined && d.spec !== null && d.spec !== "") {
                sTitle = sTitle + "\nSpecification: " + d.spec;
              }
              if (d.note !== undefined && d.note !== null && d.note !== "") {
                sTitle = sTitle + "\n\nnote: " + d.note;
              }
              return sTitle
            });

          // Now add the watermark
          gwm = svg.append("g");
          gwm.attr("class", "watermark-main")
             .attr("transform", "translate(" + width / 2 + "," + (height - 33) + ") scale(2.0)");
          $(".watermark-main").html(watermark);

          // Link a handler to select the right color
          $(".overlap-node").on("click", function (event) {
            var el = $(this),
                color = "";
            // Get the color
            color = $(el).find("circle").first().attr("fill");
            // Set the color
            $("#nodecolor").val(rgb2hex(color));
            // Remember this node
            loc_clicked_nodeid = $(el).attr("nodeid");
          });

          // ====================== HELP FUNCTIONS =============================
          function get_radius(d) {
            var scount = 0,
                iSize = 4;
            if (d !== undefined) {
              scount = d.scount;
            }
            if ("overlap_scount" in loc_network_options && loc_network_options["overlap_scount"] === true) {
              // Need to pay more attention to the scount
              iSize = Math.max(4, scount+1);
            } else {
              // This is usually [5]
              iSize = Math.max(5, scount / 4);
            }
            return iSize;
          }

          function get_width(d) {
            return 10 * d.label.length;
          }

          function get_height(d) {
            var r = get_radius(d);
            return r * 4;
          }

          // Defind the 'zoomed' function
          function zoomed(event) {
            // Get the transform
            var transform = event.transform;
            var scale = event.transform.k;

            // THis is geometric re-scale:
            // (but note: CSS prevents lines from scaling)
            g.attr("transform", event.transform);

            // EK While looking at issue #510, #511, I saw that the code below
            //             causes the 'hover' effect to disappear, which is a pity
            //
            // EK Possibly remove completely in time??
            //
            //link.style("stroke-width", function (d) {
            //  var width;
            //  // Issue #510: used to be:
            //  //width = widthrange(d.value);
            //  width = fixed_width;
            //  return width;
            //});
            //
            //link.style("stroke", function (d) {
            //  var m = ru.lila.seeker.overlap_stroke(d);
            //  return m;
            //});*/

            // Make sure that the circle retain their size by dividing by the scale factor
            node.selectAll("circle")
              .attr("r", function (d) {
                var iSize = get_radius(d);
                return iSize / scale;
              })
              .attr("stroke-width", function (d) {
                return 3 / scale;
              });
            node.selectAll("text")
              .attr("x", function (d) {
                var x = (-1 * get_width(d) / 2) / scale;
                return x.toString();
              })
              .attr("y", function (d) {
                var x = (3 * get_radius(d)) / scale;
                return x.toString();
              })
              .style("font-size", function (d) {
                var iSize = Math.round( 14 / scale);
                return (scale < 1) ? "14px" : iSize.toString() + "px";
              });

            // Semantic rescale: just the size of the circles
            //g.selectAll("circle")
            //  .attr('transform', event.transform);
          }

          // Define the 'ticked' function
          function ticked() {
            //var q = d3.quadtree(options['nodes']),
            //    i = 0,
            //    n = options['nodes'].length;

            //// Visit all points
            //while (++i < n) {
            //  q.visit(collide(options['nodes'][i]));
            //}

            node.attr("transform", function (d) {
              var radius = 10, ix, iy;
              //if (d.scount !== undefined) { radius = get_radius(d); }
              //ix = Math.max(radius, Math.min(width - radius, d.x));
              //iy = Math.max(radius, Math.min(height - radius, d.y));
              ix = d.x;
              iy = d.y;
              return `translate(${ix},${iy})`
            });

            // Halfway points, issue #511, was shot down :)
            //link.attr("points", function (d) {
            //  var sBack;
            //  sBack = d.source.x + "," + d.source.y + " " +
            //          (d.source.x + d.target.x) / 2 + "," + (d.source.y + d.target.y) / 2 + " " +
            //          d.target.x + "," + d.target.y;
            //  return sBack;
            //})

            // After issue #511
            //link.attr("x1", d => d.target.x)
            //    .attr("y1", d => d.target.y)
            //    .attr("x2", d => d.source.x)
            //    .attr("y2", d => d.source.y);
            link.attr("x1", function (d) {
              var result;
              switch (d.spectype) {
                case "usd":
                case "usi":
                  result = d.target.x;
                  break;
                default:
                  result = d.source.x;
                  break;
              }
              return result;
            });
            link.attr("y1", function (d) {
              var result;
              switch (d.spectype) {
                case "usd":
                case "usi":
                  result = d.target.y;
                  break;
                default:
                  result = d.source.y;
                  break;
              }
              return result;
            });
            link.attr("x2", function (d) {
              var result;
              switch (d.spectype) {
                case "usd":
                case "usi":
                  result = d.source.x;
                  break;
                default:
                  result = d.target.x;
                  break;
              }
              return result;
            });
            link.attr("y2", function (d) {
              var result;
              switch (d.spectype) {
                case "usd":
                case "usi":
                  result = d.source.y;
                  break;
                default:
                  result = d.target.y;
                  break;
              }              
              return result;
            });

            // Original
            //link.attr("x1", d => d.source.x)
            //    .attr("y1", d => d.source.y)
            //    .attr("x2", d => d.target.x)
            //    .attr("y2", d => d.target.y);
          }

          function rectCollide(node) {
            var nodes, sizes, masses;
            var strength = 1;
            var iterations = 1;
            var nodeCenterX;
            var nodeMass;
            var nodeCenterY;

            function force() {

              var node;
              var i = -1;
              while (++i < iterations) { iterate(); }
              function iterate() {
                var quadtree = d3.quadtree(nodes, xCenter, yCenter);
                var j = -1
                while (++j < nodes.length) {
                  node = nodes[j];
                  nodeMass = masses[j];
                  nodeCenterX = xCenter(node);
                  nodeCenterY = yCenter(node);
                  quadtree.visit(collisionDetection);
                }
              }
            }

            function collisionDetection(quad, x0, y0, x1, y1) {
              var updated = false;
              var data = quad.data;
              if (data) {
                if (data.index > node.index) {

                  let xSize = (node.width + data.width) / 2;
                  let ySize = (node.height + data.height) / 2;
                  let dataCenterX = xCenter(data);
                  let dataCenterY = yCenter(data);
                  let dx = nodeCenterX - dataCenterX;
                  let dy = nodeCenterY - dataCenterY;
                  let absX = Math.abs(dx);
                  let absY = Math.abs(dy);
                  let xDiff = absX - xSize;
                  let yDiff = absY - ySize;

                  if (xDiff < 0 && yDiff < 0) {
                    //collision has occurred

                    //separation vector
                    let sx = xSize - absX;
                    let sy = ySize - absY;
                    if (sx < sy) {
                      if (sx > 0) {
                        sy = 0;
                      }
                    } else {
                      if (sy > 0) {
                        sx = 0;
                      }
                    }
                    if (dx < 0) {
                      sx = -sx;
                    }
                    if (dy < 0) {
                      sy = -sy;
                    }

                    let distance = Math.sqrt(sx * sx + sy * sy);
                    let vCollisionNorm = { x: sx / distance, y: sy / distance };
                    let vRelativeVelocity = { x: data.vx - node.vx, y: data.vy - node.vy };
                    let speed = vRelativeVelocity.x * vCollisionNorm.x + vRelativeVelocity.y * vCollisionNorm.y;
                    if (speed < 0) {
                      //negative speed = rectangles moving away
                    } else {
                      var collisionImpulse = 2 * speed / (masses[data.index] + masses[node.index]);
                      if (Math.abs(xDiff) < Math.abs(yDiff)) {
                        //x overlap is less
                        data.vx -= (collisionImpulse * masses[node.index] * vCollisionNorm.x);
                        node.vx += (collisionImpulse * masses[data.index] * vCollisionNorm.x);
                      } else {
                        //y overlap is less
                        data.vy -= (collisionImpulse * masses[node.index] * vCollisionNorm.y);
                        node.vy += (collisionImpulse * masses[data.index] * vCollisionNorm.y);
                      }

                      updated = true;
                    }
                  }
                }
              }
              return updated
            }

            function xCenter(d) {
              return d.x;
            }
            function yCenter(d) {
              return d.y;
            }

            force.initialize = function (_) {
              sizes = (nodes = _).map(function (d) { return [d.width, d.height] })
              masses = sizes.map(function (d) { return d[0] * d[1] })
            };

            force.size = function (_) {
              return (arguments.length
                   ? (size = typeof _ === 'function' ? _ : constant(_), force)
                   : size)
            }

            force.strength = function (_) {
              return (arguments.length ? (strength = +_, force) : strength)
            }

            force.iterations = function (_) {
              return (arguments.length ? (iterations = +_, force) : iterations)
            }

            return force;
          }

          function collide(node) {
            var r = get_radius(node),
                w = get_width(node),
                nx1 = node.x - w / 2,
                nx2 = node.x + w / 2,
                ny1 = node.y - r,
                ny2 = node.y + r * 3;
            try {
              return function (quad, x1, y1, x2, y2) {
                var x = 0,
                    y = 0,
                    l = 0,
                    r = 0;

                if (quad.point && (quad.point !== node)) {
                  x = node.x - quad.point.x;
                  y = node.y - quad.point.y;
                  l = Math.sqrt(x * x + y * y);
                  r = node.radius + quad.point.radius;
                  if (l < r) {
                    l = (l - r) / l * 0.5;
                    node.x -= x *= l;
                    node.y -= y *= l;
                    quad.point.x += x;
                    quad.point.y += y;
                  }
                }
                return (x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1);
              };
            } catch (ex) {
              private_methods.errMsg("collide", ex);
              return false;
            }

          }

          function network_color(d) {
            var col_result = "";
            // col_result = scale(d.group);
            col_result = colrange(d.group);
            return col_result;
          }

          function network_drag(simulation) {
            function dragstarted(event) {
              if (!event.active) simulation.alphaTarget(0.4).restart();
              event.subject.fx = event.subject.x;
              event.subject.fy = event.subject.y;
            }

            function dragged(event) {
              event.subject.fx = event.x;
              event.subject.fy = event.y;
            }

            function dragended(event) {
              if (!event.active) simulation.alphaTarget(0);
              event.subject.fx = null;
              event.subject.fy = null;
            }

            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
          }

          // Return positively
          return true;
        } catch (ex) {
          private_methods.errMsg("draw_network_overlap", ex);
          return false;
        }
      },

      /**
       * draw_network_trans
       *    draw a force-directed network (e.g. medieval text transmission)
       *
       * See: https://observablehq.com/@d3/force-directed-graph
       *
       * node: {id: "Champtercier", group: 1}
       * link: {source: "CountessdeLo", target: "Myriel", value: 1}
       * 
       * @param {type} options
       * @returns {Boolean}
       */
      draw_network_trans: function (options) {
        var svg,      // the SVG element within the DOM that is being used
            svgA,     // Author svg element
            divSvg,   // The target svg div
            divAuthor,
            color,    // D3 color scheme
            factor,
            size = 10,  //Size of each author selection square
            width,
            height,
            watermark = "",
            i,
            count,
            maxcount = 0,
            bDoTransform = true,
            gravityvalue = 100,
            gravityid = "#gravity_trans_value",
            p = {},
            g = null,
            gwm = null,
            author,
            link,
            node;
        const scale = d3.scaleOrdinal(d3.schemeCategory10);

        try {
          // Validate the options
          if (!('nodes' in options && 'links' in options &&
                options['nodes'] !== undefined && options['links'] !== undefined &&
                'target' in options && 'width' in options &&
                'height' in options)) { return false; }

          // Initialize
          loc_simulation = null;
          if ($(gravityid).length > 0) {
            gravityvalue = parseInt($(gravityid).text(), 10);
          }

          // Get parameters
          width = options['width'];
          height = options['height'];
          factor = options['factor'];
          watermark = options['watermark'];

          // Calculate the maxcount
          for (i = 0; i < options['nodes'].length; i++) {
            count = options['nodes'][i]['scount'];
            if (count > maxcount) {
              maxcount = count;
            }
          }

          // Define the SVG element and the color scheme
          divSvg = "#" + options['target'] + " svg";
          $(divSvg).empty();
          svg = d3.select(divSvg);
          // Add a viewbox
          svg.attr("viewBox", [0, 0, width, height])
          svg.attr("width", width)
            .attr("height", height)
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("xmlns:xlink", "http://www.w3.org/1999/xlink")
          color = network_color;
          // Make sure to tie everything under a <g> element
          g = svg.append("g");

          // Append a legend: top center
          private_methods.addLegend({
            'x': 50,          // width / 2,
            'y': 50,          // height - 50,
            'divsvg': divSvg,
            'legend': options['legend']
          });

          // This is based on D3 version *6* !!! (not version 3)
          loc_simulation = d3.forceSimulation(options['nodes'])
              .force("link", d3.forceLink(options['links']).id(function (d) {
                var result;
                // This determines the size of each link
                // Should be: result = d.value * factor;
                result = d.id;
                return result;
              }).distance(function (d) { return 2 * maxcount; })
              )
              // .force("charge", d3.forceManyBody().strength(-100)) // Was: .charge(-100)
              .force("charge", d3.forceManyBody().strength(-1 * gravityvalue))
              .force("center", d3.forceCenter(width / 2, height / 2))
              .force("collide", d3.forceCollide(d => 65).radius(function (d) {
                var scount = d.scount;
                var iSize = Math.max(10, scount / 2);
                return iSize + 1;
              }).iterations(3))
              .on("tick", ticked);

          if (bDoTransform) {
            // Define the zooming
            svg.call(d3.zoom()
              .extent([[0, 0], [width, height]])
              .scaleExtent([0.2, 100])
              .on("zoom", zoomed));
          }

          // Define a d3 function based on the information in 'nodes' and 'links'
          link = g.append("g")
                    .attr("fill", "none")
                    .attr("class", "links")
                    .selectAll("path")
                    .data(options['links'])
                    .join("path")
                    // .attr("stroke", "black")
                    .attr("style", "stroke: #999;")
                    .attr("stroke-width", function (d) {
                      return Math.sqrt(2 * d.value);
                    });
          node = g.append("g")
                    .attr("class", "nodes")
                    .selectAll("g")
                    .data(options['nodes'])
                    .join("g")
                    .call(network_drag(loc_simulation));

          // Add the circle below the <g>
          node.append("circle")
              .attr("r", function (d) {
                var scount = d.scount;
                var iSize = Math.max(10, scount / 2);
                return iSize;
              })
              .attr('fill', color);

          // Add signature to node below the <g>
          node.append("text")
              .attr("x", function (d) {
                var scount = d.scount;
                var iSize = Math.max(10, scount / 2);
                return iSize;
              })
              .attr("y", "0.31em")
              .text(function (d) {
                return d.sig;
              })
              .clone(true).lower()
              .attr("fill", "none")
              .attr("stroke", "white")
              .attr("stroke-width", 3);

          // Add popup title to nodes;
          node.append("title")
            .text(function (d) { return d.label; });
          // Add popup title to links: this provides the actual weight
          link.append("title")
            .text(function (d) { return d.value; });

          // ====================== Author SVG element =========================
          divAuthor = "#" + options['targetA'] + " svg";
          $(divAuthor).empty()
          svgA = d3.select(divAuthor);
          // Add a viewbox
          svgA.attr("viewBox", [0, 0, 2 * width / 10, height])

          // Add a rectangle for each author
          author = svgA.append("g")
              .selectAll("g")
              .data(options['authors'])
              .join("g");


          // Add a rectangle for each author
          author.append("rect").attr("x", 5)
              .attr("y", function (d, i) { return 50 + i * (size + 5); })
              .attr("width", size).attr("height", size)
              .style("fill", function (d) {
                return network_color(d);
              });

          // Add a name (legend) for each author
          author.append("text")
                .attr("x", 5 + size * 1.2)
                .attr("y", function (d, i) { return 50 + i * (size + 5) + (size ) }) // 50 is where the first dot appears. 25 is the distance between dots
                .style("fill", function (d) {
                  return network_color(d);
                })
                .text(function (d) {
                  return d.category + " (" + d.count + ")";
                })
                .attr("text-anchor", "left")
                .style("alignment-baseline", "middle");

          // Now add the watermark
          gwm = svg.append("g");
          gwm.attr("class", "watermark-main")
             .attr("transform", "translate(" + width / 2 + "," + (height - 33) + ") scale(2.0)");
          $(".watermark-main").html(watermark);

          // ====================== HELP FUNCTIONS =============================
          // Defind the 'zoomed' function
          function zoomed(event) {
            // Get the transform
            var transform = event.transform;
            var scale = event.transform.k;

            // THis is geometric re-scale:
            // (but note: CSS prevents lines from scaling)
            g.attr("transform", event.transform);

            link.style("stroke-width", function (d) {
              return Math.sqrt(2 * d.value) / scale;
            });

            // Make sure that the circle retain their size by dividing by the scale factor
            node.selectAll("circle")
              .attr("r", function (d) {
                var scount = d.scount;
                var iSize = Math.max(10, scount / 2);
                return iSize / scale;
              })
              .attr("stroke-width", function (d) {
                return 3 / scale;
              });
            node.selectAll("text")
              .attr("x", function (d) {
                var scount = d.scount;
                var iSize = Math.max(10, scount / 2);
                return iSize / scale;
              })
              .style("font-size", function (d) {
                var iSize = Math.round(14 / scale);
                return (scale < 1) ? "14px" : iSize.toString() + "px";
              });

          }

          // Define the 'ticked' function
          function ticked() {
            node.attr("transform", function (d) {
              var radius = 10, ix, iy;
              if (d.scount !== undefined) { radius = Math.max(10, d.scount / 2); }
              ix = Math.max(radius, Math.min(width - radius, d.x));
              iy = Math.max(radius, Math.min(height - radius, d.y));
              return `translate(${ix},${iy})`
            });
 
            link.attr("d", linkArc);
          }

          function network_color(d) {
            var col_result = "";
            //if (d.category > 1) {
            //  col_result = "aap";
            //}
            col_result = scale(d.category);
            return col_result;
          }

          function linkArc(d) {
            const r = Math.hypot(d.target.x - d.source.x, d.target.y - d.source.y);
            return `M${d.source.x},${d.source.y} A${r},${r} 0 0,1 ${d.target.x},${d.target.y}`;
          }

          function network_drag(simulation) {
            function dragstarted(event) {
              if (!event.active) simulation.alphaTarget(0.4).restart();
              event.subject.fx = event.subject.x;
              event.subject.fy = event.subject.y;
            }

            function dragged(event) {
              event.subject.fx = event.x;
              event.subject.fy = event.y;
            }

            function dragended(event) {
              if (!event.active) simulation.alphaTarget(0);
              event.subject.fx = null;
              event.subject.fy = null;
            }

            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
          }


          // Return positively
          return true;
        } catch (ex) {
          private_methods.errMsg("draw_network_trans", ex);
          return false;
        }
      },

      errMsg: function (sMsg, ex, bNoCode) {
        var sHtml = "",
            bCode = true;

        // Check for nocode
        if (bNoCode !== undefined) {
          bCode = not(bNoCode);
        }
        // Replace newlines by breaks
        sMsg = sMsg.replace(/\n/g, "\n<br>");
        if (ex === undefined) {
          sHtml = "Error: " + sMsg;
        } else {
          sHtml = "Error in [" + sMsg + "]<br>" + ex.message;
        }
        sHtml = "<code>" + sHtml + "</code>";
        console.log(sHtml);
        $("#" + loc_divErr).html(sHtml);
      },

      errClear: function () {
        $("#" + loc_divErr).html("");
        loc_bExeErr = false;
      },

      mainWaitStart : function() {
        var elWait = $(".main-wait").first();
        if (elWait !== undefined && elWait !== null) {
          $(elWait).removeClass("hidden");
        }
      },

      mainWaitStop: function () {
        var elWait = $(".main-wait").first();
        if (elWait !== undefined && elWait !== null) {
          $(elWait).addClass("hidden");
        }
      },

      /*
       * sticky_switch - switch visualization
       */
      sticky_switch: function (elStart) {
        var sStatus = "",
            divNetwork = "";

        try {
          // Figure out what course of action to take
          if ($(elStart).hasClass("sticky-visualization")) {
            // Need to do switching on/off
            if ($(elStart).hasClass("jumbo-1")) {
              // Close all visualizations
              $(".sticky-visualization").each(function (idx, el) {

                // Switch off everything
                $(el).addClass("jumbo-1");
                $(el).removeClass("jumbo-2");
                // Close the network area
                $($(el).attr("data-target")).addClass("hidden");
              });
              // Show that the button has been clicked
              $(elStart).removeClass("jumbo-1");
              $(elStart).addClass("jumbo-2");
              sStatus = "continue";
            } else {
              // We are switching OFF
              $(elStart).addClass("jumbo-1");
              $(elStart).removeClass("jumbo-2");
              // Now CLOSE this visualization
              divNetwork = $(elStart).attr("data-target");
              $(divNetwork).addClass("hidden");
              // And leave
              sStatus = "leave";
            }
          }
          // REturn the status
          return sStatus;
        } catch (ex) {
          private_methods.errMsg("sticky_switch", ex);
        }
      },

      waitInit: function (el) {
        var elResPart = null,
            elWait = null;

        try {
          // Set waiting div
          elResPart = $(el).closest(".research_part");
          if (elResPart !== null) {
            elWait = $(elResPart).find(".research-fetch").first();
          }
          return elWait;
        } catch (ex) {
          private_methods.errMsg("waitInit", ex);
        }
      },

      waitStart: function(el) {
        if (el !== null) {
          $(el).removeClass("hidden");
        }
      },

      waitStop: function (el) {
        if (el !== null) {
          $(el).addClass("hidden");
        }
      }


    }

    // Public methods
    return {

      /**
       *  codico_toggle
       *      Sermon enters codico
       *
       */
      codico_dragenter: function (ev) {
        var divSrcId = "";

        try {
          // Prevent default handling
          ev.preventDefault();

          if ($(ev.target).hasClass("codico-target")) {
            divSrcId = ev.dataTransfer.getData("text");
            $(ev.target).addClass("dragover");
          }
        } catch (ex) {
          private_methods.errMsg("codico_dragenter", ex);
        }
      },

      /**
       *  codico_dragleave
       *      Sermon leaves this codico
       *
       */
      codico_dragleave: function (ev) {
        var divSrcId = "";

        try {
          // Prevent default handling
          ev.preventDefault();

          if ($(ev.target).hasClass("codico-target")) {
            divSrcId = ev.dataTransfer.getData("text");
            $(ev.target).removeClass("dragover");
          }
        } catch (ex) {
          private_methods.errMsg("codico_dragleave", ex);
        }
      },

      /**
       *  codico_drag
       *      Codico starts being dragged
       *
       */
      codico_drag: function (ev) {
        var elTable = null,
            divId = "";

        try {
          elTable = $(ev.target).closest("table");
          divId = $(elTable).attr("id");

          ev.dataTransfer.setData("text", divId);
        } catch (ex) {
          private_methods.errMsg("codico_drag", ex);
        }
      },

      /**
       *  codico_drop
       *      Sermon gets dropped into a (different) codico
       *
       */
      codico_drop: function (ev) {
        var elTable = null,
            elRoot = null,
            bChanged = false,
            orderSrc = "",
            orderDst = "",
            divSrc = null,  // The div.codico-unit
            divDst = null,  // THe div.codico-unit
            divSrcId = "",
            divDstId = "";

        try {
          // Prevent default handling
          ev.preventDefault();

          if ($(ev.target).hasClass("codico-target")) {
            // Remove the dragover class
            $(ev.target).removeClass("dragover");

            // Figure out what the source and destination is
            divSrcId = ev.dataTransfer.getData("text");
            elTable = $(ev.target).closest("table");
            divDstId = $(elTable).attr("id");
            elRoot = $(elTable).closest(".codico-list");

            // Do not move to myself:
            if (divSrcId === divDstId) {
              // We don't do anything
            } else {
              // Find out what the order values are
              orderSrc = parseInt( $("table[id=" + divSrcId + "] .codico-target").first().text().trim(), 10);
              orderDst = parseInt($("table[id=" + divDstId + "] .codico-target").first().text().trim(), 10);
              // Make sure we don't move just one down, because that doesn't work
              if (orderSrc !== (orderDst - 1)) {
                // The target is correct!!! 
                divSrc = $("table[id=" + divSrcId + "]").closest(".codico-unit");
                divDst = $("table[id=" + divDstId + "]").closest(".codico-unit");
                // Put the [divSrc] *right before* the [divDst]
                $(divSrc).insertBefore(divDst);

                // Indicate that changes have been made
                bChanged = true;
              }
            }

            // What if change happened?
            if (bChanged) {
              // Show the SAVE and RESTORE buttons
              $("#save_section").removeClass("hidden");
              // Now re-number the codicological unites + make sure that 
              private_methods.codico_renumber(elRoot);
            }
          }

        } catch (ex) {
          private_methods.errMsg("codico_drop", ex);
        }
      },

      /**
       *  codico_remove
       *      Remove this codico unit
       *
       */
      codico_remove: function (elThis) {
        var elTr = null,
            elRoot = null;

        try {
          // Find the right row to remove
          elTr = $(elThis).closest(".codico-unit");
          elRoot = $(elTr).closest(".codico-list");
          // Make sure the save button is visible
          $("#save_section").removeClass("hidden");
          // Remove it
          $(elTr).remove();
          // Now re-number the codicological unites
          private_methods.codico_renumber(elRoot);
        } catch (ex) {
          private_methods.errMsg("codico_remove", ex);
        }
      },

      /**
       *  codico_process
       *      Process one or more codico's of a manuscript
       *
       */
      codico_process: function (elStart, codico_type) {
        var elForm = null,
            targeturl = "",
            elRoot = null,
            hList = null,
            data = null;

        try {
          // Get to the form
          elForm = $(elStart).closest("form").first();
          elRoot = $(".codico-list").first();
          // check for saving
          if (codico_type !== undefined && codico_type === "save") {
            // 'Read' the current hierarchy...
            hList = private_methods.codico_hlisttree(elRoot);
            // Set the <input> value to return the contents of [hList]
            $("#id_mrec-codicolist").val(JSON.stringify(hList));
          }
          // Submit it
          $(elForm).submit();
        } catch (ex) {
          private_methods.errMsg("codico_process", ex);
        }
      },

      /**
       *  codico_toggle
       *      Toggle visibility of codico units by class
       *
       */
      codico_toggle: function (elThis, target) {
        var elBody = null,
            sClass = "";

        try {
          elBody = $(elThis).closest("div.panel-body").first();
          sClass = "." + target;
          // Double check
          if ($(elBody).find(sClass).first().hasClass("hidden")) {
            // Need to show them
            $(elBody).find(sClass).removeClass("hidden");
          } else {
            // Need to hide them
            $(elBody).find(sClass).addClass("hidden");
          }
        } catch (ex) {
          private_methods.errMsg("codico_toggle", ex);
        }
      },

      /**
       *  do_new_sermon
       *      Open up the possibility to add a new sermon
       *
       */
      do_new_sermon: function (divname) {
        var elStart = null;

        try {
          elStart = $("#" + divname).closest("div");
          if (elStart !== null) {
            if ($(elStart).hasClass("hidden")) {
              $(elStart).removeClass("hidden");
            } else {
              $(elStart).addClass("hidden");
            }
          }

        } catch (ex) {
          private_methods.errMsg("do_new_sermon", ex);
        }
      },

      /**
       * postsubmit
       *    Submit nearest form as POST
       *
       */
      postsubmit: function (el) {
        var frm = null;

        try {
          frm = $(el).closest("form");
          // Make sure we do a POST
          frm.attr("method", "POST");
          // Submit
          $(frm).submit();
        } catch (ex) {
          private_methods.errMsg("postsubmit", ex);
        }
      },

      /**
       *  init_charts
       *      Check if this is the homepage and then supply charts
       *
       */
      init_charts: function () {
        var charts = ['canwit', 'austat', 'manu'],
            elStart = null,
            divid = null,
            data = null,
            ptype = "",
            i = 0;
        try {

          // Check if this is the HOME Page, for which the pie charts need to be drawn
          for (i = 0; i < charts.length; i++) {
            ptype = charts[i];
            divid = "pie_" + ptype;
            elStart = "#" + divid;
            if ($(elStart).length > 0 && g_pie_data !== undefined && ptype in g_pie_data) {
              data = g_pie_data[ptype];
              private_methods.draw_pie_chart(divid, data);
            }
          }

         } catch (ex) {
          private_methods.errMsg("init_charts", ex);
        }
      },

      /**
       *  init_events
       *      Bind main necessary events
       *
       */
      init_events: function (sUrlShow) {
        var lHtml = [],
            elA = null,
            object_id = "",
            targetid = null,
            post_loads = [],
            options = {},
            sHtml = "";

        try {
          // See if there are any post-loads to do
          $(".post-load").each(function (idx, value) {
            var targetid = $(this);
            post_loads.push(targetid);
            // Remove the class
            $(targetid).removeClass("post-load");
          });

          // No closing of certain dropdown elements on clicking
          $(".dropdown-toggle").on({
            "click": function (event) {
              var evtarget = $(event.target);
              if ($(evtarget).closest(".nocloseonclick")) {
                $(this).data("closable", false);
              } else {
                $(this).data("closable", true);
              }
            }
          });

          // Now address all items from the list of post-load items
          post_loads.forEach(function (targetid, index) {
            var data = [],
                lst_ta = [],
                i = 0,
                targeturl = $(targetid).attr("targeturl");

            // Load this one with a GET action
            $.get(targeturl, data, function (response) {
              // Remove the class
              $(targetid).removeClass("post-load");

              // Action depends on the response
              if (response === undefined || response === null || !("status" in response)) {
                private_methods.errMsg("No status returned");
              } else {
                switch (response.status) {
                  case "ok":
                    // Show the result
                    $(targetid).html(response['html']);
                    // Call initialisation again
                    ru.lila.seeker.init_events(sUrlShow);
                    // Handle type aheads
                    if ("typeaheads" in response) {
                      // Perform typeahead for these ones
                      ru.lila.init_event_listeners(response.typeaheads);
                    }
                    break;
                  case "error":
                    // Show the error
                    if ('msg' in response) {
                      $(targetid).html(response.msg);
                    } else {
                      $(targetid).html("An error has occurred (lila.seeker post_loads)");
                    }
                    break;
                }
              }

            });
          });

          //options = { "templateSelection": ru.lila.ssg_template };
          //$(".django-select2.select2-ssg").djangoSelect2(options);
          //$(".django-select2.select2-ssg").select2({
          //  templateSelection: ru.lila.ssg_template
          //});
          //$(".django-select2.select2-ssg").on("select2:select", function (e) {
          //  var sId = $(this).val(),
          //      sText = "",
          //      sHtml = "",
          //      idx = 0,
          //      elOption = null,
          //      elRendered = null;

          //  elRendered = $(this).parent().find(".select2-selection__rendered");
          //  sHtml = $(elRendered).html();
          //  idx = sHtml.indexOf("</span>");
          //  if (idx > 0) {
          //    idx += 7;
          //    sText = sHtml.substring(idx);
          //    if (sText.length > 50) {
          //      sText = sText.substring(0, 50) + "...";
          //      sHtml = sHtml.substring(0, idx) + sText;
          //      $(elRendered).html(sHtml);
          //    }
          //  }
          //});

          // NOTE: only treat the FIRST <a> within a <tr class='add-row'>
          $("tr.add-row").each(function () {
            elA = $(this).find("a").first();
            $(elA).unbind("click");
            $(elA).click(ru.lila.seeker.tabular_addrow);
          });
          // Bind one 'tabular_deletrow' event handler to clicking that button
          $(".delete-row").unbind("click");
          $('tr td a.delete-row').click(ru.lila.seeker.tabular_deleterow);

          // Bind the click event to all class="ajaxform" elements
          $(".ajaxform").unbind('click').click(ru.lila.seeker.ajaxform_click);

          $(".ms.editable a").unbind("click").click(ru.lila.seeker.manu_edit);
          $(".srm.editable a").unbind("click").click(ru.lila.seeker.sermo_edit);

          // Show URL if needed
          if (loc_urlStore !== undefined && loc_urlStore !== "") {
            // show it
            window.location.href = loc_urlStore;
          } else if (sUrlShow !== undefined && sUrlShow !== "") {
            // window.location.href = sUrlShow;
            // history.pushState(null, null, sUrlShow);
          }

          // Set handling of unique-field
          $("td.unique-field input").unbind("change").change(ru.lila.seeker.unique_change);

          // Make sure typeahead is re-established
          ru.lila.init_event_listeners();
          ru.lila.init_typeahead();

          // Switch filters
          $(".badge.filter").unbind("click").click(ru.lila.seeker.filter_click);

          // Make modal draggable
          $(".modal-header, modal-dragpoint").on("mousedown", function (mousedownEvt) {
            var $draggable = $(this),
                x = mousedownEvt.pageX - $draggable.offset().left,
                y = mousedownEvt.pageY - $draggable.offset().top;

            $("body").on("mousemove.draggable", function (mousemoveEvt) {
              $draggable.closest(".modal-dialog").offset({
                "left": mousemoveEvt.pageX - x,
                "top": mousemoveEvt.pageY - y
              });
            });
            $("body").one("mouseup", function () {
              $("body").off("mousemove.draggable");
            });
            $draggable.closest(".modal").one("bs.modal.hide", function () {
              $("body").off("mousemove.draggable");
            });
          });

          //// Any other draggables
          //$(".draggable").draggable({
          //  cursor: "move",
          //  snap: ".draggable",
          //  snapMode: "inner",
          //  snapTolerance: 20
          //});

         } catch (ex) {
          private_methods.errMsg("init_events", ex);
        }
      },

      /**
       * comment_send
       *    Send a user-comment to the server
       * 
       * @param {DOM} elStart
       */
      comment_send: function (elStart) {
        var frm = null,
            data = null,
            divList = "#comment_list",
            divContent = "#id_com-content",
            targeturl = null,
            comment_list = null,
            target = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Get the data from the form
          data = frm.serializeArray();
          // The url is in the ajaxurl
          targeturl = $(elStart).attr("ajaxurl");

          // Call the ajax POST method
          // Issue a post
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "ok":
                  // Try to get the (adapted) list of comments
                  comment_list = response.comment_list;
                  if (comment_list !== undefined && comment_list !== null && comment_list.length > 0) {
                    // There actually *is* a list!
                    $(divList).html(comment_list);
                  }
                  // Clear the previously made comment
                  $(divContent).val("");
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(target).html(response.msg);
                  } else {
                    $(target).html("An error has occurred (lila.seeker comment_send)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("comment_send", ex);
        }
      },

      /**
       *  manusermo
       *      Visibility buttons for sermons within a manuscript
       *
       */
      manusermo: function (elThis, target) {
        var elTree = "#sermon_tree",
            cls = ".manusermo." + target;

        try {
          // CHeck if we need to switch visibility on or off
          if ($(elTree).find(cls).first().hasClass("hidden")) {
            // It is hidden, we must show them
            $(elTree).find(cls).removeClass("hidden");
            // Make sure the color of the button is right
            $(elThis).removeClass("jumbo-1");
            $(elThis).removeClass("jumbo-2");
            $(elThis).addClass("jumbo-2");
          } else {
            // It is shown, we must hide them
            $(elTree).find(cls).addClass("hidden");
            // Make sure the color of the button is right
            $(elThis).removeClass("jumbo-1");
            $(elThis).removeClass("jumbo-2");
            $(elThis).addClass("jumbo-1");
          }

        } catch (ex) {
          private_methods.errMsg("manusermo", ex);
        }
      },

      /**
       *  sermon_drag
       *      Starting to drag: keep track of the divId that is being dragged.
       *
       */
      sermon_drag: function (ev) {
        var elTree = null,
            divId = "",
            sermontype = "",  // can be 'sermon' or 'head'
            sermonid = "";
        try {
          elTree = $(ev.target).closest(".tree");
          sermonid = $(elTree).attr("sermonid");
          divId = $(elTree).attr("id");

          ev.dataTransfer.setData("text", divId);
        } catch (ex) {
          private_methods.errMsg("sermon_drag", ex);
        }
      },

      /**
       *  sermon_dragenter
       *      Entering a region where dropping is possible
       *
       */
      sermon_dragenter: function (ev) {
        var elTree = null,
            divSrcId = null,
            divDstId = null,
            divSrc = null,
            sermonid = "";
        try {
          // Prevent default handling
          ev.preventDefault();

          // Figure out what the source and destination is
          elTree = $(ev.target).closest(".tree");
          divDstId = $(elTree).attr("id");
          divSrcId = ev.dataTransfer.getData("text");
          if (divSrcId !== "") {
            // Nothing yet
            divSrc = $("#sermon_tree").find("#" + divSrcId);

            if (divDstId === "sermon_new" && $(divSrc).attr("sermontype") !== "head") {
              // This is not allowed
              return;
            } else if (divSrcId === "codico_break" && !$(ev.target).hasClass("ruler")) {
              // Destination may only be a ruler between sermons
              return;
            } else if (divDstId.indexOf("codi") >= 0) {
              // Destination may *not* be a codico rulder
              return;
            }
          }

          if (ev.target.nodeName.toLowerCase() === "td" && $(ev.target).hasClass("ruler")) {
            //$(ev.target).addClass("dragover");
            $(ev.target).addClass("ruler_black");
            $(ev.target).removeClass("ruler_white");
            // make row larger
            $(ev.target).parent().addClass("ruler_show");
          } else {
            $(ev.target).closest("td").addClass("dragover");
            $(ev.target).addClass("dragover");
          }
        } catch (ex) {
          private_methods.errMsg("sermon_dragenter", ex);
        }
      },

      /**
       *  sermon_dragleave
       *      Leaving...
       *
       */
      sermon_dragleave: function (ev) {
        var elTree = null, sermonid = "";
        try {
          $("#sermon_tree .dragover").removeClass("dragover");
          $("#sermon_tree .ruler").removeClass("ruler_black");
          $("#sermon_tree .ruler").addClass("ruler_white");
          $("#sermon_tree .ruler_show").removeClass("ruler_show");
        } catch (ex) {
          private_methods.errMsg("sermon_dragleave", ex);
        }
      },

      /**
       *  sermon_drop
       *      What happens when a sermon is dropped here?
       *
       */
      sermon_drop: function (ev) {
        var elTree = null,
            divSrcId = "",
            divDstId = "",
            divHierarchy = "#sermon_hierarchy_element",
            divSrc = null,
            divDst = null,
            divCodi = null,
            divParent = null,
            bChanged = false,
            level = 0,
            target_under_source = false,
            type = "under",
            sermonid = "";
        try {
          // Prevent default handling
          ev.preventDefault();

          // Figure out what the source and destination is
          elTree = $(ev.target).closest(".tree");
          divSrcId = ev.dataTransfer.getData("text");
          divDstId = $(elTree).attr("id");

          // Reset the class of the drop element
          $("#sermon_tree .dragover").removeClass("dragover");
          $("#sermon_tree .ruler").removeClass("ruler_black");
          $("#sermon_tree .ruler").addClass("ruler_white");
          $("#sermon_tree .ruler_show").removeClass("ruler_show");

          // Prevent foul-play
          if (divSrcId == "sermon_new" && divDstId.indexOf("sermon_new") >= 0) {
            // Get out of here
            return;
          } else if (divSrcId.indexOf("codi") >= 0 && !$(ev.target).hasClass("ruler")) {
            return;
          }

          // Find the actual source div
          if (divSrcId === "sermon_new") {
            // Create a new element
            divSrc = $(divHierarchy).clone(true);
            // Adapt the @id field
            loc_newSermonNumber += 1;
            divSrcId = "sermon_new_" + loc_newSermonNumber;
            $(divSrc).attr("id", divSrcId);
            // Make a good @sermonid field to be sent to the caller
            $(divSrc).attr("sermonid", "new_" + loc_newSermonNumber);
            // Set the text for 'tussenkopje'
            $(divSrc).find(".sermon-new-head").first().html('<div id="id_shead-' + loc_newSermonNumber + '" name="shead-' +
              loc_newSermonNumber + '" contenteditable="true">(Structural element)</div>');
            // Add a sermon number
            $(divSrc).find(".sermonnumber").first().html("<span>H-" + loc_newSermonNumber + "</span>")
            // Make sure the new element becomes visible
            $(divSrc).removeClass("hidden");
          } else {
            divSrc = $("#sermon_tree").find("#" + divSrcId);
            if (divDstId === "sermon_new") {
              if ($(divSrc).attr("sermontype") === "head") {
                type = "struct_del"; // Remove structural head
              } else {
                // This is not allowed
                return;
              }
            }
          }
          // The destination - that is me myself
          divDst = elTree;

          // Do we need to put the source "under" the destination or "before" it?
          if ($(ev.target).hasClass("ruler")) {
            if ($(divSrc).hasClass("codi-start") || $(divSrc).children(".codi-start").length > 0) {
              type = "below";
            } else {
              type = "before";
            }
          }

          // Action now depends on the type
          switch (type) {
            case "under":   // Put src under div dst
              // check for target under source -- that is not allowed
              target_under_source = ($(divSrc).find("#" + divDstId).length > 0);

              // Check if the target is okay to go to
              if (divSrcId !== divDstId && !target_under_source) {

                // Move source *UNDER* the destination
                divDst.append(divSrc);
                // Get my dst level
                level = parseInt($(divDst).attr("level"), 10);
                level += 1;
                $(divSrc).attr("level", level.toString());

                // Check if my parent already has a plus sign showing
                $(divDst).children("table").find(".sermonbutton").html('<span class="glyphicon glyphicon-plus"></span>');
                $(divDst).children("table").find(".sermonbutton").attr("onclick", "ru.lila.seeker.sermon_level(this);");

                // Signal we have changed
                bChanged = true;
              } else {
                console.log("not allowed to move from " + divSrcId + " to UNDER " + divDstId);
              }
              break;
            case "before":  // Put src before div dst
              // Validate
              if (divSrcId === divDstId) {
                console.log("Cannot move me " + divSrcId + " before myself " + divDstId);
              } else {
                // Move source *BEFORE* the destination
                divSrc.insertBefore(divDst);
                // Adapt my level to the one before me
                $(divSrc).attr("level", $(divDst).attr("level"));
                // Possible adaptations if [divDst] starts a new codico section
                if (divSrcId.indexOf("sermon_new") === 0 && $(divDst).children(".codi-start").length > 0) {
                  // Need to move the [.codi-start] to myself...
                  $(divSrc).prepend($(divDst).children(".codi-start").first());
                }

                // SIgnal change
                bChanged = true;
              }
              break;
            case "below": // Put src inside the divDst, but not in the table
              if (divSrcId === divDstId) {
                console.log("Cannot move me " + divSrcId + " before myself " + divDstId);
              } else {
                // Make sure we know what the codi is
                divCodi = divSrc;
                if (!divCodi.hasClass("codi-start")) {
                  divCodi = $(divSrc).find(".codi-start").first();
                }
                // Move source inside the destination
                $(divDst).prepend(divCodi);
                // SIgnal change
                bChanged = true;
              }
              break;
            case "struct_del":  // Remove a structural head
              // This is a structural head that is being removed

              // This means: 
              // (1) all 'children' of the structure element must become 'children' of the structure element's 'parent'
              // (1a) get my parent
              divParent = $(divSrc).parent();
              // (1b) walk all .tree descendants and decrease the level
              $(divSrc).find(".tree").each(function (idx, el) {
                level = parseInt($(el).attr("level"), 10);
                level -= 1;
                $(el).attr("level", level.toString());
              });
              // (1c) walk all my children and set their different parent
              $(divSrc).children(".tree").each(function (idx, el) {
                divParent.append(el);
              });

              // (2) Hide the structural element
              $(divSrc).addClass("hidden");

              // Signal we have changed
              bChanged = true;
              break;
          }

          // What if change happened?
          if (bChanged) {
            // Show the SAVE and RESTORE buttons
            $("#sermon_tree").find(".edit-mode").removeClass("hidden");
          }
        } catch (ex) {
          private_methods.errMsg("sermon_drop", ex);
        }
      },

      /**
       * sermon_locus
       *    Calculate the locus of this Codhead element
       * 
       * @param {el} elThis
       * @returns {bool}
       */
      sermon_locus: function (elThis) {
        var elCode = null,
            elChildFirst = null,
            elChildLast = null,
            sLocusFirst = "",
            sLocusLast = "",
            arLocusFirst = null,
            arLocusLast = null,
            sLocus = "";

        try {
          // Determine where the code element is
          elCode = $(elThis).closest("td").find("code").first();
          // Find first and last child .tree elements
          elChildFirst = $(elThis).closest(".tree").children(".tree").first();
          elChildLast = $(elThis).closest(".tree").children(".tree").last();
          // Get the first code
          sLocusFirst = $(elChildFirst).find("code.draggable").first().text()
          sLocusLast = $(elChildLast).find("code.draggable").first().text()
          // Calculate the range
          arLocusFirst = sLocusFirst.split(/–|-/);
          sLocus = arLocusFirst[0];
          arLocusLast = sLocusLast.split(/–|-/);
          sLocus = sLocus + "-" + ((arLocusLast.length == 1) ? arLocusLast[0] : arLocusLast[1]);

          // Store the code where it belongs
          $(elCode).html(sLocus);

          // Show the SAVE and RESTORE buttons
          $("#sermon_tree").find(".edit-mode").removeClass("hidden");

          // Return okay
          return true;
        } catch (ex) {
          private_methods.errMsg("sermon_locus", ex);
          return false;
        }
      },

      /**
       * sermon_change
       *    Signal that changes need to be stored
       * 
       * @param {el} elThis
       * @returns {bool}
       */
      sermon_change: function (elThis) {
        try {

          // Show the SAVE and RESTORE buttons
          $("#sermon_tree").find(".edit-mode").removeClass("hidden");

          // Return okay
          return true;
        } catch (ex) {
          private_methods.errMsg("sermon_change", ex);
          return false;
        }
      },

      /**
       * unique_change
       *    Make sure only one input box is editable
       *
       */
      init_select2: function (elName) {
        var select2_options = null,
            i = 0,
            elDiv = "#" + elName,
            oRow = null;

        try {
          for (i = 0; i < lAddTableRow.length; i++) {
            oRow = lAddTableRow[i];
            if (oRow['table'] === elName) {
              if ("select2_options" in oRow) {
                select2_options = oRow['select2_options'];
                // Remove previous .select2
                $(elDiv).find(".select2").remove();
                // Execute djangoSelect2()
                $(elDiv).find(".django-select2").djangoSelect2(select2_options);
                return true;
              }
            }
          }
          return false;
        } catch (ex) {
          private_methods.errMsg("init_select2", ex);
          return false;
        }
      },

      /**
       * unique_change
       *    Make sure only one input box is editable
       *
       */
      unique_change: function () {
        var el = $(this),
            elTr = null;

        try {
          elTr = $(el).closest("tr");
          $(elTr).find("td.unique-field").find("input").each(function (idx, elInput) {
            if ($(el).attr("id") !== $(elInput).attr("id")) {
              $(elInput).prop("disabled", true);
            }
          });
  
        } catch (ex) {
          private_methods.errMsg("unique_change", ex);
        }
      },

      /**
       * filter_click
       *    What happens when clicking a badge filter
       *
       */
      filter_click: function (el) {
        var target = null,
            specs = null;

        try {
          target = $(this).attr("targetid");
          if (target !== undefined && target !== null && target !== "") {
            target = $("#" + target);
            // Action depends on checking or not
            if ($(this).hasClass("on")) {
              // it is on, switch it off
              $(this).removeClass("on");
              $(this).removeClass("jumbo-3");
              $(this).addClass("jumbo-1");
              // Must hide it and reset target
              $(target).addClass("hidden");

              // Check if target has a targetid
              specs = $(target).attr("targetid");
              if (specs !== undefined && specs !== "") {
                // Reset related badges
                $(target).find("span.badge").each(function (idx, elThis) {
                  var subtarget = "";

                  $(elThis).removeClass("on");
                  $(elThis).removeClass("jumbo-3");
                  $(elThis).removeClass("jumbo-2");
                  $(elThis).addClass("jumbo-1");
                  subtarget = $(elThis).attr("targetid");
                  if (subtarget !== undefined && subtarget !== "") {
                    $("#" + subtarget).addClass("hidden");
                  }
                });
                // Re-define the target
                target = $("#" + specs);
              } 

              $(target).find("input").each(function (idx, elThis) {
                $(elThis).val("");
              });
              // Also reset all select 2 items
              $(target).find("select").each(function (idx, elThis) {
                $(elThis).val("").trigger("change");
              });

            } else {
              // Must show target
              $(target).removeClass("hidden");
              // it is off, switch it on
              $(this).addClass("on");
              $(this).removeClass("jumbo-1");
              $(this).addClass("jumbo-3");
            }

          }
        } catch (ex) {
          private_methods.errMsg("filter_click", ex);
        }
      },

      /**
       * scount_histogram_show
       *    Show histogram using D3
       *
       *  The data is expected to be: 'count', 'freq'
       *
       */
      scount_histogram_show: function (lst_data, divid) {
        var margin = null,
            width = null,
            height = null,
            parseDate = null,
            data = [],
            x = null,
            y = null,
            i = 0,
            max_scount = 0,
            max_freq = 0,
            freq = 0,
            targeturl = null,
            found = null,
            xAxis = null,
            yAxis = null,
            histo = null,
            oBin = null,
            viewbox = "",
            bins = null,
            tooltip = null, showTooltip=null, moveTooltip = null, hideTooltip = null,
            svg = null;

        try {
          // Set the margin, width and height
          margin = { top: 20, right: 20, bottom: 30, left: 50 }
          width = 960 - margin.left - margin.right;
          height = 500 - margin.top - margin.bottom;
          viewbox = "0 0 970 510";

          // Create an SVG top node
          svg = d3.select("#" + divid).append("svg")
            //.attr("width", "100%").attr("height", "100%")
            //.attr("viewBox", viewbox)
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("xmlns:xlink", "http://www.w3.org/1999/xlink")
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

          // Calculate the maximum [scount] and the maximum [freq]
          max_scount = d3.max(lst_data, function (d) { return +d.scount });
          max_freq = d3.max(lst_data, function (d) { return +d.freq });

          // Set up the x scale
          x = d3.scaleLinear().domain([0, max_scount+1]).range([0, width]);

          // Convert the lst_data into data bins
          for (i = 0; i <= max_scount; i++) {
            // Find out what the frequency is
            found = lst_data.find(function (el) {
              return (el.scount == i);
            });
            if (found === undefined) {
              found = {scount: i, freq: 0};
            }

            // Append frequency to one-dimensional array
            targeturl = ('targeturl' in found) ? found.targeturl : '#';
            data.push({ x1: i + 1, x0: found.scount, length: found.freq, targeturl: targeturl });
          }

          // Set the histogram parameter
          histo = d3.histogram()
            .value(function (d) { return +d.freq; })
            .domain(x.domain())
            .thresholds(x.ticks(max_scount));

          //Apply the function to data to get the bins
          //bins = histo(data);
          // bins = histo(lst_data);
          bins = data

          // Y axis: scale
          y = d3.scaleLinear().range([height, 0]);
          y.domain([0, d3.max(bins, function (d) { return d.length; })]);

          // Draw X axis
          svg.append("g").attr("class", "x axis").attr("transform", "translate(0," + height + ")")
            .call(d3.axisBottom(x))
            .append("text").attr("y", 30).attr("x", width - 100).text("Sermons per SSG");

          // Draw Y axis
          svg.append("g").attr("class", "y axis")
            .call(d3.axisLeft(y))
            .append("text")
              .attr("transform", "rotate(-90)")
              .attr("y", -40)
              .attr("dy", ".71em")
              .style("text-anchor", "end")
              .text("SSG frequency");

          // Add a tooltip <div>
          tooltip = d3.select("#" + divid)
            .append("div").attr("class", "tooltip").style("opacity", 0);

          // Tooltip data respond function
          showTooltip = function (event, d) {
            tooltip.transition().duration(100).style("opacity", 0.9);
            tooltip.html(d.length + " SSGs have a set of " + d.x0 + " sermon(s)")
              .style("left", (event.x + 10 ) + "px")
              .style("top", (event.y - 35) + "px");
          };
          // Make sure the tooltip shows about where the user hovers
          moveTooltip = function (event, d) {
            tooltip.style("left", (event.x + 10) + "px")
                   .style("top", (event.y - 35) + "px");
          };
          // Change the opacity again
          hideTooltip = function (event, d) {
            tooltip.transition().duration(300).style("opacity", 0);
          };

          // Append the bar rectangles to the SVG element
          svg.selectAll("rect").data(bins).enter()
              .append("g")
              .append("a").attr("href", function (d) { return d.targeturl; })
              .append("rect")
                .attr("x", 1)
                .attr("transform", function (d) { return "translate(" + x(d.x0) + "," + y(d.length) + ")"; })
                .attr("width", function (d) { return x(d.x1) - x(d.x0) - 1; })
                .attr("height", function (d) { return height - y(d.length); })
                .attr("class", "histogram-bar")
                .attr("tabindex", 0)
                .on("mouseover", showTooltip)
                .on("mousemove", moveTooltip)
                .on("mouseleave", hideTooltip);
                //.on("click", ru.lila.seeker.histogram_click);
          
          // THis should have drawn the histogram correctly
        } catch (ex) {
          private_methods.errMsg("scount_histogram_show", ex);
        }
      },

      /**
       * histogram_click
       *    What happens when the user clicks through on a histogram bar
       *
       */
      histogram_click: function (event, d) {
        var scount = 0,
            elStart = null;

        try {
          // Check if this is one with targeturl specified or not
          if ('targeturl' in d) {
            // Click through to the targeturl
            window.location.href = d.targeturl;
          } else {
            // Extract the scount from the [d]
            scount = d.x0;

            // Set the correct form values
            $("#id_ssg-soperator option[value='exact']").attr("selected", true);
            $("#id_ssg-scount").val(scount);
            $("#id_ssg-scount")[0].value = scount;

            // Get the start element
            elStart = $("#tab_filter .search-button").first();

            // Call the usual 'search' function with this additional parameter
            ru.basic.search_start(elStart);

          }
          // THis should have drawn the histogram correctly
        } catch (ex) {
          private_methods.errMsg("histogram_click", ex);
        }
      },

      /**
       * d3_lineplot_show
       *    Show lineplot using D3
       *
       *  The data is expected to be: 'count', 'freq'
       *
       */
      d3_lineplot_show: function (data, divid) {
        var margin = null,
            width = null,
            height = null,
            parseDate = null,
            x = null,
            y = null,
            xAxis = null,
            yAxis = null,
            line = null,
            svg = null;

        try {
          // Set the margin, width and height
          margin = { top: 20, right: 20, bottom: 30, left: 50 }
          width = 960 - margin.left - margin.right;
          height = 500 - margin.top - margin.bottom;

          // Set up the x and y scales
          x = d3.scaleLinear().range([0, width]);
          y = d3.scaleLinear().range([height, 0]);

          // Set up the axes (d3 v6)
          xAxis = d3.axisBottom(x);
          yAxis = d3.axisLeft(y);

          // How the line is being made
          line = d3.line()
            .x(function (d) { return x(d.scount); })
            .y(function (d) { return y(d.freq); });

          // Create an SVG top node
          svg = d3.select("#" + divid).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

          //domain specifications
          x.domain(d3.extent(data, function (d) {
            return d.scount;
          }));
          y.domain(d3.extent(data, function (d) {
            return d.freq;
          }));

          // Draw the axes
          svg.append("g").attr("class", "x axis").attr("transform", "translate(0," + height + ")")
            .call(xAxis)
            .append("text").attr("y", 30).attr("x", width - 100).text("Frequency");

          svg.append("g").attr("class", "y axis")
            .call(yAxis)
            .append("text")
              .attr("transform", "rotate(-90)")
              .attr("y", -50)
              .attr("dy", ".71em")
              .style("text-anchor", "end")
              .text("Sermons per SSG");

          svg.append("path")
            .datum(data)
            .attr("class", "line")
            .attr("d", line);

          // THis should have drawn the lineplot correctly
        } catch (ex) {
          private_methods.errMsg("d3_lineplot_show", ex);
        }
      },

      /**
       * add_new_select2
       *    Show [table_new] element
       *
       */
      add_new_select2: function (el) {
        var elTr = null,
            elRow = null,
            options = {},
            elDiv = null;

        try {
          elTr = $(el).closest("tr");           // Nearest <tr>
          elDiv = $(elTr).find(".new-mode");    // The div with new-mode in it
          // Show it
          $(elDiv).removeClass("hidden");
          // Find the first row
          elRow = $(elDiv).find("tbody tr").first();
          options['select2'] = true;
          ru.lila.seeker.tabular_addrow($(elRow), options);

          // Add
        } catch (ex) {
          private_methods.errMsg("add_new_select2", ex);
        }
      },

      /**
       * form_row_select
       *    By selecting this slement, the whole row gets into the 'selected' state
       *
       */
      form_row_select: function (elStart) {
        var elTable = null,
          elRow = null, // The row
          iSelCount = 0, // Number of selected rows
          elHier = null,
          bSelected = false;

        try {
          // Get to the row
          elRow = $(elStart).closest("tr.form-row");
          // Get current state
          bSelected = $(elRow).hasClass("selected");
          // FInd nearest table
          elTable = $(elRow).closest("table");
          // Check if anything other than me is selected
          iSelCount = 1;
          // Remove all selection
          $(elTable).find(".form-row.selected").removeClass("selected");
          elHier = $("#sermon_hierarchy");
          // CHeck what we need to do
          if (bSelected) {
            // We are de-selecting: hide the 'Up' and 'Down' buttons if needed
            // ru.cesar.seeker.show_up_down(this, false);
            $(elHier).removeClass("in");
            $(elHier).hide()
          } else {
            // Make a copy of the tree as it is
            $("#sermon_tree_copy").html($("#sermon_tree").html());
            // Select the new row
            $(elRow).addClass("selected");
            // SHow the 'Up' and 'Down' buttons if needed
            // ru.cesar.seeker.show_up_down(this, true);
            // document.getElementById('sermon_manipulate').submit();
            $(elHier).addClass("in");
            $(elHier).show();
          }

        } catch (ex) {
          private_methods.errMsg("form_row_select", ex);
        }
      },

      /**
       *  manuscript
       *      Save the current constellation of sermons in the manuscript
       *
       */
      manuscript: function (operation, elStart) {
        var targeturl = "",
            elCopy = $("#sermon_tree_copy"),
            elMain = $("#sermon_tree_main"),
            elTree = $("#sermon_tree"),
            maxwidth = 0,
            yoffset = 0,
            hList = null,
            data = null;

        try {
          // Get the 'targeturl' attribute 
          targeturl = $(elStart).attr("targeturl");

          switch (operation) {
            case "save":    // Save the current constellation of sermons 
              if (targeturl !== undefined && targeturl !== null) {
                // 'Read' the current hierarchy...
                hList = private_methods.sermon_hlisttree(elMain);
                // Set the <input> value to return the contents of [hList]
                $("#id_manu-hlist").val(JSON.stringify(hList));

                // Indicate we are waiting
                $(elTree).find(".waiting").removeClass("hidden");
                // Hide the buttons
                $(elTree).find(".edit-mode").addClass("hidden");

                // Pass this on as parameter??
                $("#save_new_hierarchy").submit();
              }
              break;
            case "restore": // Resture the sermon hierarchy to what it was
              // REmove what is under [elTree]
              $(elMain).empty();
              // Copy everything from #sermon_tree_copy to after the first child of #sermon_tree
              $(elMain).append($(elCopy).html());
              // Hide the SAVE and RESTORE buttons
              $(elTree).find(".edit-mode").addClass("hidden");
              break;
            case 'expand':
              // Remove all hidden stuff
              $(elMain).find(".tree").removeClass("hidden");
              break;
            case 'collapse':
              // Hide everything that is under the main level
              $(elMain).find(".tree[level!='1']").addClass("hidden");
              break;
            case 'init':
              // Set the current codicologial borders

              // Make a copy of the tree as it is
              $(elCopy).html($(elMain).html());
              // If there is a location movement, select it
              if (location.hash) {
                location.href = location.hash;
                $(location.hash).find(".sermonnumber").first().addClass("selected");
                // $(location.hash)[0].scrollIntoView(true);
                //$(location.hash)[0].scrollTop -= 100;
                //yoffset = window.pageYoffset - 100;
                //window.scrollTo(window.pageXoffset, yoffset);
                loc_vscrolling = -100;
              }
              // Re-calculate and set the width of 'sermonnumber' and 'sermonlocus'
              maxwidth = 0;
              $(elMain).find(".sermonnumber").each(function (idx, el) {
                var iwidth = parseInt(el.clientWidth, 10);
                if (iwidth > maxwidth) { maxwidth = iwidth;}
              });
              $(elMain).find(".sermonnumber").each(function (idx, el) {
                $(el).css("min-width", maxwidth.toString() + "px");
              });
              maxwidth = 0;
              $(elMain).find(".sermonlocus").each(function (idx, el) {
                var iwidth = parseInt(el.clientWidth, 10);
                if (iwidth > maxwidth) { maxwidth = iwidth; }
              });
              $(elMain).find(".sermonlocus").each(function (idx, el) {
                $(el).css("min-width", maxwidth.toString() + "px");
              });
              break;
          }

        } catch (ex) {
          private_methods.errMsg("manuscript", ex);
        }
      },

      /**
       *  sermon_move
       *      Select or deselect a sermon
       *
       */
      sermon_selection: function (elStart) {
        try {
          if ($(elStart).hasClass("selected")) {
            // remove selection
            $(elStart).removeClass("selected");
          } else {
            $(elStart).addClass("selected");
          }

        } catch (ex) {
          private_methods.errMsg("sermon_selection", ex);
        }
      },

      /**
       *  sermon_move
       *      Move the selected row
       *
       */
      sermon_move: function (type) {
        var elRoot = null,
            elSrc = null,
            elDst = null,
            elStart = null,
            elTable = null,
            elRow = null,
            elRowRef = null,
            data = [],
            sibling = [],
            oTree = null,
            targeturl = "",
            sText = "",
            method = "dom",   //
            hList = [],       // List of current hierarchy
            dst = -1,         // Target count
            sermonid = "",    // The sermonid of the selected one
            nodeid = -1,
            nodedstid = -1,
            level = -1,
            childof = -1;

        try {
          // Make sure we know where the DOM is
          elRoot = $("#sermon_tree");

          // Determine which row is selected
          elStart = $("#canwit_list").find("tr.selected > td.selectable").first();
          elRow = $(elStart).parent();
          elTable = $(elRow).closest("table");
          sermonid = $(elRow).attr("sermonid");

          // Action depends on the type
          switch (type) {
            case "close": // Close the modal
              ru.lila.seeker.form_row_select(elStart);
              // Return the stored copy
              $("#sermon_tree").html($("#sermon_tree_copy").html());
              // Make sure the tree is redrawn
              ru.lila.seeker.sermon_drawtree();
              break;
            case "up":    // position me before my preceding sibling
              // Get the <div> that should be moved
              elSrc = $(elRoot).find("div.tree[sermonid={0}]".format(sermonid)).first();
              // See if we have a preceding sibling
              elDst = $(elSrc).prev("div.tree");
              if (elDst.length > 0) {
                $(elSrc).insertBefore(elDst);
                // Make sure the tree is redrawn
                ru.lila.seeker.sermon_drawtree(sermonid);
              }

              break;
            case "down":  // position me after my following sibling
              // Get the <div> that should be moved
              elSrc = $(elRoot).find("div.tree[sermonid={0}]".format(sermonid)).first();
              // See if we have a following sibling
              elDst = $(elSrc).next("div.tree");
              if (elDst.length > 0) {
                $(elSrc).insertAfter(elDst);
                // Make sure the tree is redrawn
                ru.lila.seeker.sermon_drawtree(sermonid);
              }

              break;
            case "left":  // let me become a child of my grandparent, positioned AFTER my parent
              // Get the <div> that should be moved
              elSrc = $(elRoot).find("div.tree[sermonid={0}]".format(sermonid)).first();
              // See if there is a parent after which I can be placed
              elDst = $(elSrc).parent("div.tree");
              if (elDst.length > 0) {
                // There is a parent: put me after it
                $(elSrc).insertAfter(elDst);
                // Change the level
                level = parseInt($(elSrc).attr("level"), 10);
                $(elSrc).attr("level", level - 1);
                // Make sure the tree is redrawn
                ru.lila.seeker.sermon_drawtree(sermonid);
              }
              break;
            case "right":  // let me become a child of my preceding SIBLING
              // Get the <div> that should be moved
              elSrc = $(elRoot).find("div.tree[sermonid={0}]".format(sermonid)).first();
              // See if there is a preceding sibling
              elDst = $(elSrc).prev("div.tree");
              if (elDst.length > 0) {
                // There is a preceding sibling: make me into its child
                $(elDst).append(elSrc);
                // Change the level
                level = parseInt($(elSrc).attr("level"), 10);
                $(elSrc).attr("level", level + 1);
                // Make sure the tree is redrawn
                ru.lila.seeker.sermon_drawtree(sermonid);
              }
              break;
            case "save":  // Get an adapted list of the hierarchy, post to the server and receive response
              // Get list of current hierarchy
              //hList = private_methods.sermon_hlisttree(elRoot);
              ///*
              hList = private_methods.sermon_hlist(elTable);
              // Set the <input> value to return the contents of [hList]
              $("#id_manu-hlist").val(JSON.stringify(hList));
              // Send it onwards
              $("#save_new_hierarchy").submit();
              // */
              break;
          }

        } catch (ex) {
          private_methods.errMsg("sermon_move", ex);
        }
      },

      /**
       *  sermon_drawtree
       *      Copy the list of sermons to the div with id=sermon_tree
       *
       */
      sermon_drawtree: function (sermonid) {
        var elRoot = null,
            elTable = null;

        try {
          elTable = $("#canwit_list");
          elRoot = $("#sermon_tree");
          // Create the tree from [elTable] to [elRoot]
          private_methods.sermon_treetotable(elRoot, elTable, sermonid);

        } catch (ex) {
          private_methods.errMsg("sermon_drawtree", ex);
        }
      },

      /**
       *  sermon_level
       *      Open or close the current level in the sermon tree
       *
       */
      sermon_level: function (elThis) {
        var elChild = null,
            elTree = null,
            elTable = null;

        try {
          // Get my tree part
          elTree = $(elThis).closest(".tree");
          // Get my first child
          elChild = $(elTree).children(".tree").first();
          // Action depends on hidden or not
          if ($(elChild).hasClass("hidden")) {
            // Show
            $(elTree).children(".tree").removeClass("hidden");
          } else {
            // Hide
            $(elTree).children(".tree").addClass("hidden");
          }

        } catch (ex) {
          private_methods.errMsg("sermon_level", ex);
        }
      },

      /**
       * do_get
       *    Perform a $.get() based on the information in DOM element with id sId
       *
       */
      do_get: function (sId, func_after) {
        var elStart = null,
            data = [],
            targeturl = "",
            targetid = null;

        try {
          // Retrieve the information
          elStart = $("#" + sId);
          targeturl = $(elStart).attr("targeturl");
          targetid = $(elStart).attr("targetid");
          if (targetid === undefined || targetid === "") {targetid = sId;}
          if (targetid !== "") { targetid = "#" + targetid;}

          // Load this one with a GET action
          $.get(targeturl, data, function (response) {
            // Perform any function defined after receiving the response from the host
            if (func_after !== undefined) {
              func_after();
            }

            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ok":
                  // Show the result
                  $(targetid).html(response['html']);
                  // Call initialisation again
                  ru.lila.seeker.init_events(sUrlShow);
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker do_get)");
                  }
                  break;
              }
            }

          });

        } catch (ex) {
          private_methods.errMsg("do_get", ex);
        }
      },

      /**
       * do_basket
       *    Perform a basket action
       *
       */
      do_basket: function (elStart) {
        var frm = null,
            targeturl = "",
            redirecturl = "",
            operation = "",
            targetid = "",
            colladdid = "#colladdinterface",
            basketwait = "#basket_waiting",
            basketreport = "#basket_report",
            basketlink = "#basket_coll_link",
            target = null,
            data = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Get the data from the form
          data = frm.serializeArray();
          // The url is in the ajaxurl
          targeturl = $(elStart).attr("ajaxurl");
          // Get the operation
          operation = $(elStart).attr("operation");
          // Get the targetid
          targetid = $(elStart).attr("targetid");
          // Basket report is normally hidden
          $(basketreport).addClass("hidden");

          switch (operation) {
            case "colladdstart":
              $(colladdid).removeClass("hidden");
              return;
              break;
            case "colladdcancel":
              $(colladdid).addClass("hidden");
              return;
              break;
            default:
              $(colladdid).addClass("hidden");
              break;
          }

          // validation
          if (targeturl === undefined || targeturl === "" || operation === undefined || operation === "" ||
              targetid === undefined || targetid === "") { return; }

          // Where to go to 
          target = $('#' + targetid);

          // Add operation to data
          data.push({ "name": "operation", "value": operation });

          // Show we are waiting
          $(basketwait).removeClass("hidden");

          // Call the ajax POST method
          // Issue a post
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "ok":
                  // Should we do redirection?
                  if ("redirecturl" in response && response.redirecturl !== "") {
                    redirecturl = response.redirecturl;
                    window.location.href = redirecturl;
                  }
                  // Show the HTML target
                  $(target).html(response['html']);
                  // Possibly do some initialisations again??

                  // Hide the colladd interface
                  $(colladdid).addClass("hidden");

                  // Show we are no longer waiting
                  $(basketwait).addClass("hidden");

                  // Possibly show a report
                  switch (operation) {
                    case "colladd":
                      // Add the correct parameters to the report
                      $(basketlink).attr("href", response.collurl);
                      $(basketlink).html("<span>" + response.collname + "</span>");
                      // Show the report
                      $(basketreport).removeClass("hidden");
                      break;
                  }

                  // Make sure events are re-established
                  ru.lila.seeker.init_events();
                  // ru.lila.init_typeahead();

                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(target).html(response.msg);
                  } else {
                    $(target).html("An error has occurred (lila.seeker do_basket)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("do_basket", ex);
        }
      },

      /**
       * search_reset
       *    Clear the information in the form's fields and then do a submit
       *
       */
      search_reset: function (elStart) {
        var frm = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Clear the information in the form's INPUT fields
          $(frm).find("input:not([readonly]).searching").val("");
          // Show we are waiting
          $("#waitingsign").removeClass("hidden");
          // Now submit the form
          frm.submit();
        } catch (ex) {
          private_methods.errMsg("search_reset", ex);
        }
      },

      /**
       * search_clear
       *    No real searching, just reset the criteria
       *
       */
      search_clear: function (elStart) {
        var frm = null,
            idx = 0,
            lFormRow = [];

        try {
          // Clear filters
          $(".badge.filter").each(function (idx, elThis) {
            var target;

            target = $(elThis).attr("targetid");
            if (target !== undefined && target !== null && target !== "") {
              target = $("#" + target);
              // Action depends on checking or not
              if ($(elThis).hasClass("on")) {
                // it is on, switch it off
                $(elThis).removeClass("on");
                $(elThis).removeClass("jumbo-3");
                $(elThis).addClass("jumbo-1");
                // Must hide it and reset target
                $(target).addClass("hidden");
                $(target).find("input").each(function (idx, elThis) {
                  $(elThis).val("");
                });
                // Also reset all select 2 items
                $(target).find("select").each(function (idx, elThis) {
                  $(elThis).val("").trigger("change");
                });
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("search_clear", ex);
        }
      },

      /**
       * search_start
       *    Gather the information in the form's fields and then do a submit
       *
       */
      search_start: function (elStart, method, iPage, sOrder) {
        var frm = null,
            url = "",
            targetid = null,
            targeturl = "",
            data = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Get the data from the form
          data = frm.serializeArray();

          // Determine the method
          if (method === undefined) { method = "submit";}

          // Get the URL from the form
          url = $(frm).attr("action");

          // Action depends on the method
          switch (method) {
            case "submit":
              // Show we are waiting
              $("#waitingsign").removeClass("hidden");
              // Store the current URL
              loc_urlStore = url;
              // If there is a page number, we need to process it
              if (iPage !== undefined) {
                $(elStart).find("input[name=page]").each(function (el) {
                  $(this).val(iPage);
                });
              }
              // If there is a sort order, we need to process it
              if (sOrder !== undefined) {
                $(elStart).find("input[name=o]").each(function (el) {
                  $(this).val(sOrder);
                });
              }
              // Now submit the form
              frm.submit();
              break;
            case "post":
              // Determine the targetid
              targetid = $(elStart).attr("targetid");
              if (targetid == "subform") {
                targetid = $(elStart).closest(".subform");
              } else {
                targetid = $("#" + targetid);
              }
              // Get the targeturl
              targeturl = $(elStart).attr("targeturl");

              // Get the page we need to go to
              if (iPage === undefined) { iPage = 1; }
              data.push({ 'name': 'page', 'value': iPage });
              if (sOrder !== undefined) {
                data.push({ 'name': 'o', 'value': sOrder });
              }

              // Issue a post
              $.post(targeturl, data, function (response) {
                // Action depends on the response
                if (response === undefined || response === null || !("status" in response)) {
                  private_methods.errMsg("No status returned");
                } else {
                  switch (response.status) {
                    case "ready":
                    case "ok":
                      // Show the HTML target
                      $(targetid).html(response['html']);
                      // Possibly do some initialisations again??

                      // Make sure events are re-established
                      // ru.lila.seeker.init_events();
                      ru.lila.init_typeahead();
                      break;
                    case "error":
                      // Show the error
                      if ('msg' in response) {
                        $(targetid).html(response.msg);
                      } else {
                        $(targetid).html("An error has occurred (lila.seeker search_start)");
                      }
                      break;
                  }
                }
              });


              break;
          }

        } catch (ex) {
          private_methods.errMsg("search_start", ex);
        }
      },

      /**
       * search_paged_start
       *    Perform a simple 'submit' call to search_start
       *
       */
      search_paged_start: function(iPage) {
        var elStart = null;

        try {
          // And then go to the first element within the form that is of any use
          elStart = $(".search_paged_start").first();
          ru.lila.seeker.search_start(elStart, 'submit', iPage)
        } catch (ex) {
          private_methods.errMsg("search_paged_start", ex);
        }
      },

      /**
       * search_ordered_start
       *    Perform a simple 'submit' call to search_start
       *
       */
      search_ordered_start: function (order) {
        var elStart = null;

        try {
          // And then go to the first element within the form that is of any use
          elStart = $(".search_ordered_start").first();
          ru.lila.seeker.search_start(elStart, 'submit', 1, order)
        } catch (ex) {
          private_methods.errMsg("search_ordered_start", ex);
        }
      },

      /**
       * submitform
       *    Submit the form at [elStart]
       *    If 'disable' is true, then disable all <a> with class 'btn'
       *
       */
      submitform: function (elStart, disable) {
        var elForm = null;

        try {
          // Disable all buttons in the document, except the submit one
          $("a.btn").addClass("disabled");

          // Possibly get the waiting rolling
          $("#" + elStart).find(".waiting").removeClass("hidden");
          
          // COntinue to submit
          document.getElementById(elStart).submit();
        } catch (ex) {
          private_methods.errMsg("submitform", ex);
        }
      },

      /**
       * gold_search_prepare
       *    Prepare the modal form to search for gold-sermon destinations
       *
       */
      gold_search_prepare: function (elStart) {
        var targetid = "",
            data = [],
            targeturl = "";

        try {
          // Set our own location
          loc_goldlink_td = $(elStart).closest("td");
          // Get the target url and the target id
          targeturl = $(elStart).attr("targeturl");
          targetid = $(elStart).attr("targetid");
          // Show the waiting signal at the targetid
          $("#" + targetid).html(loc_sWaiting);
          // Fetch and show the targeturl
          $.get(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ok":
                  // Show the result
                  $("#" + targetid).html(response['html']);
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $("#" + targetid).html(response.msg);
                  } else {
                    $("#" + targetid).html("An error has occurred (lila.seeker gold_search_prepare)");
                  }
                  break;
              }
              // Make sure events are re-established
              // ru.lila.seeker.init_events();
              ru.lila.init_typeahead();
            }

          });

        } catch (ex) {
          private_methods.errMsg("gold_search_prepare", ex);
        }
      },

      /**
       * gold_select_save
       *    When a gold sermon has been chosen as destination link, make sure it is shown in the list
       *
       */
      gold_select_save: function (elStart) {
        var elResults = "#goldselect_results",
            elSelect = null,
            gold_html = "",
            gold_equal = "",
            gold_id = "";

        try {
          // Find out which one has been selected
          elSelect = $(elResults).find("tr.selected").first();
          gold_id = $(elSelect).find("td.gold-id").text();
          gold_html = $(elSelect).find("td.gold-text").html();
          // Set the items correctly in loc_goldlink_td
          $(loc_goldlink_td).find("input").val(gold_id);
          $(loc_goldlink_td).find(".view-mode").first().html(gold_html);
          $(loc_goldlink_td).find(".edit-mode").first().html(gold_html);

          // Remove the selection
          //$(elResults).find("tr.selected").find(".selected").removeClass("selected");

        } catch (ex) {
          private_methods.errMsg("gold_select_save", ex);
        }
      },

      /**
       * gold_page
       *    Make sure we go to the indicated page
       * 
       * @param {type} iPage
       * @param {type} sFormDiv
       */
      gold_page: function (iPage, sFormDiv) {
        var elStart = null;

        try {
          elStart = $("#" + sFormDiv);
          ru.lila.seeker.search_start(elStart, "post", iPage);
        } catch (ex) {
          private_methods.errMsg("gold_page", ex);
        }
      },

      /**
       * check_progress
       *    Check the progress of reading e.g. codices
       *
       */
      check_progress: function (progrurl, sTargetDiv) {
        var elTarget = "#" + sTargetDiv,
            sMsg = "",
            lHtml = [];

        try {
          $(elTarget).removeClass("hidden");
          // Call the URL
          $.get(progrurl, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "finished":
                  // NO NEED for further action
                  //// Indicate we are ready
                  //$(elTarget).html("READY");
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(elTarget).html(response.msg);
                  } else {
                    $(elTarget).html("An error has occurred (lila.seeker check_progress)");
                  }                  
                  break;
                default:
                  if ("msg" in response) { sMsg = response.msg; }
                  // Combine the status
                  sMsg = "<tr><td>" + response.status + "</td><td>" + sMsg + "</td></tr>";
                  // Check if it is on the stack already
                  if ($.inArray(sMsg, loc_progr) < 0) {
                    loc_progr.push(sMsg);
                  }
                  // Combine the status HTML
                  sMsg = "<div style=\"max-height: 200px; overflow-y: scroll;\"><table>" + loc_progr.reverse().join("\n") + "</table></div>";
                  $(elTarget).html(sMsg);
                  // Make sure we check again
                  window.setTimeout(function () { ru.lila.seeker.check_progress(progrurl, sTargetDiv); }, 200);
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("check_progress", ex);
        }
      },

      /**
       * hide
       *   Hide element [sHide] and 
       *
       */
      hide: function (sHide) {
        try {
          $("#" + sHide).addClass("hidden");
        } catch (ex) {
          private_methods.errMsg("hide", ex);
        }
      },

      /**
       * select_row
       *   Select one row in a table
       *
       */
      select_row: function (elStart, method, id) {
        var tbl = null,
            elsubform = null,
            eltowards = null,
            sSermon = "",
            select_id = "";

        try {
          // Get the table
          tbl = $(elStart).closest("table");
          // Deselect all other rows
          $(tbl).children("tbody").children("tr").removeClass("selected");
          // Select my current row
          $(elStart).addClass("selected");

          // Determine the select id: the id of the selected target
          if (id !== undefined && id !== "") {
            select_id = id;
          }

          // Determine the element in [sermongoldlink_info.html] where we need to change something
          elsubform = $(elStart).closest("div .subform");
          if (elsubform !== null && elsubform !== undefined) {
            eltowards = $(elsubform).attr("towardsid");
            if (eltowards === undefined) {
              eltowards = null;
            } else {
              eltowards = $("#" + eltowards);
            }
          }

          // Action depends on the method
          switch (method) {
            case "gold_link":
              // Select the correct gold sermon above
              if (eltowards !== null && $(eltowards).length > 0) {
                // Set the text of this sermon
                sSermon = $(elStart).find("td").last().html();
                $(eltowards).find(".edit-mode").first().html(sSermon);

                // Set the id of this sermon
                // DOESN'T EXIST!!! $(eltowards).find("#id_glink-dst").val(select_id.toString());
              }
              break;
          }
        } catch (ex) {
          private_methods.errMsg("select_row", ex);
        }
      },

      /**
       * import_data
       *   Allow user to upload a file
       *
       * Assumptions:
       * - the [el] contains parameter  @targeturl
       * - there is a div 'import_progress'
       * - there is a div 'id_{{ftype}}-{{forloop.counter0}}-file_source'
       *   or one for multiple files: 'id_files_field'
       *
       */
      import_data: function (sKey) {
        var frm = null,
            targeturl = "",
            options = {},
            fdata = null,
            el = null,
            elProg = null,    // Progress div
            elErr = null,     // Error div
            progrurl = null,  // Any progress function to be called
            data = null,
            xhr = null,
            files = null,
            sFtype = "",      // Type of function (cvar, feat, cond)
            elWait = null,
            bDoLoad = false,  // Need to load with a $.get() afterwards
            elInput = null,   // The <input> element with the files
            more = {},        // Additional (json) data to be passed on (from form-data)
            sTargetDiv = "",  // The div where the uploaded reaction comes
            sSaveDiv = "",    // Where to go if saving is needed
            sMsg = "";

        try {
          // The element to use is the key + import_info
          el = $("#" + sKey + "-import_info");
          elProg = $("#" + sKey + "-import_progress");
          elErr = $("#" + sKey + "-import_error");

          // Set the <div> to be used for waiting
          elWait = private_methods.waitInit(el);

          // Get the URL
          targeturl = $(el).attr("targeturl");
          progrurl = $(el).attr("sync-progress");
          sTargetDiv = $(el).attr("targetid");
          sSaveDiv = $(el).attr("saveid");

          if (targeturl === undefined && sSaveDiv !== undefined && sSaveDiv !== "") {
            targeturl = $("#" + sSaveDiv).attr("ajaxurl");
            sTargetDiv = $("#" + sSaveDiv).attr("openid");
            sFtype = $(el).attr("ftype");
            bDoLoad = true;
          }

          if ($(el).is("input")) {
            elInput = el;
          } else {
            elInput = $(el).find("input").first();
          }

          // Show progress
          $(elProg).attr("value", "0");
          $(elProg).removeClass("hidden");
          if (bDoLoad) {
            $(".save-warning").html("loading the definition..." + loc_sWaiting);
            $(".submit-row button").prop("disabled", true);
          }

          // Add data from the <form> nearest to me: 
          frm = $(el).closest("form");
          if (frm !== undefined) { data = $(frm).serializeArray(); }

          for (var i = 0; i < data.length; i++) {
            more[data[i]['name']] = data[i]['value'];
          }
          // Showe the user needs to wait...
          private_methods.waitStart(elWait);

          // Now initiate any possible progress calling
          if (progrurl !== null) {
            loc_progr = [];
            window.setTimeout(function () { ru.lila.seeker.check_progress(progrurl, sTargetDiv); }, 2000);
          }

          // Upload XHR
          $(elInput).upload(targeturl,
            more,
            function (response) {
              // Transactions have been uploaded...
              console.log("done: ", response);

              // Show where we are
              $(el).addClass("hidden");
              $(".save-warning").html("saving..." + loc_sWaiting);

              // First leg has been done
              if (response === undefined || response === null || !("status" in response)) {
                private_methods.errMsg("No status returned");
              } else {
                switch (response.status) {
                  case "ok":
                    // Check how we should react now
                    if (bDoLoad) {
                      // Show where we are
                      $(".save-warning").html("retrieving..." + loc_sWaiting);

                      $.get(targeturl, function (response) {
                        if (response === undefined || response === null || !("status" in response)) {
                          private_methods.errMsg("No status returned");
                        } else {
                          switch (response.status) {
                            case "ok":
                              // Show the response in the appropriate location
                              $("#" + sTargetDiv).html(response.html);
                              $("#" + sTargetDiv).removeClass("hidden");
                              break;
                            default:
                              // Check how/what to show
                              if ("err_view" in response) {
                                private_methods.errMsg(response['err_view']);
                              } else if ("error_list" in response) {
                                private_methods.errMsg(response['error_list']);
                              } else {
                                // Just show the HTML
                                $("#" + sTargetDiv).html(response.html);
                                $("#" + sTargetDiv).removeClass("hidden");
                              }
                              break;
                          }
                          // Make sure events are in place again
                          ru.lila.seeker.init_events();
                          switch (sFtype) {
                            case "cvar":
                              ru.lila.seeker.init_cvar_events();
                              break;
                            case "cond":
                              ru.lila.seeker.init_cond_events();
                              break;
                            case "feat":
                              ru.lila.seeker.init_feat_events();
                              break;
                          }
                          // Indicate we are through with waiting
                          private_methods.waitStop(elWait);
                        }
                      });
                    } else {
                      // Remove all project-part class items
                      $(".project-part").addClass("hidden");
                      // Place the response here
                      $("#" + sTargetDiv).html(response.html);
                      $("#" + sTargetDiv).removeClass("hidden");
                    }
                    break;
                  default:
                    // Check WHAT to show
                    sMsg = "General error (unspecified)";
                    if ("err_view" in response) {
                      sMsg = response['err_view'];
                    } else if ("error_list" in response) {
                      sMsg = response['error_list'];
                    } else {
                      // Indicate that the status is not okay
                      sMsg = "Status is not good. It is: " + response.status;
                    }
                    // Show the message at the appropriate location
                    $(elErr).html("<div class='error'>" + sMsg + "</div>");
                    // Make sure events are in place again
                    ru.lila.seeker.init_events();
                    switch (sFtype) {
                      case "cvar":
                        ru.lila.seeker.init_cvar_events();
                        break;
                      case "cond":
                        ru.lila.seeker.init_cond_events();
                        break;
                      case "feat":
                        ru.lila.seeker.init_feat_events();
                        break;
                    }
                    // Indicate we are through with waiting
                    private_methods.waitStop(elWait);
                    $(".save-warning").html("(not saved)");
                    break;
                }
              }
              private_methods.waitStop(elWait);
            }, function (progress, value) {
              // Show  progress of uploading to the user
              console.log(progress);
              $(elProg).val(value);
            }
          );
          // Hide progress after some time
          setTimeout(function () { $(elProg).addClass("hidden"); }, 1000);

          // Indicate waiting can stop
          private_methods.waitStop(elWait);
        } catch (ex) {
          private_methods.errMsg("import_data", ex);
          private_methods.waitStop(elWait);
        }
      },

      stop_bubbling: function(event) {
        event.handled = true;
        return false;
      },


      /**
       * sermo_edit
       *   Switch between edit modes for this sermon
       *   And if saving is required, then call the [targeturl] to send a POST of the form data
       *
       */
      sermo_edit: function (el, sType) {
        var sMode = "",
            targetid = "",
            targeturl = "",
            manusurl = "",
            number = "",
            bNew = false,
            data = null,
            frm = null,
            bOkay = true,
            err = "#sermon_err_msg",
            elTd = null,
            parent = "",
            elSermon = "",
            elView = null,
            elEdit = null;

        try {
          // Possibly correct [el]
          if (el !== undefined && "currentTarget" in el) {
            el = el.currentTarget;
          }
          // Check if type is specified
          if (sType === undefined) {
            // Get to the <td> we are in
            elTd = $(el).closest("td");
            if (elTd === undefined || elTd.length === 0) {
              el = this;
              elTd = $(el).closest("td");
            }
            // Check if we need to take the table
            if ($(elTd).hasClass("table")) {
              elTd = $(el).closest("table");
            } else if ($(elTd).hasClass("tabletd")) {
              elTd = $(el).closest("table").closest("td");
            }
          } else {
            // We ourselves are the td
            elTd = el;
          }
          // Get the targeturl and the number
          targeturl = $(elTd).attr("targeturl");
          if (targeturl === undefined) { targeturl = $(el).attr("targeturl"); }
          number = $(elTd).attr("number");
          if (number === undefined) {
            number = $("#sermon_number").attr("number");
          }
          // Get the view and edit values
          elView = $(el).find(".view-mode").first();
          elEdit = $(el).find(".edit-mode").first();
          // Determine the mode we are in
          if (sType !== undefined && sType === "new") {
            // Creating a new one
            sMode = "new";
          } else if ($(el).attr("mode") !== undefined && $(el).attr("mode") !== "") {
            sMode = $(el).attr("mode");
          } else {
            // Check what is opened
            if ($(elView).hasClass("hidden")) {
              // Apparently we are editing, and need to go to VIEW mode (this is the equivalent to Cancel)
              sMode = "view";
            } else {
              // Apparently VIEW is visible, so we are in VIEW mode and need to go to Edit
              sMode = "edit";
            }
          }

          // Act on the mode that we need to SWITCH TO
          switch (sMode) {
            case "view":
            case "cancel":
              // Is this by pressing the 'cancel' button?
              if (el.localName === "a" && $(el).hasClass("btn")) {
                // This is pressing the cancel button
                $(".edit-sermon").addClass("hidden");
                $("#canwit_edit").html("");
                // Show the table data in view mode
                elSermon = "#sermon-number-" + number;
                $(elSermon).find(".view-mode").removeClass("hidden");
                $(elSermon).find(".edit-mode").addClass("hidden");
                //$("#canwit_list").find(".view-mode").removeClass("hidden");
                //$("#canwit_list").find(".edit-mode").addClass("hidden");
              } else {
                // Show the data in view mode
                $(elTd).find(".view-mode").removeClass("hidden");
                $(elTd).find(".edit-mode").addClass("hidden");
              }
              break;
            case "new":
              // (1) Make sure everything in the table is in view-mode
              $("#canwit_list").find(".edit-mode").addClass("hidden");
              $("#canwit_list").find(".view-mode").removeClass("hidden");
              // (2) Request information from the server
              $.get(targeturl, data, function (response) {
                $(".edit-sermon").removeClass("hidden");
                $("#sermon_new").html(response);
                // Determine the number of rows we have
                number = $("#canwit_list").find("tr").length;
                $("#sermon_number").html(" new item (will be #"+number+")");
                $("#sermon_number").attr("number", number);
                $("#sermon_number").attr("new", true);
                // Pass on a message to the user
                // NOTE: this cannot happen, because we are above...
                // $(targetid).html("<i>Please edit sermon " + number + " above and then either Save or Cancel</i>");



                ru.lila.seeker.init_events();
                ru.lila.init_typeahead();
              });
              break;
            case "edit":
              // Go over to edit mode
              // (1) Make sure everything is in view-mode
              $(elTd).closest("table").find(".edit-mode").addClass("hidden");
              $(elTd).closest("table").find(".view-mode").removeClass("hidden");
              // (1) Get the target id
              targetid = $(elTd).find(".edit-mode").first();
              // (2) Show we are loading
              $(elTd).find(".view-mode").addClass("hidden");
              $(elTd).find(".edit-mode").removeClass("hidden");
              $(targetid).html(loc_sWaiting);
              // (2) Request information from the server
              $.get(targeturl, data, function (response) {
                $(".edit-sermon").removeClass("hidden");
                $("#canwit_edit").html(response);
                $("#sermon_number").html(" manuscript item #" + number);
                $("#sermon_number").attr("number", number);
                // Pass on a message to the user
                $(targetid).html("<i>Please edit manuscript item "+number+" above and then either Save or Cancel</i>");
                ru.lila.seeker.init_events();
                ru.lila.init_typeahead();
              });
              break;
            case "delete":
              // Ask for confirmation
              if (!confirm("Do you really want to remove this sermon from the current manuscript?")) {
                // Return from here
                return;
              }
              // (1) Get the form data
              data = $(el).closest("form").serializeArray();
              // (2) Get the manuscript id
              parent = $("#canwit_edit").attr("parent");
              // Add this to the data
              if (parent !== undefined) {
                data.push({ 'name': 'manuscript_id', 'value': parent });
              }
              // (3) Add the action: delete
              data.push({ 'name': 'action', 'value': "delete" });
              // (4) Find out what we need to open later on
              manusurl = $("#canwit_edit").attr("manusurl");
              // (5) Send to the server
              $.post(targeturl, data, function (response) {
                // Action depends on the (JSON!) response
                if (response === undefined || response === null || !("status" in response)) {
                  private_methods.errMsg("No status returned");
                } else {
                  switch (response.status) {
                    case "ready":
                    case "ok":
                    case "error":
                      // If there is an error, indicate this
                      if (response.status === "error") {
                        // Process the error message
                        if ("msg" in response) {
                          r = response['msg'];
                          if (typeof r === "string") {
                            $(err).html("Error: " + response['msg']);
                          } else {
                            lHtml.push("Errors:");
                            for (k in r) {
                              lHtml.push("<br /><b>" + k + "</b>: <code>" + r[k][0] + "</code>");
                            }
                            $(err).html(lHtml.join("\n"));
                          }
                        } else {
                          $(err).html("<code>There is an error</code>");
                        }
                      } else {
                        // There is NO ERROR, all is well...
                        // Deletion has gone well, so renew showing the manuscript
                        window.location.href = manusurl;
                      }
                      break;
                    default:
                      // Something went wrong -- show the page or not?
                      $(err).html("The status returned is unknown: " + response.status);
                      break;
                  }
                }
              });

              ru.lila.seeker.init_events();
              ru.lila.init_typeahead();
              break;
            case "save":
              // Enter into save mode
              // (1) get the target id where the summary should later come
              bNew = ($("#sermon_number").attr("new") !== undefined);
              if (bNew) {
                manusurl = $("#canwit_edit").attr("manusurl");
              } else {
                elSermon = "#sermon-number-" + number;
              }
              // (2) Get the form data
              data = $(el).closest("form").serializeArray();
              // (2) Get the manuscript id
              parent = $("#canwit_edit").attr("parent");
              // Add this to the data
              if (parent !== undefined) {
                data.push({ 'name': 'manuscript_id', 'value': parent });
              }
              // Add the action: edit
              data.push({ 'name': 'action', 'value': "edit" });
              // (3) Send to the server
              $.post(targeturl, data, function (response) {
                var lHtml = [], i, r, k;

                // Action depends on the (JSON!) response
                if (response === undefined || response === null || !("status" in response)) {
                  private_methods.errMsg("No status returned");
                } else {
                  switch (response.status) {
                    case "ready":
                    case "ok":
                    case "error":
                      if ("html" in response) {
                        // If there is an error, indicate this
                        if (response.status === "error") {
                          if ("msg" in response) {
                            r = response['msg'];
                            if (typeof r === "string") {
                              $(err).html("Error: " + response['msg']);
                            } else {
                              lHtml.push("Errors:");
                              for (k in r) {
                                lHtml.push("<br /><b>" + k + "</b>: <code>" + r[k][0] + "</code>");
                              }
                              $(err).html(lHtml.join("\n"));
                            }
                          } else {
                            $(err).html("<code>There is an error</code>");
                          }
                        } else {
                          // There is NO ERROR, all is well...
                          // Check if this is a NEW sermon
                          if (bNew) {
                            // Load and show the whole manuscript
                            window.location.href = manusurl;
                          } else {
                            // Show the HTML in the VIEW-MODE part of elSermon
                            $(elSermon).find(".view-mode").first().html(response['html']);
                            // Make sure the correct part is visible
                            $(elSermon).find(".view-mode").removeClass("hidden");
                            $(elSermon).find(".edit-mode").addClass("hidden");
                            // And now shut down the editable part
                            $(".edit-sermon").addClass("hidden");
                            $("#canwit_edit").html("");
                          }
                        }
                      } else {
                        // Send a message
                        $(err).html("<i>There is no <code>html</code> in the response from the server</i>");
                      }
                      break;
                    default:
                      // Something went wrong -- show the page or not?
                      $(err).html("The status returned is unknown: " + response.status);
                      break;
                  }
                }
              });
              break;
          }

        } catch (ex) {
          private_methods.errMsg("sermo_edit", ex);
        }
      },

      /**
       * manu_edit
       *   Switch between edit modes on this <tr>
       *   And if saving is required, then call the [targeturl] to send a POST of the form data
       *
       */
      manu_edit: function (el, sType, oParams) {
        var //el = this,
            sMode = "",
            colspan = "",
            targeturl = "",
            targetid = "",
            afterurl = "",
            targethead = null,
            lHtml = [],
            data = null,
            key = "",
            i=0,
            frm = null,
            bOkay = true,
            bReloading = false,
            manutype = "",
            err = "#little_err_msg",
            elTr = null,
            elView = null,
            elEdit = null;

        try {
          // Possibly correct [el]
          if (el !== undefined && "currentTarget" in el) { el = el.currentTarget; }
          // Get the mode
          if (sType !== undefined && sType !== "") {
            sMode = sType;
          } else {
            sMode = $(el).attr("mode");
          }
          // Get the <tr>
          elTr = $(el).closest("td");
          // Get the manutype
          manutype = $(el).attr("manutype");
          if (manutype === undefined) { manutype = "other"; }

          // Get alternative parameters from [oParams] if this is defined
          if (oParams !== undefined) {
            if ('manutype' in oParams) { manutype = oParams['manutype']; }
          }

          // Check if we need to take the table
          if ($(elTr).hasClass("table")) {
            elTr = $(el).closest("table");
          }
          // Get the view and edit values
          elView = $(el).find(".view-mode").first();
          elEdit = $(el).find(".edit-mode").first();

          // Action depends on the mode
          switch (sMode) {
            case "skip":
              return;
              break;
            case "edit":
              // Make sure all targetid's that need opening are shown
              $(elTr).find(".view-mode:not(.hidden)").each(function () {
                var elTarget = $(this).attr("targetid");
                var targeturl = $(this).attr("targeturl");

                frm = $(el).closest("form");
                data = frm.serializeArray();
                if (elTarget !== undefined && elTarget !== "") {
                  // Do we have a targeturl?
                  if (targeturl !== undefined && targeturl !== "") {
                    // Make a post to the targeturl
                    $.post(targeturl, data, function (response) {
                      // Action depends on the response
                      if (response === undefined || response === null || !("status" in response)) {
                        private_methods.errMsg("No status returned");
                      } else {
                        switch (response.status) {
                          case "ready":
                          case "ok":
                            if ("html" in response) {
                              // Show the HTML in the targetid
                              $("#" + elTarget).html(response['html']);
                            }
                            // In all cases: open the target
                            $("#" + elTarget).removeClass("hidden");
                            // And make sure typeahead works
                            ru.lila.init_typeahead();
                            break;
                        }
                      }
                    });
                  } else {
                    // Just open the target
                    $("#" + elTarget).removeClass("hidden");
                  }
                }
              });
              // Go to edit mode
              $(elTr).find(".view-mode").addClass("hidden");
              $(elTr).find(".edit-mode").removeClass("hidden");
              $(elTr).find(".new-mode").removeClass("hidden");
              // Make sure typeahead works here
              ru.lila.init_typeahead();
              break;
            case "view":
            case "new":
              // Get any possible targeturl
              targeturl = $(el).attr("targeturl");
              targetid = $(el).attr("targetid");
              // If the targetid is specified, we need to get it from there
              if (targetid === undefined || targetid === "") {
                // No targetid specified: just open the target url
                window.location.href = targeturl;
              } else if (loc_bManuSaved) {
                loc_bManuSaved = false;
                // Refresh page
                window.location.href = window.location.href;
              } else {
                switch (manutype) {
                  case "goldlink":
                  case "goldnew":
                  case "newgoldlink":
                    targethead = $("#" + targetid);
                    break;
                  case "goldlinkclose":
                    targethead = $("#" + targetid).closest(".goldlink");
                    $(targethead).addClass("hidden");
                    $(elTr).find(".edit-mode").addClass("hidden");
                    $(elTr).find(".view-mode").removeClass("hidden");
                    return;
                  default:
                    targethead = $("#" + targetid).closest("tr.gold-head");
                    if (targethead !== undefined && targethead.length > 0) {
                      // Targetid is specified: check if we need to close
                      if (!$(targethead).hasClass("hidden")) {
                        // Close it
                        $(targethead).addClass("hidden");
                        return;
                      }
                    } else if ($("#" + targetid).attr("showing") !== undefined) {
                      if ($("#" + targetid).attr("showing") === "true") {
                        $("#" + targetid).attr("showing", "false");
                        $("#" + targetid).html("");
                        return;
                      }
                    }
                    break;
                }

                // There is a targetid specified, so make a GET request for the information and get it here
                data = [];
                // Check if there are any parameters in [oParams]
                if (oParams !== undefined) {
                  for (key in oParams) {
                    data.push({'name': key, 'value': oParams[key]});
                  }
                }

                $.get(targeturl, data, function (response) {
                  // Action depends on the response
                  if (response === undefined || response === null || !("status" in response)) {
                    private_methods.errMsg("No status returned");
                  } else {
                    switch (response.status) {
                      case "ready":
                      case "ok":
                      case "error":
                        if ("html" in response) {
                          // Show the HTML in the targetid
                          $("#" + targetid).html(response['html']);
                          // Make sure invisible ancestors show up
                          $("#" + targetid).closest(".hidden").removeClass("hidden");
                          // Indicate that we are showing here
                          $("#" + targetid).attr("showing", "true");

                          switch (manutype) {
                            case "goldsermon":
                              // Close any other edit-mode items
                              $(targethead).closest("table").find(".edit-mode").addClass("hidden");
                              // Open this particular edit-mode item
                              $(targethead).removeClass("hidden");
                              break;
                            case "goldlink":
                              $(el).closest("table").find(".edit-mode").addClass("hidden");
                              $(el).closest("table").find(".view-mode").removeClass("hidden");
                              $(elTr).find(".edit-mode").removeClass("hidden");
                              $(elTr).find(".view-mode").addClass("hidden");
                              break;
                            case "goldnew":
                              // Use the new standard approach for *NEW* elements
                              $("#" + targetid).closest(".subform").find(".edit-mode").removeClass("hidden");
                              $("#" + targetid).closest(".subform").find(".view-mode").addClass("hidden");
                              break;
                            default:
                              break;
                          }

                          // Check on specific modes
                          if (sMode === "new") {
                            $("#" + targetid).find(".edit-mode").removeClass("hidden");
                            $("#" + targetid).find(".view-mode").addClass("hidden");
                            // This is 'new', so don't show buttons cancel and delete
                            $("#" + targetid).find("a[mode='cancel'], a[mode='delete']").addClass("hidden");
                            // Since this is new, don't show fields that may not be shown for new
                            $("#" + targetid).find(".edit-notnew").addClass("hidden");
                            $("#" + targetid).find(".edit-new").removeClass("hidden");
                          } else {
                            // Just viewing means we can also delete...
                            // What about CANCEL??
                            // $("#" + targetid).find("a[mode='delete']").addClass("hidden");
                          }

                          // If there is an error, indicate this
                          if (response.status === "error") {
                            if ("msg" in response) {
                              if (typeof response['msg'] === "object") {
                                lHtml = []
                                lHtml.push("Errors:");
                                $.each(response['msg'], function (key, value) { lHtml.push(key + ": " + value); });
                                $(err).html(lHtml.join("<br />"));
                              } else {
                                $(err).html("Error: " + response['msg']);
                              }
                            } else {
                              $(err).html("<code>There is an error</code>");
                            }
                          }
                        } else {
                          // Send a message
                          $(err).html("<i>There is no <code>html</code> in the response from the server</i>");
                        }
                        break;
                      default:
                        // Something went wrong -- show the page or not?
                        $(err).html("The status returned is unknown: " + response.status);
                        break;
                    }
                  }
                  switch (manutype) {
                    case "goldlink":
                    case "goldnew":
                      break;
                    default:
                      // Return to view mode
                      $(elTr).find(".view-mode").removeClass("hidden");
                      $(elTr).find(".edit-mode").addClass("hidden");
                      // Hide waiting symbol
                      $(elTr).find(".waiting").addClass("hidden");
                      break;
                  }
                  // Perform init again
                  ru.lila.init_typeahead();
                  ru.lila.seeker.init_events();
                });

              }
              break;
            case "save":
              // Do we have an afterurl?
              afterurl = $(el).attr("afterurl");

              // Show waiting symbol
              $(elTr).find(".waiting").removeClass("hidden");

              // Make sure we know where the error message should come
              if ($(err).length === 0) { err = $(".err-msg").first();}

              // Get any possible targeturl
              targeturl = $(el).attr("targeturl");
              targetid = $(el).attr("targetid");

              // What if no targetid is specified?
              if (targetid === undefined || targetid === "") {
                // Then we need the parent of our closest enclosing table
                targetid = $(el).closest("form").parent();
              } else {
                targetid = $("#" + targetid);
              }

              // Check
              if (targeturl === undefined) { $(err).html("Save: no <code>targeturl</code> specified"); bOkay = false }
              if (bOkay && targetid === undefined) { $(err).html("Save: no <code>targetid</code> specified"); }

              // Get the form data
              frm = $(el).closest("form");
              if (bOkay && frm === undefined) { $(err).html("<i>There is no <code>form</code> in this page</i>"); }

              // Either POST the request
              if (bOkay) {
                // Get the data into a list of k-v pairs
                data = $(frm).serializeArray();
                // Adapt the value for the [library] based on the [id] 
                // Try to save the form data: send a POST
                $.post(targeturl, data, function (response) {
                  // Action depends on the response
                  if (response === undefined || response === null || !("status" in response)) {
                    private_methods.errMsg("No status returned");
                  } else {
                    switch (response.status) {
                      case "error":
                        // Indicate there is an error
                        bOkay = false;
                        // Show the error in an appropriate place
                        if ("msg" in response) {
                          if (typeof response['msg'] === "object") {
                            lHtml = [];
                            lHtml.push("Errors:");
                            $.each(response['msg'], function (key, value) { lHtml.push(key + ": " + value); });
                            $(err).html(lHtml.join("<br />"));
                          } else {
                            $(err).html("Error: " + response['msg']);
                          }
                        } else if ("errors" in response) {
                          lHtml = [];
                          lHtml.push("<h4>Errors</h4>");
                          for (i = 0; i < response['errors'].length; i++) {
                            $.each(response['errors'][i], function (key, value) {
                              lHtml.push("<b>"+ key + "</b>: </i>" + value + "</i>");
                            });
                          }
                          $(err).html(lHtml.join("<br />"));
                        } else if ("error_list" in response) {
                          lHtml = [];
                          lHtml.push("Errors:");
                          $.each(response['error_list'], function (key, value) { lHtml.push(key + ": " + value); });
                          $(err).html(lHtml.join("<br />"));
                        } else {
                          $(err).html("<code>There is an error</code>");
                        }
                        break;
                      case "ready":
                      case "ok":
                        // First check for afterurl
                        if (afterurl !== undefined && afterurl !== "") {
                          // Make sure we go to the afterurl
                          window.location = afterurl;
                        }
                        if ("html" in response) {
                          // Show the HTML in the targetid
                          $(targetid).html(response['html']);
                          // Signal globally that something has been saved
                          loc_bManuSaved = true;
                          // If an 'afternewurl' is specified, go there
                          if ('afternewurl' in response && response['afternewurl'] !== "") {
                            window.location = response['afternewurl'];
                            bReloading = true;
                          } else {
                            // nothing else yet
                          }
                        } else {
                          // Send a message
                          $(err).html("<i>There is no <code>html</code> in the response from the server</i>");
                        }
                        break;
                      default:
                        // Something went wrong -- show the page or not?
                        $(err).html("The status returned is unknown: " + response.status);
                        break;
                    }
                  }
                  if (!bReloading && bOkay) {
                    // Return to view mode
                    $(elTr).find(".view-mode").removeClass("hidden");
                    $(elTr).find(".edit-mode").addClass("hidden");
                    // Hide waiting symbol
                    $(elTr).find(".waiting").addClass("hidden");
                    // Perform init again
                    ru.lila.seeker.init_events();
                  }
                });
              } else {
                // Or else stop waiting - with error message above
                $(elTr).find(".waiting").addClass("hidden");
              }

              break;
            case "cancel":
              // Make sure all targetid's that need closing are hidden
              $(elTr).find(".edit-mode:not(.hidden)").each(function () {
                var elTarget = $(this).attr("targetid");
                if (elTarget !== undefined && elTarget !== "") {
                  $("#" + elTarget).addClass("hidden");
                }
              });
              // Go to view mode without saving
              $(elTr).find(".view-mode").removeClass("hidden");
              $(elTr).find(".edit-mode").addClass("hidden");
              $(elTr).find(".new-mode").addClass("hidden");
              break;
            case "delete":
              // Do we have an afterurl?
              afterurl = $(el).attr("afterurl");

              // Check if we are under a delete-confirm
              if (!$(el).closest("div").hasClass("delete-confirm")) {
                // Ask for confirmation
                // NOTE: we cannot be more specific than "item", since this can be manuscript or sermongold
                if (!confirm("Do you really want to remove this item?")) {
                  // Return from here
                  return;
                }
              }
              // Show waiting symbol
              $(elTr).find(".waiting").removeClass("hidden");

              // Get any possible targeturl
              targeturl = $(el).attr("targeturl");

              // Determine targetid from own
              targetid = $(el).closest(".gold-head");
              targethead = $(targetid).prev();

              // Check
              if (targeturl === undefined) { $(err).html("Save: no <code>targeturl</code> specified"); bOkay = false }

              // Get the form data
              frm = $(el).closest("form");
              if (bOkay && frm === undefined) { $(err).html("<i>There is no <code>form</code> in this page</i>"); }
              // Either POST the request
              if (bOkay) {
                // Get the data into a list of k-v pairs
                data = $(frm).serializeArray();
                // Add the delete mode
                data.push({ name: "action", value: "delete" });

                // Try to delete: send a POST
                $.post(targeturl, data, function (response) {
                  // Action depends on the response
                  if (response === undefined || response === null || !("status" in response)) {
                    private_methods.errMsg("No status returned");
                  } else {
                    switch (response.status) {
                      case "ready":
                      case "ok":
                        // Do we have afterdelurl afterurl?
                        // If an 'afternewurl' is specified, go there
                        if ('afterdelurl' in response && response['afterdelurl'] !== "") {
                          window.location = response['afterdelurl'];
                        } else if (afterurl === undefined || afterurl === "") {
                          // Delete visually
                          $(targetid).remove();
                          $(targethead).remove();
                        } else {
                          // Make sure we go to the afterurl
                          window.location = afterurl;
                        }
                        break;
                      case "error":
                        if ("html" in response) {
                          // Show the HTML in the targetid
                          $(err).html(response['html']);
                          // If there is an error, indicate this
                          if (response.status === "error") {
                            if ("msg" in response) {
                              if (typeof response['msg'] === "object") {
                                lHtml = []
                                lHtml.push("Errors:");
                                $.each(response['msg'], function (key, value) { lHtml.push(key + ": " + value); });
                                $(err).html(lHtml.join("<br />"));
                              } else {
                                $(err).html("Error: " + response['msg']);
                              }
                            } else {
                              $(err).html("<code>There is an error</code>");
                            }
                          } 
                        } else {
                          // Send a message
                          $(err).html("<i>There is no <code>html</code> in the response from the server</i>");
                        }
                        break;
                      default:
                        // Something went wrong -- show the page or not?
                        $(err).html("The status returned is unknown: " + response.status);
                        break;
                    }
                  }
                  // Return to view mode
                  $(elTr).find(".view-mode").removeClass("hidden");
                  $(elTr).find(".edit-mode").addClass("hidden");
                  // Hide waiting symbol
                  $(elTr).find(".waiting").addClass("hidden");
                  // Perform init again
                  ru.lila.seeker.init_events();
                });
              } else {
                // Or else stop waiting - with error message above
                $(elTr).find(".waiting").addClass("hidden");
              }


              break;
          }
        } catch (ex) {
          private_methods.errMsg("manu_edit", ex);
        }
      },


      /**
       * goto_url
       *   Go to the indicated target URL
       *
       */
      goto_url: function (target) {
        try {
          location.href = target;
        } catch (ex) {
          private_methods.errMsg("goto_url", ex);
        }
      },

      /**
       * gold_row_edit
       *   Switch everything in the current <tr> according to the mode
       *
       */
      gold_row_edit: function (el, mode, option) {
        var elTr = null,
            elDiv = null;

        try {
          // Get to the <tr>
          elTr = $(el).closest("tr");
          // Action depends on mode
          switch (mode) {
            case "edit":
              // Start editing
              $(elTr).find(".edit-mode").removeClass("hidden");
              $(elTr).find(".view-mode").addClass("hidden");
              $(el).closest("td").addClass("hightlighted");
              if (option !== undefined && option === "select2") {
                elDiv = $(el).closest("div[id]");

                ru.lila.seeker.init_select2($(elDiv).attr("id"));
              }
              break;
            case "view":
              $(el).closest("td").removeClass("hightlighted");
              // Save edit results, post the results and if all is well, show the view

              // If everything went well show the view mode
              $(elTr).find(".edit-mode").addClass("hidden");
              $(elTr).find(".view-mode").removeClass("hidden");
              break;
          }
        } catch (ex) {
          private_methods.errMsg("gold_row_edit", ex);
        }
      },

      /**
       * base_sermon
       *   Base the sermon on the gold-sermon identified by sClass
       *
       */
      base_sermon: function (el, sClass) {
        var frm = null,
            url = "",
            data = null,
            goldid = "";

        try {
          // Get to the form I'm in
          frm = $(el).closest("form");
          // Get the initial URL
          url = $(el).attr("targeturl");
          // Does it have a number for the gold sermon?
          if (url.indexOf("goldid") < 0 && !url.match(/\/\d+\/$/i)) {
            // Find the gold-sermon ID
            goldid = $(frm).find("." + sClass + " input").first().val();
            // Get the values of this gold sermonid
            url = url + "?goldid=" + goldid;
          }
          $.get(url, null, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ok":
                  // Process the results
                  data = response['data'];
                  $("#id_sermo-incipit").val(data['incipit']);
                  $("#id_sermo-explicit").val(data['explicit']);
                  $("#id_sermo-author").val(data['author']);
                  $("#id_sermo-authorname").val(data['authorname']);
                  // Set editing mode
                  $(".sermon-details a[mode=edit]").click();
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker base_sermon)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("base_sermon", ex);
        }
      },

      /**
       * delete_confirm
       *   Open the next <tr> to get delete confirmation (or not)
       *
       */
      delete_confirm: function (el, bNeedConfirm) {
        var elDiv = null;

        try {
          if (bNeedConfirm === undefined) { bNeedConfirm = true; }
          // Action depends on the need for confirmation
          if (bNeedConfirm) {
            // Find the [.delete-row] to be shown
            elDiv = $(el).closest("tr").find(".delete-confirm").first();
            if (elDiv.length === 0) {
              // Try goint to the next <tr>
              elDiv = $(el).closest("tr").next("tr.delete-confirm");
            }
            $(elDiv).removeClass("hidden");
          } else {

          }
        } catch (ex) {
          private_methods.errMsg("delete_confirm", ex);
        }
      },

      /**
       * delete_cancel
       *   Hide this <tr> and cancel the delete
       *
       */
      delete_cancel: function (el) {
        try {
          $(el).closest("div.delete-confirm").addClass("hidden");
        } catch (ex) {
          private_methods.errMsg("delete_cancel", ex);
        }
      },

      /**
       * elevate_confirm
       *   Open the next <tr> to get delete confirmation (or not)
       *
       */
      elevate_confirm: function (el, bNeedConfirm) {
        var elDiv = null;

        try {
          if (bNeedConfirm === undefined) { bNeedConfirm = true; }
          // Action depends on the need for confirmation
          if (bNeedConfirm) {
            // Find the [.elevate-row] to be shown
            elDiv = $(el).closest("tr").find(".elevate-confirm").first();
            if (elDiv.length === 0) {
              // Try goint to the next <tr>
              elDiv = $(el).closest("tr").next("tr.elevate-confirm");
            }
            if ($(elDiv).hasClass("hidden")) {
              $(elDiv).removeClass("hidden");
            } else {
              $(elDiv).html(loc_sWaiting);
            }
          } else {

          }
        } catch (ex) {
          private_methods.errMsg("elevate_confirm", ex);
        }
      },

      /**
       * elevate_cancel
       *   Hide this <tr> and cancel the delete
       *
       */
      elevate_cancel: function (el) {
        try {
          $(el).closest("div.elevate-confirm").addClass("hidden");
        } catch (ex) {
          private_methods.errMsg("elevate_cancel", ex);
        }
      },

      /**
       * network_stop
       *   Stop the visualization within [elStart]
       *
       */
      network_stop: function (elStart) {
        var elMain = null,
            targeturl = "",
            frm = null,
            elSvg = null;
        try {
          // Get to the container inside which I am
          elMain = $(elStart).closest(".container-small");
          targeturl = $(elStart).attr("targeturl");
          // REmove the SVG
          elSvg = $(elMain).find("svg").first().html("");
          // Hide myself
          $(elMain).addClass("hidden");
          // Make sure the form's action is correct
          frm = $(elMain).find("form").first();
          $(frm).attr("action", targeturl);
        } catch (ex) {
          private_methods.errMsg("network_stop", ex);
        }
      },

      /**
       * network_graph
       *   Create and show a network graph
       *
       */
      network_graph: function (elStart) {
        var targeturl = "",
            frm = null,
            data = null,
            options = {},
            link_list = null,
            node_list = null,
            watermark = "",
            lock_status = "",
            iWidth = 800,
            iHeight = 500,
            max_value = 0,
            divTarget = "super_network_graph",
            divWait = "#super_network_graph_wait",
            divNetwork = "#ssg_network_graph";

        try {
          if (private_methods.sticky_switch(elStart) === "leave") {
            return;
          }

          // Show what we can about the network
          $(divNetwork).removeClass("hidden");
          $(divWait).removeClass("hidden");
          $("#" + divTarget).find("svg").empty();
          // Get the target url
          frm = $(divNetwork).find("form").first();
          targeturl = $(frm).attr("action");
          // Get the data for the form
          data = frm.serializeArray();
          // Go and call...
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || typeof (response) === "string" || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              $(divWait).addClass("hidden");
              switch (response.status) {
                case "ready":
                case "ok":
                  // Then retrieve the data here: two lists
                  options['nodes'] = response.node_list;
                  options['links'] = response.link_list;
                  options['watermark'] = response.watermark;
                  if ("networkslider" in response) {
                    $("#networkslidervalue").html(response.networkslider);
                  }

                  // Other data
                  max_value = response.max_value;
                  options['target'] = divTarget;
                  options['width'] = iWidth;
                  options['height'] = iHeight;
                  options['factor'] = Math.min(iWidth, iHeight) / (2 * max_value);
                  options['legend'] = response.legend;

                  loc_network_options = options;

                  // Use D3 to draw a force-directed network
                  private_methods.draw_network(options);

                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker network_graph)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("network_graph", ex);
        }
      },

      /**
       * network_overlap_option
       *   Set or clear a network graph option
       *
       */
      network_overlap_option: function (elStart, type) {
        var status = elStart.checked,
            bShow = false,
            idx = -1,
            linktype = "";

        try {
          //loc_network_linktypes = null;
          // Action depends on [type]
          switch (type) {
            case "overlap_linktypes":
              // Hide or show the link types
              if ($(".linktypes").hasClass("hidden")) {
                // Show them
                $(".linktypes").removeClass("hidden");
                // Make sure to store this status
                loc_network_options[type] = true;
                // Push all the linktypes
                loc_network_linktypes = [];
                loc_network_linktypes.push("neq");
                loc_network_linktypes.push("prt");
                loc_network_linktypes.push("ech");
                loc_network_linktypes.push("uns");
              } else {
                // Hide and reset them
                $(".linktypes input").prop("checked", true);
                $(".linktypes").addClass("hidden");
                // And make sure all linktypes are shown again
                $("svg line").removeClass("hidden");
                // Make sure to store this status
                loc_network_options[type] = false;
                // Set the list to null again
                loc_network_linktypes = null;
              }
              // No need to continue
              return;
            case "overlap_linktype_change":
              ru.lila.seeker.network_overlap_linktype_changed(elStart);
              // No need to continue
              return;
            case "overlap_histcoll":
              // Hide or show the historical collection buttons
              if ($(".histcolls").hasClass("hidden")) {
                // Show the historical collection buttons
                $(".histcolls").removeClass("hidden");
              } else {
                // Unset the buttons
                $(".histcolls .badge.signature.gr").each(function (idx, el) {
                  $(el).removeClass("gr");
                  $(el).addClass("ot");
                });
                // Re-set what needs to be shown
                $(".overlap-node").each(function (idx, el) {
                  $(el).attr("class", "overlap-node");
                });
                // Hide the historical collection buttons
                $(".histcolls").addClass("hidden");
              }
              // No need to continue
              return;
          }
          loc_network_options[type] = status;
          // Redraw
          ru.lila.seeker.network_overlap(elStart);
 
        } catch (ex) {
          private_methods.errMsg("network_overlap_option", ex);
        }
      },

      /**
       * network_overlap_linktype_changed
       *   Hide or show a particular linktype
       *
       */
      network_overlap_linktype_changed: function (elStart) {
        var linktype, bShow, idx;
        try {
          linktype = $(elStart).val();
          bShow = $(elStart)[0].checked;
          if (bShow) {
            $("svg line." + linktype).each(function (idx, el) {
              var opacity = $(el).attr("stroke-opacity-copy"),
                  marker_end = $(el).attr("marker-end-copy");
              $(el).attr("stroke-opacity", opacity);
              $(el).attr("marker-end", marker_end);
            });
            loc_network_linktypes.push(linktype.replace("linktype_", ""));
          } else {
            $("svg line." + linktype)
              .attr("stroke-opacity", "0.02")
              .attr("marker-end", "");
            // Remove it from the list
            idx = loc_network_linktypes.indexOf(linktype.replace("linktype_", ""));
            if (idx >= 0) {
              loc_network_linktypes.splice(idx, 1);
            }
          }

        } catch (ex) {
          private_methods.errMsg("network_overlap_linktype_changed", ex);
        }
      },

      /**
       * network_graph_option
       *   Set or clear a network graph option
       *
       */
      overlap_marker_end: function (d) {
        var sArrow = "url(#arrow_uses)",
            sResponse = "";

        try {
          if (loc_network_options['overlap_direction'] === true) {
            // Check what kind of value is returned
            switch (d.spectype) {
              case "usd":
              case "usi":
                // Was:
                // sResponse = "";
                // Issue #511:
                sResponse = sArrow;
                break;
              case "udd":
              case "udi":
                // was:
                // sResponse = sArrow;
                // Issue #511:
                // sResponse = "";

                // Issue #521:
                sResponse = sArrow;
                break;
              default:
                sResponse = "";
                break;
            }
            return sResponse;
          } else {
            return "";
          }
        } catch (ex) {
          private_methods.errMsg("overlap_marker_end", ex);
        }
      },

      /**
       * overlap_stroke
       *   Helper function for network overlap
       *
       */
      overlap_stroke: function (d) {
        var m = "#222";  // Default blackish
        try {
          if ('overlap_alternatives' in loc_network_options &&
            loc_network_options['overlap_alternatives'] === true && 
            d.alternatives === "true") {
            m = "#00F";
          }
          return m;
        } catch (ex) {
          private_methods.errMsg("overlap_stroke", ex);
        }
      },

      /**
       * overlap_stroke_opacity
       *   Helper function for network overlap
       *
       */
      overlap_stroke_opacity: function (d, or) {
        var m = "0.2";  // Default light
        try {
          if ('overlap_direction' in loc_network_options && loc_network_options['overlap_direction'] === true) {
            // Check what kind of value is returned
            switch (d.spectype) {
              case "usi": // Indirect link
              case "udi": // Indirect link
                m = "0.2";  // See issue # 520
                break;
              case "usd": // Direct link
              case "udd": // Direct link
                m = "0.8";  // See issue # 520
                break;
              default:
                m = "0.3";  // Other link
                break;
            }
          } else {
            // Issue #510: make all lines equal in blackness
            // WAS: sm = or(d.value).toString();
            m = "0.8";
          }
          return m;
        } catch (ex) {
          private_methods.errMsg("overlap_stroke_opacity", ex);
        }
      },

      /**
       * network_overlap_setcolor
       *   Apply the color that has just been selected to the clicked node
       *
       */
      network_overlap_setcolor: function (elStart) {
        var color = "",
            elNode = null;

        try {
          // Get the selected color
          color = $(elStart).closest(".modal-dialog").find("input[type=color]").first().val();
          // Apply it to the currently selected node
          elNode = $("g[nodeid=" + loc_clicked_nodeid + "]").find("circle").first().attr("fill", color);
          // Somehow remember this list of manually defined colors
          loc_manual_colors.push({nodeid: loc_clicked_nodeid, color: color});
        } catch (ex) {
          private_methods.errMsg("network_overlap_setcolor", ex);
        }
      },

      /**
       * network_overlap_hist
       *   Color particular historical collections
       *
       */
      network_overlap_hist: function (elStart) {
        var dataid = 0,
            lst_data = [];

        try {
          if (elStart !== undefined) {
            // Perform switching on/off 
            if ($(elStart).hasClass("ot")) {
              // Switch 'on': transition from [gr] to [ot]
              $(elStart).removeClass("ot");
              $(elStart).addClass("gr");
            } else {
              // Switch 'off': transition from [ot] to [gr]
              $(elStart).removeClass("gr");
              $(elStart).addClass("ot");
            }
          }

          // Get the list of those that are switched on
          $(".histcolls span.gr").each(function (idx, el) {
            lst_data.push($(el).attr("data-id"));
          });

          // Re-visit what needs to be shown
          $(".overlap-node").each(function (idx, el) {
            var i = 0,
                count = 0,
                lst_ids = $(el).attr("hcs").split(",");
            // Check how many are matching
            for (i = 0; i < lst_ids.length; i++) {
              if (lst_data.indexOf(lst_ids[i]) >= 0) {
                count += 1;
              }
            }
            // Highlighting depends on the number of matches
            if (count === 0) {
              $(el).attr("class", "overlap-node");
            } else if (count === 1) {
              $(el).attr("class", "overlap-node node-highlight");
            } else if (count > 1) {
              $(el).attr("class", "overlap-node node-highlight-multi");
            }
          });

        } catch (ex) {
          private_methods.errMsg("network_overlap_hist", ex);
        }
      },

      /**
       * network_overlap
       *   Create and show a SSG-overlap network
       *
       */
      network_overlap: function (elStart) {
        var targeturl = "",
            frm = null,
            data = null,
            options = {},
            link_list = null,
            node_list = null,
            lock_status = "",
            fFactor = 1.6,
            iWidth = 1600,
            iHeight = 1000,
            max_value = 0,
            divTarget = "super_network_overlap",
            divWait = "#super_network_overlap_wait",
            divNetwork = "#ssg_network_overlap";

        try {
          // Figure out what course of action to take
          if (private_methods.sticky_switch(elStart) === "leave") {
            return;
          }

          // Show what we can about the network
          $(divNetwork).removeClass("hidden");
          $(divWait).removeClass("hidden");
          $("#" + divTarget).find("svg").empty();
          // Get the target url
          frm = $(divNetwork).find("form").first();
          targeturl = $(frm).attr("action");
          // Get the data for the form
          data = frm.serializeArray();
          // Go and call...
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || typeof(response) === "string" || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              $(divWait).addClass("hidden");
              switch (response.status) {
                case "ready":
                case "ok":
                  // Then retrieve the data here: two lists
                  options['nodes'] = response.node_list;
                  options['links'] = response.link_list;
                  options['watermark'] = response.watermark;
                  options['hcset'] = response.hist_set;
                  options['degree'] = 1;
                  if ("networkslider" in response) {
                    $("#network_overlap_slider_value").html(response.networkslider);
                    options['degree'] = parseInt(response.networkslider, 10);
                  }
                  // Calculate the width we have right now
                  iWidth = $("#" + divTarget).width();
                  // iHeight = iWidth / fFactor - 100;
                  iHeight = $("#" + divTarget).height();

                  // Process the hist coll buttons
                  if (response.hist_buttons !== undefined) {
                    $(".histcolls").first().html(response.hist_buttons);
                  }

                  // Other data
                  max_value = response.max_value;
                  options['target'] = divTarget;
                  options['width'] = iWidth;
                  options['height'] = iHeight;
                  options['factor'] = Math.min(iWidth, iHeight) / (2 * max_value);
                  options['legend'] = response.legend;
                  options['max_value'] = max_value;
                  options['max_group'] = response.max_group;

                  // Copy from [options] to [loc]
                  for (var key in options) {
                    loc_network_options[key] = options[key];
                  }
                  // COpy from [loc] to [options]
                  for (var key in loc_network_options) {
                    options[key] = loc_network_options[key];
                  }
                  // loc_network_options = options;

                  // Use D3 to draw a force-directed network
                  private_methods.draw_network_overlap(options);

                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker network_overlap)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("network_overlap", ex);
        }
      },

      /**
       * network_transmission
       *   Create and show a sermon-transmission network
       *
       */
      network_transmission: function (elStart) {
        var targeturl = "",
            frm = null,
            data = null,
            options = {},
            link_list = null,
            node_list = null,
            lock_status = "",
            fFactor = 1.6,
            iWidth = 1600,
            iHeight = 1000,
            max_value = 0,
            divTargetA = "super_network_trans_authors",
            divTarget = "super_network_trans",
            divWait = "#super_network_trans_wait",
            divNetwork = "#ssg_network_trans";

        try {
          // Figure out what course of action to take
          if (private_methods.sticky_switch(elStart) === "leave") {
            return;
          }

          // Show what we can about the network
          $(divNetwork).removeClass("hidden");
          $(divWait).removeClass("hidden");
          $("#" + divTarget).find("svg").empty();
          // Get the target url
          frm = $(divNetwork).find("form").first();
          targeturl = $(frm).attr("action");
          // Get the data for the form
          data = frm.serializeArray();
          // Go and call...
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              $(divWait).addClass("hidden");
              switch (response.status) {
                case "ready":
                case "ok":
                  // Then retrieve the data here: two lists
                  options['nodes'] = response.node_list;
                  options['links'] = response.link_list;
                  options['authors'] = response.author_list;
                  if ("networkslider" in response) {
                    $("#network_trans_slider_value").html(response.networkslider);
                  }
                  // Calculate the width we have right now
                  iWidth = $("#"+divTarget).width();
                  // iHeight = iWidth / fFactor - 100;
                  iHeight = $("#" + divTarget).height();

                  // Other data
                  max_value = response.max_value;
                  options['target'] = divTarget;
                  options['targetA'] = divTargetA;
                  options['width'] = iWidth;
                  options['height'] = iHeight;
                  options['factor'] = Math.min(iWidth, iHeight) / (2 * max_value);
                  options['legend'] = response.legend;
                  options['watermark'] = response.watermark;

                  loc_network_options = options;

                  // Use D3 to draw a force-directed network
                  private_methods.draw_network_trans(options);

                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker network_transmission)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("network_transmission", ex);
        }
      },

      /**
       * network_pca
       *   Create and show a PCA of SSGs
       *
       */
      network_pca: function (elStart) {
        var targeturl = "",
            frm = null,
            data = null,
            options = {},
            link_list = null,
            node_list = null,
            lock_status = "",
            iWidth = 800,
            iHeight = 500,
            max_value = 0,
            divTarget = "super_pca",
            divWait = "#super_pca_wait",
            divNetwork = "#ssg_pca";

        try {
          // Show what we can about the network
          $(divNetwork).removeClass("hidden");
          $(divWait).removeClass("hidden");
          $("#" + divTarget).find("svg").empty();
          // Get the target url
          frm = $(divNetwork).find("form").first();
          targeturl = $(frm).attr("action");
          // Get the data for the form
          data = frm.serializeArray();
          // Go and call...
          $.post(targeturl, data, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              $(divWait).addClass("hidden");
              switch (response.status) {
                case "ready":
                case "ok":
                  // Then retrieve the data here: two lists
                  options['nodes'] = response.node_list;
                  options['links'] = response.link_list;

                  // Other data
                  max_value = response.max_value;
                  options['target'] = divTarget;
                  options['width'] = iWidth;
                  options['height'] = iHeight;
                  options['factor'] = Math.min(iWidth, iHeight) / (2 * max_value);
                  options['legend'] = response.legend;
                  options['watermark'] = response.watermark;

                  loc_network_options = options;

                  // Use D3 to draw a force-directed network
                  private_methods.draw_network(options);

                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(targetid).html(response.msg);
                  } else {
                    $(targetid).html("An error has occurred (lila.seeker network_pca)");
                  }
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("network_pca", ex);
        }
      },

      /**
       * formset_setdel
       *   Set the delete checkbox of me
       *
       */
      formset_setdel: function (elStart) {

        try {
          // Set the delete value of the checkbox
          $(elStart).closest("td").find("input[type=checkbox]").first().prop("checked", true);
        } catch (ex) {
          private_methods.errMsg("formset_setdel", ex);
        }
      },

      /**
       * formset_update
       *   Send an Ajax POST request and process the response in a standard way
       *
       */
      formset_update: function (elStart, sAction) {
        var targetid = "",
            err = "#error_location",
            errdiv = null,
            waitclass = ".formset-wait",
            elWaitRow = null,
            data = [],
            lHtml = [],
            i = 0,
            frm = null,
            targeturl = "";

        try {
          // Get the correct error div
          errdiv = $(elStart).closest("form").find(err).first();
          if (errdiv === undefined || errdiv === null) {
            errdiv = $(err);
          }

          // Get attributes
          targetid = $(elStart).attr("targetid");
          targeturl = $(elStart).attr("targeturl");

          // Possibly set delete flag
          if (sAction !== undefined && sAction !== "") {
            switch (sAction) {
              case "delete":
                // Set the delete value of the checkbox
                $(elStart).closest("td").find("input[type=checkbox]").first().prop("checked", true);
                break;
              case "wait":
                // Set a waiting thing at the targetid
                $("#" + targetid).html(loc_sWaiting);
                // Make sure the caller is inactivated
                $(elStart).addClass("hidden");
                break;
            }
          }

          // Check if there is a waiting row
          elWaitRow = $(elStart).closest("table").find(waitclass);
          if (elWaitRow.length > 0) { $(elWaitRow).removeClass('hidden');}

          // Gather the data
          frm = $(elStart).closest("form");
          data = $(frm).serializeArray();
          data = jQuery.grep(data, function (item) {
            return (item['value'].indexOf("__counter__") < 0 && item['value'].indexOf("__prefix__") < 0);
          });
          $.post(targeturl, data, function (response) {
            // Show we have a response
            if (elWaitRow.length > 0) { $(elWaitRow).addClass('hidden'); }

            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "ok":
                case "error":
                  if ("html" in response) {
                    // If there is an error, indicate this
                    if (response.status === "error") {
                      if ("msg" in response) {
                        if (typeof response['msg'] === "object") {
                          lHtml = []
                          lHtml.push("Errors:");
                          $.each(response['msg'], function (key, value) { lHtml.push(key + ": " + value); });
                          $(errdiv).html(lHtml.join("<br />"));
                        } else {
                          $(errdiv).html("Error: " + response['msg']);
                        }
                      } else if ('error_list' in response) {
                        lHtml = []
                        lHtml.push("Errors:");
                        for (i = 0; i < response['error_list'].length; i++) {
                          lHtml.push(response['error_list'][i]);
                        }
                        $(errdiv).html(lHtml.join("<br />"));
                      } else {
                        $(errdiv).html("<code>There is an error</code>");
                      }
                      $(errdiv).removeClass("hidden");
                    } else {
                      // Show the HTML in the targetid
                      $("#" + targetid).html(response['html']);
                      // Action...
                      if (sAction !== undefined && sAction !== "") {
                        switch (sAction) {
                          case "wait":
                            $(elStart.removeClass("hidden"));
                            break;
                        }
                      }
                      // Check for other specific matters
                      switch (targetid) {
                        case "sermongold_eqset":
                          // We need to update 'sermongold_linkset'
                          ru.lila.seeker.do_get("sermongold_linkset");
                          break;
                        case "sermon_linkset":
                          // We need to update 'sermongold_ediset'
                          ru.lila.seeker.do_get("canwit_ediset");
                          break;
                      }
                    }
                    // But make sure events are back on again
                    ru.lila.seeker.init_events();
                  } else {
                    // Send a message
                    $(errdiv).html("<i>There is no <code>html</code> in the response from the server</i>");
                  }
                  break;
                default:
                  // Something went wrong -- show the page or not?
                  $(errdiv).html("The status returned is unknown: " + response.status);
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("formset_update", ex);
        }
      },

      /**
       * tabular_deleterow
       *   Delete one row from a tabular inline
       *
       */
      tabular_deleterow: function () {
        var sId = "",
            elDiv = null,
            elRow = null,
            elPrev = null,
            elDel = null,   // The delete inbox
            sPrefix = "",
            elForms = "",
            counter = $(this).attr("counter"),
            deleteurl = "",
            data = [],
            frm = null,
            bCounter = false,
            bHideOnDelete = false,
            iForms = 0,
            prefix = "simplerel",
            use_prev_row = false,   // Delete the previous row instead of the current one
            bValidated = false;

        try {
          // Get the prefix, if possible
          sPrefix = $(this).attr("extra");
          bCounter = (typeof counter !== typeof undefined && counter !== false && counter !== "");
          elForms = "#id_" + sPrefix + "-TOTAL_FORMS"
          // Find out just where we are
          elDiv = $(this).closest("div[id]")
          sId = $(elDiv).attr("id");
          // Find out how many forms there are right now
          iForms = $(elForms).val();
          frm = $(this).closest("form");
          // The validation action depends on this id
          switch (sId) {
            // gold
            case "glink_formset":
            case "gedi_formset":
            case "gftxt_formset":
            case "gsign_formset":
            case "gkw_formset":
            case "gcol_formset":
            // super
            case "scol_formset":
            case "ssglink_formset":
            // sermo 
            case "stog_formset":
            case "sdsignformset":
            case "sdcol_formset":
            case "sdkw_formset":
            // manu
            case "mprov_formset":
            case "mdr_formset":
            case "mkw_formset":
            case "mcol_formset":
            case "manu_search":
              //// Indicate that deep evaluation is needed
              //if (!confirm("Do you really want to remove this gold sermon? (All links to and from this gold sermon will also be removed)")) {
              //  // Return from here
              //  return;
              //}
              use_prev_row = false;
              bValidated = true;
              break;
          }
          // Continue with deletion only if validated
          if (bValidated) {
            // Get the deleteurl (if existing)
            deleteurl = $(this).attr("targeturl");
            // Get to the row
            if (use_prev_row) {
              // Delete both the current and the previous row
              elRow = $(this).closest("tr");
              elPrev = $(elRow).prev();
              $(elRow).remove();
              $(elPrev).remove();
            } else {
              // Only delete the current row
              elRow = $(this).closest("tr");
              // Do we need to hide or delete?
              if ($(elRow).hasClass("hide-on-delete")) {
                bHideOnDelete = true;
                $(elRow).addClass("hidden");
              } else {
                $(elRow).remove();
              }
            }

            // Further action depends on whether the row just needs to be hidden
            if (bHideOnDelete) {
              // Row has been hidden: now find and set the DELETE checkbox
              elDel = $(elRow).find("input:checkbox[name$='DELETE']");
              if (elDel !== null) {
                $(elDel).prop("checked", true);
              }
            } else {
              // Decrease the amount of forms
              iForms -= 1;
              $(elForms).val(iForms);

              // Re-do the numbering of the forms that are shown
              $(elDiv).find(".form-row").not(".empty-form").each(function (idx, elThisRow) {
                var iCounter = 0, sRowId = "", arRowId = [];

                iCounter = idx + 1;
                // Adapt the ID attribute -- if it EXISTS
                sRowId = $(elThisRow).attr("id");
                if (sRowId !== undefined) {
                  arRowId = sRowId.split("-");
                  arRowId[1] = idx;
                  sRowId = arRowId.join("-");
                  $(elThisRow).attr("id", sRowId);
                }

                if (bCounter) {
                  // Adjust the number in the FIRST <td>
                  $(elThisRow).find("td").first().html(iCounter.toString());
                }

                // Adjust the numbering of the INPUT and SELECT in this row
                $(elThisRow).find("input, select").each(function (j, elInput) {
                  // Adapt the name of this input
                  var sName = $(elInput).attr("name");
                  if (sName !== undefined) {
                    var arName = sName.split("-");
                    arName[1] = idx;
                    sName = arName.join("-");
                    $(elInput).attr("name", sName);
                    $(elInput).attr("id", "id_" + sName);
                  }
                });
              });
            }

            // The validation action depends on this id (or on the prefix)
            switch (sId) {
              case "search_mode_simple":
                // Update -- NOTE: THIS IS A LEFT-OVER FROM CESAR
                ru.lila.seeker.simple_update();
                break;
              case "ssglink_formset":
                if (deleteurl !== undefined &&  deleteurl !== "") {
                  // prepare data
                  data = $(frm).serializeArray();
                  data.push({ 'name': 'action', 'value': 'delete' });
                  $.post(deleteurl, data, function (response) {
                    // Action depends on the response
                    if (response === undefined || response === null || !("status" in response)) {
                      private_methods.errMsg("No status returned");
                    } else {
                      switch (response.status) {
                        case "ready":
                        case "ok":
                          // Refresh the current page
                          window.location = window.location;
                          break;
                        case "error":
                          // Show the error
                          if ('msg' in response) {
                            $(targetid).html(response.msg);
                          } else {
                            $(targetid).html("An error has occurred (lila.seeker tabular_deleterow)");
                          }
                          break;
                      }
                    }
                  });
                }
                break;
            }
          }

        } catch (ex) {
          private_methods.errMsg("tabular_deleterow", ex);
        }
      },

      /**
       * tabular_addrow
       *   Add one row into a tabular inline
       *
       */
      tabular_addrow: function (elStart, options) {
        // NOTE: see the definition of lAddTableRow above
        var arTdef = lAddTableRow,
            oTdef = {},
            rowNew = null,
            elTable = null,
            select2_options = {},
            iNum = 0,     // Number of <tr class=form-row> (excluding the empty form)
            sId = "",
            bSelect2 = false,
            i;

        try {
          // Find out just where we are
          if (elStart === undefined || elStart === null || $(elStart).closest("div").length === 0)
            elStart = $(this);
          sId = $(elStart).closest("div[id]").attr("id");
          // Process options
          if (options !== undefined) {
            for (var prop in options) {
              switch (prop) {
                case "select2": bSelect2 = options[prop]; break;
              }
            }
          } else {
            options = $(elStart).attr("options");
            if (options !== undefined && options === "select2") {
              bSelect2 = true;
            }
          }
          // Walk all tables
          for (i = 0; i < arTdef.length; i++) {
            // Get the definition
            oTdef = arTdef[i];
            if (sId === oTdef.table || sId.indexOf(oTdef.table) >= 0) {
              // Go to the <tbody> and find the last form-row
              elTable = $(elStart).closest("tbody").children("tr.form-row.empty-form")

              if ("select2_options" in oTdef) {
                select2_options = oTdef.select2_options;
              }

              // Perform the cloneMore function to this <tr>
              rowNew = ru.lila.seeker.cloneMore(elTable, oTdef.prefix, oTdef.counter);
              // Call the event initialisation again
              if (oTdef.events !== null) {
                oTdef.events();
              }
              // Possible Select2 follow-up
              if (bSelect2) {
                // Remove previous .select2
                $(rowNew).find(".select2").remove();
                // Execute djangoSelect2()
                $(rowNew).find(".django-select2").djangoSelect2(select2_options);
              }
              // Any follow-up activity
              if ('follow' in oTdef && oTdef['follow'] !== null) {
                oTdef.follow(rowNew);
              }
              // We are done...
              break;
            }
          }
        } catch (ex) {
          private_methods.errMsg("tabular_addrow", ex);
        }
      },

      /**
       *  cloneMore
       *      Add a form to the formset
       *      selector = the element that should be duplicated
       *      type     = the formset type
       *      number   = boolean indicating that re-numbering on the first <td> must be done
       *
       */
      cloneMore: function (selector, type, number) {
        var elTotalForms = null,
            total = 0;

        try {
          // Clone the element in [selector]
          var newElement = $(selector).clone(true);
          // Find the total number of [type] elements
          elTotalForms = $('#id_' + type + '-TOTAL_FORMS').first();
          // Determine the total of already available forms
          if (elTotalForms === null || elTotalForms.length ===0) {
            // There is no TOTAL_FORMS for this type, so calculate myself
          } else {
            // Just copy the TOTAL_FORMS value
            total = parseInt($(elTotalForms).val(), 10);
          }

          // Find each <input> element
          newElement.find(':input').each(function (idx, el) {
            var name = "",
                id = "",
                val = "",
                td = null;

            if ($(el).attr("name") !== undefined) {
              // Get the name of this element, adapting it on the fly
              name = $(el).attr("name").replace("__prefix__", total.toString());
              // Produce a new id for this element
              id = $(el).attr("id").replace("__prefix__", total.toString());
              // Adapt this element's name and id, unchecking it
              $(el).attr({ 'name': name, 'id': id }).val('').removeAttr('checked');
              // Possibly set a default value
              td = $(el).parent('td');
              if (td.length === 0) {
                td = $(el).parent("div").parent("td");
              }
              if (td.length === 1) {
                val = $(td).attr("defaultvalue");
                if (val !== undefined && val !== "") {
                  $(el).val(val);
                }
              }
            }
          });
          newElement.find('select').each(function (idx, el) {
            var td = null;

            if ($(el).attr("name") !== undefined) {
              td = $(el).parent('td');
              if (td.length === 0) { td = $(el).parent("div").parent("td"); }
              if (td.length === 0 || (td.length === 1 && $(td).attr("defaultvalue") === undefined)) {
                // Get the name of this element, adapting it on the fly
                var name = $(el).attr("name").replace("__prefix__", total.toString());
                // Produce a new id for this element
                var id = $(el).attr("id").replace("__prefix__", total.toString());
                // Adapt this element's name and id, unchecking it
                $(el).attr({ 'name': name, 'id': id }).val('').removeAttr('checked');
              }
            }
          });

          // Find each <label> under newElement
          newElement.find('label').each(function (idx, el) {
            if ($(el).attr("for") !== undefined) {
              // Adapt the 'for' attribute
              var newFor = $(el).attr("for").replace("__prefix__", total.toString());
              $(el).attr('for', newFor);
            }
          });

          // Look at the inner text of <td>
          newElement.find('td').each(function (idx, el) {
            var elInsideTd = $(el).find("td");
            var elText = $(el).children().first();
            if (elInsideTd.length === 0 && elText !== undefined) {
              var sHtml = $(elText).html();
              if (sHtml !== undefined && sHtml !== "") {
                sHtml = sHtml.replace("__counter__", (total+1).toString());
                $(elText).html(sHtml);
              }
              // $(elText).html($(elText).html().replace("__counter__", total.toString()));
            }
          });
          // Look at the attributes of <a> and of <input>
          newElement.find('a, input').each(function (idx, el) {
            // Iterate over all attributes
            var elA = el;
            $.each(elA.attributes, function (i, attrib) {
              var attrText = $(elA).attr(attrib.name).replace("__counter__", total.toString());
              // EK (20/feb): $(this).attr(attrib.name, attrText);
              $(elA).attr(attrib.name, attrText);
            });
          });


          // Adapt the total number of forms in this formset
          total++;
          $('#id_' + type + '-TOTAL_FORMS').val(total);

          // Adaptations on the new <tr> itself
          newElement.attr("id", "arguments-" + (total - 1).toString());
          newElement.attr("class", "form-row row" + total.toString());

          // Insert the new element before the selector = empty-form
          $(selector).before(newElement);

          // Should we re-number?
          if (number !== undefined && number) {
            // Walk all <tr> elements of the table
            var iRow = 1;
            $(selector).closest("tbody").children("tr.form-row").not(".empty-form").each(function (idx, el) {
              var elFirstCell = $(el).find("td").not(".hidden").first();
              $(elFirstCell).html(iRow);
              iRow += 1;
            });
          }

          // Return the new <tr> 
          return newElement;

        } catch (ex) {
          private_methods.errMsg("cloneMore", ex);
          return null;
        }
      },

      /**
       * toggle_click
       *   Action when user clicks an element that requires toggling a target
       *
       */
      toggle_click: function (elThis, class_to_close) {
        var elGroup = null,
            elTarget = null,
            sStatus = "";

        try {
          // Get the target to be opened
          elTarget = $(elThis).attr("targetid");
          // Sanity check
          if (elTarget !== null) {
            // Show it if needed
            if ($("#" + elTarget).hasClass("hidden")) {
              $("#" + elTarget).removeClass("hidden");
            } else {
              $("#" + elTarget).addClass("hidden");
              // Check if there is an additional class to close
              if (class_to_close !== undefined && class_to_close !== "") {
                $("." + class_to_close).addClass("hidden");
              }
            }
          }
        } catch (ex) {
          private_methods.errMsg("toggle_click", ex);
        }
      },

    };
  }($, ru.config));

  return ru;
}(jQuery, window.ru || {})); // window.ru: see http://stackoverflow.com/questions/21507964/jslint-out-of-scope

