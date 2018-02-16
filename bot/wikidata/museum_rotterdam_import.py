#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Museum Rotterdam to Wikidata.

Using the v2 Europeana api, see
http://www.europeana.eu/portal/en/search?q=what%3A%22schilderij%22&f[DATA_PROVIDER][]=Museum+Rotterdam (broken now)
https://www.europeana.eu/api/v2/search.json?wskey=1hfhGH67Jhs&query=DATA_PROVIDER%3A(%22Museum%20Rotterdam%22)%20AND%20what%3A(*schilderij*)

This bot uses artdatabot to upload it to Wikidata

Europeana doesn't seem to contain all the works so might have to redo this based on the museum website.

"""
import artdatabot
import pywikibot
import requests
import re

def getRotterdamGenerator():
    """
    Generator to return Museum Rotterdam paintings
    
    """
    basesearchurl = u'http://www.europeana.eu/api/v2/search.json?wskey=1hfhGH67Jhs&profile=minimal&start=%s&rows=%s&query=DATA_PROVIDER%%3A(%%22Museum%%20Rotterdam%%22)%%20AND%%20what%%3A(*schilderij*)'
    start = 1
    end = 902
    rows = 50

    isfreetext = u'<strong>Beeldrechten:</strong> <a href="https://creativecommons.org/publicdomain/mark/1.0/deed.nl"'

    for i in range (start, end, rows):
        searchUrl = basesearchurl % (i, rows)
        print (searchUrl)
        searchPage = requests.get(searchUrl)
        searchJson = searchPage.json()

        for item in searchJson.get(u'items'):
            itemurl = item.get('link')
            print (itemurl)

            itemPage = requests.get(itemurl)
            itemJson = itemPage.json()
            metadata = {}

            metadata['collectionqid'] = u'Q2130225'
            metadata['collectionshort'] = u'Museum Rotterdam'
            metadata['locationqid'] = u'Q2130225'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['refurl'] = itemJson.get('object').get('europeanaAggregation').get(u'edmLandingPage')
            metadata['url'] = itemJson.get('object').get('aggregations')[0].get(u'webResources')[0].get('about')

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = itemJson.get('object').get('aggregations')[0].get('about').replace(u'/aggregation/provider/2021609/objecten_',u'').replace(u'_', u'-')
            metadata['idpid'] = u'P217'

            museumpage = requests.get(metadata['url'])
            if u'-' in metadata['id'] and u'Pagina niet gevonden' in museumpage.text:
                print u'Pagina niet gevonden'
                newurl = metadata['url'] + u'-B'
                newid =  metadata['id'] + u'-B'
                print newurl
                print newid
                museumpage = requests.get(newurl)
                if u'content="Museum Rotterdam - van de stad">' in museumpage.text:
                    print u'Gevonden'
                    metadata['url'] = newurl
                    metadata['id'] = newid

            title = itemJson.get('object').get('proxies')[0].get(u'dcTitle').get('def')[0]
            metadata['title'] = { u'nl' : title,
                                }
            if itemJson.get('object').get('proxies')[0].get(u'dcCreator'):
                metadata['creatorname'] = itemJson.get('object').get('proxies')[0].get(u'dcCreator').get('def')[0]

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            dimensions = itemJson.get('object').get('proxies')[0].get(u'dcFormat').get('def')[0]
            regex_2d = u'^hg (?P<height>\d+(,\d+)?) / br (?P<width>\d+(,\d+)?)$'
            match_2d = re.match(regex_2d, dimensions)
            if match_2d:
                metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            metadata['inception'] = itemJson.get('object').get('proxies')[0].get(u'dcDate').get('def')[0]

            if itemJson.get('object').get('proxies')[0].get(u'dctermsMedium') and \
               itemJson.get('object').get('proxies')[0].get(u'dctermsMedium').get('def')[0] == u'olieverf, linnen':
                # FIXME : This will only catch oil on canvas
                metadata['medium'] = u'oil on canvas'
            if itemJson.get('object').get('aggregations')[0].get('edmIsShownBy'):
                if isfreetext in museumpage.text:
                    metadata[u'imageurl'] = itemJson.get('object').get('aggregations')[0].get('edmIsShownBy')
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageurllicense'] = u'Q6938433' # cc-zero

            yield metadata

    return
    
def main():
    dictGen = getRotterdamGenerator()

    #for painting in dictGen:
    #     print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    artDataBot.run()

if __name__ == "__main__":
    main()
