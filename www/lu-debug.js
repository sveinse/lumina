/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .controller('LuminaDebug', ['$scope', 'LuminaComm', function(
        $scope, LuminaComm) {

        $scope.luminaComm = LuminaComm;

        $scope.command = '';

        var onCommandComplete = function(data) {
            // This is a hack: LuminaComm.command() will add any failing
            // commands to the debug.log, but we'll have to do this
            // on successful commands too.
            $scope.luminaComm.debug.log += $scope.luminaComm.debug.stage + data + '\n';
            console.log(data);
        };

        $scope.send = function() {
            if ($scope.command) {
                LuminaComm.command($scope.command)
                    .then(onCommandComplete);
            };
        };
    }]);
