#!/usr/bin/env python
#
# Small framwork for generaring HTML web pages
#
#   import html
#   page = new html.Document()
#   page.


import os
import cgi


class ElementContents(list):
    ''' Element contents list type. '''

    def __init__(self,*args):
        self._append(self, args)

    def _append(self, l, args):
        ''' Append args members to l. If args member is list or tuple, append its members '''
        for a in args:
            if type(a) is list or type(a) is tuple:
                l.extend(a)
            else:
                l.append(a)

    def add(self, *args):
        ''' Add members '''
        self._append(self,args)

    def insert(self, *args):
        ''' Insert members '''
        l = list()
        self._append(l,args)
        l.reverse()
        for a in l:
            list.insert(self, 0, a)

    def render(self,level=0):
        ''' Render HTML output '''
        t = ''
        for k in self:
            if isinstance(k, Element):
                t += k.render(level=level)
            elif isinstance(k, raw):
                t += str(k)
            elif k is None:
                pass
            else:
                t += cgi.escape(str(k), True)
        return t

    def __iadd__(self, other):
        ''' += method. '''
        self.add(other)
        return self

    def __nonzero__(self):
        ''' Return True if object contains non-zero data. That is any objects which is True.
            (Normal list returns True if len()>0) '''
        for k in self:
            if k:
                return True
        return False

    def __str__(self):
        l = [ str(a) for a in self ]
        return "'%s'" %("', '".join(l))


class raw(str):
    """ raw str object to be able to pass non-quotable text. Use this to
        pass raw HTML code to output
    """
    pass


class Element(dict):
    ''' Fundamental HTML element, <tag attribute='value'...>content</tag>. The tag is the
        class name (when inherited).

            e = Element( *args, **kwargs)

        where args is a list of contents, and kwargs is a dict of attributes. The constructor
        support a number of ways to initialize data:

            e = Element('content')
            e = Element( 'content1', 'content2' )
            e = Element( attribute='value' )
            e = Element( 'content1', 'content2', attribute='value' )
            e = Element( 'content1', { 'attribute': 'value' }, 'content2' )
            e = Element( [ 'content1', 'content2' ], 'content3' )

        Any dict operations on the class would access the attributes:

            e['attribute'] = 'value'

        Adding data to the object can be done with the += operator:

            e += 'content'
            e += ( 'content1', 'content2' )
            e += { 'attribute': 'value' }
            e += ( 'content1', { 'attribute': 'value' }, 'content2' )
            e += ( [ 'content1', 'content2' ], 'content3' )

       Use the render() method to generate the final HTML code.
    '''

    # The nl tuple control if \n should be printed with the HTML output
    # "\n<TAG>\n  ...data...  \n</TAG>\n'
    #  [0]    [1]             [2]    [3]
    #
    nl = ( False, False, False, False )

    # Does this element require a closing tag </tag>? If set to False, the
    # objects contents will be ignored.
    endtag = True

    # List of attributes that will be rewritten when rendering
    alias = {
        'cls': 'class',
        'http_equiv': 'http-equiv' }


    def __init__(self,*args,**kwargs):
        self.ec = ElementContents()
        self.add(*args,**kwargs)


    def _update(self, *args, **kwargs ):
        #print "_UPDATE(ARGS=%s , KWARGS=%s)" %(args,kwargs)

        # Add dicts in args
        ea = [ a for a in args if type(a) is dict ]
        #print "   EA(%s)" %(ea)
        for a in ea:
            self.update(a)

        # Add keyword as attributes
        self.update(**kwargs)


    def add(self, *args, **kwargs):
        #print "ADD(ARGS=%s , KWARGS=%s)" %(args,kwargs)
        self._update(*args,**kwargs)

        # Add all args (except dicts) as contents
        ec = [ a for a in args if type(a) is not dict ]
        self.ec.add(*ec)


    def insert(self, *args, **kwargs):
        self._update(*args, **kwargs)

        # Insert all args (except dicts) as contents
        ec = [ a for a in args if type(a) is not dict ]
        self.ec.insert(*ec)


    def render(self,level=0):
        ''' Render HTML text output '''

        # Name of tag
        tag = self.__class__.__name__.lower()

        # Generate list of element attributes (ea)
        l = []
        ea = ''
        for (k,d) in self.items():
            if k in self.alias:
                k = self.alias[k]
            l.append( '%s="%s"' %(k, cgi.escape(str(d), True)) )
        if l:
            ea = ' ' + ' '.join(l)

        # Generate contents (ec)
        ec = self.ec.render(level=level+1)

        # Newline handling
        #nl = [ '\n' if n else '' for n in self.nl ]
        nl = [ '\n' + ( '  '*level) if self.nl[0] else '',
               '\n' + ( '  '*(level+1)) if self.nl[1] else '',
               '\n' + ( '  '*level) if self.nl[2] else '',
               '\n' + ( '  '*level) if self.nl[3] else '' ]

        #if self.endtag and ec and ec[0] == '\n':
        #    # Don't use nl before contents if content begins with nl
        #    nl[1] = ''
        #if ec and ec[-1] == '\n':
        #    # Don't use nl before close tag if contents ends with nl
        #    nl[2] = ''
        #if nl[1] == '\n' and nl[2] == '\n' and not ec:
        #    # Dont't use nl before close tag if open tag end with nl and no contents
        #    nl[2] = ''

        # Print tag and attributes
        o = '%s<%s%s>%s' %(nl[0], tag, ea, nl[1])

        # Print contents and closing tag
        if self.endtag:
            o += '%s%s</%s>' %(ec, nl[2], tag)

        # Print \n after closing tag
        o += nl[3]

        return o


    def __iadd__(self, other):
        ''' Implement += method. It supports single objects or iterable lists. dict() types will be added as attributes,
            while all other types as contents.'''
        #print "IADD(%s)" %(other,)
        if type(other) is list or type(other) is tuple:
            self.add(*other)
        else:
            self.add(other)
        return self


    def __nonzero__(self):
        ''' Return true if object contains no data, that is no content nor any attributes.
        '''
        if len(self):
            return True
        if self.ec:
            return True
        return False


    def __str__(self):
        l = ["'%s'='%s'" %(k,d) for k,d in self.items()]
        return "<%s {%s} %s>" %(self.__class__.__name__, ", ".join(l), self.ec)



class Document(object):
    ''' High-level HTML document generator '''

    def __init__(self):
        self.head = head()
        self.body = body()
        self.header = header()
        self.nav = nav()
        self.footer = footer()

        self.title = None
        self.lang = "en"
        self.style = None

    def render(self):
        o = '<!DOCTYPE html>'

        self.head.insert(
            title(self.title),
            meta(charset="utf-8"),
            raw("""
<!--[if lt IE 9]>
<script src="http://html5shiv.googlecode.com/svn/trunk/html5.js">
</script>
<![endif]-->"""),
            style(self.style) or None
        )

        self.body.insert(
            self.header or None,
            self.nav or None
        )
        self.body.add (
            self.footer or None
        )

        o_html = html( self.head, self.body, lang=self.lang )
        return '<!DOCTYPE html>' + o_html.render() + '\n'



#
#  HTML objects
#
class html(Element):
    nl = ( True, True, True, False)

class head(Element):
    nl = ( True, True, True, False)

class body(Element):
    nl = ( True, True, True, False)

class meta(Element):
    nl = ( False, False, False, False)
    endtag = False

class title(Element):
    nl = ( True, False, False, True)

class style(Element):
    nl = (True, False, True, True)

class header(Element):
    nl = (True, True, True, False)

class nav(Element):
    nl = (True, True, True, False)

class main(Element):
    nl = (True, True, True, False)

class footer(Element):
    nl = (True, True, True, False)


#
# HTML contents objects
#
class h1(Element):
    nl = (True, False, False, True)

class hr(Element):
    nl = (True, False, False, True)
    endtag = False

class ul(Element):
    pass

class li(Element):
    nl = (True, False, False, True)

class a(Element):
    pass




#
# Testing
#
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
