/**
 * @license Lumina v0.1
 * (c) 2014-2017 Svein Seldal
 * License: GPL3
*/
angular.module('LuminaApp')

    .controller('LuminaAdmin', ['$scope', '$routeParams', '$sce', 'LuminaComm', function(
        $scope, $routeParams, $sce, LuminaComm) {

        $scope.renderHtml = function(html_code) {
            return $sce.trustAsHtml(html_code);
        };

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
                                }).catch(function(failure){});
                        };
                    };
                });
        };

        $scope.on_select_host = function(hostid) {
            $scope.selected_host = $scope.hosts[hostid];

            $scope.plugins = $scope.selected_host.plugins;
            $scope.configs = $scope.selected_host.config;

        };

        $scope.status_html = function(status, why) {
            let color = 'off';
            let icon = 'fa-circle';
            switch(status) {
                case 'RED':
                    color='red';
                    break;
                case 'YELLOW':
                    color='yellow';
                    break;
                case 'GREEN':
                    color='green';
                    break;
                default:
                    icon='fa-circle-o';
            };
            let whyt = '';
            if (why) {
                whyt = '&emsp;' + why;
            }
            return $sce.trustAsHtml('<i class="fa ' + icon + ' fa-lg ' + color +'"></i>' + whyt);
        }

        on_page_load();

    }]);
