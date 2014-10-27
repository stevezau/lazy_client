String.prototype.startsWith = function (str)
{
   return this.indexOf(str) == 0;
};

(function($) {
$.fn.serializeFormJSON = function() {

   var o = {};
   var a = this.serializeArray();
   $.each(a, function() {
       if (o[this.name]) {
           if (!o[this.name].push) {
               o[this.name] = [o[this.name]];
           }
           o[this.name].push(this.value || '');
       } else {
           o[this.name] = this.value || '';
       }
   });
   return o;
};
})(jQuery);

lazyapi_url = "/api"

function ConvertFormToJSON(form){
    var array = jQuery(form).serializeArray();
    var json = {};

    jQuery.each(array, function() {
        json[this.name] = this.value || '';
    });

    return json;
}


$( document ).ready(function() {
    /////////////////////////
    /// AJAX DJANGO SEND ////
    /////////////////////////

    $(document).ajaxSend(function(event, xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        function sameOrigin(url) {
            // url could be relative or scheme relative or absolute
            var host = document.location.host; // host + port
            var protocol = document.location.protocol;
            var sr_origin = '//' + host;
            var origin = protocol + sr_origin;
            // Allow absolute or scheme relative URLs to same origin
            return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
                (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
                // or any other URL that isn't scheme relative or absolute i.e relative.
                !(/^(\/\/|http:|https:).*/.test(url));
        }
        function safeMethod(method) {
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    });

    $(document).on('click', '.alert-close', function(event) {
       $(this).hide();
    });

    /* Cleanup */
    $(document).on('click', '.select_all_panel', function(event) {
        checkbox = $(this);
        checked = checkbox.prop('checked');
        panel = checkbox.parent().parent();

        if (checked) {
            panel.find('input:checkbox').filter(':visible').prop('checked', true);
        } else {
            panel.find('input:checkbox').filter(':visible').prop('checked', false);
        }
        event.stopPropagation()
    });

    $(document).on('click', '.cleanup_delete_prompt', function(event) {
        id = $(this).attr("delete-target");
        $("#deleteModal .clean_delete_all").attr("form", id);
        $('#deleteModal').modal()
    });

    $(document).on('click', '.clean_delete_all', function(event) {
        btn = $(this);
        form = $("#" + btn.attr("form"));

        $("#deleteModal .clean_delete_all").attr("form", null);

        toggle_success = function (data, textStatus, jqXHR) {
            status = data['status']
            if (status == "success") {
                label = $('.tvshow-' + this.custom_data.id).remove()
            } else {
                add_alert("Error deleting tvshow as " + data['detail'])
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
            add_alert("Error deleting tvshow: " + errorThrown);

        };

        form.find('input:checked').each(function() {
            checkbox = $(this);
            result_tr = checkbox.parent().parent();
            result_td = result_tr.find(".result");
            result_td.append('<span class="label label-danger">Deleting     <span class="spinner"></span></span>');
            result_td.find(".spinner").spin("tiny");
            id = $(checkbox).attr("value")
            call_ajax("/api/tvshow/" + id + "/action/", {'action': "delete_all"}, {"id": id}, toggle_success, toggle_error, "POST", btn);
        });

    });

    /* input spinner for a links */
    $(document).on('click', '[spinner]', function(event) {
        button_spin($(this), $(this).attr("spinner"))
    });

    /* Queue Manager */
    $(document).on('click', '.manage-queue', function(event) {
        item_obj = $(this);

        current_state = $(this).attr("state");

        if (current_state == "started") {
            item_obj.text("Stopping Queue...");
            action = "stop_queue";
        } else {
            item_obj.text("Starting Queue...");
            action = "start_queue";
        }

        queue_success = function (data, textStatus, jqXHR) {
            if (this.custom_data.action == "stop_queue") {
                location.reload();
            } else {
                location.reload();
            }
        };

        queue_error = function (jqXHR, textStatus, errorThrown) {
            if (this.custom_data.action == "start_queue") {
                this.custom_data.item_obj.text("Failed Starting Queue: " + errorThrown);
            } else {
                this.custom_data.item_obj.text("Failed Stopping Queue: " + errorThrown);
            }
        };
        call_ajax("/api/server/", {"action": action}, {"action": action, "item_obj": item_obj}, queue_success, queue_error, "POST");

    });

    /* Add from search */
    $(document).on('click', '.add-download', function(event) {
        event.preventDefault();
        obj = $(this);
        site = obj.attr("site");
        torrent = obj.attr("torrent");

        data = {"site": site, "download": torrent};

        obj.addClass("glyphicon-refresh");
        obj.addClass("glyphicon-refresh-animate");

        call_ajax("/api/downloads/add/", data, {"obj": obj}, search_download_success, search_download_error, "POST");
    });

    /* Remove border if there is only 1 item */
    if ($(".media-list").length > 0) {
        dlitems = $(".media-list").children(".download-item");
        if (dlitems.length == 1) {
            $(dlitems).addClass("no-border");
        }
    }

    /* Download Items */
    $(document).on('click', '[class^="item_approve_"]', function(event) {
        btn = $(this);
        id = $(this).prop("class").match(/item_approve.+[0-9]/).toString().replace("item_approve_", "");
        action_item(id, "approve", btn);
    });

    $(document).on('click', '[class^="item_delete_"]', function(event) {
        btn = $(this);
        id = $(this).prop("class").match(/item_delete_.+[0-9]/).toString().replace("item_delete_", "");
        action_item(id, "delete", btn);
    });

    $(document).on('click', '[class^="item_ignore_"]', function(event) {
        btn = $(this);
        id = $(this).prop("class").match(/item_ignore_.+[0-9]/).toString().replace("item_ignore_", "");
        action_item(id, "ignore", btn);
    });

    $(document).on('click', '[class^="item_reset_"]', function(event) {
        btn = $(this);
        id = $(this).prop("class").match(/item_reset_.+[0-9]/).toString().replace("item_reset_", "");
        action_item(id, "reset", btn);
    });

    $(document).on('click', '[class^="item_retry_"]', function(event) {
        btn = $(this);
        id = $(this).prop("class").match(/item_retry_.+[0-9]/).toString().replace("item_retry_", "");
        action_item(id, "retry", btn);
    });

    $(document).on('click', '[class^="item_pri_low_"]', function(event) {
        id = $(this).prop("class").match(/item_pri_low_.+[0-9]/).toString().replace("item_pri_low_", "");
        sort_download(id, 10);
    });

    $(document).on('click', '[class^="item_pri_medium_"]', function(event) {

        id = $(this).prop("class").match(/item_pri_medium_.+[0-9]/).toString().replace("item_pri_medium_", "");
        sort_download(id, 5);
    });

    $(document).on('click', '[class^="item_pri_high_"]', function(event) {
        id = $(this).prop("class").match(/item_pri_high_.+[0-9]/).toString().replace("item_pri_high_", "");
        sort_download(id, 1);
    });


    $('[class^="seconds_left_"]').each(function(event) {
        obj = $(this)
        id = obj.prop("class").match(/seconds_left_.+[0-9]/).toString().replace("seconds_left_", "");

        spinner = obj.find('.spinner')
        if (spinner) { spinner.spin("tiny") }

        toggle_success = function (data, textStatus, jqXHR) {
            seconds = data['detail'];

            left = "Time Remaining: Unknown"

            if (seconds == 0) {
                left = "Time Remaining: Finsihed"
            } else if (seconds > 0) {
                left = "Time Remaining: " + millisecondsToStr(seconds * 1000)
            }

            this.custom_data.spinner.remove()
            this.custom_data.obj.text(left)
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
            //do nothing
        };

        call_ajax("/api/downloads/" + id + "/action/", {'action': "seconds_left"}, {"obj": obj, "spinner": spinner}, toggle_success, toggle_error, "POST", null);
    });


    /* TVShow Management */
    $('#deleteModal').on('hide.bs.modal', function(e) {
        $("#deleteModal .tvshow_delete_all").attr("showid", null)
    });

    $(document).on('click', '.tvshow_delete_all', function(event) {
        btn = $(this);
        id = btn.attr("showid")

        obj = $("#" + id);

        toggle_success = function (data, textStatus, jqXHR) {
            $('#deleteModal').modal('hide');
            $("#deleteModal .tvshow_delete_all").attr("showid", null)
            $("#" + this.custom_data.id).find(".glyphicon-hdd").addClass("hidden")
            $("#" + this.custom_data.id).find(".tvshow_delete_prompt").attr("disabled", true)
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
            $('#deleteModal').modal('hide');
            $("#deleteModal .tvshow_delete_all").attr("showid", null)
            add_alert("Failed deleting all epsiodes: " + errorThrown);

        };

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "delete_all"}, {"id": id}, toggle_success, toggle_error, "POST", btn);
    });

    $(document).on('click', '.tvshow_delete_prompt', function(event) {
        id = $(this).closest(".tvshow").attr("id");
        obj = $("#" + id)

        $("#deleteModal .tvshow_delete_all").attr("showid", id)
        $("#deleteModal .tvshow_title").text(obj.find(".title").text())
        $('#deleteModal').modal()
    });

    $(document).on('click', '.tvshow_toggle_fav', function(event) {
        btn = $(this);
        id = $(this).parents(".tvshow").attr("id");

        obj = $("#" + id);

        toggle_success = function (data, textStatus, jqXHR) {
            state = data['state'];
            fav_span = this.custom_data.obj.find(".tvshow_toggle_fav .btn-text");
            ignore_span = this.custom_data.obj.find(".tvshow_toggle_ignore .btn-text");

            if (state) {
                this.custom_data.obj.find('h4 .glyphicon-ban-circle').addClass("hidden");
                this.custom_data.obj.find('h4 .glyphicon-star').removeClass("hidden");
                fav_span.text("Remove Favorite");
                ignore_span.text("Ignore Show");
                this.custom_data.obj.find('.tvshow_show_missing').attr("disabled", false)
            } else {
                this.custom_data.obj.find('h4 .glyphicon-star').addClass("hidden");
                fav_span.text("Add Favorite");
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
            add_alert("Failed setting favoriate status: " + errorThrown)
        };

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "toggle_fav"}, {"obj": obj}, toggle_success, toggle_error, "POST", btn);
    });

    $(document).on('click', '.tvshow_toggle_ignore', function(event) {
        btn = $(this);
        id = $(this).parents(".tvshow").attr("id");

        obj = $("#" + id);

        toggle_success = function (data, textStatus, jqXHR) {
            state = data['state'];
            fav_span = this.custom_data.obj.find(".tvshow_toggle_fav .btn-text");
            ignore_span = this.custom_data.obj.find(".tvshow_toggle_ignore .btn-text");

            if (state) {
                this.custom_data.obj.find('h4 .glyphicon-star').addClass("hidden");
                this.custom_data.obj.find('h4 .glyphicon-ban-circle').removeClass("hidden");
                this.custom_data.obj.find('.tvshow_show_missing').attr("disabled", true)
                ignore_span.text("Remove Ignored");
                fav_span.text("Add Favorite");

                if (this.custom_data.obj.find(".glyphicon-hdd").is(":visible")) {
                    $("#ignoreModal .tvshow_delete_all").attr("showid", id)
                    $("#ignoreModal .tvshow_title").text(this.custom_data.obj.find(".title").text())
                    $('#ignoreModal').modal()
                }
            } else {
                this.custom_data.obj.find('h4 .glyphicon-ban-circle').addClass("hidden");
                this.custom_data.obj.find('.tvshow_show_missing').attr("disabled", false)
                ignore_span.text("Ignore Show");
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
            add_alert("Failed setting ignore status: " + errorThrown)
        };

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "toggle_ignore"}, {"obj": obj}, toggle_success, toggle_error, "POST", btn);
    });

    $(document).on('click', '.tvshow_show_missing', function(event) {
        btn = $(this);
        button_spin(btn);
        load_html("missing/", $("#tvshow-missing"), btn)
    });
    $(document).on('click', '.tvshow_show_missing_results', function(event) {
        btn = $(this);
        button_spin(btn);
        load_html("missing/results/", $("#tvshow-fix-results"), btn)
    });


    $(document).on('click', '.clear_missing_results', function(event) {
        btn = $(this);
        id = $(".tvshow").attr("id");

        toggle_success = function (data, textStatus, jqXHR) {
            status = data['status']
            if (status == "success") {
                $("#tvshow-fix-results").addClass("hidden");
                $(".tvshow_show_missing").attr('disabled',false);
            } else {
                add_alert("Error clearing as " + data['detail'])
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
           add_alert("Error clearing as " + errorThrown)
        };

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "clear_results"}, null, toggle_success, toggle_error, "POST", btn);
    });


    $(document).on('click', '.cancel_missing', function(event) {
        btn = $(this);
        id = $(".tvshow").attr("id");

        toggle_success = function (data, textStatus, jqXHR) {
            status = data['status']
            if (status == "success") {
                $("#tvshow-fix-results").addClass("hidden")
                $(".tvshow_show_missing").attr('disabled',false);
            } else {
                add_alert("Error cancelling as " + data['detail'])
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
           add_alert("Error cancelling as " + errorThrown)
        };

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "cancel_missing"}, null, toggle_success, toggle_error, "POST", btn);
    });

    $(document).on('click', '.fix_missing', function(event) {
        btn = $(this);
        id = $(".tvshow").attr("id");

        obj = $("#" + id)

        toggle_success = function (data, textStatus, jqXHR) {
            status = data['status']
            if (status == "success") {
                $("#fixModal .tvshow_title").text(this.custom_data.obj.find(".title").text())
                $('#fixModal').modal()
                $("#tvshow-missing").addClass("hidden")
                $(".tvshow_show_missing").attr('disabled',true);
                load_html("missing/results/", $("#tvshow-fix-results"), btn)
            } else {
                add_alert("Error searching for missing eps as " + data['detail'])
            }
        };

        toggle_error = function (jqXHR, textStatus, errorThrown) {
           add_alert("Error searching for missing eps as " + errorThrown)
        };

        var formdata = $('#fixmissing-form').serializeFormJSON()

        call_ajax("/api/tvshow/" + id + "/action/", {'action': "fix_missing", 'fix': formdata}, {"obj": obj}, toggle_success, toggle_error, "POST", btn);
    });

    $(document).on('click', '.select_all_missing', function(event) {
        if ($(this).prop('checked')) {
            $('input:checkbox').filter(':visible').prop('checked', true);
        } else {
            $('input:checkbox').filter(':visible').prop('checked', false);
        }
    });


    /////////////////////////
    /// Handle Manual Fix ///
    /////////////////////////

    $("input[id$='_imdbid_display']").autocomplete({
        source: lazyapi_url + "/search_imdb/",
        minLength: 3,
        select: function(event, ui) {
            id = parseInt($(this).attr("name").toString().replace("_imdbid_display", ""));
            file_obj = $("#file_" + id);

            if (ui.item == null) {
                file_obj.find("input[name$='_imdbid_id']").val(null);
            } else {
                file_obj.find("input[name$='_imdbid_id']").val(ui.item.id);
            }
        }
    });

    $("input[id$='_tvdbid_display']").autocomplete({
        source: lazyapi_url + "/search_tvdb/",
        minLength: 3,
        select: function(event, ui) {
            id = parseInt($(this).attr("name").toString().replace("_tvdbid_display", ""));
            file_obj = $("#file_" + id);

            if (ui.item == null) {
                file_obj.find("input[id$='_tvdbid_id']").val(null);
                file_obj.find("select[id$='_tvdbid_season_override']").empty();
                file_obj.find("input[id$='_tvdbid_ep_override']").empty()
            } else {
                file_obj.find("input[id$='_tvdbid_id']").val(ui.item.id);
                update_season(id)
            }
    }
    });

    // Update fields when the type is changed..
    $("select[name$='_type']").change(function() {
        id = parseInt($(this).attr("name").toString().replace("_type", ""));
        update_fields(id)

    });

    $("select[name$='_tvdbid_season_override']").change(function() {
        id = parseInt($(this).attr("name").toString().replace("_tvdbid_season_override", ""));
        update_ep(id);
    });


});

//////////////////////
/// Helper Methods ///
//////////////////////

function call_ajax(url, data, custom_data, succes_handler, error_handler, type, btn) {

    if (error_handler == null) {
        error_handler = function (jqXHR, textStatus, errorThrown) {
            add_alert("Error: " + errorThrown)
        };
    }

    if (btn) {button_spin(btn)}

    $.ajax({
        url: url,
        data: JSON.stringify(data),
        dataType : "json",
        contentType: "application/json",
        custom_data: custom_data,
        success: succes_handler,
        error: error_handler,
        type: type}).always(function() {
            if (btn){
                button_unspin(btn)
            }
        })
}

///////////////////
/// Search Page ///
///////////////////

function search_alert(obj, text, type) {
    alert = obj.parent().siblings().find(".alert");

    if (alert.length > 0) {
        alert.remove()
    } else {
        obj.parent().siblings().append("<div class='alert alert-" + type + "'>" + text + "</div>")
    }
}

function search_download_success(data, textStatus, jqXHR) {
    if (data['status'] == "success") {
        this.custom_data.obj.removeClass("glyphicon-refresh");
        this.custom_data.obj.removeClass("glyphicon-refresh-animate");
        this.custom_data.obj.addClass("glyphicon-ok");
        search_alert(this.custom_data.obj, "Added to the queue", "success")
    } else {
        search_error(this.custom_data.obj, data['detail'])
    }
}

function search_download_error(jqXHR, textStatus, errorThrown) {
    search_error(this.custom_data.obj, textStatus + " " + errorThrown)
}

function search_error(obj, message) {
    obj.removeClass("glyphicon-refresh");
    obj.removeClass("glyphicon-refresh-animate");
    obj.addClass("glyphicon-remove");
    search_alert(obj, message, "danger")
}

////////////////////////////////
/// Download Item Functions ///
///////////////////////////////

function sort_download(id, pri) {

    item = $("#item_" + id);
    url = "/api/downloads/" + id + "/";
    data = {"priority": pri};
    call_ajax(url, data, null, null, null, "PATCH");

    item.attr("pri", pri);

    if (pri >= 10) {
        item.find(".priority .value").text("Low");
    } else if (pri >= 5) {
        item.find(".priority .value").text("Medium");
    } else {
        item.find(".priority .value").text("High");
    }

    dlitems = $('.download-item')

    item.detach();

    inserted = false;

    $('.download-item').each(function(index) {
        cur_obj = $(this);
        cur_id = parseInt(cur_obj.attr("id").replace("item_", ""));
        cur_pri = parseInt(cur_obj.attr("pri"));

        if (pri == cur_pri) {
            if (id < cur_id) {
                cur_obj.before(item);
                inserted = true;
                return false
            }
        }

        if (pri < cur_pri) {
            //append previous
            cur_obj.before(item);
            inserted = true;
            return false
        }
    });

    if (!inserted) {
        $('.media-list').append(item)
    }
}

function downloads_success_handler(data, textStatus, jqXHR) {
    num = parseInt($('button.active > span').text());

    if (!isNaN(num)) {
        $('button.active > span').text(num - 1)
    }

    if (this.custom_data.multi_obj_id) {
        this.custom_data.item_obj.remove();
    } else {
        this.custom_data.item_obj.delay("fast").fadeOut('fast');
    }

    //Any left?
    if (this.custom_data.multi_obj_id) {
        multi_obj = $("#" + this.custom_data.multi_obj_id);

        if ($(multi_obj).find("[id^='item_']").length == 0){
            $(multi_obj).delay("fast").fadeOut('fast');
        }
    }
};

function downloads_error_handler(jqXHR, textStatus, errorThrown)
{
    // Append to container body
    if (!$(".container.body #message").length) {
        $(".container.body").prepend('<div id="message" class="col-xs-12"></div>')
    }

   if (this.custom_data.multi_obj_id) {
       multi_obj = $("#" + this.custom_data.multi_obj_id);
       ep_season = this.custom_data.item_obj.find(".ep_title").text();
       title = multi_obj.find(".title").text() + " " + ep_season
   } else {
       title = this.custom_data.item_obj.find(".title").text()
   }

   msg = title + ": " + errorThrown;

   $(".container.body #message").prepend('<div id="inner-message" class="alert alert-close alert-danger">' +
                                            '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                                            '' + msg + '' +
                                        '</div>')};

function action_item(id, action, btn) {
    obj_name = "#item_" + id;
    item_obj = $(obj_name);

    url = "/api/downloads/" + id + "/action/";
    data = {"action": action};

    if ($(item_obj).attr("multi") == "yes") {
        multi_obj_id = $(item_obj).attr("id");

        $(item_obj).find("[id^='item_']").each(function(i, obj) {
            item_id = $(obj).attr("id").replace("item_", "");
            url = "/api/downloads/" + item_id + "/action/";
            custom_data = {"action": action,"item_obj": item_obj, "multi_obj_id": multi_obj_id};

            call_ajax(url, data, custom_data, downloads_success_handler, downloads_error_handler, "POST", btn)
        });

    } else {
        custom_data = {"action": action,"item_obj": item_obj, "multi_obj_id": false};
        call_ajax(url, data, custom_data, downloads_success_handler, downloads_error_handler, "POST", btn)
    }

}

/////////////////////////
/// Handle Manual Fix ///
/////////////////////////
function update_fields(id) {

    file_obj = $("#file_" + id);
    type_obj = file_obj.find("select[name='" + id + "_type']");
    value = type_obj.find(":selected").text();
    div_str = "#div_id_" + id;

    // TVShow
    if (value == "TVShow") {

        file_obj.find(div_str + "_imdbid_display").hide();
        file_obj.find(div_str + "_tvdbid_display").show();
        file_obj.find(div_str + "_tvdbid_season_override").show();

        file_obj.find(div_str + "_tvdbid_ep_override").show();
    }

    // Movie
    if (value == "Movie") {
        file_obj.find(div_str + "_tvdbid_display").hide();
        file_obj.find(div_str + "_tvdbid_season_override").hide();
        file_obj.find(div_str + "_tvdbid_ep_override").hide();

        file_obj.find(div_str + "_imdbid_display").show();
    }
}

function load_html(url, target, btn) {
    $.get(url, function( data ) {
        target.html( data );
        button_unspin(btn);
        target.removeClass("hidden");
    });
}


function update_season(id) {
    file_obj = $("#file_" + id);

    showid = file_obj.find("input[name$='_tvdbid_id']").val();
    season_override = file_obj.find("select[name$='_tvdbid_season_override']");
    ep_override = file_obj.find("select[name$='_tvdbid_ep_override']");

    $(season_override).empty();
    $(ep_override).empty();

    $(season_override).append("<option value='Select Season'>Select Season</option>");

    $.ajax({
        url: lazyapi_url + "/get_tvdb_season/" + showid,
        type: 'GET',
        dataType: 'json', // or your choice of returned data
        success: function(seasons){
             $.each(seasons, function(i, stt){
                 $(season_override).append('<option value="'+stt.value+'">'+stt.label+'</option>');
             });
        }
    });
}


function update_ep(id) {
    file_obj = $("#file_" + id);

    season_override_obj = file_obj.find("select[name$='_tvdbid_season_override']");
    ep_override_obj = file_obj.find("select[name$='_tvdbid_ep_override']");
    tvdb_id_obj = file_obj.find("input[name$='_tvdbid_id']");

    season = $(season_override_obj).val();
    tvdb_id = $(tvdb_id_obj).val();
    ep_override_obj.empty();

    $.ajax({
        url: lazyapi_url + "/get_tvdb_eps/" + tvdb_id + "/" + season,
        type: 'GET',
        dataType: 'json', // or your choice of returned data
        success: function(eps){
             $.each(eps, function(i, stt){
                 ep_override_obj.append('<option value="'+stt.value+'">'+stt.label+'</option>');
             });
        }
    });
}

function add_alert(msg) {

    msg_obj = $(".container.body #message");

    if (msg_obj.length == 0) {
        $(".container.body").append('<div id="message"></div>');
        msg_obj = $(".container.body #message");
    }
    msg_obj.prepend('<div id="inner-message" class="alert alert-close alert-danger">' +
            '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
            '' + msg + '' +
            '</div>'
        );
}

function button_unspin(btn) {
    btn.attr("disabled", false);
    spinner = $(btn).find(".spinner");

    if (spinner.length > 0) {
        spinner.remove()
    }

    glyphicon = btn.find('.glyphicon');

    if (glyphicon.length > 0) {
        glyphicon.removeClass('hidden')
    } else {
        btn.spin(false)
    }
}

function button_spin(btn, size) {
    if (!size) {
        size = "tiny"
    }

    form = btn.parents('form')
    if (form.length > 0) {

    } else {
        btn.attr("disabled", true);
    }

    if (btn.find(".spinner").length > 0) {
        return
    }

    //Check for glyphicon
    glyphicon = btn.find('.glyphicon');

    if (glyphicon.length > 0) {
        glyphicon.addClass("hidden");
        glyphicon.after("<span class='spinner'></span>");
        btn.find(".spinner").spin(size)
    } else {
        btn.prepend("<span class='spinner'></span>");
        btn.find(".spinner").spin(size)
    }


}

function two(x) {return ((x>9)?"":"0")+x}
function three(x) {return ((x>99)?"":"0")+((x>9)?"":"0")+x}

function millisecondsToStr(ms) {
    var sec = Math.floor(ms / 1000)
    ms = ms % 1000
    t = three(ms)

    var min = Math.floor(sec / 60)
    sec = sec % 60

    t = ""

    if (sec > 0) {
        t = two(sec) + " seconds "
    }

    var hr = Math.floor(min/60)
    min = min % 60

    if (min > 0) {
        t = two(min) + " minutes " + t
    }

    var day = Math.floor(hr/60)

    hr = hr % 60

    if (hr > 0) {
     t = two(hr) + " hours " + t
    }

    if (day > 0) {
       t = day + " days " + t
    }

    return t
}
