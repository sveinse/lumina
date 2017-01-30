/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .factory('LuminaComm', [ '$http', function(
        $http) {

        var debug = {
            log: ''
        };

        var log = function(what) {
            debug.log += what + '\n';
            console.log(what);
        }

        var command = function(command,args) {
            //log('<<< ' + command);
            return $http.post('/rest/command/' + command, args)
                .then(function(response) {
                    //log('>>> ' + JSON.stringify(response.data));
                    return response.data.result;
                },function(failure) {
                    log('<<< ' + command);
                    log('>>> FAIL: ' + failure.status + ' ' + failure.statusText);
                    return failure;
                });
        };


        // Admin functions
        var get_master_info = function() {
            return $http.get('/rest/master/info')
                .then(function(response) {
                    return response.data;
                });
        }

        var get_host_info = function(hostid) {
            return command(hostid + '/' + 'info');
        }

        var get_server_info = function(hostid) {
            return command(hostid + '/' + 'server');
        }

        var get_plugins = function(hostid) {
            return command(hostid + '/' + 'plugins');
        }

        var get_config = function(hostid) {
            return command(hostid + '/' + 'config');
        }

        var get_nodes = function(hostid) {
            return command(hostid + '/' + 'nodes')
                .then(function(data) {
                    for(var i=0; i < data.length; i++) {
                        data[i].lastactivity = new Date(data[i].lastactivity);
                    }
                    return data;
                });
        }


        // Functions
        return {
            debug: debug,
            command: command,

            get_master_info: get_master_info,
            get_host_info: get_host_info,
            get_server_info: get_server_info,

            get_nodes: get_nodes,
            get_plugins: get_plugins,
            get_config: get_config,
        };

    }]);
