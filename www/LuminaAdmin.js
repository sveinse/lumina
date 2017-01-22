/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp')

    .controller('LuminaAdmin', ['$scope', '$routeParams', 'LuminaComm', function(
        $scope, $routeParams, LuminaComm) {

        (function() {
            LuminaComm.get_plugins('')
                .then(function(data) {
                    $scope.plugins = data;
                });
        }());

        (function() {
            LuminaComm.get_nodes('')
                .then(function(data) {
                    $scope.nodes = data;
                });
        }());

    }]);
