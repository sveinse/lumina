/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp', ['ngRoute'])

    .config(['$routeProvider', '$locationProvider', function(
        $routeProvider, $locationProvider) {

        $routeProvider
            .when('/main', {
                templateUrl: 'LuminaMain.html',
                controller: 'LuminaMain'
            })
            .when('/yamaha', {
                templateUrl: 'LuminaYamaha.html',
                controller: 'LuminaYamaha'
            })
            .otherwise( {redirectTo:'/main'} );

        //$locationProvider.html5Mode(true);

    }]);
