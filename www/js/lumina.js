function update_on_icon(id,result)
{
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

function do_cmd(command)      { $.post('ctrl/' + command, ''); }
function do_cmdfn(command,fn) { $.post('ctrl/' + command, '', fn); }

function poll_avr_volume() {
    do_cmdfn("avr/volume", function(data) { $(".lu-avr-volume").html(data.args[0] + ' dB'); });
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

    $.post("ctrl/avr/ison", '', function(result)  { update_on_icon(".lu-avr-on-icon",result); });
    $.post("ctrl/hw50/ison", '', function(result) { update_on_icon(".lu-hw50-on-icon",result); });
    $.post("ctrl/oppo/ison", '', function(result) { update_on_icon(".lu-oppo-on-icon",result); });

    $.post("ctrl/td/ison", '', function(result)   { update_connect_icon(".lu-td-on-icon",result); });

    do_cmdfn("avr/volume", function(data) { $(".lu-avr-volume").html(data.args[0] + ' dB'); });
    do_cmdfn("avr/input", function(data)  { $(".lu-avr-input").html(data.args[0]); });

    $(".lu-light-off").click(function()    { do_cmd('light/off'); });
    $(".lu-light-weak").click(function()   { do_cmd('light/weak'); });
    $(".lu-light-normal").click(function() { do_cmd('light/normal'); });
    $(".lu-light-full").click(function()   { do_cmd('light/full'); });

    $(".lu-elec-on").click(function()      { do_cmd('elec/on'); });
    $(".lu-elec-off").click(function()     { do_cmd('elec/off'); });

    $(".lu-avr-on").click(function()       { do_cmd('avr/on'); });
    $(".lu-avr-off").click(function()      { do_cmd('avr/off'); });
    $(".lu-avr-volume-up").click(function()   { do_cmd('avr/volume/up'); poll_avr_volume(); });
    $(".lu-avr-volume-down").click(function() { do_cmd('avr/volume/down'); poll_avr_volume(); });

    $("#lu-command").submit(function(event) {
        do_cmdfn($("#lu-command-input").val(),function(data) { $("#lu-command-output").html(JSON.stringify(data)); });
        event.preventDefault();
    });

});
