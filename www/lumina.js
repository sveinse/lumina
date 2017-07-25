/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp', ['ngRoute', 'ui.bootstrap'])

    .config(['$routeProvider', '$locationProvider', function(
        $routeProvider, $locationProvider) {

        $routeProvider
            .when('/main', {
                templateUrl: 'lu-main.html',
                controller: 'LuminaMain'
            })
            .when('/yamaha', {
                templateUrl: 'lu-yamaha.html',
                controller: 'LuminaYamaha'
            })
            .when('/admin', {
                templateUrl: 'lu-admin.html',
                controller: 'LuminaAdmin'
            })
            .otherwise( {redirectTo:'/main'} );

    }]).run(['$rootScope', '$location', function($rootScope, $location){
        var path = function() { return $location.path();};
        $rootScope.$watch(path, function(newVal, oldVal) {
            $rootScope.activetab = newVal;
        });
     }]);
