var menus = [ 'home', 'lights', 'power', 'projector', 'player', 'receiver' ];

function hideotherparts(name) {
    for (i=0; i < menus.length; i++) {
        if ( menus[i] == name ) {
            continue;
        }
        document.getElementById("menu_" + menus[i]).className = "hide";
        document.getElementById("nav_" + menus[i]).removeAttribute("class");
    }
}

function showpart(w) {
    var name=w.parentNode.id.replace("nav_","");
    document.getElementById("menu_" + name).className = "show";
    document.getElementById("nav_" + name).className = "active";
    hideotherparts(name);
}
