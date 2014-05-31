#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A program do generate descriptions for KIT (Tropenmuseum) images and to upload them right away.

'''
import sys, os.path, glob, re, hashlib, base64
import pyodbc
import wikipedia, config, query, upload, csv
import flickrripper


def generateDescription(baseFilename, database):
    '''
    Generate a description for a file
    '''

    record=database.get(baseFilename)

    description = u'{{subst:User:Multichill/Spaarnestad\n'
    description = description + u'|POLITICUS=%s\n' % (unicode(record[0], 'utf-8'),)
    description = description + u'|FOTONUMMER=%s\n' % (unicode(record[1], 'utf-8'),)
    description = description + u'|OMSCHRIJVING=%s\n' % (unicode(record[2], 'utf-8'),)
    description = description + u'|CREDITLINE=%s\n' % (unicode(record[3], 'utf-8'),)
    description = description + u'|PLAATS=%s\n' % (unicode(record[4], 'utf-8'),)
    description = description + u'|DATUM=%s\n' % (unicode(record[5], 'utf-8'),)
    description = description + u'|COLLECTIE=%s\n' % (unicode(record[6], 'utf-8'),)
    description = description + u'}}\n'
    
    

    #Maybe add location

    #Add politici
    politici = unicode(record[0], 'utf-8')
    for politicus in politici.split(u'|'):
        description = description + u'[[Category:Images from Nationaal Archief, politicus %s]]\n' % (politicus,)

    locaties = unicode(record[4], 'utf-8').strip()
    if locaties:
        for locatie in locaties.split(u'|'):
            description = description + u'[[Category:Images from Nationaal Archief, locatie %s]]\n' % (locatie,)
        
    return description
    
def findDuplicateImages(filename):
    '''
    Takes the photo, calculates the SHA1 hash and asks the mediawiki api for a list of duplicates.

    TODO: Add exception handling, fix site thing
    '''
    f = open(filename, 'rb')
    
    result = []
    hashObject = hashlib.sha1()
    hashObject.update(f.read(-1)) 
    #f.close()
    sha1Hash = base64.b16encode(hashObject.digest())
    
    params = {
    'action'    : 'query',
        'list'      : 'allimages',
        'aisha1'    : sha1Hash,
        'aiprop'    : '',
    }
    data = query.GetData(params, site=wikipedia.getSite(), useAPI = True, encodeTitle = False)

    for image in data['query']['allimages']:
        result.append(image['name'])
    return result

def getTitle(baseFilename, database):
    title = u''
    
    record=database.get(baseFilename)
    politici = unicode(record[0], 'utf-8')
    for politicus in politici.split(u'|'):
        if politicus.strip():
            title = title + u'%s - ' % (politicus.strip(),)

    title = title + u'%s.jpg' % (baseFilename,)
    return flickrripper.cleanUpTitle(title)


def main(args):


    directory = u'D:/Wikipedia/nationaal archief/WeTransfer-4C9iKiKK/'
    csvFile = u'D:/Wikipedia/nationaal archief/WeTransfer-4C9iKiKK/memorixwikipol1.csv'

    database = {}

    reader = csv.reader(open(csvFile, "rb"))
    for row in reader:
        database[row[1]] = row
        #print row[1]
        #        wikipedia.output(row)

    if os.path.isdir(directory):
        for filename in glob.glob(directory + "/*.jpg"):
            #print filename
            duplicates = findDuplicateImages(filename)
            if duplicates:
                wikipedia.output(u'Found duplicate image at %s' % duplicates.pop())
            else:
                print 'bla'
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)
                baseFilename, extension = os.path.splitext(basename)

                description = generateDescription(baseFilename, database)
                title = getTitle(baseFilename, database)

                #wikipedia.output(description)
                #wikipedia.output(title)
                bot = upload.UploadRobot(url=filename.decode(sys.getfilesystemencoding()), description=description, useFilename=title, keepFilename=True, verifyDescription=False)
                bot.run()

    
    
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print "All done!"
