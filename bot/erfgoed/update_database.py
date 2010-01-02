#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Update the monuments database either from a text file or from some wiki page(s)

'''
import sys, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, MySQLdb, config, re, pagegenerators

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect('sql.toolserver.org', db='u_multichill', user = config.db_username, passwd = config.db_password, use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def updateMonument(contents, conn, cursor):
    query = u"""REPLACE INTO monumenten(objrijksnr, woonplaats, adres, objectnaam, type_obj, oorspr_functie, bouwjaar, architect, cbs_tekst, RD_x, RD_y, lat, lon, source)
		VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')""";

    cursor.execute(query % (contents.get(u'objrijksnr'),
			    contents.get(u'woonplaats'),
			    contents.get(u'adres'),
                            contents.get(u'objectnaam'),
                            contents.get(u'type_obj'),
                            contents.get(u'oorspr_functie'),
                            contents.get(u'bouwjaar'),
                            contents.get(u'architect'),
                            contents.get(u'cbs_tekst'),
                            contents.get(u'RD_x'),
                            contents.get(u'RD_y'),
                            contents.get(u'lat'),
                            contents.get(u'lon'),
                            contents.get(u'source')))
    #print u'updating!'
    #time.sleep(5)

def processMonument(text, source, conn, cursor):
    '''
    Process a single instance of the Tabelrij rijksmonument template
    '''
    # First remove line breaks like \n and \r
    #text = text.replace(u'\n', u' ')
    #text = text.replace(u'\r', u' ')
    
    # The regexes to find all the fields
    fields = [u'objrijksnr',
	     u'woonplaats',
             u'adres',
             u'objectnaam',
             u'type_obj',
	     u'oorspr_functie',
             u'bouwjaar',
             u'architect',
             u'cbs_tekst',
             u'RD_x',
             u'RD_y',
             u'lat',
             u'lon',
	    ]
    
    # Get all the fields
    contents = {}
    contents['source'] = source
    for field in fields:
	regex = field + u'=([^|^}]+)'
	#print regex
	match = re.search(regex, text)
	if match:
	    # Big fucking escape hack. Stupid mysql lib
	    contents[field] = match.group(1).strip().replace("'", "\\'") 
	else:
	    contents[field] = u'' 
    #print contents
    #time.sleep(5)

    # Insert it into the database
    if contents.get('objrijksnr'):
	updateMonument(contents, conn, cursor)

def processText(text, source, conn, cursor):
    '''
    Process a text containing one or multiple instances of the Tabelrij rijksmonument template
    '''
    regex = u'\{\{Tabelrij rijksmonument[^}]+\}\}'
    matches = re.findall(regex, text)
    for match in matches:
	monument = match.group(0)
	processMonument(monument, source, conn, cursor)

def processTextfile(textfile, conn, cursor):
    '''
    Process the contents of a text file containing one or more lines with the Tabelrij rijksmonument template
    '''
    file = open(textfile, 'r')
    for line in file:
	processMonument(line.decode('UTF-8').strip(), textfile, conn, cursor)

def main():
    '''
    The main loop
    '''
    # First find out what to work on

    textfile = u''
    genFactory = pagegenerators.GeneratorFactory()
    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    for arg in wikipedia.handleArgs():
	if arg.startswith('-textfile:'):
	    textfile = arg [len('-textfile:'):]
	else:
	    genFactory.handleArg(arg)

    if textfile:
	print 'going to work on textfile'
	processTextfile(textfile, conn, cursor)
    else:
	generator = genFactory.getCombinedGenerator()
	if not generator:
	    wikipedia.output(u'You have to specify what to work on. This can either be -textfile:<filename> to work on a local file or you can use one of the standard pagegenerators (in pagegenerators.py)')
	else:
	    for page in generator:
		# Do some checking
		processText(page.get(), page.permalink(), conn, cursor)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()