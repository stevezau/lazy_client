
String.prototype.startsWith = function (str)
{
   return this.indexOf(str) == 0;
};

$( document ).ready(function() {
		
	$( "#dialog" ).dialog();
	 
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
	
	$(document).on('click', '[class^=button_]', function(event) {
		var curUrl = document.URL;
		var myRegexp = /action=([a-z[A-Z]+)/i;
		var matches = myRegexp.exec(curUrl);
		
		var action = matches[1];
		var name = $(this).prop('class').replace('button_', '');
		
		var okPage = $('.downloads').attr('okPage');
		
		var refresh = $('.downloads').attr('refresh');
		var downloads = $('.downloads').length;
		
		if (downloads == 0) {
			refresh = 'false';
		}
		
		event.preventDefault();
		
		formdata=$('#formID').serialize();

		if (name.startsWith('page_')) {
			var pgname = name.replace('page_', '');
					
			var idparts = formdata.split("&");
			get = '';

			jQuery.each( idparts, function( i, field ) {
				var txt = field.replace("item%5B%5D=", "");
				get += "&id[]=" + txt;
		
		    });
			window.location = 'index.php?action=' + action + '&t=' + pgname + get;
			return;
		}

		$.post("actions/" + action + "/update.php?action=" + name,formdata).done(function(data){
			
			if (refresh != 'false') {
				getContent();
			}
						
			errorDiv = "<div id='dialog'><pre>" + data + "</pre></div>";
			
			if ($('#dialog').length > 0) {
				$('#dialog').html(errorDiv);
			} else {
				$('#content').prepend(errorDiv);
			}
			
			$( "#dialog" ).dialog({
				  minHeight: 300,
			      width: 700,
			      modal: true,
			      resize: "auto",
			     
			      buttons: {
			          Ok: function() {
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
		
		geturl = 'actions/' + action +'/getContent.php?t=' + type + idget;
	} else {
		geturl = 'actions/' + action + '/getContent.php?t=' + type;
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

