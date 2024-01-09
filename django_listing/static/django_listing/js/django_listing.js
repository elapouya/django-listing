function djlst_replaceUrlParam(url, param_name, param_value)
{
    if (param_value == null) {
        param_value = '';
    }
    let url_obj;
    if (url.startsWith("/")) {
        url_obj = new URL(url, window.location.origin);
    } else {
        url_obj = new URL(url);
    }
    url_obj.searchParams.set(param_name, param_value);
    return url_obj.toString();
}

function djlst_removeUrlParam(url, param_name)
{
    let url_obj = new URL(url);
    url_obj.searchParams.delete(param_name);
    return url_obj.toString();
}

function get_csrf_token() {
    name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue
}

function update_csrf_token() {
    $.ajaxSetup({
        data: { 'csrfmiddlewaretoken': get_csrf_token() }
    });
}

function djlst_load_listing_url(nav_obj, url) {
    if (! $("div.django-listing-ajax").length) {
        window.location.href = url;
    }
    var listing_div = nav_obj.closest("div.django-listing-ajax");
    listing_div.addClass("spinning");
    var listing_id = $(listing_div).attr("id");
    var listing_suffix = $(listing_div).attr("listing-suffix");
    var listing_target = nav_obj.attr("listing-target");
    if (! listing_target) listing_target = "#"+listing_id;
    var listing_part = nav_obj.attr("listing-part");
    if (! listing_part) listing_part = "all";
    update_csrf_token();
    $(listing_target).load(
        url,
        {
            "listing_id": listing_id,
            "listing_suffix": listing_suffix,
            "listing_part": listing_part
        },
        function (responseText, textStatus, req) {
            if (textStatus == "error") {
                listing_div.removeClass("spinning");
                alert(responseText);
            } else {
                $(this).children(":first").unwrap();
            }
            djlst_listing_on_load();
            $(document).trigger( "djlst_ajax_loaded", [ listing_target ] );
        } // to avoid cascade of listing container divs
    );
    return false;
}

function djlst_load_listing_href() {
    return djlst_load_listing_url($(this),$(this).attr("href"));
}

function djlst_load_listing_val() {
    var param_value = $(this).val();
    var param_name = $(this).attr("name");
    var ajax_url = $(this).closest("div.django-listing-ajax").attr("ajax_url");
    var url = djlst_replaceUrlParam(ajax_url, param_name, param_value);
    return djlst_load_listing_url($(this),url);
}

function djlst_post_button_action(event) {
    event.preventDefault();
    var nav_obj = $(this);
    var listing_div = nav_obj.closest("div.django-listing-ajax");
    var ajax_url = listing_div.attr("ajax_url");
    listing_div.addClass("spinning");
    var listing_id = listing_div.attr("id");
    var listing_suffix = listing_div.attr("listing-suffix");
    var listing_target = nav_obj.attr("listing-target");
    if (! listing_target) listing_target = "#"+listing_id;
    var listing_part = nav_obj.attr("listing-part");
    if (! listing_part) listing_part = "all";
    request_data = {
        listing_id : listing_id,
        listing_suffix : listing_suffix,
        listing_part : listing_part,
        serialized_data : nav_obj.closest('form').serialize()
    };
    request_data[$(this).attr('name')]=$(this).val();
    update_csrf_token();
    $.ajax({
       type: "POST",
       url: ajax_url,
       data: request_data,
       success: function(response)
       {
           $(listing_target).html(response);
           $(listing_target).children(":first").unwrap();
           djlst_listing_on_load();
           $(document).trigger( "djlst_ajax_loaded", [ listing_target ] );
       }
    });
}

function djlst_multiple_row_select(e) {
    var row=$(this).closest('.row-container');
    var hidden=row.find('input.row-select').first();
    if (row.hasClass('selected')) {
        row.removeClass('selected');
        hidden.removeAttr('name');
        row.find('input.selection-box').first().prop('checked',false);
    } else {
        row.addClass('selected');
        hidden.attr('name',hidden.attr('select-name'));
        row.find('input.selection-box').first().prop('checked',true);
    }
    djlst_selection_menu_update($(this));
}

function djlst_unique_row_select(e) {
    var row=$(this).closest('.row-container');
    var hidden=row.find('input.row-select').first();
    if (row.hasClass('selected')) {
        row.removeClass('selected');
        hidden.removeAttr('name');
        row.find('input.selection-box').first().prop('checked',false);
    } else {
        row.siblings().removeClass('selected').find('input.row-select').removeAttr('name');
        row.addClass('selected');
        hidden.attr('name', hidden.attr('select-name'));
        row.find('input.selection-box').first().prop('checked', true);
    }
    djlst_selection_menu_update($(this));
}


function djlst_select_all(e) {
    var listing_id = $(this).attr('listing-target');
    var listing = $('#'+listing_id);
    listing.find('.row-container').addClass('selected');
    listing.find('input.selection-box').prop('checked',true);
    listing.find('input.row-select').each(function () {
        var hidden=$(this);
        hidden.attr('name',hidden.attr('select-name'));
    });
    djlst_selection_menu_update(listing);
}

function djlst_unselect_all(e) {
    var listing_id = $(this).attr('listing-target');
    var listing = $('#'+listing_id);
    djlst_listing_unselect_all(listing);
}

function djlst_listing_unselect_all(listing) {
    listing.find('.row-container').removeClass('selected');
    listing.find('input.selection-box').prop('checked',false);
    listing.find('input.row-select').each(function () {
        $(this).removeAttr('name');
    });
    djlst_selection_menu_update(listing);
}

function djlst_activate_selection(e) {
    var listing = $(this).closest("div.django-listing-selecting");
    listing.find(".selection-overlay.hover")
           .removeClass('hover').addClass('had-hover');
    var selection_menu_id = listing.attr('selection-menu-id');
    var selection_menu = $('#'+selection_menu_id);
    selection_menu.attr('listing-id',listing.attr('id'));
    var display_mode = selection_menu.attr('menu-display-mode');
    switch (display_mode) {
        case 'show':
            selection_menu.show();
            break;
        case 'fade':
            selection_menu.fadeIn(300);
            break;
        case 'slide':
            selection_menu.slideDown(300);
            break;
    }
    djlst_selection_menu_update($(this));
}

function djlst_deactivate_selection(e) {
    var selection_menu = $(this).closest('.listing-selection-menu');
    var listing_id = selection_menu.attr('listing-id');
    var listing =  $('#'+listing_id);
    listing.find(".selection-overlay.had-hover")
           .addClass('hover').removeClass('had-hover');
    djlst_listing_unselect_all(listing);
    var display_mode = selection_menu.attr('menu-display-mode');
    switch (display_mode) {
        case 'show':
            selection_menu.hide();
            break;
        case 'fade':
            selection_menu.fadeOut(300);
            break;
        case 'slide':
            selection_menu.slideUp(300);
            break;
    }
}

function djlst_selection_menu_update(e) {
    var listing = e.closest("div.django-listing-selecting");
    var selection_menu_id = listing.attr('selection-menu-id');
    if (selection_menu_id) {
        var selection_menu = $('#' + selection_menu_id);
        var selected_items = selection_menu.find('span.selected_items')
        var count = listing.find('.row-container.selected').length;
        if (count == 0) {
            selected_items.text(selected_items.attr('none'));
        } else if (count == 1) {
            selected_items.text(selected_items.attr('one'));
        } else {
            selected_items.text(selected_items.attr('many').replace('{nb}', count));
        }
    }
}

function djlst_view_object_popup(event) {
    event.preventDefault();
    var nav_obj = $(this);
    var listing_div = nav_obj.closest("div.django-listing-container");
    var ajax_url = listing_div.attr("ajax_url");
    listing_div.addClass("spinning");
    var listing_id = listing_div.attr("id");
    var listing_suffix = listing_div.attr("listing-suffix");
    request_data = {
        listing_id : listing_id,
        listing_suffix : listing_suffix,
        action_button : 'view_object_popup',
        serialized_data : nav_obj.closest('form').serialize()
    };
    update_csrf_token();
    $.ajax({
       type: "POST",
       url: ajax_url,
       data: request_data,
       success: function(response)
       {
           listing_div.removeClass("spinning");
           $("#listing-popup-container").html(response);
           $("#listing-popup-container > div.modal").modal("show");
       }
    });
}

function djlst_listing_on_load() {
    $(".group-by-container").each(function() {
        let group_by_select = $(this).find(".group-by-select")
        new DualListbox(group_by_select[0], {
            addButtonText: '>',
            removeButtonText: '<',
            addAllButtonText: '>>',
            removeAllButtonText: '<<',
            availableTitle: group_by_select.attr("available-title") || 'Available columns',
            selectedTitle: group_by_select.attr("selected-title") || 'Selected columns'
        });
        let annotation_select = $(this).find(".annotation-select")
        new DualListbox(annotation_select[0], {
            addButtonText: '>',
            removeButtonText: '<',
            addAllButtonText: '>>',
            removeAllButtonText: '<<',
            availableTitle: annotation_select.attr("available-title") || 'Available columns',
            selectedTitle: annotation_select.attr("selected-title") || 'Selected columns'
        });
        $(this).find(".apply-group-by").on("click", function () {
            let gb_cols = group_by_select.val().join(",");
            let url = djlst_replaceUrlParam(window.location.href, "gb_cols", gb_cols);
            let gb_annotate_cols = annotation_select.val().join(",");
            url = djlst_replaceUrlParam(url, "gb_annotate_cols", gb_annotate_cols);
            djlst_load_listing_url($(this), url);
        });
        $(this).find(".remove-group-by").on("click", function () {
            let url = djlst_removeUrlParam(window.location.href, "gb_cols");
            url = djlst_removeUrlParam(url, "gb_annotate_cols");
            djlst_load_listing_url($(this), url);
        });
    });
}

$(document).ready(function () {

    var select2_opened = false;

    $('form.listing-form').submit(function () {
        $(this).find('input[name]').filter(function () {
            return !this.value;
        }).prop('name', '');
    });

    $(document.body).on("click","div.django-listing-ajax button.listing-nav",djlst_post_button_action);
    $(document.body).on("click","div.django-listing-ajax a.listing-nav",djlst_load_listing_href);
    $(document.body).on("change","div.django-listing-ajax select.listing-nav",djlst_load_listing_val);
    $(document.body).on("click","div.django-listing-selecting.selection_multiple .row-selector",djlst_multiple_row_select);
    $(document.body).on("click","div.django-listing-selecting.selection_unique .row-selector",djlst_unique_row_select);
    $(document.body).on("click","div.django-listing-selecting .selection-overlay.hover",djlst_activate_selection);
    $(document.body).on("click","[listing-action='select-all']", djlst_select_all);
    $(document.body).on("click","[listing-action='unselect-all']", djlst_unselect_all);
    $(document.body).on("click",".listing-selection-menu .listing-menu-close", djlst_deactivate_selection);
    $(document.body).on("click","li.action-item.view-object-popup a", djlst_view_object_popup);
    $(document.body).on("click", ".button-action-group-by", function () {
        $(this).closest(".django-listing-container").find(".group-by-container").slideToggle(200);
    });

    $('[data-toggle="popover"]').popover();

    var dropzoneCounter = 0;

    $('.dropzone').on('dragenter', function(){
        dropzoneCounter++;
        $(this).addClass('drag-over');
    });

    $('.dropzone').bind('dragleave', function(){
        dropzoneCounter--;
        if (dropzoneCounter === 0) {
            $(this).removeClass('drag-over');
        }
    });

    $('.dropzone').bind('drop', function(){
        dropzoneCounter = 0;
        $(this).removeClass('drag-over');
    });

    $('.submit-action-form').on('click', function () {
        var action = $(this).val();
        var form = $(this).closest('.django-listing-container').find('.action-form');
        var hidden = form.find('.action-hidden-value');
        hidden.val(action);
        form.submit();
    });

    $(document).on('select2:open', function(e) {
        let aria_owns = $(e.target).parent().find('.select2-selection').attr('aria-owns');
        document.querySelector('input[aria-controls="' + aria_owns + '"]').focus();
        select2_opened = true;
    });

    $("form").keyup(function(e) {
        if (e.keyCode == 9) {
            const target = $(e.target)
            if (target.hasClass("select2-selection")) {
                 if (! select2_opened) {
                     target.closest(".select2").siblings("select").first().select2("open");
                 }
                 select2_opened = true;
            } else {
                select2_opened = false;
            }
        }
    });

    djlst_listing_on_load();
});
