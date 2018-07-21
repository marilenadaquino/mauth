(function($) {

    var contact;

    $(document).bind('gform_post_render', function(event, id, page){       
        
        if(id === 1){
            $('#gform_wrapper_1').removeClass('gform_wrapper--show');            
            updateWorkForm();
        }
        
        if(id === 2){
            $('#gform_wrapper_2').removeClass('gform_wrapper--show');
            updateContactForm(page);
        }

        if(id === 3){
            updateSignupForm();
        }        

        $(document).on('keyup', '.gfield input[type="text"]', function(e){
            
            if($(this).siblings('.validation_message').length > 0){
                
                $(this).siblings('.validation_message').css('display', 'none');
            }

            $(this).siblings('span').html($(this).val());

            if($(this).siblings('span').text().length < 1){
                $(this).siblings('span').html($(this).attr('placeholder'));
                //$(this).siblings('.validation_message').css('display', 'block');
            }
            
            if($(this).parent('span').width() < $(this).parent('span').parent().parent().width()){
                $(this).parent('span').css('min-width', $(this).siblings('span').width() + 1 + 'px');
            }
            
        });

        // Remove input scroll 
        $('input').bind('focusin focus', function(e){
            e.preventDefault();
        });


        // Autocomplete no to all text inputs
        $('input[type="text"], input[type="email"], input[type="number"]').each(function(index, element){
            $(element).attr('autocomplete', 'off');
        });

        // code to trigger on AJAX form render
        if( $('.gfield_error').length ) {
            $('.gfield_error').each(function(e){
                // Get the field
                $(this).css({ display : 'none' });
                if($(this).attr('class').match(/contact-[a-z-]+/)){
                    var field = $(this).attr('class').match(/contact-[a-z-]+/)[0];
                    field = '.' + field.substring(0, field.length - 6);
                }

                if($(this).attr('class').match(/work-[a-z-]+/)){
                    var field = $(this).attr('class').match(/work-[a-z-]+/)[0];
                    field = '.' + field.substring(0, field.length - 6);
                }
                
                // Add validation message to corresponding 
                $(field).append($(this).find('div.validation_message'));
            });
        }

        $('.gfield select').on('change', function(e){
            $(this).siblings('span').html($(this).val());
            $(this).parent('span').css('min-width', $(this).siblings('span').width() + 1 + 'px');
        });

        $('.gfield select').on('focus', function(e){
            $(this).siblings('span').html($(this).val());
            $(this).parent('span').css('min-width', $(this).siblings('span').width() + 1 + 'px');
        });


        
    });

    $(document).bind('gform_confirmation_loaded', function(event, formId){
        if(formId === 2){
            $('.home__contact-message h3').html('Message received.');
            $('.home__contact-message').parent().removeClass('full--no-padding-bottom');
        }
        if(formId === 1){
            $('.home__work-message').css('display', 'none')
        }
    });

    function updateSignupForm(){
        $('.signup-email').append($('.signup-email-input').find('input'));

        $('.signup-email').find('input').attr('value') === '' ? false : $('signup-email span').html($('.signup-email').find('input').attr('value'));

        $('.signup-email-input').css('display', 'none');

        $('#gform_wrapper_3').addClass('gform_wrapper--show'); 
    }

    function updateWorkForm(){
        // Add form elements to top HTML block
        $('.work-name').append($('.work-name-input').find('input'));
        $('.work-email').append($('.work-email-input').find('input'));
        $('.work-style').append($('.work-style-input').find('select'));

        $('.work-name').find('input').attr('value') === '' ? false : $('.work-name span').html($('.work-name').find('input').attr('value')); 
        $('.work-email').find('input').attr('value') === '' ? false : $('.work-email span').html($('.work-email').find('input').attr('value')); 
        $('.work-style').find('select').attr('value') === '' ? false : $('.work-style span').html($('.work-style').find('select').find('option').eq(0).text());

        // Disable placeholder option
        $('.work-style').find('select').find('option').eq(0).attr('disabled', 'disabled');

        $('.work-name').css('min-width', $('.work-first-name').children('span').width() + 'px');
        $('.work-email').css('min-width', $('.work-email').children('span').width() + 'px');

        $('.work-name-input').css('display', 'none');
        $('.work-email-input').css('display', 'none');
        $('.work-style-input').css('display', 'none');

        $('#gform_wrapper_1').addClass('gform_wrapper--show');        
    }

    function updateContactForm(page){

        if(page == 1){

            $('.home__contact-message h3').html('Go on, leave us a message after the beeeep.');
                       
            // Add form elements to top HTML block
            $('.contact-name').append($('.contact-name-input').find('input'));
            $('.contact-company').append($('.contact-company-input').find('input'));
            $('.contact-email').append($('.contact-email-input').find('input'));
            $('.contact-number').append($('.contact-number-input').find('input'));
            $('.contact-country').append($('.contact-country-input').find('select'));

            // Update form with input values
            $('.contact-name').find('input').attr('value') === '' ? false : $('.contact-name span').html($('.contact-name').find('input').attr('value'));
            $('.contact-company').find('input').attr('value') === '' ? false : $('.contact-company span').html($('.contact-company').find('input').attr('value'));
            $('.contact-email').find('input').attr('value') === '' ? false : $('.contact-email span').html($('.contact-email').find('input').attr('value'));
            $('.contact-number').find('input').attr('value') === '' ? false : $('.contact-number span').html($('.contact-number').find('input').attr('value'));
            $('.contact-country').find('select').attr('selected') === '' ? false : $('.contact-country span').html($('.contact-country').find('select').find('option').eq(0).text());

            // Disable placeholder option
            $('.contact-country').find('select').find('option').eq(0).attr('disabled', 'disabled');

            // Add min-width to span's
            $('.contact-name').css('min-width', $('.contact-first-name').children('span').width() + 'px');
            $('.contact-company').css('min-width', $('.contact-company').children('span').width() + 'px');
            $('.contact-email').css('min-width', $('.contact-email').children('span').width() + 'px');
            $('.contact-number').css('min-width', $('.contact-number').children('span').width() + 'px');
            $('.contact-country').css('min-width', $('.contact-country').children('span').width() + 'px');

            // Remove old list elements
            $('.contact-name-input').css('display', 'none');
            $('.contact-company-input').css('display', 'none');
            $('.contact-email-input').css('display', 'none');
            $('.contact-number-input').css('display', 'none');
            $('.contact-country-input').css('display', 'none');

            //Add second button to contact form
            $('#gform_page_2_1 .gform_page_footer').append($('.contact-button-input').find('input'));

            $('#gform_page_2_1 .gform_page_footer input').each(function(index, element){
                $(element).addClass('btn-' + (index + 1));
            });
        }

        if(page == 2){
            contact = JSON.parse(Cookies.get('contact'));

            if(contact.button == 1){
                $('.btn-copy span').append(contact.name);
                $('.home__contact-message h3').html($('.btn1').text());
            }
            
            if(contact.button == 2){
                $('.btn-copy span').append(contact.name);
                $('.home__contact-message h3').html($('.btn2').text());
            }
        }

        $('#gform_wrapper_2').addClass('gform_wrapper--show');
    }

    $(document).on('click', '#contact .gform_next_button', function(e){
        e.preventDefault();

        if($(this).hasClass('btn-1')){
            
            Cookies.set('contact', {
                    name: $('.contact-name span').text(),
                    button: '1'
                }, 
                { expires: 0.001 }
            );
        }
        if($(this).hasClass('btn-2')){
            
            Cookies.set('contact', {
                    name: $('.contact-name span').text(),
                    button: '2'
                }, 
                { expires: 0.001 }
            );
        }
        $('.textarea').focus();
        return false;
    });

    $(document).on('click', '#contact .gform_previous_button', function(){
        Cookies.remove('contact');
    });

    $(document).on('click', '#work .gform_button', function(e){
        //e.preventDefault();
        window.open('http://folio.apostrophe.xyz');
    });

})(jQuery);

