$( document ).ready(function() {
	
	$(document).on('submit', '#tvdbsearch', function(event) {
		var action = $('.downloads').attr('action');
		var type = $('.downloads').attr('getType');
		
		formdata=$('#tvdbsearch').serialize();

		$.post("/actions/" + action + "/update.php?action=" + name + '&t=' + type,formdata).done(function(data){
			
			getContent();
						
			if ($('.returnmsg').length > 0) {
				$('.returnmsg').html("<div class='returnmsg highlight middle-outer'><div class='middle-inner'>" + data + "</div></div>" );
			} else {
				$('#content').prepend( "<div class='returnmsg highlight middle-outer'><div class='middle-inner'>" + data + "</div></div>" );
			}
				
			
		});
		
		event.preventDefault();
	});
	
);