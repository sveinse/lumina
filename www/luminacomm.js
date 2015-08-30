/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
(function(){

    var luminaComm = function($http) {

        var debug = {
            log: ''
        };

        var log = function(what) {
            debug.log += what + '\n';
            //console.log(what);
        }

        var command = function(command) {
            log('<<< ' + command);
            return $http.post('/ctrl/' + command)
                .then(function(response) {
                    log('>>> ' + JSON.stringify(response.data));
                    return response.data;
                },function(failure) {
                    log('>>> FAIL: ' + failure.status + ' ' + failure.statusText);
                });
        };

        return {
            debug: debug,
            command: command,
        };

    };

    var module = angular.module("LuminaApp");
    module.factory("LuminaComm", luminaComm);

}());
