# -*- python -*-
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

from callback import Callback


if __name__ == "__main__":

    def f(result):
        print "f()",result

    c = Callback()
    c.addCallback(f)
    c.callback(123)

    print

    a = Callback()
    a.addCallback(f)
    b = Callback()
    b.addCallback(f)
    #d = allCallbacks(a,b)
    #d.addCallback(f)

    a.callback(1)
    b.callback(2)
    print "C"

    class A:
        def f(self,r,a):
            print 'A.f()',r,a

    a = A()
    c = Callback()
    c.addCallback(a.f,12)
    c.callback(42)
