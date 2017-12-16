from esUrlParse import parseUrl
from judgments import Judgment, judgmentsFromFile, judgmentsToFile
from elasticsearch import Elasticsearch, TransportError
import json

def formatSearch(keywords):
    from jinja2 import Template
    template = Template(open("rateSearch.json.jinja").read())
    jsonStr = template.render(keywords=keywords)
    return json.loads(jsonStr)

def getPotentialResults(esUrl, keywords):
    (esUrl, index, searchType) = parseUrl(esUrl)
    es = Elasticsearch(esUrl)

    query = formatSearch(keywords)
    try:
        print("Query %s" % json.dumps(query))
        results = es.search(index=index, body=query)
        return results['hits']['hits']
    except TransportError as e:
        print("Query %s" % json.dumps(query))
        print("Query Error: %s " % e.error)
        print("More Info  : %s " % e.info)
        raise e



def gradeResults(results, keywords, qid):
    titleField = 'title'
    overviewField = 'overview'
    ratings = []
    print("Rating %s results" % len(results))
    for result in results:
        grade = None
        if 'fields' not in result:
            if '_source' in result:
                result['fields'] = result['_source']
        if 'fields' in result:
            print("")
            print("")
            print("## %s %s " % (result['fields'][titleField], result['_id']))
            print("")
            print("   %s " % result['fields'][overviewField])
            while grade not in ["0", "1", "2", "3", "4"]:
                grade = input("Rate this shiznit (0-4) ")
            judgment = Judgment(int(grade), qid=qid, keywords=keywords, docId=result['_id'])
            ratings.append(judgment)

    return ratings


def loadJudgments(judgFile):
    currJudgments = []
    existingKws = set()
    lastQid = 0
    try:
        currJudgments = [judg for judg in judgmentsFromFile(judgFile)]
        existingKws = set([judg.keywords for judg in currJudgments])
        lastQid = currJudgments[-1].qid
    except FileNotFoundError:
        pass

    return (currJudgments, existingKws, lastQid)


def handleKeywords(inputKws, currJudgments):

    keywordsWithExpansion = inputKws.split(';')
    keywordsWithSearchInstead = inputKws.split(';;')
    keywords = keywordsWithExpansion[0]
    searchWith = keywords
    if (len(keywordsWithExpansion) > 1):
        searchWith += " %s" % keywordsWithExpansion[1]
    if (len(keywordsWithSearchInstead) > 1):
        searchWith = keywordsWithSearchInstead[1]

    existingQid = -1
    thisQueryJudgments = []
    if keywords in existingKws:
        for judgment in currJudgments:
            if judgment.keywords == keywords:
                thisQueryJudgments.append(judgment)
                existingQid = judgment.qid

    return keywords, searchWith, thisQueryJudgments, existingQid


def foldInNewRatings(fullJudgments, origJudgments, newJudgs):
    for newJudg in newJudgs:
        wasAnUpdate = False
        for origJudg in origJudgments:
            if (origJudg.sameQueryAndDoc(newJudg)):
                origJudg.grade = newJudg.grade
                wasAnUpdate = True
        if not wasAnUpdate:
            fullJudgments.append(newJudg)



if __name__ == "__main__":
    """ Usage python rateShit.py esURL ratingsFileName """
    from sys import argv

    judgFile = argv[2]
    fullJudgments, existingKws, lastQid = loadJudgments(judgFile)

    keywords = "-"
    newQid = lastQid + 1
    while len(keywords) > 0:
        inputKws = input("Enter the Keywords ('GTFO' to exit) ")

        if inputKws == "GTFO":
            break

        keywords, searchWith, origQueryJudgments, existingQid = handleKeywords(inputKws, fullJudgments)
        currQid = 0
        if existingQid > 0:
            currQid = existingQid
            print("Updating judgments for qid:%s" % currQid)
        else:
            currQid = newQid
            newQid += 1

        results = getPotentialResults(argv[1], searchWith)
        newQueryJudgments = gradeResults(results, keywords, currQid)

        foldInNewRatings(fullJudgments, origQueryJudgments, newQueryJudgments)

    judgmentsToFile(judgFile, fullJudgments)
