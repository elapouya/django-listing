function djlst_format_number(val) {
    const text = String(val);
    const formattedText = text.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return formattedText;
}

const djlst_sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

$.fn.djlst_format_digits = function() {
  return this.each(function() {
    // Save the original HTML content
    var $this = $(this);

    // Use a replacement function with a regex
    // that only targets sequences of digits in visible text
    var html = $this.html();

    // Function that will be applied to text nodes only
    var formatTextNode = function(node) {
      if (node.nodeType === 3) { // Type 3 = text node
        // Replace only sequences of digits
        var text = node.nodeValue;
        var formattedText = text.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1\u00A0');
        if (text !== formattedText) {
          node.nodeValue = formattedText;
        }
      } else if (node.nodeType === 1) { // Type 1 = element
        // Recursively process children
        for (var i = 0; i < node.childNodes.length; i++) {
          formatTextNode(node.childNodes[i]);
        }
      }
    };

    // Apply formatting to all text nodes of the element
    for (var i = 0; i < this.childNodes.length; i++) {
      formatTextNode(this.childNodes[i]);
    }
  });
};

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

function djlst_removeUrlParam(url, params) {
    if (!url.startsWith('/') || !params || !params.length) {
        return url;
    }
    const [basePath, queryString] = url.split('?');
    if (!queryString) {
        return url;
    }
    const searchParams = new URLSearchParams(queryString);
    params.forEach(param => searchParams.delete(param));
    const newQueryString = searchParams.toString();
    return newQueryString ? `${basePath}?${newQueryString}` : basePath;
}

function update_csrf_token() {
    $.ajaxSetup({
        data: {'csrfmiddlewaretoken': Cookies.get('csrftoken')}
    });
}

function djlst_get_form_data_advanced(form) {
    const formData = new FormData(form);
    let form_data = {};

    // Group values by key name
    for (const [key, value] of formData.entries()) {
        if (!form_data[key]) {
            // First occurrence of this key
            form_data[key] = formData.getAll(key).length > 1 ? formData.getAll(key) : value;
        }
        // If there's only one value, it's stored directly
        // If there are multiple values, we store them as an array
    }

    return form_data;
}

function djlst_add_filter_request_data($listing_div, $nav_obj, data) {
    // if filter form available and post method is used :
    // merge form data inside ajax payload
    let listing_id = $listing_div.attr('id');
    const filter_form = $(`form[listing-id=${listing_id}]`);
    if (filter_form.length) {
        const method = filter_form.attr("method");
        if (method !== undefined && method.toLowerCase() == "post") {
            let form_data = djlst_get_form_data_advanced(filter_form[0]);
            data = { ...data, ...form_data };
        }
    }
    if ($nav_obj.closest(".toolbar_item.variationstoolbaritem").length == 0) {
        const gb_cols = $listing_div.find(".group-by-select");
        if (gb_cols.length) data.gb_cols = gb_cols.val().join(",");
        const gb_annotate_cols = $listing_div.find(".annotation-select");
        if (gb_annotate_cols.length) data.gb_annotate_cols = gb_annotate_cols.val().join(",");
    }
    return data
}

function djlst_extract_params_from_url(url, keysToRemove) {
    const queryString = url.split('?')[1] || '';
    const params = new URLSearchParams(queryString);
    const extracted_params = {};
    const keys = Array.isArray(keysToRemove) ? keysToRemove : [keysToRemove];

    keys.forEach(key => {
        if (params.has(key)) {
            extracted_params[key] = params.get(key);
            params.delete(key);
        }
    });

    return extracted_params;
}

function djlst_load_listing_url(nav_obj, url, additional_data) {
    if (url === null) {
        url = djlst_get_requested_url(nav_obj);
    }
    // fixes variation selection
    const extracted_params = djlst_extract_params_from_url(url, ["variation"]);
    if (Object.keys(extracted_params).length > 0) {
        if (additional_data) {
            additional_data = {...additional_data, ...extracted_params};
        } else {
            additional_data = extracted_params;
        }
    }
    if (!$("div.django-listing-ajax").length) {
        window.location.href = url;
    }
    const listing_div = nav_obj.closest("div.django-listing-ajax");
    listing_div.addClass("spinning");
    const listing_id = $(listing_div).attr("id");
    const filter_form = $(`form[listing-id=${listing_id}]`);
    const listing_suffix = $(listing_div).attr("listing-suffix");
    let listing_target = nav_obj.attr("listing-target");
    if (!listing_target) listing_target = "#" + listing_id;
    let listing_part = nav_obj.attr("listing-part");
    if (!listing_part) listing_part = "all";
    let request_data = {
        "listing_id": listing_id,
        "listing_suffix": listing_suffix,
        "listing_part": listing_part,
    }
    request_data = djlst_add_filter_request_data(listing_div, nav_obj, request_data);
    if (additional_data) {
        request_data = { ...request_data, ...additional_data };
    }
    $(document).trigger("djlst_before_load_listing_url",
        {listing: listing_target, url: url, payload:request_data}
    );
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: url,
        data: request_data,
        traditional: true,
        success: function (mixed_response) {
            if (mixed_response.filters_form) {
                filter_form.replaceWith(mixed_response.filters_form);
                listing_div.removeClass("spinning");
            }
            if (mixed_response.listing) {
                listing_div.replaceWith(mixed_response.listing);
                djlst_listing_on_load();
                $(document).trigger("djlst_ajax_loaded", {listing_target: listing_target, response: mixed_response.listing});
            }
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        },
    });
    $(document).trigger("djlst_after_load_listing_url");
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
    const nav_obj = $(this);
    const listing_div = nav_obj.closest("div.django-listing-ajax");
    const ajax_url = listing_div.attr("ajax_url");
    listing_div.addClass("spinning");
    const listing_id = listing_div.attr("id");
    const filter_form = $(`form[listing-id=${listing_id}]`);
    const listing_suffix = listing_div.attr("listing-suffix");
    let listing_target = nav_obj.attr("listing-target");
    if (!listing_target) listing_target = "#" + listing_id;
    let listing_part = nav_obj.attr("listing-part");
    if (!listing_part) listing_part = "all";
    let request_data = {
        listing_id: listing_id,
        listing_suffix: listing_suffix,
        listing_part: listing_part,
        serialized_data: nav_obj.closest('form').serialize()
    };
    request_data[$(this).attr('name')] = $(this).val();
    request_data = djlst_add_filter_request_data(listing_div, nav_obj, request_data);
    update_csrf_token();
    $(document).trigger("djlst_before_post_action_button",
        {listing: listing_target, payload:request_data}
    );
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        traditional: true,
        success: function (mixed_response) {
            if (mixed_response.filters_form) {
                filter_form.replaceWith(mixed_response.filters_form);
                listing_div.removeClass("spinning");
            }
            if (mixed_response.listing) {
                listing_div.replaceWith(mixed_response.listing);
                djlst_listing_on_load();
                $(document).trigger("djlst_ajax_loaded", {listing_target: listing_target, response: mixed_response.listing});
            }
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        }
    });
    $(document).trigger("djlst_after_post_action_button",
        {listing: listing_target, payload:request_data}
    );
}

var djlst_mass_op_cbs_displayed = false;

function djlst_show_mass_op_cbs(form) {
    djlst_mass_op_cbs_displayed = false;
    form.find(".mass-op-cb").prop('checked', false).show();
    form.addClass("mass-op-cbs-displayed");
    setTimeout(function () {djlst_mass_op_cbs_displayed = true;}, 100);
}

function djlst_hide_mass_op_cbs(form) {
    form.find(".mass-op-cb").hide();
    form.removeClass("mass-op-cbs-displayed");
    if (djlst_mass_op_cbs_displayed) {
        form.find(".form-buttons button.clear")[0].click();
    }
    djlst_mass_op_cbs_displayed = false;
}

async function djlst_post_attached_form(event) {
    event.preventDefault();
    const nav_obj = $(this);
    const form_fields = nav_obj.closest('form').find('.form-fields');
    const action_button = nav_obj.val();
    const attached_form = nav_obj.closest("form.listing-form");
    const attached_form_container = attached_form.closest(".attached-form-container");
    let attached_form_id = attached_form.attr("id");
    let listing_div = $("#" + attached_form.attr("related-listing"));
    let selected_rows = listing_div.find(".row-container.selected");
    if (!nav_obj.hasClass("flip") && attached_form_container.hasClass("flipped")) {
        form_fields.addClass('flip-out');
        if (attached_form.hasClass("animate")) await djlst_sleep(300);
    }
    if (action_button == "update_all") {
        listing_div.find('.row-container').addClass('selected');
    }
    if (action_button == "update_all" || (action_button == "update" && selected_rows.length > 1)) {
        const visibleCheckboxCount = attached_form.find('input.mass-op-cb:visible').length;
        if (visibleCheckboxCount == 0) {
                djlst_show_mass_op_cbs(attached_form);
                djlst_clear_form(attached_form);
        }
        const checkedCheckboxCount = attached_form.find('input.mass-op-cb:checked').length;
        if (checkedCheckboxCount == 0 || visibleCheckboxCount == 0) {
            setTimeout(function() { alert(use_mass_cb_msg);}, 50);
            return;
        }
    }
    if (action_button == "clear") {
        djlst_listing_unselect_all(listing_div);
    }
    let confirm_msg = nav_obj.attr("confirm-msg");
    if (confirm_msg) {
        let confirm_msg_nb_items = nav_obj.attr("confirm-msg-nb-items");
        confirm_msg_nb_items = parseInt(confirm_msg_nb_items);
        if (isNaN(confirm_msg_nb_items)) confirm_msg_nb_items = 0;
        confirm_msg = confirm_msg.replace("{nb_items}", selected_rows.length);
        let nb_all_items = listing_div.attr("nb-rows");
        if (!nb_all_items) nb_all_items = "";
        confirm_msg = confirm_msg.replace("{nb_all_items}", nb_all_items);
        if (selected_rows.length >= confirm_msg_nb_items) {
            if (!confirm(confirm_msg)) return;
        }
    }
    if (nav_obj.hasClass("flip")) {
        form_fields.addClass('flip-out');
        attached_form_container.addClass('flipped');
        if (attached_form.hasClass("animate")) await djlst_sleep(300);
    }
    let selected_pks = selected_rows.map(function () {
        return $(this).attr("data-pk")
    }).get().join(',');
    let ajax_url = listing_div.attr("ajax_url");
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
    request_data = djlst_add_filter_request_data(listing_div, nav_obj, request_data);
    $(document).trigger("djlst_before_attached_form_post",
        {listing: listing_target, form: attached_form, payload:request_data, nav_obj:nav_obj}
    );

    update_csrf_token();
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        traditional: true,
        success: function (mixed_response) {
            let new_attached_form;
            if (mixed_response.listing) {
                listing_div.replaceWith(mixed_response.listing)
                // very important : reload listing_div from the DOM
                listing_div = $("#" + listing_id);
                djlst_listing_on_load();
            }
            if (mixed_response.attached_form) {
                attached_form.replaceWith(mixed_response.attached_form);
                djlst_selection_changed_hook(listing_div);
                if (attached_form_container.hasClass("flipped")) {
                    // very important : reload attached form from the DOM
                    new_attached_form = $("#" + attached_form_id);
                    new_attached_form.find(".mass-op-cb").hide();
                    new_attached_form.removeClass("mass-op-cbs-displayed");
                    djlst_mass_op_cbs_displayed = false;
                }
            }
            if (mixed_response.object_pk) {
                new_attached_form = $("#" + attached_form_id);
                let object_pk_input = new_attached_form.find('input[name="object_pk"]');
                object_pk_input.val(mixed_response.object_pk);
            }
            $(document).trigger(
                "djlst_ajax_attached_form_loaded",
                {listing: listing_target, form: new_attached_form, response:mixed_response}
            );
            if ((!nav_obj.hasClass("flip") || mixed_response.layout_name === "") && attached_form_container.hasClass("flipped")) {
                setTimeout(() => {
                    attached_form_container.removeClass('flipped');
                    form_fields.removeClass('flip-out');
                }, 300);
            }
        },
        error: function (response) {
            text = "An error occured.\n\nIndications :\n\n" + response.responseText;
            alert(text);
        }
    });
    $(document).trigger("djlst_after_attached_form_post",
        {listing: listing_target, form: attached_form, payload:request_data, nav_obj:nav_obj}
    );

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
    let listing_div = row.closest('.django-listing-container');
    let form = $("#" + listing_div.attr('attached-form-id'));
    let hidden = row.find('input.row-select').first();
    row.removeClass('selected');
    hidden.removeAttr('name');
    row.find('input.selection-box').first().prop('checked', false);
    let nb_selected = row.siblings(".selected").length;
    if (nb_selected == 1) {
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
        // Remove form validation errors if any
        form.find(".form-field.errors > span").remove();
        form.find(".form-field.errors > ul.errorlist").remove();
        form.find("ul.errorlist.nonfield").remove();
        form.find(".form-field.errors").removeClass("errors");

        if (listing_div.hasClass("attached_form_autofill")) {
            let nb_selected = row.siblings(".selected").length;
            if (nb_selected == 0) {
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
    listing.find('.row-container').addClass('selected');
    // not working in showcase with div rows : listing.find('.row-container.row-selector').addClass('selected');
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
    listing.find('.row-container').removeClass('selected');
    // not working in showcase with div rows : listing.find('.row-container.row-selector').removeClass('selected');
    listing.find('input.selection-box').prop('checked', false);
    listing.find('input.row-select').each(function () {
        $(this).removeAttr('name');
    });
    djlst_selection_changed_hook(listing);
}

function djlst_invert_selection(e) {
    let listing_id = $(this).attr('listing-target');
    let listing = $('#' + listing_id);
    listing.find('.row-container').toggleClass('selected');
    // not working in showcase with div rows : listing.find('.row-container.row-selector').toggleClass('selected');
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

function djlst_get_requested_url($nav_obj) {
    const $listing_div = $nav_obj.closest("div.django-listing-container")
    const $requested_url_hidden = $listing_div.find("input[name='requested_url']");
    if ($requested_url_hidden.length) {
        return $requested_url_hidden.val();
    } else {
        return window.location.href;
    }
}

function djlst_reload_listing_from_form(elt, additional_data) {
    if (elt) {
        const source_elt_data = {
            src_elt_name: elt.name,
            src_elt_value: elt.value,
            src_elt_class: elt.className
        }
        if (additional_data) {
            additional_data = {...additional_data, ...source_elt_data};
        } else {
            additional_data = source_elt_data;
        }
    }
    var form = $(elt).closest('.listing-form');
    var listing_id = form.attr('listing-id');
    var listing = $('#' + listing_id);
    const url = djlst_get_requested_url(listing);
    djlst_load_listing_url(listing, url, additional_data);
}

function djlst_update_attached_form_buttons($listing, $attached_form) {
    const all_count = $listing.attr("nb-rows");
    if (all_count === "0") {
        $attached_form.find("button.all-count").addClass("disabled");
    } else {
        $attached_form.find("button.all-count:not(.no-perm)").removeClass("disabled");
    }
    let form = $("#" + $listing.attr('attached-form-id'));
    let count = $listing.find('.row-container.selected').length;
    if (count === 0) {
        $(".selected-count,.disabled-if-no-selection").addClass("disabled");
        $attached_form.find("button.hide-if-no-selection").hide();
        $attached_form.find("button.hide-if-selection").show();
    } else {
        $(".selected-count:not(.no-perm),.disabled-if-no-selection:not(.no-perm)").removeClass("disabled");
        $attached_form.find("button.hide-if-no-selection").show();
        $attached_form.find("button.hide-if-selection").hide();
    }
    if (count > 1) {
        djlst_clear_form(form);
        djlst_show_mass_op_cbs(form);
    } else {
        djlst_hide_mass_op_cbs(form);
    }
    let selection_menu_id = $listing.attr('selection-menu-id');
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

    const selected_pill = `<span class="badge rounded-pill text-bg-dark">${count}</span>`
    const all_pill = `<span class="badge rounded-pill text-bg-dark">${all_count}</span>`
    $attached_form.find("button.selected-count span.button-extra-middle").html(selected_pill);
    $attached_form.find("button.all-count span.button-extra-middle").html(all_pill);

    return {selected_count: count, all_count: all_count}
}

function djlst_selection_changed_hook(e) {
    const $listing = e.closest("div.django-listing-selecting");
    const $attached_form = $('body form[related-listing="' + $listing.attr("id") + '"]');
    const data = djlst_update_attached_form_buttons($listing, $attached_form);

    $(document).trigger("djlst_selection_changed", {
        listing: $listing,
        selected_count: data.selected,
        all_count: data.all
    });
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
                // If 2-dimension array : this is a multi-select
                if (Array.isArray(value) && value.every(Array.isArray)) {
                    element.empty();
                    for (const [pk, label] of value) {
                        element.append($("<option>", {
                            value: pk,
                            text: label,
                            selected: true
                        }));
                    }
                    element.trigger('change');
                } else {
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
                            text: label,
                        }));
                    }
                    element.val(value);
                    if (element.hasClass("select2-hidden-accessible")) {
                        element.trigger('change');
                    }
                }
            } else {
                element.val(value);
            }
        }

    });
    $(document).trigger("djlst_form_filled", {form: form});
}

function djlst_clear_form(form) {
    form.find("input[type='text']:not(.mass-op-no-clear),input[type='number']:not(.mass-op-no-clear),textarea:not(.mass-op-no-clear)").attr("disabled", false).val("");
    form.find("input[type='date']:not(.mass-op-no-clear),input[type='time']:not(.mass-op-no-clear)").attr("disabled", false).val("");
    form.find("input[type='datetime-local']:not(.mass-op-no-clear)").attr("disabled", false).val("");
    form.find("input:checkbox").attr("disabled", false).prop('checked', false);
    form.find("select:not(.mass-op-no-clear)").each(function (index) {
        let option = $(this).find("option[value='']");
        if (option.length === 0) {
            $(this).append($("<option>", {value: "", text: no_choice_msg}));
        }
        $(this).attr("disabled", false).val("").trigger('change');
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
    request_data = djlst_add_filter_request_data(listing_div, nav_obj, request_data);
    update_csrf_token();
    $.ajax({
        type: "POST",
        url: ajax_url,
        data: request_data,
        traditional: true,
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
    });
    $(".django-listing-container.format-numbers .type-Decimal,.django-listing-container.format-numbers .type-int,.django-listing-container.format-numbers .type-float,.django-listing-container.format-numbers .format-number").djlst_format_digits();

    $(".django-listing-container").each(function () {
        const $listing = $(this);
        const $attached_form = $('body form[related-listing="' + this.id + '"]');
        djlst_update_attached_form_buttons($listing, $attached_form);
    });
}

function djlst_attached_form_input_changed(event) {
    if (djlst_mass_op_cbs_displayed) {
        $(this).closest(".form-field").find(".mass-op-cb:visible").prop('checked', true);
    }
}

function djlst_reset_form_fields($form) {
    $form.find('input[type="text"], \
               input[type="password"], \
               input[type="date"], \
               input[type="email"], \
               input[type="number"], \
               input[type="tel"], \
               input[type="url"], \
               input[type="search"], \
               textarea').val('');

    // Clear checkboxes and radio buttons
    $form.find('input[type="checkbox"], \
               input[type="radio"]').prop('checked', false);

    // Clear select fields
    $form.find('select').prop('selectedIndex', -1);

    // Clear file inputs
    $form.find('input[type="file"]').val('');

    // Clear select2 fields
    $form.find('select').each(function () {
        if ($(this).hasClass('select2-hidden-accessible')) {
            $(this).val(null).trigger('change');
        }
    });
}

function djlst_empty_form_fields($form) {
    // Empty regular text inputs, textareas, and password fields
    $form.find('input[type="text"], input[type="pasword"], input[type="date"], input[type="number"], textarea').val('');

    // Empty regular select elements
    $form.find('select').not('.select2-hidden-accessible').val('');

    // Empty Select2 elements
    $form.find('select.select2-hidden-accessible').each(function() {
        $(this).val(null).trigger('change');
    });

    // Handle radio buttons - uncheck all except those with no value
    $form.find('input[type="radio"]').each(function() {
        if ($(this).val()) {
            $(this).prop('checked', false);
        } else {
            $(this).prop('checked', true);
        }
    });

    // Empty checkboxes
    $form.find('input[type="checkbox"]').prop('checked', false);

    // Empty file inputs
    $form.find('input[type="file"]').val('');
}

function djlst_patch_form_data($form, extraData) {
    $form.on('submit', function(event) {
        // Add extra data to the existing form
        for (const [name, value] of Object.entries(extraData)) {
            // Check if field already exists
            const existingField = $form.find(`input[name="${name}"]`);

            if (existingField.length) {
                // Update existing field value
                existingField.val(value);
            } else {
                // Create new field only if it doesn't exist
                const $input = $('<input>', {
                    type: 'hidden',
                    name: name,
                    value: value
                });
                $form.append($input);
            }
        }
    });
}

$(document).ready(function () {
    $(document.body).on("click", ".filters-form .advanced-button", function () {
        const form = $(this).closest(".filters-form");
        form.find(".filters-layout-advanced").slideToggle();
        $(this).find(".button-icon.up").toggle();
        $(this).find(".button-icon.down").toggle();
    });

    var select2_opened = false;

    $('form.listing-form').submit(function () {
        $(this).find('input[name]').filter(function () {
            return !this.value;
        }).prop('name', '');
    });

    $(document.body).on("click", "div.django-listing-ajax button.listing-nav", djlst_post_action_button);
    $(document.body).on("click", "div.django-listing-ajax a.listing-nav", djlst_load_listing_href);
    $(document.body).on("change", "div.django-listing-ajax select.listing-nav", djlst_load_listing_val);
    if ($("div.django-listing-selecting td.col-selection_checkbox").length) {
        $(document.body).on("click", "div.django-listing-selecting.selection_multiple .row-selector td.col-selection_checkbox", djlst_multiple_row_select);
        $(document.body).on("click", "div.django-listing-selecting.selection_unique .row-selector td.col-selection_checkbox", djlst_unique_row_select);
    } else {
        $(document.body).on("click", "div.django-listing-selecting.selection_multiple .row-selector", djlst_multiple_row_select);
        $(document.body).on("click", "div.django-listing-selecting.selection_unique .row-selector", djlst_unique_row_select);
    }
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
    $(document.body).on("change", ".attached-form-container input:not(.mass-op-cb)", djlst_attached_form_input_changed);
    $(document.body).on("change", ".attached-form-container select,.attached-form-container textarea", djlst_attached_form_input_changed);
    $(document.body).on("click", ".listing-form.filters-form-ajax .submit-button", function () {djlst_reload_listing_from_form(this); return false;});
    $(document.body).on("click", ".listing-form.filters-form-ajax button.reset-button", function (e) {
        // filter form reset button must reload without f_* params in querystring
        e.preventDefault();
        let url = new URL(window.location.href);
        url.searchParams.forEach(function(value, key) {
            if (key.startsWith("f_")) {
                url.searchParams.delete(key);
            }
        });
        window.location.href = url.toString();
    });

    $(".django-listing-container").each(function () {
        djlst_selection_changed_hook($(this));
    });
    $(document.body).on("click", ".apply-group-by", function () {djlst_load_listing_url($(this), null);});
    $(document.body).on("click", ".remove-group-by", function () {
        $(this).closest("div.django-listing-ajax").find(".group-by-container select").val("");
        let url = djlst_get_requested_url($(this));
        url = djlst_removeUrlParam(url, ["sort", "page", "per_page"]);
        djlst_load_listing_url($(this), url);
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

    $(document.body).on("click", ".submit-action-form", function () {
        var action = $(this).val();
        var form = $(this).closest('.django-listing-container').find('.action-form');
        var hidden = form.find('.action-hidden-value');
        hidden.val(action);
        form.submit();
    });

    $(document).on('select2:open', function (e) {
        let aria_owns = $(e.target).parent().find('.select2-selection').attr('aria-owns');
        let input = document.querySelector('input[aria-controls="' + aria_owns + '"]');
        if (input) {  // may be null for multi-select widget
            document.querySelector('input[aria-controls="' + aria_owns + '"]').focus();
            select2_opened = true;
        }
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

   $('form.attached-form input[type="text"], form.attached-form input[type="number"]').on('keypress', function(e) {
        // Check if the pressed key is Enter (keyCode 13) and not textarea
        // otherwise, the first button found will be pressed !!!
        if (e.which === 13) {
            // Prevent the default action (form submission)
            e.preventDefault();
            // If the value has changed, manually trigger the change event
            $(this).blur().focus();
            return false;
        }
    });

    $(document.body).on("click", ".file-generation-button", function() {
        const nav_obj = $(this);
        let select = $(this).siblings("select");
        if (select.length && !select.val()) {
            let msg = $(this).data("empty-select-msg");
            if (!msg) msg = "Please select a value !"
            alert(msg);
            return false;
        }
        const $form = $(this).closest("form");
        const $listing_div = $form.closest(".django-listing-container");
        const filter_data = djlst_add_filter_request_data($listing_div, nav_obj, {});
        const url_str = djlst_get_requested_url(nav_obj)
        const qs = url_str.split('?')[1];
        const params = new URLSearchParams(qs);
        const sort_value = params.get('sort');
        if (sort_value) filter_data["sort"] = sort_value;
        // Get form payload for event
        const formDataArray = $form.serializeArray();
        let payload = {};
        $.each(formDataArray, function(i, field) {
            payload[field.name] = field.value;
        });
        $(document).trigger("djlst_before_file_generation",
            {listing: $listing_div, filter_data:filter_data, payload:payload}
        );
        djlst_patch_form_data($form, filter_data);
        Cookies.set('file_generation', 'working', {expires: 1});
        let listing_div = $(this).closest("div.django-listing-ajax");
        listing_div.addClass("spinning").removeClass('done');

        function follow_file_generation() {
            const status = Cookies.get('file_generation');
            if (status !== 'done') {
                setTimeout(follow_file_generation, 300);
            } else {
                Cookies.remove('file_generation');
                $('.spinning').removeClass('spinning').addClass('done');
                $(document).trigger("djlst_after_file_generation",
                    {listing: $listing_div, filter_data:filter_data, payload:payload}
                );
            }
        }
        follow_file_generation();
    });

    // make attached form always visible on big listings
    if ($('.attached-form-container.sticky .attached-form').length) {
        $(window).on('scroll resize', () => updateAttachedFormsPosition(false));
        $(document).on("djlst_selection_changed djlst_form_filled", () => updateAttachedFormsPosition(true));
    }
    function updateAttachedFormsPosition(force_update) {
        const attached_form = document.querySelector('.attached-form-container.sticky .attached-form');
        if (attached_form) {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const windowHeight = document.documentElement.clientHeight;
            const rect = attached_form.getBoundingClientRect();
            const parentTop = attached_form.parentElement.offsetTop;
            // If attached form is too big to be sticky, use another strategy :
            // Stick it only on listing item selection (force_update = true)
            if (rect.height >= windowHeight && scrollTop > 0 && !force_update) return;
            let newMarginTop = Math.max(0, scrollTop - parentTop);
            attached_form.style.marginTop = newMarginTop + 'px';
            const attached_form_toggle = document.querySelector('.toggle-attached-form');
            if (attached_form_toggle) {
                attached_form_toggle.style.marginTop = newMarginTop + 'px';
            }
        }
    }

    djlst_listing_on_load();
});
