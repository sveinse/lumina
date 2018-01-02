/**
 * @license Lumina v0.1
 * (c) 2014-2018 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .controller('LuminaMain', ['$scope', 'LuminaComm', function(
        $scope, LuminaComm) {

        $scope.luminaComm = LuminaComm;

        var onCommandComplete = function(data) {
        };

        $scope.command = function(command) {
            if (command) {
                LuminaComm.command(command)
                    .then(onCommandComplete);
            };
        };

        $scope.sections = [
            {
                title: 'Visning',
                icon: 'fa-picture-o',

                buttons: [ [
                    {  type: 'danger',  icon: 'fa-bell-slash-o',  text: 'Anlegg av', cmd: 'show/elec-off' },
                    {  type: 'default', icon: 'fa-music',         text: 'Musikk',    cmd: 'show/music' },
                    {  type: 'default', icon: 'fa-play-circle-o', text: 'Netflix',   cmd: 'show/netflix' },
                    {  type: 'default', icon: 'fa-youtube',       text: 'Youtube',   cmd: 'show/youtube' },
                    {  type: 'default', icon: 'fa-chrome',        text: 'Chrome',    cmd: 'show/chrome' },
                    {  type: 'info',    icon: 'fa-television',    text: 'TV',        cmd: 'show/tv'  },
                    {  type: 'success', icon: 'fa-film',          text: 'Film',      cmd: 'show/movie'  },
                ] ]
            },
            {
                title: 'Lys',
                icon: 'fa-lightbulb-o',

                buttons: [ [
                    {  type: 'danger',  icon: 'fa-moon-o',    text: 'Helt av', cmd: 'light/all-off'  },
                    {  type: 'primary', icon: 'fa-circle',    text: 'Av',      cmd: 'light/off'  },
                    {  type: 'default', icon: 'fa-adjust',    text: 'Ambient', cmd: 'light/ambient'  },
                    {  type: 'default', icon: 'fa-adjust',    text: 'Svakt',   cmd: 'light/weak'  },
                    {  type: 'default', icon: 'fa-sun-o',     text: 'Fullt',   cmd: 'light/full'  },
                    {  type: 'success', icon: 'fa-power-off', text: 'På',      cmd: 'light/normal'  },
                ],[
                    {  type: 'default', icon: 'fa-search',    text: 'Finne',   cmd: 'light/finder'  },
                    {  type: 'default', icon: 'fa-remove',    text: 'LED av',  cmd: 'light/led-off'  },
                    {  type: 'default', icon: 'fa-remove',    text: 'Spot av', cmd: 'light/spot-off'  },
                ] ]
            },
            {
                title: 'Forsterker',
                icon: 'fa-volume-off',

                //bar: [ 'Yes' ],

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o',  text: 'Av', cmd: 'avr/off'  },
                    {  type: 'default', icon: 'fa-minus fa-rotate-90', text: 'På', cmd: 'avr/on'  },
                ], [
                    {  type: 'default', icon: 'fa-circle-o',  text: 'Av', cmd: 'amp1/off'  },
                    {  type: 'default', icon: 'fa-minus fa-rotate-90', text: 'På', cmd: 'amp1/on'  },
                ], [
                    {  type: 'default', icon: 'fa-circle-o',  text: 'Av', cmd: 'amp2/off'  },
                    {  type: 'default', icon: 'fa-minus fa-rotate-90', text: 'På', cmd: 'amp2/on'  },
                ], [
                    {  type: 'default', icon: 'fa-bell-slash', text: '', cmd: 'avr/mute'   },
                    {  type: 'default', icon: 'fa-bell-slash', text: '', cmd: 'amp1/mute'  },
                    {  type: 'default', icon: 'fa-bell-slash', text: '', cmd: 'amp2/mute'  },
                ], [
                    {  type: 'default', icon: '', text: 'P', cmd: 'avr/pure_direct'   },
                    {  type: 'default', icon: '', text: 'P', cmd: 'amp1/pure_direct'  },
                    {  type: 'default', icon: '', text: 'P', cmd: 'amp2/pure_direct'  },
                ] ]
            },
            {
                title: 'Spiller',
                icon: 'fa-play-circle',

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o', text: 'Av', cmd: 'oppo/off'  },
                    {  type: 'default', icon: 'fa-power-off', text: 'På', cmd: 'oppo/on'  },
                ],[
                    {  type: 'default', icon: 'fa-home', text: 'Home', cmd: 'oppo/home'  },
                    {  type: 'default', icon: 'fa-play-circle-o', text: 'Netflix', cmd: 'oppo/netflix'  },
                    {  type: 'default', icon: 'fa-youtube', text: 'YouTube',       cmd: 'oppo/youtube'  },
                ],[
                    {  type: 'default', icon: 'fa-stop', text: '', cmd: 'oppo/stop'  },
                    {  type: 'default', icon: 'fa-play', text: '', cmd: 'oppo/play'  },
                    {  type: 'default', icon: 'fa-pause', text: '', cmd: 'oppo/pause'  },
                    {  type: 'default', icon: 'fa-eject', text: '', cmd: 'oppo/eject'  },
                ] ]
            },
            {
                title: 'Prosjektor',
                icon: 'fa-video-camera',

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o', text: 'Av', cmd: 'hw50/off'  },
                    {  type: 'default', icon: 'fa-power-off', text: 'På', cmd: 'hw50/on'  },
                ],[
                    {  type: 'default', icon: 'fa-film', text: 'Film', cmd: 'hw50/preset/film1'  },
                    {  type: 'default', icon: 'fa-television', text: 'TV', cmd: 'hw50/preset/tv'  },
                ] ]
            },
        ];

    }]);
