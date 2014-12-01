import os,sys

from telldus import Telldus
from oppo import Oppo
from event import Action, Event, ActionList
import web

from twisted.internet import reactor
from twisted.python import log, syslog


# Lazy...
A = Action
E = Event

#
# Mapping of incoming events to outgoing actions.
# Actions can be string, Action() objects, or tuples with strings or Action() objects
#
connections = {
    # Event -> Action(s)

    # Telldus connections
    'td/starting' : None,
    'td/connected' : None,
    'td/error': None,

    # Nexa fjernkontroll
    'td/remote/g/on' :   A('td/lights/on'),
    'td/remote/g/off':   A('td/lights/off'),
    'td/remote/4/on' :   A('td/lights/dim', 30),
    'td/remote/4/off': ( A('td/roof/off'),
                         A('td/table/dim', 30) ),

    #'td/remote/1/on' :   A('oppo/play'),
    'td/remote/1/off': ( A('td/lights/off'),
                         A('oppo/off') ),

    # Veggbryter overst hjemmekino
    'td/wallsw1/on'  :   A('td/lights/on'),
    'td/wallsw1/off' :   A('td/lights/off'),

    # Veggbryter nederst kino
    'td/wallsw2/on'  :   A('td/lights/dim', 30),
    'td/wallsw2/off' : ( A('td/roof/off'),
                         A('td/table/dim', 30) ),

    # Oppo regler
    'oppo/pause'     :   A('td/lights/dim', 30),
    'oppo/play'      :   A('td/lights/off'),
    'oppo/stop'      :   A('td/lights/on'),
}


#
# (Dynamic) list of all actions
#
actions = ActionList()



def handle_event(event):
    ''' Event dispatcher '''

    if not event:
        return

    if isinstance(event,str):
        event=Event(event)

    log.msg("%s" %(event), system='EVENT ')

    # Known event?
    if event.name not in connections:
        log.msg("   Unknown event '%s', ignoring" %(event.name), system='EVENT ')
        return

    # Turn into list
    actions = connections[event.name]
    if actions is None:
        actions = ( )
    elif not isinstance(actions, tuple) and not isinstance(actions, list):
        actions = ( actions, )
    log.msg("   -> %s" %(actions,), system='EVENT ')

    # Execute actions
    for action in actions:
        execute_action(action)



def execute_action(action):
    ''' Action handler '''

    if not action:
        return

    if isinstance(action,str):
        action=Action(action)

    log.msg("%s" %(action), system='ACTION')

    # Known action?
    if action.name not in actions:
        log.msg("   Unknown action '%s', ignoring" %(action.name), system='ACTION')
        return

    # Call action
    actions[action.name](action)



#
# ***  MAIN  ***
#
def main(use_syslog=False):
    ''' Lumina entry point '''

    if use_syslog:
        syslog.startLogging(prefix='Lumina')
    else:
        log.startLogging(sys.stdout)

    # Start Telldus integration
    td = Telldus()
    td.add_eventcallback(handle_event)
    actions.add(td.get_actiondict())
    td.setup()

    # Start Oppo integration
    oppo = Oppo('/dev/ttyUSB1')
    oppo.add_eventcallback(handle_event)
    actions.add(oppo.get_actiondict())
    oppo.setup()

    # Start WEB interface
    #web.setup()

    # Start everything
    print 'Server PID: %s' %(os.getpid())
    reactor.run()
