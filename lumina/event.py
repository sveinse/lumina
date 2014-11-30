
class Base:
    def __init__(self,name,*args,**kw):
        self.name = name
        self.args = args
        self.kw = kw
    def __repr__(self):
        return "'%s' %s" %(self.name,self.args)

class Action(Base):
    pass

class Event(Base):
    pass


class EventList(dict):
    pass


class ActionList:
    def __init__(self, actions=None):
        self.actions = { }
        if actions:
            self.addlist(actions)

    def add(self, actions):
        for (name,fn) in actions.items():
            if name in self.actions:
                raise Exception("Action '%s' already in list" %(name))
            self.actions[name] = fn

    def __iter__(self):
        return self.actions.__iter__

    def __contains__(self, obj):
        return self.actions.__contains__(obj)

    def __getitem__(self, obj):
        return self.actions.__getitem__(obj)
