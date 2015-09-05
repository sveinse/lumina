/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp')

    .controller('LuminaConfig', ['$scope', '$routeParams', 'LuminaComm', function(
        $scope, $routeParams, LuminaComm) {

        (function() {
            LuminaComm.config('')
                .then(function(data) {
                    $scope.config = data;
                });
        }());

    }]);
