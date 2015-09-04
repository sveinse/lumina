/**
 * @license Lumina v0.1
 * (c) 2014-2015 Svein Seldal
 * License: MIT
*/
angular.module('LuminaApp')

    .factory('LuminaComm', function($http) {

        var debug = {
            log: ''
        };

        var log = function(what) {
            debug.log += what + '\n';
            //console.log(what);
        }

        var command = function(command,args) {
            log('<<< ' + command);
            return $http.post('/ctrl/' + command, args)
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

    });