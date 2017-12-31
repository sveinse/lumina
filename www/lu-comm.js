/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .factory('LuminaComm', [ '$http', function(
        $http) {

        var debug = {
            log: '',
            stage: ''
        };

        var log = function(what) {
            debug.stage += what + '\n';
            console.log(what);
        }

        
        // Lumina functional commands
        var command = function(command,args) {
            debug.stage = '';
            log('<<< ' + command);
            return $http.post('/rest/command/' + command, args)
                .then(function(response) {
                    log('>>> ' + JSON.stringify(response.data));
                    return response.data.result;
                }).catch(function(failure) {
                    //log('<<< ' + command);
                    console.log(failure);
                    log('>>> FAIL ' + failure.status + ' ' + failure.statusText + ':  ' + failure.data.result);
                    debug.log += debug.stage;
                    throw failure;
                });
        };

        // Admin functions
        var get_server_info = function() {
            return command('_server');
        }

        var get_host_info = function(node='') {
            if (node.length>0) {
                node = node + '/';
            }
            return command(node + '_info');
        }

        // Functions
        return {
            debug: debug,
            command: command,

            get_server_info: get_server_info,
            get_host_info: get_host_info,
        };

    }]);
