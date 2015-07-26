function update_on_icon(id,result)
{
    console.log($(id));
    if (result.args[0] == true) {
        $(id).html('<i class="fa fa-power-off"></i>');
        $(id).removeClass("label-default");
        $(id).addClass("label-success");
    } else {
        $(id).html('<i class="fa fa-circle-o"></i>');
        $(id).removeClass("label-default");
        $(id).addClass("label-default");
    }
}

function update_connect_icon(id,result)
{
    console.log($(id));
    if (result.args[0] == true) {
        $(id).html('<i class="fa fa-check"></i>');
        $(id).removeClass("label-default");
        $(id).addClass("label-success");
    } else {
        $(id).html('<i class="fa fa-square"></i>');
        $(id).removeClass("label-default");
        $(id).addClass("label-default");
    }
}

function do_post(command) {
    $.post('ctrl/' + command, function(data,status,xhr) {
        console.log(status);
    });
}

$(document).ready(function() {

    $(document).ajaxError(function(event,xhr,option,exc) {
        $("#error").addClass("show");
        $("#error-text").append(" <code>" + option.url.replace('ctrl/','') + "</code>")
        $("#error-close").click(function() {
            $("#error").removeClass("show");
            $("#error-text").html('');
        });
    });

    $.post("ctrl/avr/ison", '', function(result) {
        update_on_icon(".avr-on-icon",result);
    });
    $.post("ctrl/hw50/ison", '', function(result) {
        update_on_icon(".hw50-on-icon",result);
    });
    $.post("ctrl/oppo/ison", '', function(result) {
        update_on_icon(".oppo-on-icon",result);
    });
    $.post("ctrl/td/ison", '', function(result) {
        update_connect_icon(".td-on-icon",result);
    });

    $(".lu-light-on").click(function() {
        do_post('light/on');
    });
    $(".lu-light-off").click(function() {
        do_post('light/off');
    });
    $(".lu-elec-on").click(function() {
        do_post('elec/on');
    });
    $(".lu-elec-off").click(function() {
        do_post('elec/off');
    });
});
