$( document ).ready(function() {
    $('#menu').slicknav({
        'label' : 'MENU', // Label for menu button. Use an empty string for no label.
        'duplicate': true, // If true, the mobile menu is a copy of the original.
        'duration': true, // The duration of the sliding animation.
        'easingOpen': 'swing', // Easing used for open animations.
        'easingClose': 'swing', // Easing used for close animations.
        'prependTo': 'body', // Element, jQuery object, or jQuery selector string to prepend the mobile menu to.
        'parentTag': 'a', // Element type for parent menu items.
        'closeOnClick': false // Close menu when a link is clicked.
    });
});