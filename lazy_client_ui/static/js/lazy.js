
String.prototype.startsWith = function (str)
{
   return this.indexOf(str) == 0;
};

lazyapi_url = "/api"

$( document ).ready(function() {
	//$( "#dialog" ).dialog();

    $("#id_tvdbid_display").autocomplete({
        source: lazyapi_url + "/search_tvdb/",
        minLength: 3,
        change: function(event, ui) {
            console.log(this.value);
            if (ui.item == null) {
                $("#id_tvdbid_id").val(null)
                $("#id_epoverride").empty()
                $("#id_seasonoverride").empty()
            } else {
                $("#id_tvdbid_id").val(ui.item.id)
                update_season()
            }
    }
    });


    $('#id_seasonoverride').change(function() {
        update_ep();
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
		
	//get Download content
	if ($('.downloads').size()) {
		getContent();
	}

	//Hightlight from checkbox click
	$(document).on('click', 'input:checkbox', function(event) {

		var downloadItem = $(this).closest('.download-item, .selectable');
		
		if (!downloadItem.length) {
			return;
		}
		
		var inputName = $(this).prop('name');
			
		if (inputName.indexOf('multi') !== -1) {
			//Multi Item top check box
			var input = downloadItem.find(':checkbox');
			
		    if ($(this).is(':checked')) {
		    	//check all boxes
		    	input.prop('checked', true);
		    	
		    	//add hightlight
		    	downloadItem.addClass('highlight');
		    } else {
		    	input.prop('checked', false);
		    	downloadItem.removeClass('highlight');
		    }
		} else {
			//part of a multi?
			var firstInput = downloadItem.find(':checkbox').first();
			var inputName = firstInput.prop('name');
			
			if (inputName.indexOf('multi') !== -1) {
				//Multi download item checkbox
			    if ($(this).is(':checked')) {
			    	downloadItem.addClass('highlight');
			    } else {
			    	if (downloadItem.find(':checkbox').is(':checked')) {
			    		downloadItem.addClass('highlight');
			    	} else {
			    		downloadItem.removeClass('highlight');
			    	}
			    	
			    }	
			} else {
				//NON MULTI
			    if ($(this).is(':checked')) {
			    	downloadItem.addClass('highlight');
			    } else {
			    	downloadItem.removeClass('highlight');
			    }
			}
		}
		
		return;

	});
    
	//Highlight checked items
	$(document).on('click', '.download-item, .selectable', function(event) {

		var target = $(event.target);
	    if (target.is('input:checkbox')) return;
			
	    var input = $(this).find(':checkbox');
	    
	    if (input.is(':checked')) {
	    	input.prop('checked', false);
	        $(this).removeClass('highlight');
	    } else {
	    	input.prop('checked', true);
	        $(this).addClass('highlight');
	    }
	    return ;
	    			
	});

   calc_shows()

    $(document).on('click', '#show-shows-no-missing', function(event) {

        $( ".show" ).each(function( index ) {
            //how many seasons do we have
            seasons_count = $(this).find(".season").length
            all_exist_count = $(this).find(".season-all-exists").length

            if (seasons_count == all_exist_count) {
                $(this).show()
            }
        });

        //change button
        $("#show-shows-no-missing").text("Hide shows with none missing")
        $("#show-shows-no-missing").attr("id","hide-shows-no-missing")

        calc_shows()
    });


    $(document).on('click', '#hide-shows-no-missing', function(event) {

        $( ".show" ).each(function( index ) {
            //how many seasons do we have

            seasons_count = $(this).find(".season:visible").length
            all_exist_count = $(this).find(".season-all-exists:visible").length
            wont_fix_count = $(this).find(".season-wont-fix:visible").length

            count = all_exist_count + wont_fix_count

            if (seasons_count == count) {
                $(this).hide()
            }
        });

        //change button
        $("#hide-shows-no-missing").text("Show shows with none missing")
        $("#hide-shows-no-missing").attr("id","show-shows-no-missing")

        calc_shows()
    });

    $(document).on('click', '#hide-missing-seasons', function(event) {
        //hide all the entire missing seasons
        $(".missing-all-season").parent().hide()

        //change button
        $("#hide-missing-seasons").text("Show Missing Seasons")
        $("#hide-missing-seasons").attr("id","show-missing-seasons")
    });

    $(document).on('click', '#show-missing-seasons', function(event) {
        //hide all the entire missing seasons
        $(".missing-all-season").parent().show()

        //change button
        $("#show-missing-seasons").text("hide Missing Seasons")
        $("#show-missing-seasons").attr("id","hide-missing-seasons")
    });

    /////////////////////
    /// BUTTON POST ////
    ////////////////////

    $(document).on('click', '.button_post_newpage', function(event) {
        var url = $(this).attr('url');
        event.preventDefault();

        $('#formID').prop("method", "post")
        $('#formID').prop("name", "downloads")
        $('#formID').prop("action", url)

        document.forms['downloads'].submit();


	});

	$(document).on('click', '.button_post', function(event) {
		var url = $(this).attr('url');

		var okPage = $('.downloads').attr('okPage');
		var refresh = $('.downloads').attr('refresh');
		var downloads = $('.downloads').length;
        var button_reload_page = $(this).attr('reload');

        if (refresh == undefined) {
            if (downloads == 0) {
                refresh = 'false';
            }
        }

		event.preventDefault();
		
		formdata=$('#formID').serialize();

		$.post(url,formdata).done(function(data){
			
			if (refresh != 'false') {
				getContent();
			}
						
			result = "<pre id='dialog'>" + data + "</pre>";
			
			if ($('#dialog').length > 0) {
				$('#dialog').html(result);
			} else {
				$('#content').prepend(result);
			}
			
			$( "#dialog" ).dialog({
				  minHeight: 300,
			      width: 700,
			      modal: true,
			      resize: "auto",
			     
			      buttons: {
			          Ok: function() {
                          if (button_reload_page == "true") {
                              $( this ).dialog( "close" );
                              location.reload();
                          }
                          if (okPage == undefined) {
                              $( this ).dialog( "close" );
                          } else {
                              window.location.href = okPage;

                          }
                          $(window).scrollTop(0);
			          }
			        }
			    });

		});

 		return false;
	});
	
	
	

});


function update_season() {
    showid = $('#id_tvdbid_id').val()
    $('#id_epoverride').empty();
    $('#id_seasonoverride').empty();

    $('#id_seasonoverride').append("<option value='Select Season'>Select Season</option>");

    $.ajax({
        url: lazyapi_url + "/get_tvdb_season/" + showid,
        type: 'GET',
        dataType: 'json', // or your choice of returned data
        success: function(seasons){
             $.each(seasons, function(i, stt){
                 $('#id_seasonoverride').append('<option value="'+stt.value+'">'+stt.label+'</option>');
             });
        }
    });
}

function update_ep() {
    season = $('#id_seasonoverride').val();
    showid = $('#id_tvdbid_id').val()
    epselect = $('#id_epoverride');
    epselect.empty();

    $.ajax({
        url: lazyapi_url + "/get_tvdb_eps/" + showid + "/" + season,
        type: 'GET',
        dataType: 'json', // or your choice of returned data
        success: function(eps){
             $.each(eps, function(i, stt){
                 epselect.append('<option value="'+stt.value+'">'+stt.label+'</option>');
             });
        }
    });
}

function calc_shows() {
     $("#report_count").text($(".show:visible").length)
}


function getContent() {
	var type = $('.downloads').attr('getType');
	var action = $('.downloads').attr('action');
	var post = $('.downloads').attr('post'); 
	
	geturl = '';
	
	if(type == '10') {
		
		var ids = $('.downloads').attr('ids').split(',');
		
		var idget = '';
		
		jQuery.each( ids, function( i, field ) {
			idget += "&id[]=" + field;
	    });
		
		geturl = action + idget;
	} else {
		geturl = action;
	}
	
	if (post && post != '') {
		geturl = geturl + post;
	}
	
	$.get(geturl, function( data ) {
		$('.downloads').html( data );
		var action = $('.downloads').attr('action');
		
		if (action == 'downloads') {
			$(".download-item").each(function() {
				//var lefth = $(this).children(".left-col").height();
				var righth = $(this).children(".right-col").height();
				
				if (righth < 230) {
					var righth = 230;
				}
			
				$(this).children(".left-col").height(righth);
			});
		}
	});	
}

function doProgressbar(id, percent) {
    $( '.progressbar_' + id).progressbar({
    	value: percent
	});
	
	if (percent < 10){
	    $('.progressbar_' + id + ' > div').css({ 'background': 'Red' });
	} else if (percent < 30){
	    $('.progressbar_' + id + ' > div').css({ 'background': 'Orange' });
	} else if (percent < 50){
	    $('.progressbar_' + id + ' > div').css({ 'background': 'Yellow' });
	} else{
	    $('.progressbar_' + id + ' > div').css({ 'background': 'LightGreen' });
	}
}

function doReverseProgressbar(id, percent) {
    $( '.progressbar_' + id).progressbar({
    	value: percent
	});
	
	if (percent > 95){
	    $('.progressbar_' + id + ' > div').css({ 'background': 'Red' });
	} else if (percent > 80){
	    $('.progressbar_' + id + ' > div').css({ 'background': 'Orange' });
	} else{
	    $('.progressbar_' + id + ' > div').css({ 'background': 'LightGreen' });
	}
}

