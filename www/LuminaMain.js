/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
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
                    {  type: 'primary', icon: 'fa-circle-o', text: 'Alt AV', cmd: 'elec/off'  },
                    {  type: 'success', icon: 'fa-power-off', text: 'Alt PÅ', cmd: 'elec/on'  },
                ] ]
            },
            {
                title: 'Lys',
                icon: 'fa-lightbulb-o',

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o', text: 'Av', cmd: 'light/off'  },
                    {  type: 'default', icon: 'fa-circle-o', text: 'Svakt', cmd: 'light/weak'  },
                    {  type: 'default', icon: 'fa-circle-o', text: 'På', cmd: 'light/normal'  },
                    {  type: 'default', icon: 'fa-circle-o', text: 'Fullt', cmd: 'light/full'  },
                ] ]
            },
            {
                title: 'Forsterker',
                icon: 'fa-volume-off',

                bar: [ 'Yes' ],

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o', text: 'Av', cmd: 'avr/off'  },
                    {  type: 'default', icon: 'fa-power-off', text: 'På', cmd: 'avr/on'  },
                ],[
                    {  type: 'default', icon: 'fa-circle-o',  text: 'Ned', cmd: 'avr/volume/down'  },
                    {  type: 'default', con: 'fa-circle-o', text: 'Opp', cmd: 'avr/volume/up'  },
                ] ]
            },
            {
                title: 'Spiller',
                icon: 'fa-play-circle',

                buttons: [ [
                    {  type: 'default', icon: 'fa-circle-o', text: 'Av', cmd: 'oppo/off'  },
                    {  type: 'default', icon: 'fa-power-off', text: 'På', cmd: 'oppo/on'  },
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
                ] ]
            },
        ];

    }]);
