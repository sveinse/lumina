function update_on_icon(id,result)
{
    if (result.result == true) {
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
    if (result.result == true) {
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

function poll_avr_ison()    { do_cmdfn("avr/ison", function(data) { update_on_icon(".lu-avr-on-icon",data); }); }
function poll_avr_volume()  { do_cmdfn("avr/volume", function(data) { $(".lu-avr-volume").html(data.result + ' dB'); }); }
function poll_avr_input()   { do_cmdfn("avr/input", function(data) {
    var i=data.result;
    switch(i) {
    case 'AV1': i='KROM'; break;
    case 'AV3': i='HTPC'; break;
    case 'AV4': i='OPPO'; break;
    case 'AUDIO1': i='SONOS'; break;
    }
    $(".lu-avr-input").html(i); }); }

function poll_oppo_ison()   { do_cmdfn("oppo/ison", function(data) { update_on_icon(".lu-oppo-on-icon",data); }); }
function poll_oppo_status() { do_cmdfn("oppo/status", function(data) {
    var r='';
    var t=data.result[0];
    switch(t) {
    case 'PLAY': r='play'; break;
    case 'STOP': r='stop'; break;
    case 'PAUSE': r='pause'; break;
    case 'OPEN': r='eject'; break;
    case 'NO': r='ban'; break;
    default: r='circle-o';
    }
    $(".lu-oppo-status").html('<i class="fa fa-' + r + '"></i> ' + t ); })}
function poll_oppo_time() { do_cmdfn("oppo/time", function(data) { $(".lu-oppo-time").html(data.result[0]); }); }
function poll_oppo_audio() { do_cmdfn("oppo/audio", function(data) { $(".lu-oppo-audio").html(data.result.join(' ')); }); }

function poll_hw50_ison()   { do_cmdfn("hw50/ison", function(data) { update_on_icon(".lu-hw50-on-icon",data); }); }
function poll_hw50_hours()  { do_cmdfn("hw50/lamp_timer", function(data) { $(".lu-hw50-hours").html(data.result); }); }
function poll_hw50_preset() { do_cmdfn("hw50/preset", function(data) { $(".lu-hw50-preset").html(data.result); }); }

function update_avr() {
    poll_avr_ison();
    poll_avr_volume();
    poll_avr_input();
}
function update_oppo() {
    poll_oppo_ison();
    poll_oppo_status();
    poll_oppo_time();
    poll_oppo_audio();
}
function update_hw50() {
    poll_hw50_ison();
    poll_hw50_hours();
    poll_hw50_preset();
}
function update_all() {
    update_avr();
    update_oppo();
    update_hw50();
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

    //$.post("ctrl/td/ison", '', function(result)   { update_connect_icon(".lu-td-on-icon",result); });

    update_all();

    $("#h2-avr").click(update_avr);
    $("#h2-oppo").click(update_oppo);
    $("#h2-hw50").click(update_hw50);

    $(".lu-elec-on").click(function()      { do_cmd('elec/on'); });
    $(".lu-elec-off").click(function()     { do_cmd('elec/off'); });

    $(".lu-light-off").click(function()    { do_cmd('light/off'); });
    $(".lu-light-weak").click(function()   { do_cmd('light/weak'); });
    $(".lu-light-normal").click(function() { do_cmd('light/normal'); });
    $(".lu-light-full").click(function()   { do_cmd('light/full'); });

    $(".lu-avr-on").click(function()       { do_cmd('avr/on'); });
    $(".lu-avr-off").click(function()      { do_cmd('avr/off'); });
    $(".lu-avr-volume-up").click(function()   { do_cmd('avr/volume/up'); poll_avr_volume(); });
    $(".lu-avr-volume-down").click(function() { do_cmd('avr/volume/down'); poll_avr_volume(); });

    $(".lu-oppo-on").click(function()       { do_cmd('oppo/on'); });
    $(".lu-oppo-off").click(function()      { do_cmd('oppo/off'); });
    $(".lu-oppo-stop").click(function()     { do_cmd('oppo/stop'); });
    $(".lu-oppo-play").click(function()     { do_cmd('oppo/play'); });
    $(".lu-oppo-pause").click(function()    { do_cmd('oppo/pause'); });

    $(".lu-hw50-on").click(function()       { do_cmd('hw50/on'); });
    $(".lu-hw50-off").click(function()      { do_cmd('hw50/off'); });

    $("#lu-command").submit(function(event) {
        $("#lu-command-output").html('')
        do_cmdfn($("#lu-command-input").val(),function(data) { $("#lu-command-output").html(JSON.stringify(data)); });
        event.preventDefault();
    });

});
