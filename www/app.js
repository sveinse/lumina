/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp', ["ngRoute"])

    .config(function($routeProvider) {
        $routeProvider
            .when("/main", {
                templateUrl: "LuminaMain.html",
                controller: "LuminaMain"
            })
            .otherwise({redirectTo:'/main'});
        });
