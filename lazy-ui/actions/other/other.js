$( document ).ready(function() {	
	
	//Hightlight from checkbox click
	$(document).on('click', 'input:checkbox', function(event) {
		
		var epItem = $(this).closest('.ep');
		
		
	    if ($(this).is(':checked')) {
	    	epItem.addClass('highlight');
	    } else {
	    	epItem.removeClass('highlight');
	    }
	    
		return;
	});
    
	//Highlight checked items
	$(document).on('click', '.ep', function(event) {

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
	
});