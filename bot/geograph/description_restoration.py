#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to upload geograph images from the Toolserver to Commons

'''
import sys, os.path, hashlib, base64, MySQLdb, glob, re, urllib, time
import wikipedia, config, query
import xml.etree.ElementTree, shutil
import imagerecat
import MySQLdb.converters

def connectDatabase(server='sql.toolserver.org', db='u_multichill_geograph_p'):
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    my_conv = MySQLdb.converters.conversions
    del my_conv[MySQLdb.converters.FIELD_TYPE.DATE]
    #print my_conv
    conn = MySQLdb.connect(server, db=db, user = config.db_username, passwd = config.db_password, conv =my_conv , use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)

def connectDatabase2(server='sql.toolserver.org', db='u_multichill_geograph_p'):
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(server, db=db, user = config.db_username, passwd = config.db_password, charset='utf8', use_unicode=True)
    cursor = conn.cursor()
    return (conn, cursor)



def findDuplicateImages(filename, site = wikipedia.getSite(u'commons', u'commons')):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')

    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1))
    return site.getFilesFromAnHash(base64.b16encode(hashObject.digest()))

def getDescription(metadata):
    '''
    Create the description of the image based on the metadata
    '''
    description = u''

    description = description + u'== {{int:filedesc}} ==\n'
    description = description + u'{{Information\n'
    description = description + u'|description={{en|1=' + metadata.get('title')
    if not metadata['comment']==u'':
	description = description + u' ' + metadata['comment']
    description = description + u'}}\n'
    description = description + u'|date='
    if metadata.get('imagetaken') and not metadata.get('imagetaken')==u'0000-00-00':
	description = description + metadata.get('imagetaken').replace(u'-00', u'') + u'\n'
    else:
	description = description + u'{{Unknown}}\n'
    description = description + u'|source=From [http://www.geograph.org.uk/photo/' + str(metadata.get('id')) + u' geograph.org.uk]\n'
    description = description + u'|author=[http://www.geograph.org.uk/profile/' + str(metadata.get('user_id')) + u' ' + metadata.get('realname') + u']\n'
    description = description + u'|permission=\n'
    description = description + u'|other_versions=\n'
    description = description + u'}}\n'
    # Location, add heading
    description = description + u'{{Location dec|' + str(metadata.get('wgs84_lat'))
    description = description + u'|' + str(metadata.get('wgs84_long'))
    # ADD HEADING HERE
    if not metadata.get('view_direction') == -1:
	description = description + u'|heading:' + str(metadata.get('view_direction'))
    description = description + u'}}\n'
    description = description + u'\n'
    description = description + u'== {{int:license}} ==\n'
    description = description + u'{{Geograph|' + str(metadata.get('id'))
    description = description + u'|' + metadata.get('realname') +'}}\n'
    description = description + u'\n'

    return description

def getCategories(metadata, cursor, cursor2):
    '''
    Produce one or more suitable Commons categories based on the metadata
    '''
    result = u''
    locationList =getExtendedFindNearby(metadata.get('wgs84_lat'), metadata.get('wgs84_long')) 

    for i in range(0, len(locationList)):
	#First try to get the location category based on the id
	category = getCategoryByGeonameId(locationList[i].get('geonameId'), cursor)
	if category:
	    #print locationList[i].get('geonameId') + u' - ' + category
	    locationList[i]['category'] = category
	#Second try to get the location category based on the name
	else:
	    if i > 1:
		category = getCategoryByName(name=locationList[i]['name'], parent=locationList[i-1]['name'], grandparent=locationList[i-2]['name'], cursor2=cursor2)
	    elif i > 0:
		category = getCategoryByName(name=locationList[i]['name'], parent=locationList[i-1]['name'], cursor2=cursor2)
	    else:
		category = getCategoryByName(name=locationList[i]['name'], cursor2=cursor2)
	    locationList[i]['category'] = category
	    #print locationList[i].get('geonameId')
	#print locationList[i].get('geonameId') + u' - ' + locationList[i].get('category')
    categories = []
    for location in locationList:
	if location.get('category') and not location.get('category')==u'':
	    categories.append(location.get('category')) 
    #Third try to get a topic category
    topicCategories = getTopicCategories(metadata.get('imageclass'), categories, cursor, cursor2)

    for topic in topicCategories:
	if not topic==u'':
	    topic = topic.replace(u'_', u' ').strip()
	    categories.append(topic)
    #categories.extend(topicCategories)

    if categories:
	result = u'{{Check categories-Geograph|year={{subst:CURRENTYEAR}}|month={{subst:CURRENTMONTHNAME}}|day={{subst:CURRENTDAY}}|lat=' + str(metadata.get('wgs84_lat'))  + u'|lon=' + str(metadata.get('wgs84_long'))  + u'|Geographcategory=' + metadata.get('imageclass')  + '}}\n'
	categories = filterCategories(categories, cursor2)
	for category in categories:
	    if category:
		result = result + u'[[Category:' + category.replace(u'_', u' ') + u']]\n'
    else:
	result = u'{{Subst:Unc}}'
    return result

def getExtendedFindNearby(lat, lng):
    '''
    Get the result from http://ws.geonames.org/extendedFindNearby
    and put it in a list of dictionaries to play around with
    '''
    result = [] 
    gotInfo = False
    parameters = urllib.urlencode({'lat' : lat, 'lng' : lng})
    while(not gotInfo):
	try:
	    page = urllib.urlopen("http://ws.geonames.org/extendedFindNearby?%s" % parameters)
	    et = xml.etree.ElementTree.parse(page)
	    gotInfo=True
        except IOError:
            wikipedia.output(u'Got an IOError, let\'s try again')
	    time.sleep(30)
        except socket.timeout:
            wikipedia.output(u'Got a timeout, let\'s try again')
	    time.sleep(30)
	    
    for geoname in et.getroot().getchildren():
	geonamedict = {}
	if geoname.tag=='geoname':
	    for element in geoname.getchildren():
		geonamedict[element.tag]=element.text
	    result.append(geonamedict)
    #print result
    return result

def getCategoryByGeonameId(geonameId, cursor):
    '''
    Return the name of a category based on a geonameId
    '''
    result = u''
    query = u"SELECT category from geonames WHERE geonameId=%s LIMIT 1"
    cursor.execute(query, (geonameId,))
    row = cursor.fetchone()
    if row:
	(result,) = row

    return result

def getCategoryByName(name, parent=u'', grandparent=u'', cursor2=None):

    if not parent==u'':
	work = name.strip() + u',_' + parent.strip()
	if categoryExists(work, cursor2):
	    return work
    if not grandparent==u'':
        work = name.strip() + u',_' + grandparent.strip()
        if categoryExists(work, cursor2):
            return work
    work = name.strip()
    if categoryExists(work, cursor2):
	return work

    return u''
    '''
    # Try simple name
    page = wikipedia.Page(title=u'Category:' + name.strip(), site = site)
    if page.exists():
	return page.titleWithoutNamespace()
    elif not parent==u'':
	page = wikipedia.Page(title=u'Category:' + name.strip() + u',_' + parent.strip(), site = site)
	if page.exists():
	    return page.titleWithoutNamespace()
    if not grandparent==u'':
	page = wikipedia.Page(title=u'Category:' + name.strip() + u',_' + grandparent.strip(), site= site)
	if page.exists():
	    return page.titleWithoutNamespace()

    return u''
    '''
def getTopicCategories(topic, categories, cursor, cursor2):
    result = []
    commonsCategory = getGeographToCommonsCategory(topic, cursor)
    if not commonsCategory ==u'':
	subjects = [commonsCategory]
    else:
	subjects = [topic, topic + u's', topic + u'es']
    betweens = [u'', u' in', u' of', u' on']
    thes = [u' ', u' the ']
    workcategories = [u'']
    for cat in categories:
	workcategories.append(cat)
    for subject in subjects:
	for between in betweens:
	    for the in thes:
		for category in workcategories:
		    work = subject + between + the + category
		    if categoryExists(work, cursor2):
			result.append(work)

    return result

def getGeographToCommonsCategory(topic, cursor):
    result = u''
    topic = topic.strip().replace(u' ', u'_')
    query = u"SELECT commons FROM categories WHERE geograph=%s LIMIT 1"
    cursor.execute(query, (topic,))
    row = cursor.fetchone()
    if row: 
	(result,) = row

    return result

def categoryExists(category, cursor2):
    category = category.strip()
    category = category.replace(' ', '_')
    query = u"SELECT * FROM cats WHERE child=%s LIMIT 1"
    #print query, (category,)

    cursor2.execute(query, (category,))
    row = cursor2.fetchone()
    if row:
	return True
    return False

def filterCategories(categories, cursor2):
    '''
    Filter the categories
    '''
    #First filter the parents to quickly reduce the number of categories
    if len(categories) > 1:
	result = filterParents(categories, cursor2)
    else:
	result = categories
    #Remove disambiguation categories
    result = imagerecat.filterDisambiguation(result)
    #And follow the redirects
    result = imagerecat.followRedirects(result)
    #And filter again for parents now we followed the redirects
    if len(result) > 1:
	result = filterParents(result, cursor2)
    return result

def filterParents(categories, cursor2):
    '''
    Filter out overcategorization.
    This is a python version of http://toolserver.org/~multichill/filtercats.php
    '''
    result = []
    query = u"SELECT c1.parent AS c1p, c2.parent AS c2p, c3.parent AS c3p, c4.parent AS c4p, c5.parent AS c5p, c6.parent AS c6p FROM cats AS c1 JOIN cats AS c2 ON c1.parent=c2.child JOIN cats AS c3 ON c2.parent=c3.child JOIN cats AS c4 ON c3.parent=c4.child JOIN cats AS c5 ON c4.parent=c5.child JOIN cats AS c6 ON c5.parent=c6.child WHERE "
    for i in range(0, len(categories)):
	categories[i] = categories[i].replace(u' ', u'_')
	query = query + u"c1.child='" + categories[i].replace(u"\'", "\\'") + u"'" 
	if(i+1 < len(categories)):
	     query = query + u" OR "

    #print query
    cursor2.execute(query)

    parentCats = set()
    while True:
	try:
	    row = cursor2.fetchone()
	    (c1p, c2p, c3p, c4p, c5p, c6p)= row
	    parentCats.add(c1p)
            parentCats.add(c2p)
            parentCats.add(c3p)
            parentCats.add(c4p)
            parentCats.add(c5p)
            parentCats.add(c6p)
	except TypeError:
	    #No more results
	    break
    #print parentCats
    for currentCat in categories:
	if not currentCat in parentCats and not currentCat in result:
	    result.append(currentCat) 

    return result

def getTitle(metadata):
    '''
    Build a valid title for the image to be uploaded to.
    '''
    title = metadata.get('title') + u' - geograph.org.uk - ' + str(metadata.get('id'))

    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title =  re.sub(u"[&]", u"and", title)
    title = re.sub(u"[#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")   
    
    return title
        
def getMetadata(fileId, cursor):
    result = {}
    query = u"SELECT user_id, realname, title, imagetaken, grid_reference, x, y, wgs84_lat, wgs84_long, imageclass, comment, view_direction FROM gridimage_base LEFT JOIN gridimage_text ON gridimage_base.gridimage_id=gridimage_text.gridimage_id LEFT JOIN gridimage_geo ON gridimage_base.gridimage_id=gridimage_geo.gridimage_id WHERE gridimage_base.gridimage_id=%s LIMIT 1"
    cursor.execute(query, (fileId,))
    row = cursor.fetchone()
    if row:
	result['id'] = fileId
	(result['user_id'],
	 result['realname'],
	 result['title'],
	 result['imagetaken'],
	 result['grid_reference'],
	 result['x'],
	 result['y'],
	 result['wgs84_lat'],
	 result['wgs84_long'],
	 result['imageclass'],
	 result['comment'],
	 result['view_direction']) = row
	#print result

    return result

def getImagesToCorrect(cursor):
    result = []
    '''
    query = u"""SELECT CONCAT('File:', page_title) AS page_title, REPLACE(el_to, 'http://www.geograph.org.uk/photo/', '') AS fileId FROM page
JOIN externallinks ON page_id=el_from
WHERE page_namespace=6 AND page_is_redirect=0
AND el_to LIKE 'http://www.geograph.org.uk/photo/%'
AND NOT EXISTS(
SELECT * FROM templatelinks 
WHERE page_id=tl_from AND tl_namespace=10 AND tl_title='Geograph')"""
    '''
    query = u"""SELECT CONCAT('File:', page_title) AS page_title, REPLACE(el_to, 'http://www.geograph.org.uk/photo/', '') AS fileId FROM page
JOIN externallinks ON page_id=el_from
JOIN categorylinks ON page_id=cl_from
WHERE page_namespace=6 AND page_is_redirect=0
AND el_to LIKE 'http://www.geograph.org.uk/photo/%'
AND cl_to='Images_from_the_Geograph_British_Isles_project_with_broken_templates'"""

    cursor.execute(query)
    #row = cursor.fetchone()
    #print row

    result = cursor.fetchall()
    '''
    while True:
        try:
            row = cursor.fetchone()
            #(page, fileId)= row
	    print row
	    result.append(row)
        except TypeError:
            #No more results
            break
    '''
    return result

def main(args):
    '''
    Main loop.
    '''
    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)

    conn = None
    cursor = None
    (conn, cursor) = connectDatabase()

    conn2 = None
    cursor2 = None
    (conn2, cursor2) = connectDatabase2('commonswiki-p.db.toolserver.org', u'commonswiki_p')

    imageSet = getImagesToCorrect(cursor2)
    #print imageSet
    for (pageName, fileId) in imageSet:
	wikipedia.output(pageName)
	if not pageName==u'' and not fileId==u'':
	    #Get page contents
	    page = wikipedia.Page(site, pageName)
	    if page.exists():
		categories = page.categories()

		#Get metadata
		metadata = getMetadata(fileId, cursor)

		#Check if we got metadata
		if metadata:
		    #Get description
		    description = getDescription(metadata)

		    description = wikipedia.replaceCategoryLinks(description, categories, site)
		    comment= u'Fixing description of Geograph image with broken template'
		    wikipedia.output(description)
		    page.put(description, comment)
 
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
