/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .controller('LuminaAdmin', ['$scope', '$routeParams', 'LuminaComm', function(
        $scope, $routeParams, LuminaComm) {

        $scope.hosts = {};

        // 1) Gets the master ID ($scope.master.hostid)
        var get_master_id = function() {
            LuminaComm.get_master_info()
                .then(function(data) {
                    $scope.master = data;
                    get_master_info($scope.master.hostid);
                });
        };

        // 2) Get the info about the master, the server and its nodes
        var get_master_info = function(hostid) {

            // Get the host info
            LuminaComm.get_host_info(hostid)
                .then(function(data) {
                    $scope.main = data;
                });

            // Get the server info
            LuminaComm.get_server_info(hostid)
                .then(function(data) {
                    $scope.server = data;
                    get_hosts_info($scope.server.hosts)
                });

            // Get the nodes
            LuminaComm.get_nodes(hostid)
                .then(function(data) {
                    $scope.nodes = data;
            });
        };

        // Get info for each of the connected hosts
        var get_hosts_info = function(hosts) {
            $scope.hosts = {};
            for (var i=0; i < hosts.length; i++) {

                var hostid = hosts[i];
                $scope.hosts[hostid] = { hostid:hostid };

                LuminaComm.get_host_info(hostid)
                    .then(function(data) {
                        $scope.hosts[data.hostid] = data;
                });
            };
        };

        // Event handler for clicking on a host
        $scope.select_host = function(hostid) {
            $scope.sel_host = $scope.hosts[hostid];

            // Update server info
            LuminaComm.get_host_info(hostid)
                .then(function(data) {
                   $scope.hosts[data.hostid] = data;
                }
            );

            // Get plugina
            LuminaComm.get_plugins(hostid)
                .then(function(data) {
                    $scope.sel_plugins = data;
            });

            // Get configs
            LuminaComm.get_config(hostid)
                .then(function(data) {
                    $scope.sel_config = data;
                });

        };

        // On page load
        get_master_id();
    }]);
