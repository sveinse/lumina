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
            .when('/config', {
                templateUrl: 'LuminaConfig.html',
                controller: 'LuminaConfig'
            })
            .when('/admin', {
                templateUrl: 'LuminaAdmin.html',
                controller: 'LuminaAdmin'
            })
            .otherwise( {redirectTo:'/main'} );

    }]);
