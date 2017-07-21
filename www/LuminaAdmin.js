/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .controller('LuminaAdmin', ['$scope', '$routeParams', 'LuminaComm', function(
        $scope, $routeParams, LuminaComm) {

        $scope.hosts = {};
        $scope.plugins = [];
        $scope.configs = [];

        var on_page_load = function() {

            // Get the main master info
            LuminaComm.get_main_info()
                .then(function(data) {

                    // Set the main info and set the host info for this host
                    $scope.main = data;
                    $scope.hosts[data.hostid] = data;
                });

            // Get the server info
            LuminaComm.get_server_info()
                .then(function(data) {

                    // Set the server info and list of nodes
                    $scope.server = data;
                    $scope.nodes = data.nodes;

                    // FIXME: Sort the nodes array into a presentable order

                    for (let i=0; i < data.nodes.length; i++) {

                        var node = data.nodes[i];
                        var hostid = node.hostid;

                        // Request host information for those hosts that
                        // is missing from our records (which are remote
                        // hosts)
                        if (hostid !== null && !(hostid in $scope.hosts)) {

                            // Setup preliminary host info
                            $scope.hosts[hostid] = { hostid:hostid,
                                                     hostname:node.hostname,
                                                     node:node.name };

                            // Get host information
                            LuminaComm.get_host_info(node.name)
                                .then(function(data) {
                                    $scope.hosts[data.hostid] = data;
                                });
                        };
                    };
                });
        };

        $scope.on_select_host = function(hostid) {
            $scope.selected_host = $scope.hosts[hostid];

            $scope.plugins = $scope.selected_host.plugins;
            $scope.configs = $scope.selected_host.config;

        };

        on_page_load();

    }]);
