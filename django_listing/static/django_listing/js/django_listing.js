function djlst_replaceUrlParam(url, param_name, param_value) {
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

function djlst_removeUrlParam(url, param_name) {
    let url_obj = new URL(url);
    url_obj.searchParams.delete(param_name);
    return url_obj.toString();
}

function update_csrf_token() {
    $.ajaxSetup({
        data: {'csrfmiddlewaretoken': Cookies.get('csrftoken')}
    });
}

function djlst_load_listing_url(nav_obj, url) {
    if (!$("div.django-listing-ajax").length) {
        window.location.href = url;
    }
    var listing_div = nav_obj.closest("div.django-listing-ajax");
    listing_div.addClass("spinning");
    var listing_id = $(listing_div).attr("id");
    var listing_suffix = $(listing_div).attr("listing-suffix");
    var listing_target = nav_obj.attr("listing-target");
    if (!listing_target) listing_target = "#" + listing_id;
    var listing_part = nav_obj.attr("listing-part");
    if (!listing_part) listing_part = "all";
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: url,
        data: {
            "listing_id": listing_id,
            "listing_suffix": listing_suffix,
            "listing_part": listing_part
        },
        success: function (response) {
            $(listing_target).replaceWith(response);
            djlst_listing_on_load();
            $(document).trigger("djlst_ajax_loaded", {listing_target: listing_target});
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        },
    });
    return false;
}

function djlst_load_listing_href() {
    return djlst_load_listing_url($(this), $(this).attr("href"));
}

function djlst_load_listing_val() {
    var param_value = $(this).val();
    var param_name = $(this).attr("name");
    var ajax_url = $(this).closest("div.django-listing-ajax").attr("ajax_url");
    var url = djlst_replaceUrlParam(ajax_url, param_name, param_value);
    return djlst_load_listing_url($(this), url);
}

function djlst_post_action_button(event) {
    event.preventDefault();
    var nav_obj = $(this);
    var listing_div = nav_obj.closest("div.django-listing-ajax");
    var ajax_url = listing_div.attr("ajax_url");
    listing_div.addClass("spinning");
    var listing_id = listing_div.attr("id");
    var listing_suffix = listing_div.attr("listing-suffix");
    var listing_target = nav_obj.attr("listing-target");
    if (!listing_target) listing_target = "#" + listing_id;
    var listing_part = nav_obj.attr("listing-part");
    if (!listing_part) listing_part = "all";
    let request_data = {
        listing_id: listing_id,
        listing_suffix: listing_suffix,
        listing_part: listing_part,
        serialized_data: nav_obj.closest('form').serialize()
    };
    request_data[$(this).attr('name')] = $(this).val();
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        success: function (response) {
            $(listing_target).replaceWith(response);
            djlst_listing_on_load();
            $(document).trigger("djlst_ajax_loaded", {listing_target: listing_target});
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        }
    });
}

function djlst_post_attached_form(event) {
    event.preventDefault();
    let nav_obj = $(this);
    let action_button = nav_obj.val();
    let attached_form = nav_obj.closest("form.listing-form");
    let attached_form_id = attached_form.attr("id");
    let listing_div = $("#" + attached_form.attr("related-listing"));
    let selected_rows = listing_div.find(".row-container.selected");
    let confirm_msg = nav_obj.attr("confirm-msg");
    if (confirm_msg) {
        let confirm_msg_nb_items = nav_obj.attr("confirm-msg-nb-items");
        confirm_msg_nb_items = parseInt(confirm_msg_nb_items);
        if (isNaN(confirm_msg_nb_items)) confirm_msg_nb_items = 0;
        confirm_msg = confirm_msg.replace("{nb_items}", selected_rows.length);
        nb_all_items = listing_div.attr("nb-rows");
        if (!nb_all_items) nb_all_items = "";
        confirm_msg = confirm_msg.replace("{nb_all_items}", nb_all_items);
        if (selected_rows.length >= confirm_msg_nb_items) {
            if (!confirm(confirm_msg)) return;
        }
    }
    let selected_pks = selected_rows.map(function () {
        return $(this).attr("data-pk")
    }).get().join(',');
    let ajax_url = listing_div.attr("ajax_url");
    // listing_div.addClass("spinning");
    let listing_id = listing_div.attr("id");
    let listing_suffix = listing_div.attr("listing-suffix");
    let listing_target = nav_obj.attr("listing-target");
    if (!listing_target) listing_target = "#" + listing_id;
    let listing_part = nav_obj.attr("listing-part");
    if (!listing_part) listing_part = "all";

    let request_data = {
        listing_id: listing_id,
        listing_suffix: listing_suffix,
        listing_part: listing_part,
        action: "attached_form",
        action_button: action_button,
        selected_pks: selected_pks,
        serialized_data: nav_obj.closest('form').serialize()
    };
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        success: function (mixed_response) {
            let new_attached_form;
            if (mixed_response.listing) {
                listing_div.replaceWith(mixed_response.listing);
            }
            if (mixed_response.attached_form) {
                attached_form.replaceWith(mixed_response.attached_form);
                djlst_selection_changed_hook(listing_div);
            }
            if (mixed_response.object_pk) {
                new_attached_form = $("#" + attached_form_id);
                let object_pk_input = new_attached_form.find('input[name="object_pk"]');
                object_pk_input.val(mixed_response.object_pk);
            }
            $(document).trigger(
                "djlst_ajax_attached_form_loaded",
                {listing: listing_target, form: new_attached_form}
            );
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        }
    });
}

var djlst_last_selected_rows_container = null;
var djlst_last_selected_index = null;

function djlst_multiple_row_select(e) {
    let row = $(this).closest('.row-container');
    let rows_container = row.parent();
    let index = row.index();
    let last_rows_container = djlst_last_selected_rows_container;
    let last_index = djlst_last_selected_index;
    let listing_div = row.closest('.django-listing-container');
    let selection_ctrl = listing_div.hasClass("selection-multiple-ctrl");
    let action;
    if (row.hasClass('selected')) {
        action = djlst_multiple_row_do_unselect;
    } else {
        action = djlst_multiple_row_do_select;
    }
    if (selection_ctrl && !e.ctrlKey) {
        row.siblings().removeClass('selected');
    }
    if (e.shiftKey && last_rows_container[0] === rows_container[0] && last_index != null) {
        djlst_map_children_range(rows_container, last_index, index, action);
        djlst_unselectText();
    } else {
        action(row);
    }
    djlst_selection_changed_hook($(this));
    djlst_last_selected_rows_container = rows_container;
    djlst_last_selected_index = index;
}

function djlst_map_children_range(container, index1, index2, func) {
    if (index2 >= index1) {
        rows = container.children().slice(index1, index2 + 1);
    } else {
        rows = container.children().slice(index2, index1 + 1);
    }
    rows.each(function () {
        func($(this));
    });
}

function djlst_multiple_row_do_unselect(row) {
    let hidden = row.find('input.row-select').first();
    row.removeClass('selected');
    hidden.removeAttr('name');
    row.find('input.selection-box').first().prop('checked', false);
    let nb_slected = row.siblings(".selected").length;
    if (nb_slected == 1) {
        row = row.siblings(".selected").first();
        let listing_div = row.closest('.django-listing-container');
        let form = $("#" + listing_div.attr('attached-form-id'));
        if (form.length) {
            if (listing_div.hasClass("attached_form_autofill")) {
                let serialized_data = row.attr('data-serialized-object');
                if (serialized_data) {
                    let serialized_obj = decodeURIComponent(escape(atob(serialized_data)));
                    let obj = JSON.parse(serialized_obj);
                    let pk = row.attr("data-pk");
                    djlst_fill_form(form, obj, pk);
                }
            }
        }
    }
}

function djlst_multiple_row_do_select(row) {
    let hidden = row.find('input.row-select').first();
    row.addClass('selected');
    hidden.attr('name', hidden.attr('select-name'));
    row.find('input.selection-box').first().prop('checked', true);
    let listing_div = row.closest('.django-listing-container');
    let form = $("#" + listing_div.attr('attached-form-id'));
    if (form.length) {
        if (listing_div.hasClass("attached_form_autofill")) {
            let nb_slected = row.siblings(".selected").length;
            if (nb_slected > 0) {
                djlst_clean_form(form);
            } else {
                let serialized_data = row.attr('data-serialized-object');
                if (serialized_data) {
                    let serialized_obj = decodeURIComponent(escape(atob(serialized_data)));
                    let obj = JSON.parse(serialized_obj);
                    let pk = row.attr("data-pk");
                    djlst_fill_form(form, obj, pk);
                }
            }
        }
    }
}

function djlst_unique_row_select(e) {
    let row = $(this).closest('.row-container');
    if (row.hasClass('selected')) {
        djlst_multiple_row_do_unselect(row);
    } else {
        row.siblings().removeClass('selected').find('input.row-select').removeAttr('name');
        djlst_multiple_row_do_select(row);
    }
    djlst_selection_changed_hook($(this));
}

function djlst_select_all(e) {
    let listing_id = $(this).attr('listing-target');
    let listing = $('#' + listing_id);
    listing.find('.row-container.row-selector').addClass('selected');
    listing.find('input.selection-box').prop('checked', true);
    listing.find('input.row-select').each(function () {
        let hidden = $(this);
        hidden.attr('name', hidden.attr('select-name'));
    });
    djlst_selection_changed_hook(listing);
}

function djlst_unselect_all(e) {
    let listing_id = $(this).attr('listing-target');
    let listing = $('#' + listing_id);
    djlst_listing_unselect_all(listing);
}

function djlst_listing_unselect_all(listing) {
    listing.find('.row-container.row-selector').removeClass('selected');
    listing.find('input.selection-box').prop('checked', false);
    listing.find('input.row-select').each(function () {
        $(this).removeAttr('name');
    });
    djlst_selection_changed_hook(listing);
}

function djlst_invert_selection(e) {
    let listing_id = $(this).attr('listing-target');
    let listing = $('#' + listing_id);
    listing.find('.row-container.row-selector').toggleClass('selected');
    listing.find('input.selection-box').prop('checked', true);
    listing.find('input.row-select').each(function () {
        let hidden = $(this);
        if (hidden.attr("name") !== undefined) {
            hidden.removeAttr('name');
        } else {
            hidden.attr('name', hidden.attr('select-name'));
        }
    });
    djlst_selection_changed_hook(listing);
}

function djlst_unselectText() {
    if (window.getSelection) {
        let selection = window.getSelection();
        selection.removeAllRanges();
    } else if (document.selection) {
        // For older IE browsers
        document.selection.empty();
    }
}

function djlst_activate_selection(e) {
    var listing = $(this).closest("div.django-listing-selecting");
    listing.find(".selection-overlay.hover")
        .removeClass('hover').addClass('had-hover');
    var selection_menu_id = listing.attr('selection-menu-id');
    var selection_menu = $('#' + selection_menu_id);
    selection_menu.attr('listing-id', listing.attr('id'));
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
    djlst_selection_changed_hook($(this));
}

function djlst_deactivate_selection(e) {
    var selection_menu = $(this).closest('.listing-selection-menu');
    var listing_id = selection_menu.attr('listing-id');
    var listing = $('#' + listing_id);
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

function djlst_selection_changed_hook(e) {
    let listing = e.closest("div.django-listing-selecting");
    let count = listing.find('.row-container.selected').length;
    if (count === 0) {
        $(".disabled-if-no-selection").addClass("disabled");
    } else {
        $(".disabled-if-no-selection:not(.no-perm)").removeClass("disabled");
    }
    let selection_menu_id = listing.attr('selection-menu-id');
    if (selection_menu_id) {
        let selection_menu = $('#' + selection_menu_id);
        let selected_items = selection_menu.find('span.selected_items')
        if (count == 0) {
            selected_items.text(selected_items.attr('none'));
        } else if (count == 1) {
            selected_items.text(selected_items.attr('one'));
        } else {
            selected_items.text(selected_items.attr('many').replace('{nb}', count));
        }
    }
    $(document).trigger("djlst_selection_changed", {listing: listing, count: count});
}

function djlst_fill_form(form, obj, pk) {
    let element = form.find('input[name="object_pk"]');
    element.val(pk);
    form.find("input, select, textarea").each(function () {
        let element = $(this);
        let name = element.attr("name");
        let value;
        if (obj.formfields !== undefined && name in obj.formfields) {
            value = obj.formfields[name];
        } else if (obj.fields !== undefined && name in obj.fields) {
            value = obj.fields[name];
        } else {
            if (this.type !== "hidden" && (
                    obj.data === undefined
                    || obj.data.no_autofill === undefined
                    || !obj.data.no_autofill.includes(name)
            )) {
                value = "";
            } else {
                return true;
            }
        }
        if (element.is(":input")) {
            if (element.is("input[type='radio']")) {
                element.filter("[value='" + value + "']").prop("checked", true);
            } else if (element.is("input[type='checkbox']")) {
                element.prop("checked", value);
            } else if (element.is("select")) {
                let label = value;
                if (Array.isArray(value)) {
                    label = value[1];
                    value = value[0];  // this last !!
                }
                if (typeof value === 'boolean') value = (value) ? "True" : "False";
                if (!value) value = "";
                let option = element.find("option[value='" + value + "']");
                if (option.length === 0) {
                    // If option doesn't exist, create it and remove others
                    if (element.hasClass("select2-hidden-accessible")) {
                        element.empty();
                    }
                    element.append($("<option>", {
                        value: value,
                        text: label
                    }));
                }
                element.val(value);
                if (element.hasClass("select2-hidden-accessible")) {
                    element.trigger('change');
                }
            } else {
                element.val(value);
            }
        }

    });
    $(document).trigger("djlst_form_filled", {form: form});
}

function djlst_clean_form(form) {
    form.find("input[type='text'],input[type='number'],textarea").val("");
    form.find("input[type='date'],input[type='time']").val("");
    form.find("input[type='datetime-local']").val("");
    form.find("select").each(function (index) {
        let option = $(this).find("option[value='']");
        if (option.length === 0) {
            $(this).append($("<option>", {value: "", text: no_choice_msg}));
        }
        $(this).val("");
    });
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
        listing_id: listing_id,
        listing_suffix: listing_suffix,
        action_button: 'view_object_popup',
        serialized_data: nav_obj.closest('form').serialize()
    };
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        success: function (response) {
            listing_div.removeClass("spinning");
            $("#listing-popup-container").html(response);
            $("#listing-popup-container > div.modal").modal("show");
        }
    });
}

function djlst_listing_on_load() {
    $(".group-by-container").each(function () {
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

function djlst_follow_file_generation() {
    var status = Cookies.get('file_generation');
    if (status !== 'done') {
        setTimeout(djlst_follow_file_generation, 300);
    } else {
        Cookies.remove('file_generation');
        $('.spinning').removeClass('spinning').addClass('done');
    }
}

$(document).ready(function () {

    var select2_opened = false;

    $('form.listing-form').submit(function () {
        $(this).find('input[name]').filter(function () {
            return !this.value;
        }).prop('name', '');
    });

    $(document.body).on("click", "div.django-listing-ajax button.listing-nav", djlst_post_action_button);
    $(document.body).on("click", "div.django-listing-ajax a.listing-nav", djlst_load_listing_href);
    $(document.body).on("change", "div.django-listing-ajax select.listing-nav", djlst_load_listing_val);
    $(document.body).on("click", "div.django-listing-selecting.selection_multiple .row-selector", djlst_multiple_row_select);
    $(document.body).on("click", "div.django-listing-selecting.selection_unique .row-selector", djlst_unique_row_select);
    $(document.body).on("click", "div.django-listing-selecting .selection-overlay.hover", djlst_activate_selection);
    $(document.body).on("click", "[listing-action='select-all']", djlst_select_all);
    $(document.body).on("click", "[listing-action='unselect-all']", djlst_unselect_all);
    $(document.body).on("click", "[listing-action='invert-selection']", djlst_invert_selection);
    $(document.body).on("click", ".listing-selection-menu .listing-menu-close", djlst_deactivate_selection);
    $(document.body).on("click", "li.action-item.view-object-popup a", djlst_view_object_popup);
    $(document.body).on("click", ".button-action-group-by", function () {
        $(this).closest(".django-listing-container").find(".group-by-container").slideToggle(200);
    });
    $(document.body).on("click", "form.django-listing-ajax.attached-form button[name='action_button']", djlst_post_attached_form);
    $(document.body).on("click", ".btn.gb-filter", function () {
        $(this).addClass("visited")
    });

    $(".django-listing-container").each(function () {
        djlst_selection_changed_hook($(this));
    });

    $('[data-toggle="popover"]').popover();

    var dropzoneCounter = 0;

    $('.dropzone').on('dragenter', function () {
        dropzoneCounter++;
        $(this).addClass('drag-over');
    });

    $('.dropzone').bind('dragleave', function () {
        dropzoneCounter--;
        if (dropzoneCounter === 0) {
            $(this).removeClass('drag-over');
        }
    });

    $('.dropzone').bind('drop', function () {
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

    $(document).on('select2:open', function (e) {
        let aria_owns = $(e.target).parent().find('.select2-selection').attr('aria-owns');
        document.querySelector('input[aria-controls="' + aria_owns + '"]').focus();
        select2_opened = true;
    });

    $("form").keyup(function (e) {
        if (e.keyCode == 9) {
            const target = $(e.target)
            if (target.hasClass("select2-selection")) {
                if (!select2_opened) {
                    target.closest(".select2").siblings("select").first().select2("open");
                }
                select2_opened = true;
            } else {
                select2_opened = false;
            }
        }
    });

    $(".file-generation-button").on('click', function() {
        let select = $(this).siblings("select");
        if (select.length && !select.val()) {
            let msg = $(this).data("empty-select-msg");
            if (!msg) msg = "Please select a value !"
            alert(msg);
            return false;
        }
        Cookies.set('file_generation', 'working', {expires: 1});
        let listing_div = $(this).closest("div.django-listing-ajax");
        listing_div.addClass("spinning").removeClass('done');
        djlst_follow_file_generation();
    });

    djlst_listing_on_load();
});
