
String.prototype.startsWith = function (str)
{
   return this.indexOf(str) == 0;
};

lazyapi_url = "/api"


$( document ).ready(function() {

    if ($('.content').size()) {
	    getContent();
	}

    $(document).on('click', '.alert-close', function(event) {
       $(this).hide();
    })


    /////////////////
    /// Home Page ///
    /////////////////
    $(document).on('click', '.manage-queue', function(event) {
        item_obj = $(this)

        current_state = $(this).attr("state")

        if (current_state == "started") {
            item_obj.text("Stopping Queue...");
            action = "stop_queue";
        } else {
            item_obj.text("Starting Queue...");
            action = "start_queue";
        }

        $.ajax({
            url: "/api/server/",
            data: {"action": action},
            dataType : "json",
            custom_data: {"action": action,"item_obj": item_obj},
            success: function(data, textStatus, jqXHR) {
                if (this.custom_data.action == "stop_queue") {
                    location.reload();
                } else {
                    location.reload();
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                if (this.custom_data.action == "start_queue") {
                    this.custom_data.item_obj.text("Failed Starting Queue: " + errorThrown);
                } else {
                    this.custom_data.item_obj.text("Failed Stopping Queue: " + errorThrown);
                }
            },
            type: 'POST'});
    });

    /* Add from search */
    $(document).on('click', '.add-download', function(event) {
        event.preventDefault();
        obj = $(this)
        site = obj.attr("site");
        torrent = obj.attr("torrent");

        data = {"site": site, "download": torrent};

        obj.addClass("glyphicon-refresh");
        obj.addClass("glyphicon-refresh-animate");

        call_ajax("/api/downloads/add/", data, {"obj": obj}, search_download_success, search_download_error, "POST");
    });

    //////////////////////
    /// Download Items ///
    //////////////////////

    /* Remove border if there is only 1 item */
    if ($(".media-list").length > 0) {
        dlitems = $(".media-list").children(".download-item")
        if (dlitems.length == 1) {
            $(dlitems).addClass("no-border")
        }
    }

    /* Actions Buttons */
    $(document).on('click', '[class^="item_approve_"]', function(event) {
        id = $(this).prop("class").match(/item_approve.+[0-9]/).toString().replace("item_approve_", "");
        action_item(id, "approve")
    });

    $(document).on('click', '[class^="item_delete_"]', function(event) {
        id = $(this).prop("class").match(/item_delete_.+[0-9]/).toString().replace("item_delete_", "");
        action_item(id, "delete")
    });

    $(document).on('click', '[class^="item_ignore_"]', function(event) {
        id = $(this).prop("class").match(/item_ignore_.+[0-9]/).toString().replace("item_ignore_", "");
        action_item(id, "ignore")
    });

    $(document).on('click', '[class^="item_reset_"]', function(event) {
        id = $(this).prop("class").match(/item_reset_.+[0-9]/).toString().replace("item_reset_", "");
        action_item(id, "reset")
    });

    $(document).on('click', '[class^="item_retry_"]', function(event) {
        id = $(this).prop("class").match(/item_retry_.+[0-9]/).toString().replace("item_retry_", "");
        action_item(id, "retry")
    });

    $(document).on('click', '[class^="item_pri_low_"]', function(event) {
        id = $(this).prop("class").match(/item_pri_low_.+[0-9]/).toString().replace("item_pri_low_", "");
        item = $("#item_" + id);
        url = "/api/downloads/" + id + "/";
        data = {"priority": 10}
        call_ajax(url, data, null, null, null, "PATCH")

        item.attr("pri", "10")
        item.find(".priority .value").text("Low");

        sort_download(item)
    });

    $(document).on('click', '[class^="item_pri_medium_"]', function(event) {
        id = $(this).prop("class").match(/item_pri_medium_.+[0-9]/).toString().replace("item_pri_medium_", "");
        item = $("#item_" + id);
        url = "/api/downloads/" + id + "/";
        data = {"priority": 5}
        call_ajax(url, data, null, null, null, "PATCH")
        item.find(".priority .value").text("Medium");
        item.attr("pri", "5")
        sort_download(item)
    });

    $(document).on('click', '[class^="item_pri_high_"]', function(event) {
        id = $(this).prop("class").match(/item_pri_high_.+[0-9]/).toString().replace("item_pri_high_", "");
        item = $("#item_" + id);
        url = "/api/downloads/" + id + "/";
        data = {"priority": 1}
        call_ajax(url, data, null, null, null, "PATCH")
        item.find(".priority .value").text("High");
        item.attr("pri", "1")
        sort_download(item)
    });

    /////////////////////////
    /// Handle Manual Fix ///
    /////////////////////////

    $("input[id$='_imdbid_display']").autocomplete({
        source: lazyapi_url + "/search_imdb/",
        minLength: 3,
        select: function(event, ui) {
            parent = $(this).parent().parent();

            if (ui.item == null) {
                parent.find("input[name$='_imdbid_id']").val(null);
            } else {
                parent.find("input[name$='_imdbid_id']").val(ui.item.id);
            }
    }
    });

    $("input[id$='_tvdbid_display']").autocomplete({
        source: lazyapi_url + "/search_tvdb/",
        minLength: 3,
        select: function(event, ui) {
            parent = $(this).parent().parent();

            if (ui.item == null) {
                parent.find("input[id$='_tvdbid_id']").val(null)
                parent.find("select[id$='_tvdbid_season_override']").empty()
                parent.find("input[id$='_tvdbid_ep_override']").empty()
            } else {
                parent.find("input[id$='_tvdbid_id']").val(ui.item.id)
                update_season(this)
            }
    }
    });

    // Update fields when the type is changed..
    $("select[name$='_type']").change(function() {
        // We need to change the fields..a
        update_fields(this)
    });

    $("select[name$='_tvdbid_season_override']").change(function() {
        update_ep(this);
    });


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

	$(document).ajaxStart(function() {
		  $('#loading').show();
	
		}).ajaxStop(function() {
		  $('#loading').hide();
		 
		});

});

//////////////////////
/// Helper Methods ///
//////////////////////

function call_ajax(url, data, custom_data, succes_handler, error_handler, type) {

    $.ajax({
        url: url,
        data: data,
        dataType : "json",
        custom_data: custom_data,
        success: succes_handler,
        error: error_handler,
        type: type});
}

///////////////////
/// Search Page ///
///////////////////

function search_alert(obj, text, type) {
    alert = obj.parent().siblings().find(".alert")

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

/////////////////////////////
/// Download Item Buttons ///
/////////////////////////////

function downloads_success_handler(data, textStatus, jqXHR)
{
    num = parseInt($('button.active > span').text())

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
        multi_obj = $("#" + this.custom_data.multi_obj_id)

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
       multi_obj = $("#" + this.custom_data.multi_obj_id)
       ep_season = this.custom_data.item_obj.find(".ep_title").text()
       title = multi_obj.find(".title").text() + " " + ep_season
   } else {
       title = this.custom_data.item_obj.find(".title").text()
   }

   msg = title + ": " + errorThrown

   $(".container.body #message").prepend('<div id="inner-message" class="alert alert-close alert-danger">' +
                                            '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                                            '' + msg + '' +
                                        '</div>')};

function action_item(id, action) {
    obj_name = "#item_" + id;
    item_obj = $(obj_name);

    url = "/api/downloads/" + id + "/action/";
    data = {"action": action}

    if ($(item_obj).attr("multi") == "yes") {
        multi_obj_id = $(item_obj).attr("id")

        $(item_obj).find("[id^='item_']").each(function(i, obj) {
            item_id = $(obj).attr("id").replace("item_", "")
            url = "/api/downloads/" + item_id + "/action/";
            custom_data = {"action": action,"item_obj": item_obj, "multi_obj_id": multi_obj_id}
            call_ajax(url, data, custom_data, downloads_success_handler, downloads_error_handler, "POST")
        });
    } else {
        custom_data = {"action": action,"item_obj": item_obj, "multi_obj_id": false}
        call_ajax(url, data, custom_data, downloads_success_handler, downloads_error_handler, "POST")
    }

}

function set_error(item_obj, msg) {
    error_div = $(item_obj).find(".error-container")
    error_div.empty()
    error_div.html("<div class='error'>" + msg + "</div>")
}

/////////////////////////
/// Handle Manual Fix ///
/////////////////////////
function update_fields(type_obj) {

    value = $(type_obj).find(":selected").text();

    parent = $(type_obj).parent().parent();

    // TVShow
    if (value == "TVShow") {
        parent.find(".imdbid_display").hide();

        parent.find(".tvdbid_display").show();
        parent.find(".tvdbid_season_override").show();
        parent.find(".tvdbid_ep_override").show();
    }

    // Movie
    if (value == "Movie") {
        parent.find(".tvdbid_display").hide();
        parent.find(".tvdbid_season_override").hide();
        parent.find(".tvdbid_ep_override").hide();

        parent.find(".imdbid_display").show();
    }
}


function update_season(current) {

    parent = $(current).parent().parent();
    showid = parent.find("input[name$='_tvdbid_id']").val()
    season_override = parent.find("select[name$='_tvdbid_season_override']");
    ep_override = parent.find("select[name$='_tvdbid_ep_override']");

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

function getContent() {
	var geturl = $('.content').attr('action');
	var post = $('.content').attr('post');

	if (post && post != '') {
		geturl = geturl + post;
	}

	$.get(geturl, function( data ) {
		$('.content').html( data );
	});
}

function update_ep(current) {
    parent = $(current).parent().parent();

    season_override_obj = parent.find("select[name$='_tvdbid_season_override']");
    ep_override_obj = parent.find("select[name$='_tvdbid_ep_override']");
    tvdb_id_obj = parent.find("input[name$='_tvdbid_id']");

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

function sort_download(dlitem) {

    id = parseInt(dlitem.attr("id").replace("item_", ""))
    pri = parseInt(dlitem.attr("pri"))

    dlitems = $('.download-item')

    dlitem.detach()

    inserted = false

    $('.download-item').each(function(index) {
        cur_obj = $(this)
        cur_id = parseInt(cur_obj.attr("id").replace("item_", ""))
        cur_pri = parseInt(cur_obj.attr("pri"))

        if (pri == cur_pri) {
            if (id < cur_id) {
                cur_obj.before(dlitem)
                inserted = true
                return false
            }
        }

        if (pri < cur_pri) {
            //append previous
            cur_obj.before(dlitem)
            inserted = true
            return false
        }
    });

    if (!inserted) {
        $('.media-list').append(dlitem)
    }
}