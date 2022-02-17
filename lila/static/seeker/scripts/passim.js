var django = {
  "jQuery": jQuery.noConflict(true)
};
var jQuery = django.jQuery;
var $ = jQuery;

(function ($) {
  $(function () {
    $(document).ready(function () {
      // Initialize event listeners
      ru.lila.init_event_listeners( [] );
      $('#id_subtype >option').show();
      // Add 'copy' action to inlines
      ru.lila.tabinline_add_copy();
      // Initialize Bootstrap popover
      // Note: this is used when hovering over the question mark button
      $('[data-toggle="popover"]').popover();
    });
  });
})(django.jQuery);



// based on the type, action will be loaded

// var $ = django.jQuery.noConflict();

var ru = (function ($, ru) {
  "use strict";

  ru.lila = (function ($, config) {
    // Define variables for ru.collbank here
    var loc_example = "",
        loc_divErr = "lila_err",
        loc_typeahead_init = false,
        loc_sync_detail = {},
        loc_ta_done = [],
        loc_countries = [],
        loc_countriesL = [],
        loc_cities = [],
        loc_citiesL = [],
        loc_libraries = [],
        loc_librariesL = [],
        loc_authors = [],
        loc_authorsL = [],
        loc_origins = [],
        loc_originsL = [],
        loc_locations = [],         // Provenance and Origina locations for manuscripts
        loc_locationsL = [],
        loc_litrefs = [],           // Literatur references for manuscripts
        loc_litrefsL = [],
        loc_gldincipits = [],       // Use in sermongold_select.html
        loc_gldincipitsL = [],  
        loc_gldexplicits = [],      // Use in sermongold_select.html
        loc_gldexplicitsL = [],
        loc_srmincipits = [],       // Use in canwit_list.html
        loc_srmincipitsL = [],
        loc_srmexplicits = [],      // Use in canwit_list.html
        loc_srmexplicitsL = [],
        loc_signature = [],         // Use in sermongold_select.html
        loc_signatureL = [],
        loc_gldsiggryson = [],      // When creating a new Canwit
        loc_gldsiggrysonL = [],
        loc_gldsigclavis = [],      // When creating a new Canwit
        loc_gldsigclavisL = [],
        loc_srmsignature = [],      // Use in ???
        loc_srmsignatureL = [],
        loc_srmsiggryson = [],      // Use in canwit_list.html
        loc_srmsiggrysonL = [],
        loc_srmsigclavis = [],      // Use in canwit_list.html
        loc_srmsigclavisL = [],
        loc_manuidno = [],          // use in canwit_list.html
        loc_manuidnoL = [],
        loc_edition = [],           // critical editions that belong to a gold sermon
        loc_editionL = [],
        loc_keyword = [],           // Keywords that can belong to a sermongold or a canwit
        loc_keywordL = [],
        loc_collection = [],           // Collections
        loc_collectionL = [],
        loc_elInput = null,
        loc_sWaiting = " <span class=\"glyphicon glyphicon-refresh glyphicon-refresh-animate\"></span>",
        loc_cnrs_manu_url = "http://medium-avance.irht.cnrs.fr/Manuscrits/manuscritforetablissement",
        base_url = "",
        KEYS = {BACKSPACE: 8, TAB: 9, ENTER: 13, SHIFT: 16, CTRL: 17, ALT: 18, ESC: 27, SPACE: 32, PAGE_UP: 33, PAGE_DOWN: 34,
          END: 35, HOME: 36, LEFT: 37, UP: 38, RIGHT: 39, DOWN: 40, DELETE: 46 },
        oSyncTimer = null;


    // Private methods specification
    var private_methods = {
      /**
       * methodNotVisibleFromOutside - example of a private method
       * @returns {String}
       */
      methodNotVisibleFromOutside: function () {
        return "something";
      },
      get_template: function(sel_item, url) {
        var $back = $('<span><span></span></span>'),
            sText = "",
            frm = null,
            data = [],
            id = "";

        try {
          // Figure out what the correct text should be
          id = sel_item.id;
          // Normal behaviour:
          if (id !== undefined && id !== "") {
            // Figure out what the correct text should be
            data = { "id": sel_item.id };
            url = $("#__baseurl__").attr("url_home") + url;
            // Ask for the text
            $.get(url, data, function (response) {
              var short = "";

              short = response.name;
              $back.find("span").text(short);
              return $back;
            });
          } else {
            // Just showing...
            $back.find("span").text(sel_item.text);
          }

          return $back;
        } catch (ex) {
          private_methods.errMsg("get_template", ex);
        }
      },
      errClear: function() {
        $("#" + loc_divErr).html("");
      },
      errMsg: function (sMsg, ex) {
        var sHtml = "Error in [" + sMsg + "]<br>";
        if (ex !== undefined && ex !== null) {
          sHtml = sHtml + ex.message;
        }
        $("#" + loc_divErr).html(sHtml);
      }
    }

    // Public methods
    return {
      /**
       * init_event_listeners
       *    Initialize event listeners for this module
       */
      init_event_listeners: function (lst_typeahead) {
        var lst_use = [],
            base_url = "",
            div_ta = "#__typeaheads__",
            i = 0,
            lst_options = ["countries", "cities", "libraries", "origins", "locations", "litrefs", "authors",
                           "gldincipits", "srmincipits", "gldexplicits", "srmexplicits",
                           "signatures", "gldsiggrysons", "gldsigclavises", "srmsignatures", "siggrysons", "sigclavises",
                           "manuidnos", "editions", "keywords", "collections"],
            item = "";

        // Get the base URL
        base_url = $("#__baseurl__").text();
        if (lst_typeahead === undefined || lst_typeahead.length === 0) {
          if ($(div_ta).length > 0 && $(div_ta).text() !== "") {
            lst_typeahead = JSON.parse($(div_ta).text());
          }
        }

        // Set the elements that should be used
        for (i = 0; i < lst_options.length; i++) {
          item = lst_options[i];
          if (lst_typeahead === undefined || lst_typeahead.indexOf(item) > -1) { lst_use.push(item);}
        }

        if (!loc_typeahead_init || lst_use.length > 0) {
          for (i = 0; i < lst_use.length; i++) {
            item = lst_use[i];
            // Has this one been done recently?
            if (loc_ta_done.indexOf(item) < 0) {
              switch (item) {
                case "countries":
                  // Bloodhound: COUNTRY
                  loc_countries = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_countries will be an array of countries
                    // local: loc_countries,
                    prefetch: { url: base_url + 'api/countries/', cache: true },
                    remote: { url: base_url + 'api/countries/?country=%QUERY', wildcard: '%QUERY' }
                  });
                  break;
                case "cities":
                  // Bloodhound: CITY
                  loc_cities = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_cities will be an array of countries
                    local: loc_citiesL,
                    prefetch: { url: base_url + 'api/cities/', cache: true },
                    remote: {
                      url: base_url + 'api/cities/?city=',
                      replace: ru.lila.tt_city
                    }
                  });
                  break;
                case "libraries":
                  // Bloodhound: LIBRARY
                  loc_libraries = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_libraries will be an array of libraries
                    local: loc_librariesL,
                    prefetch: { url: base_url + 'api/libraries/', cache: true },
                    remote: {
                      url: base_url + 'api/libraries/?library=',
                      replace: ru.lila.tt_library
                    }
                  });
                  break;
                case "origins":
                  // Bloodhound: ORIGIN
                  loc_origins = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_libraries will be an array of libraries
                    local: loc_originsL,
                    prefetch: { url: base_url + 'api/origins/', cache: true },
                    remote: {
                      url: base_url + 'api/origins/?name=',
                      replace: ru.lila.tt_library
                    }
                  });
                  break;
                case "locations":
                  // Bloodhound: LOCATION
                  loc_locations = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_libraries will be an array of libraries
                    local: loc_locationsL,
                    prefetch: { url: base_url + 'api/locations/', cache: true },
                    remote: {
                      url: base_url + 'api/locations/?name=',
                      replace: ru.lila.tt_library
                    }
                  });
                  break;
                case "litrefs":
                  // Bloodhound: LITREF
                  loc_litrefs = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.whitespace,
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    // loc_litrefs will be an array of literature references
                    local: loc_litrefsL,
                    prefetch: { url: base_url + 'api/litrefs/', cache: true },
                    remote: {
                      url: base_url + 'api/litrefs/?name=',
                      replace: ru.lila.tt_library
                    }
                  });
                  break;
                case "authors":
                  // Bloodhound: AUTHOR
                  loc_authors = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_authorsL,
                    prefetch: { url: base_url + 'api/authors/list/', cache: true },
                    remote: {
                      url: base_url + 'api/authors/list/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "gldincipits":
                  // Bloodhound: gldincipit
                  loc_gldincipits = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_gldincipitsL,
                    prefetch: { url: base_url + 'api/gldincipits/', cache: true },
                    remote: {
                      url: base_url + 'api/gldincipits/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "srmincipits":
                  // Bloodhound: srmincipit
                  loc_srmincipits = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_srmincipitsL,
                    prefetch: { url: base_url + 'api/srmincipits/', cache: true },
                    remote: {
                      url: base_url + 'api/srmincipits/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "gldexplicits":
                  // Bloodhound: gldexplicit
                  loc_gldexplicits = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_gldexplicitsL,
                    prefetch: { url: base_url + 'api/gldexplicits/', cache: true },
                    remote: {
                      url: base_url + 'api/gldexplicits/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "srmexplicits":
                  // Bloodhound: srmexplicit
                  loc_srmexplicits = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_srmexplicitsL,
                    prefetch: { url: base_url + 'api/srmexplicits/', cache: true },
                    remote: {
                      url: base_url + 'api/srmexplicits/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "signatures":
                  // Bloodhound: SIGNATURE - SermonGold
                  loc_signature = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_signatureL,
                    prefetch: { url: base_url + 'api/gldsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/gldsignatures/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "gldsiggrysons":
                  // Bloodhound: SRMSIGGRYSON - Canwit
                  loc_gldsiggryson = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_gldsiggrysonL,
                    prefetch: { url: base_url + 'api/gldsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/gldsignatures/?type=gr&name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "gldsigclavises":
                  // Bloodhound: SRMSIGCLAVIS - Canwit
                  loc_gldsigclavis = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_gldsigclavisL,
                    prefetch: { url: base_url + 'api/gldsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/gldsignatures/?type=cl&name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "srmsignatures":
                  // Bloodhound: SRMSIGNATURE - SermonGold
                  loc_srmsignature = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_srmsignatureL,
                    prefetch: { url: base_url + 'api/srmsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/srmsignatures/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "siggrysons":
                  // Bloodhound: SRMSIGGRYSON - Canwit
                  loc_srmsiggryson = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_srmsiggrysonL,
                    prefetch: { url: base_url + 'api/srmsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/srmsignatures/?type=gr&name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "sigclavises":
                  // Bloodhound: SRMSIGCLAVIS - Canwit
                  loc_srmsigclavis = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_srmsigclavisL,
                    prefetch: { url: base_url + 'api/srmsignatures/', cache: true },
                    remote: {
                      url: base_url + 'api/srmsignatures/?type=cl&name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "manuidnos":
                  // Bloodhound: manuidno
                  loc_manuidno = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_manuidnoL,
                    prefetch: { url: base_url + 'api/manuidnos/', cache: true },
                    remote: {
                      url: base_url + 'api/manuidnos/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "editions":
                  // Bloodhound: EDITION
                  loc_edition = new Bloodhound({
                    datumTokenizer: function (myObj) {
                      return myObj;
                    },
                    queryTokenizer: function (myObj) {
                      return myObj;
                    },
                    // loc_countries will be an array of countries
                    local: loc_editionL,
                    prefetch: { url: base_url + 'api/editions/', cache: true },
                    remote: {
                      url: base_url + 'api/editions/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "keywords":
                  // Bloodhound: KEYWORD
                  loc_keyword = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of countries
                    local: loc_keywordL,
                    prefetch: { url: base_url + 'api/keywords/', cache: true },
                    remote: {
                      url: base_url + 'api/keywords/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                case "collections":
                  // Bloodhound: collection
                  loc_collection = new Bloodhound({
                    datumTokenizer: function (myObj) { return myObj; },
                    queryTokenizer: function (myObj) { return myObj; },
                    // loc_countries will be an array of collections
                    local: loc_collectionL,
                    prefetch: { url: base_url + 'api/collections/', cache: true },
                    remote: {
                      url: base_url + 'api/collections/?name=',
                      replace: function (url, uriEncodedQuery) {
                        url += encodeURIComponent(uriEncodedQuery);
                        return url;
                      }
                    }
                  });
                  break;
                default:
                  private_methods.errMsg("init_event_listeners: cannot initialize typeahead ["+item+"]");
                  break;
              }
              // Make sure to add the index to the list of done ones
              loc_ta_done.push(item);
            }
          }
          loc_typeahead_init = true;
        }

        // Initialize typeahead
        ru.lila.init_typeahead();

      },

      /**
       * init_typeahead
       *    Initialize the typeahead features, based on the existing bloodhound stuff
       */
      init_typeahead: function () {
        try {

          // First destroy them
          $(".typeahead.countries").typeahead('destroy');
          $(".typeahead.cities").typeahead('destroy');
          $(".typeahead.libraries").typeahead('destroy');
          $(".typeahead.origins").typeahead('destroy');
          $(".typeahead.locations").typeahead('destroy');
          $(".typeahead.litrefs").typeahead('destroy');
          $(".typeahead.authors").typeahead('destroy');
          $(".typeahead.gldincipits").typeahead('destroy');
          $(".typeahead.gldexplicits").typeahead('destroy');
          $(".typeahead.srmincipits").typeahead('destroy');
          $(".typeahead.srmexplicits").typeahead('destroy');
          $(".typeahead.signatures").typeahead('destroy');
          $(".typeahead.gldsiggrysons").typeahead('destroy');
          $(".typeahead.gldsigclavises").typeahead('destroy');
          $(".typeahead.srmsignatures").typeahead('destroy');
          $(".typeahead.siggrysons").typeahead('destroy');
          $(".typeahead.sigclavises").typeahead('destroy');
          $(".typeahead.editions").typeahead('destroy');
          $(".typeahead.keywords").typeahead('destroy');
          $(".typeahead.collections").typeahead('destroy');
          $(".typeahead.manuidnos").typeahead('destroy');

          // Make sure the signature types (gryson/clavis) are set correctly
          $(".editype-gr .signaturetype").each(function () {
            $(this).removeClass("signaturetype");
            $(this).addClass("gldsiggrysons");
            $(this).attr("placeholder", "Gryson code...");
          });
          $(".editype-cl .signaturetype").each(function () {
            $(this).removeClass("signaturetype");
            $(this).addClass("gldsigclavises");
            $(this).attr("placeholder", "Clavis code...");
          });

          // Explicitly clear them
          // loc_litrefs.clear();

          // Type-ahead: COUNTRY
          $(".form-row:not(.empty-form) .typeahead.countries, .manuscript-details .typeahead.countries").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            { name: 'countries', source: loc_countries, limit: 20, displayKey: "name",
              templates: { suggestion: function (item) { return '<div>' + item.name + '</div>'; } }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".country-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".country-key input").last().val("");
          });

          // Type-ahead: CITY
          $(".form-row:not(.empty-form) .typeahead.cities, .manuscript-details .typeahead.cities").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            { name: 'cities', source: loc_cities, limit: 25, displayKey: "name",
              templates: { suggestion: function (item) { return '<div>' + item.name + '</div>'; } }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".city-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".city-key input").last().val("");
          });

          // Type-ahead: LIBRARY
          $(".form-row:not(.empty-form) .typeahead.libraries, .manuscript-details .typeahead.libraries").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            { name: 'libraries', source: loc_libraries, limit: 25, displayKey: "name",
              templates: {
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".library-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".library-key input").last().val("");
          });

          // Type-ahead: ORIGIN
          $(".form-row:not(.empty-form) .typeahead.origins, .manuscript-details .typeahead.origins").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'origins', source: loc_origins, limit: 25, displayKey: "name",
              templates: {
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".origin-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".origin-key input").last().val("");
          });

          // Type-ahead: LOCATION
          $(".form-row:not(.empty-form) .typeahead.locations, .manuscript-details .typeahead.locations").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'locations', source: loc_locations, limit: 25, displayKey: "name",
              templates: {
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".location-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".location-key input").last().val("");
          });

          // Type-ahead: LITREF
          $(".form-row:not(.empty-form) .typeahead.litrefs, .manuscript-details .typeahead.litrefs").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'litrefs', source: loc_litrefs, limit: 25, displayKey: "name",
              templates: {
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".litref-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".litref-key input").last().val("");
          });

          // Type-ahead: AUTHOR -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.authors, tr .typeahead.authors").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'authors', source: loc_authors, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Not found</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".author-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".author-key input").last().val("");
          });

          // Type-ahead: gldincipit -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.gldincipits, tr .typeahead.gldincipits").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'gldincipits', source: loc_gldincipits, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact wording or # for whole words</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".gldincipit-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".gldincipit-key input").last().val("");
          });

          // Type-ahead: srmincipit -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.srmincipits, tr .typeahead.srmincipits").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'srmincipits', source: loc_srmincipits, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact wording or # for whole words</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".srmincipit-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".srmincipit-key input").last().val("");
          });

          // Type-ahead: gldexplicit -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.gldexplicits, tr:not(.empty-form) .typeahead.gldexplicits").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'gldexplicits', source: loc_gldexplicits, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact wording or # for whole words</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".gldexplicit-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".gldexplicit-key input").last().val("");
          });

          // Type-ahead: srmexplicit -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.srmexplicits, tr:not(.empty-form) .typeahead.srmexplicits").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'srmexplicits', source: loc_srmexplicits, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact wording or # for whole words</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".srmexplicit-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".srmexplicit-key input").last().val("");
          });

          // Type-ahead: SIGNATURE (SermonGold) -- NOTE: not in a form-row, but in a normal 'row'
          $("tr:not(.empty-form) .typeahead.signatures, .manuscript-details .typeahead.signatures").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'signatures', source: loc_signature, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".signature-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".signature-key input").last().val("");
          });

          // Type-ahead: Gld Gryson Signature
          $(".row .typeahead.gldsiggrysons, tr:not(.empty-form) .typeahead.gldsiggrysons").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'gldsiggrysons', source: loc_gldsiggryson, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".gldsiggryson-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".gldsiggryson-key input").last().val("");
          });

          // Type-ahead: Srm Clavis Signature
          $(".row .typeahead.gldsigclavises, tr:not(.empty-form) .typeahead.gldsigclavises").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'gldsigclavises', source: loc_gldsigclavis, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".gldsigclavis-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".gldsigclavis-key input").last().val("");
          });

          // Type-ahead: SRMSIGNATURE (Canwit) -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.srmsignatures, tr:not(.empty-form) .typeahead.srmsignatures").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'srmsignatures', source: loc_srmsignature, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".srmsignature-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".srmsignature-key input").last().val("");
          });

          // Type-ahead: Srm Gryson Signature
          $(".row .typeahead.siggrysons, tr:not(.empty-form) .typeahead.siggrysons").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'siggrysons', source: loc_srmsiggryson, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".siggryson-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".siggryson-key input").last().val("");
          });

          // Type-ahead: Srm Clavis Signature
          $(".row .typeahead.sigclavises, tr:not(.empty-form) .typeahead.sigclavises").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'sigclavises', source: loc_srmsigclavis, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark inexact code</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".sigclavis-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".sigclavis-key input").last().val("");
          });

          // Type-ahead: EDITION -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.editions, tr .typeahead.editions").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'editions', source: loc_edition, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark an inexact wording of an edition</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".edition-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".edition-key input").last().val("");
          });

          // Type-ahead: KEYWORD -- NOTE: not in a form-row, but in a normal 'row'
          $(".row .typeahead.keywords, tr .typeahead.keywords").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'keywords', source: loc_keyword, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark an inexact wording of a keyword</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".keyword-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".keyword-key input").last().val("");
          });

            // Type-ahead: collection -- NOTE: not in a form-row, but in a normal 'row'
            $(".row .typeahead.collections, tr .typeahead.collections").typeahead(
                { hint: true, highlight: true, minLength: 1 },
                {
                    name: 'collections', source: loc_collection, limit: 25, displayKey: "name",
                    templates: {
                        empty: '<p>Use the wildcard * to mark an inexact wording of a collection</p>',
                        suggestion: function (item) {
                            return '<div>' + item.name + '</div>';
                        }
                    }
                }
            ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
                $(this).closest("td").find(".collection-key input").last().val(suggestion.id);
            }).on('typeahead:open', function (e) {
                $(this).closest("td").find(".collection-key input").last().val("");
            });

          // Type-ahead: manuidno -- NOTE: not in a form-row, but in a normal 'row'
          $(".form-row:not(.empty-form) .typeahead.manuidnos, .manuscript-details .typeahead.manuidnos").typeahead(
            { hint: true, highlight: true, minLength: 1 },
            {
              name: 'manuidnos', source: loc_manuidno, limit: 25, displayKey: "name",
              templates: {
                empty: '<p>Use the wildcard * to mark an inexact wording of an manuidno</p>',
                suggestion: function (item) {
                  return '<div>' + item.name + '</div>';
                }
              }
            }
          ).on('typeahead:selected typeahead:autocompleted', function (e, suggestion, name) {
            $(this).closest("td").find(".manuidno-key input").last().val(suggestion.id);
          }).on('typeahead:open', function (e) {
            $(this).closest("td").find(".manuidno-key input").last().val("");
          });

          // Make sure we know which element is pressed in typeahead
          $(".form-row:not(.empty-form) .typeahead").on("keyup",
            function () {
              loc_elInput = $(this);
            });

          // Allow "Search on ENTER" from typeahead fields
          $(".form-row:not(.empty-form) .searching").on("keypress",
            function (evt) {
              var key = evt.which,  // Get the KEY information
                  start = null,
                  button = null;

              // Look for ENTER
              if (key === KEYS.ENTER) {
                // Find the 'Search' button
                button = $(this).closest("form").find("a[role=button]").last();                
                // Check for the inner text
                if ($(button)[0].innerText === "Search") {
                  // Found it
                  $(button).click();
                  evt.preventDefault();
                }
              }
            });

          // Make sure the twitter typeahead spans are maximized
          $("span.twitter-typeahead").each(function () {
            var style = $(this).attr("style");
            $(this).attr("style", style + " width: 100%;");
          });


        } catch (ex) {
          private_methods.errMsg("init_typeahead", ex);
        }
      },

      /**
       * litref_template
       *    Construct the template for a literature reference
       *
       */
      litref_template: function (sel_item) {
        return private_methods.get_template(sel_item, "api/litref/");
      },

      /**
       * ssglink_template
       *    Construct the template for a *link* from Canwit to a Super Sermon Gold
       *
       */
      ssglink_template: function (sel_item) {
        return private_methods.get_template(sel_item, "api/aslink/");
      },

      /**
       * as2as_template
       *    Construct the template for a *link* from an Authoritative Statement to an Authoritative Statement
       *
       */
      as2as_template: function (sel_item) {
        return private_methods.get_template(sel_item, "api/as2as/");
      },

      /**
       * as_template
       *    Construct the template for an Authoritative Statement
       *
       */
      as_template: function (sel_item) {
        return private_methods.get_template(sel_item, "api/as/");
      },

      /**
       * asdist_template
       *    Construct the template for an Authoritative Statement
       *
       */
      asdist_template: function (sel_item) {
        return private_methods.get_template(sel_item, "api/asdist/");
      },


      /**
       *  tt_country
       *    Bloodhound / remote / replace function for: COUNTRY
       */
      tt_country: function (url, uriEncodedQuery) {
        var elThis = this;

        try {

        } catch (ex) {
          private_methods.errMsg("tt_country", ex);
        }
      },

      /**
       *  tt_city
       *    Bloodhound / remote / replace function for: CITY
       */
      tt_city: function (url, uriEncodedQuery) {
        var elThis = loc_elInput,
            elRow = null,
            sPrefix = "id_",
            country = "";

        try {
          // Get to this row
          elRow = $(elThis).closest("tr").first();
          if (elRow === undefined || elRow === null) { elRow = $(this).closest("form"); }
          if (elRow.length > 0) {
            // Get the PREFIX from the first <input> that has an ID
            sPrefix = $(elRow).find("input[id]").first().attr("id");
            if (sPrefix.indexOf("-") > 0) {
              sPrefix = sPrefix.substr(0, sPrefix.lastIndexOf("-")) + "-";
            } 
          }

          // Fetch value for country in this line
          country = $("input[id=" + sPrefix + "country_ta]").val();
          if (country === undefined || country === "") {country = $("input[id=" + sPrefix + "country]").val();}
          // Build the URL with the components we have
          url += encodeURIComponent(uriEncodedQuery);
          // Possibly add country
          if (country) url += "&country=" + country;
          // Return the resulting URL
          return url;
        } catch (ex) {
          private_methods.errMsg("tt_city", ex);
        }
      },

      /**
       *  tt_library
       *    Bloodhound / remote / replace function for: LIBRARY
       */
      tt_library: function (url, uriEncodedQuery) {
        var elThis = loc_elInput,
            elRow = null,
            sPrefix = "id_",
            city = "",
            country = "";

        try {
          // Get to this row
          elRow = $(elThis).closest("tr").first();
          if (elRow === undefined || elRow === null) { elRow = $(this).closest("form");}
          if (elRow.length > 0) {
            // Get the PREFIX from the first <input> that has an ID
            sPrefix = $(elRow).find("input[id]").first().attr("id");
            sPrefix = sPrefix.substr(0, sPrefix.lastIndexOf("-")) + "-";
          }

          // Fetch values for city and country in this line
          city = $("input[id=" + sPrefix + "city_ta]").val();
          if (city === undefined || city === "") { city = $("input[id=" + sPrefix + "city]").val(); }
          country = $("input[id=" + sPrefix + "country_ta]").val();
          if (country === undefined || country === "") { country = $("input[id=" + sPrefix + "country]").val(); }
          // Build the URL with the components we have
          url += encodeURIComponent(uriEncodedQuery);
          // Possibly add country
          if (country) url += "&country=" + country;
          // Possibly add city
          if (city) url += "&city=" + city;
          // Return the resulting URL
          return url;
        } catch (ex) {
          private_methods.errMsg("tt_library", ex);
        }
      },

      /**
       *  form_submit
       *    Refer to this in an [onkeydown] item of an input box
       *    When the ENTER key is pressed, the nearest form is submitted
       */
      form_submit: function(e) {
        var target,
            targeturl = null,
            frm = null;

        try {
          // Get the event
          e = e || window.event;
          if (e.keyCode == 13) {
            // Get the target
            target = e.target || e.srcElement;
            // Find the form
            frm = $(target).closest("form");
            // If there is a downloadtype, then reset it
            $(frm).find("#downloadtype").val("");
            // if the form has a targeturl, use that in the action
            targeturl = $(frm).attr("targeturl");
            if (targeturl !== undefined && targeturl !== "") {
              $(frm).attr("action", targeturl);
            }
            // Make sure the GET method is used
            $(frm).attr("method", "GET");
            // Show we are waiting
            $("#waitingsign").removeClass("hidden");
            // Submit that form
            $(frm).submit();
          }
        } catch (ex) {
          private_methods.errMsg("form_submit", ex);
        }
      },

      /**
        * result_download
        *   Trigger creating and downloading a result CSV / XLSX / JSON
        *
        */
      post_download: function (elStart) {
        var ajaxurl = "",
            contentid = null,
            response = null,
            frm = null,
            el = null,
            sHtml = "",
            oBack = null,
            dtype = "",
            sMsg = "",
            method = "normal",
            data = [];

        try {
          // Clear the errors
          private_methods.errClear();

          // obligatory parameter: ajaxurl
          ajaxurl = $(elStart).attr("ajaxurl");
          contentid = $(elStart).attr("contentid");

          // Gather the information
          frm = $(elStart).closest(".container-small").find("form");
          if (frm.length === 0) {
            frm = $(elStart).closest("td").find("form");
            if (frm.length === 0) {
              frm = $(elStart).closest(".body-content").find("form");
              if (frm.length === 0) {
                frm = $(elStart).closest(".container-large.body-content").find("form");
              }
            }
          }
          // Check what we have
          if (frm === null || frm.length === 0) {
            // Didn't find the form
            private_methods.errMsg("post_download: could not find form");
          } else {
            // Make sure we take only the first matching form
            frm = frm.first();
          }
          // Get the download type and put it in the <input>
          dtype = $(elStart).attr("downloadtype");
          $(frm).find("#downloadtype").val(dtype);

          switch (method) {
            case "erwin":
              data = frm.serialize();
              $.post(ajaxurl, data, function (response) {
                var iready = 1;
              });
              break;
            default:
              // Set the 'action; attribute in the form
              frm.attr("action", ajaxurl);
              // Make sure we do a POST
              frm.attr("method", "POST");

              // Do we have a contentid?
              if (contentid !== undefined && contentid !== null && contentid !== "") {
                // Process download data
                switch (dtype) {
                  default:
                    // TODO: add error message here
                    return;
                }
              } else {
                // Do a plain submit of the form
                oBack = frm.submit();
              }
              break;
          }

          // Check on what has been returned
          if (oBack !== null) {

          }
        } catch (ex) {
          private_methods.errMsg("post_download", ex);
        }
      },

      /**
       * lib_manuscripts
       *   Get the manuscripts of the library
       *
       */
      lib_manuscripts: function (el) {
        var url = "",
            data = "",
            items = [],
            i = 0,
            html = [],
            sBack = "",
            frm = null,
            item = "",
            libName = "",
            idVille = "",
            target = "";

        try {
          // Which site to open when ready
          target = $(el).attr("data-target");

          // Close all other sites
          $(".lib-manuscripts").addClass("hidden");

          // Open my new site and show we are working
          $(target).removeClass("hidden");
          sBack = "Searching in the library..." + loc_sWaiting;
          $(target).find(".manuscripts-target").first().html(sBack);

          // Get the parameters
          idVille = $(el).attr("city");
          libName = $(el).attr("library");
          // Prepare the request for information
          if (base_url === "") {
            url = '/api/manuscripts/';
          } else {
            url = base_url + 'api/manuscripts/';
          }
          frm = $(el).closest("form");
          if (frm !== undefined) { data = $(frm).serializeArray(); }
          data.push({ "name": "city", "value": idVille });
          data.push({ "name": "library", "value": libName });
          // Request the information
          $.post(url, data, function (response) {
            if (response !== undefined) {
              // There is a respons object, but can we read it?
              html = [];
              for (i = 0; i < response.length; i++) {
                item = response[i];
                html.push("<span class='manuscript'>" + item + "</span>");
              }
              sBack = html.join("\n");
              $(target).find(".manuscripts-target").first().html(sBack);
              $(target).removeClass("hidden");
            } else {
              private_methods.errMsg("lib_manuscripts: undefined response ");
            }
          });
        } catch (ex) {
          private_methods.errMsg("lib_manuscripts", ex);
        }
      },
    
      /**
       * sent_click
       *   Show waiting symbol when sentence is clicked
       *
       */
      sent_click : function() {
        $("#sentence-fetch").removeClass("hidden");
      },

      /**
       * tabinline_add_copy
       *   Add a COPY button to all tabular inlines available
       */
      tabinline_add_copy: function () {
        $(".tabular .related-widget-wrapper").each(
          function (idx, obj) {
            // Find the first <a> child
            var chgNode = $(this).children("a").first();
            var sHref = $(chgNode).attr("href");
            if (sHref !== undefined) {
              // Remove from /change onwards
              var iChangePos = sHref.lastIndexOf("/change");
              if (iChangePos > 0) {
                sHref = sHref.substr(0, sHref.lastIndexOf("/change"));
                // Get the id
                var lastSlash = sHref.lastIndexOf("/");
                var sId = sHref.substr(lastSlash + 1);
                sHref = sHref.substr(0, lastSlash);
                // Get the model name
                lastSlash = sHref.lastIndexOf("/");
                var sModel = sHref.substr(lastSlash + 1);
                sHref = sHref.substr(0, lastSlash);
                // Find and adapt the history link's content to a current
                var sCurrent = $(".historylink").first().attr("href").replace("/history", "");
                // Create a new place to go to
                sHref = sHref.replace("collection", "copy") + "/?_popup=0&model=" + sModel + "&id=" + sId + "&current=" + sCurrent;
                var sAddNode = "<a class='copy-related' title='Make a copy' href='" + sHref + "'>copy</a>";
                // Append the new node
                $(this).append(sAddNode);
              }
            }
          });
      },

      text_info_show: function (el) {
        var ajaxurl = "",
            divShow = null,
            data = null;

        try {
          // Validate
          if (el === undefined || divShow === undefined || divShow === "") {
            return;
          }
          // Find the next <tr> containing the element to be shown
          divShow = $(el).closest("tr").next("tr").find("td").first();
          // Check the status of this item
          if (!$(divShow).hasClass("hidden")) {
            // This is not a hidden item, so just close it
            $(divShow).addClass("hidden");
            return;
          }
          // Hide all the info that has been shown so far
          $(el).closest("table").find(".text-details").addClass("hidden");
          // Retrieve the URL we need to have
          ajaxurl = $(el).attr("ajaxurl");
          // Get the data: this is to get a valid csrf token!
          data = $("#textsearch").serializeArray();
          // Request the information
          $.post(ajaxurl, data, function (response) {
            if (response !== undefined) {
              switch (response.status) {
                case "ok":
                  $(divShow).html(response.html);
                  $(divShow).removeClass("hidden");
                  break;
                default:
                  private_methods.errMsg("text_info_show: incorrect response " + response.status);
                  break;
              } 
            } else {
              private_methods.errMsg("text_info_show: undefined response ");
            }
          });

        } catch (ex) {
          private_methods.errMsg("text_info_show", ex);
        }
      },

      /**
       *  sync_start
       *      Start synchronisation
       *
       */
      sync_start : function(sSyncType) {
        var oJson = {},
            oData = {},
            i,
            sParam = "",
            arKV = [],
            arParam = [],
            sUrl = "";

        // Indicate that we are starting
        $("#sync_progress_" + sSyncType).html("Synchronization is starting: " + sSyncType);

        // Make sure that at the end: we stop
        oData = { 'type': sSyncType };
        // More data may be needed for particular types
        switch (sSyncType) {
          case "texts":
            // Retrieve the parameters from the <form> settings
            sParam = $("#sync_form_" + sSyncType).serialize();
            arParam = sParam.split("&");
            for (i = 0; i < arParam.length; i++) {
              arKV = arParam[i].split("=");
              // Store the parameters into a JSON object
              oData[arKV[0]] = arKV[1];
            }
            break;
        }

        // Start looking only after some time
        oJson = { 'status': 'started' };
        ru.lila.oSyncTimer = window.setTimeout(function () { ru.lila.sync_progress(sSyncType, oJson); }, 3000);

        // Define the URL
        sUrl = $("#sync_start_" + sSyncType).attr('sync-start');
        $.ajax({
          url: sUrl,
          type: "GET",
          async: true,
          dataType: "json",
          data: oData,      // This sends the parameters in the data object
          cache: false,
          success: function (json) {
            $("#sync_details_" + sSyncType).html("start >> sync_stop");
            ru.lila.sync_stop(sSyncType, json);
          },
          failure: function () {
            $("#sync_details_" + sSyncType).html("Ajax failure");
          }
        });

      },

      /**
       *  sync_progress
       *      Return the progress of synchronization
       *
       */
      sync_progress: function (sSyncType, options) {
        var oData = {},
            sUrl = "";

        oData = { 'type': sSyncType };
        sUrl = $("#sync_start_" + sSyncType).attr('sync-progress');
        $.ajax({
          url: sUrl,
          type: "GET",
          async: true,
          dataType: "json",
          data: oData,
          cache: false,
          success: function (json) {
            $("#sync_details_" + sSyncType).html("progress >> sync_handle");
            ru.lila.sync_handle(sSyncType, json);
          },
          failure: function () {
            $("#sync_details_" + sSyncType).html("Ajax failure");
          }
        });
      },

      /**
       *  sync_handle
       *      Process synchronisation
       *
       */
      sync_handle: function (sSyncType, json) {
        var sStatus = "",
            options = {};

        // Validate
        if (json === undefined) {
          sStatus = $("#sync_details_" + sSyncType).html();
          $("#sync_details_" + sSyncType).html(sStatus + "(undefined status)");
          return;
        }
        // Action depends on the status in [json]
        switch (json.status) {
          case 'error':
            // Show we are ready
            $("#sync_progress_" + sSyncType).html("Error synchronizing: " + sSyncType);
            $("#sync_details_" + sSyncType).html(ru.lila.sync_details(json));
            // Stop the progress calling
            window.clearInterval(ru.lila.oSyncTimer);
            // Leave the routine, and don't return anymore
            return;
          case "done":
          case "finished":
            // Default action is to show the status
            $("#sync_progress_" + sSyncType).html(json.status);
            $("#sync_details_" + sSyncType).html(ru.lila.sync_details(json));
            loc_sync_detail[sSyncType] = json;
            // Finish nicely
            ru.lila.sync_stop(sSyncType, json, false);
            return;
          default:
            // Default action is to show the status
            $("#sync_progress_" + sSyncType).html(json.status);
            $("#sync_details_" + sSyncType).html(ru.lila.sync_details(json));
            loc_sync_detail[sSyncType] = json;
            ru.lila.oSyncTimer = window.setTimeout(function () { ru.lila.sync_progress(sSyncType, options); }, 1000);
            break;
        }
      },

      /**
       *  sync_stop
       *      Finalize synchronisation
       *
       */
      sync_stop: function (sSyncType, json) {
        var lHtml = [], json = {};

        // Stop the progress calling
        window.clearInterval(ru.lila.oSyncTimer);

        // Show we are ready
        $("#sync_progress_" + sSyncType).html("Finished synchronizing: " + sSyncType + "<br>Last details:" );
        json = loc_sync_detail[sSyncType];
        $("#sync_details_" + sSyncType).html(ru.lila.sync_details(json));

      },

      /**
       *  sync_details
       *      Return a string with synchronisation details
       *
       */
      sync_details: function (json) {
        var lHtml = [],
            oCount = {};

        // Validate
        if (json === undefined || !json.hasOwnProperty("count"))
          return "";
        // Get the counts
        oCount = JSON.parse(json['count']);
        // Create a reply
        lHtml.push("<div><table><thead><tr><th>Item</th><th>Value</th></tr></thead><tbody>");
        for (var property in oCount) {
          if (oCount.hasOwnProperty(property)) {
            lHtml.push("<tr><td style='color: darkblue;'><b>" + property + "</b>:</td><td>" + oCount[property] + "</td></tr>");
          }
        }
        lHtml.push("</tbody></table></div>");
        // Return as string
        return lHtml.join("\n");
      },

      /**
       *  part_detail_toggle
       *      Toggle part detail
       *
       */
      part_detail_toggle: function (iPk) {
        var sId = "";

        // validate
        if (iPk === undefined) return;
        // Get the name of the tag
        sId = "#part_details_" + iPk.toString();
        // Check if it is visible or not
        if ($(sId).hasClass("hidden")) {
          // Remove it
          $(sId).removeClass("hidden");
        } else {
          // Add it
          $(sId).addClass("hidden");
        }
      },

      /**
       *  view_switch
       *      Switch from one view to the other
       *
       */
      view_switch: function (sOpen, sClose) {
        $("#" + sOpen).removeClass("hidden");
        $("#" + sClose).addClass("hidden");
        // Show/hide <li> elements
        $("li." + sOpen).removeClass("hidden");
        $("li." + sClose).addClass("hidden");
      }

    };
  }($, ru.config));

  return ru;
}(jQuery, window.ru || {})); // window.ru: see http://stackoverflow.com/questions/21507964/jslint-out-of-scope

