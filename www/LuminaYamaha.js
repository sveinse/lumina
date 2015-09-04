/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp')

    .controller('LuminaYamaha', ['$scope', 'LuminaComm', function(
        $scope, LuminaComm) {

        $scope.luminaComm = LuminaComm;

        $scope.sequence = [ 'Front_L', 'Front_R', 'Center',
                            'Sur_L', 'Sur_R', 'Sur_Back_L', 'Sur_Back_R',
                            'Front_Presence_L', 'Front_Presence_R',
                            'Subwoofer_1', 'Subwoofer_2' ]

        $scope.chdata = {}

        $scope.usedChannels = function() {
            use = [];
            for (ch in $scope.sequence) {
                if ($scope.chdata[ch] !== undefined) {
                    use.push(ch);
                }
            }
            return use;
        };

        var addChannel = function(channel) {
            if ($scope.sequence.indexOf(channel) == -1) {
                $scope.sequence.push(channel);
                //$scope.channels.sort();
            };
            if ($scope.chdata[channel] === undefined) {
                $scope.chdata[channel] = { name: channel };
            };
        };

        var getPEQ = function(channel) {
            LuminaComm.command('avr/peq/1', [ channel ])
                .then(function(data) {
                    var ch=data.args[0];
                    $scope.chdata[ch].peq = data.result;
                    for (i=0; i < $scope.chdata[ch].peq.length; i++) {
                        if ($scope.chdata[ch].peq[i].gain != 0) {
                            $scope.chdata[ch].peq[i].cls = 'success';
                        };
                    };
                    console.log($scope.chdata);
                });
        };

        var getLevels = function() {
            LuminaComm.command('avr/levels/1')
                .then(function(data) {
                    for ( channel in data.result ) {
                        addChannel(channel);
                        $scope.chdata[channel].level = data.result[channel];

                        // Do this here, because now we know that this channel is valid
                        getPEQ(channel);
                    };
                });
        };

        var getDistance = function() {
            LuminaComm.command('avr/distance/1')
                .then(function(data) {
                    for ( channel in data.result ) {
                        addChannel(channel);
                        $scope.chdata[channel].distance = data.result[channel];
                    };
                });
        };

        getLevels();
        getDistance();

    }]);
