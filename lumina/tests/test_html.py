# -*- python -*-
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

from html import *

if __name__ == "__main__":
    import sys

    #e = html( head() )
    #print e.render()
    #sys.exit(1)


    print


    e = Element()
    print e

    e = Element('content')
    print e

    e = Element( 'content1', 'content2' )
    print e

    e = Element( attribute='value' )
    print e

    e = Element( 'content1', 'content2', attribute='value' )
    print e

    e = Element( 'content1', { 'attribute': 'value' }, 'content2' )
    print e

    e = Element( [ 'content1', 'content2' ], 'content3' )
    print e


    print


    e = Element( )
    e += 'content'
    print e

    e = Element()
    e += ( 'content1', 'content2' )
    print e

    e = Element()
    e += { 'attribute': 'value' }
    print e

    e = Element()
    e += ( 'content1', { 'attribute': 'value' }, 'content2' )
    print e
    print e.render()

    e = Element()
    e += ( [ 'content1', 'content2' ], 'content3' )
    print e


    #print

    #d = Document()
    #print d
    #print d.render()


    print

    ec = ElementContents()
    ec += 'content'
    print ec

    ec = ElementContents('content')
    print ec

    ec = ElementContents()
    ec += ('content1', 'content2')
    print ec

    ec = ElementContents('content1','content2')
    print ec

    ec = ElementContents( [ 'content1', 'content2' ] )
    print ec

    l = [ 'content1', 'content2' ]
    ec = ElementContents( l )
    print ec

    ec = ElementContents( [ 'content1', 'content2' ] )
    ec.insert( 'content3', 'content4' )
    print ec

    ec = ElementContents( [ 'content1', 'content2' ] )
    l = [ 'content5', 'content6' ]
    ec.insert( 'content3', l, 'content4' )
    print ec


    print

    h = html()
    h += 'data'
    print h

    h = html()
    h.add('data')
    print h

    h = html()
    h += { 'foo': 'bar' }
    print h

    h = html()
    h.add({ 'foo': 'bar' })
    print h

    h = html()
    print
    h += ( {'foo': 'bar' }, )
    print h

    #h = html()
    #print
    #h.add( ( {'foo': 'bar' },) )
    #print h
